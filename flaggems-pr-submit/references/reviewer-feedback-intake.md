# Reviewer Feedback Intake

This document defines the nightly maintenance loop for evolving the skill from real `[KernelGen][Nvidia]` review feedback in `flagos-ai/FlagGems`.

## Nightly collection command

Run from a persistent maintenance checkout or CI job where `gh auth status` succeeds:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py \
  --repo flagos-ai/FlagGems \
  --state-file .cache/kernelgen-review-state.json \
  --output .cache/kernelgen-review-index.json
```

The collector skips PR-author comments and GitHub bot accounts by default so the output is closer to reviewer feedback. Use `--include-pr-author` only when auditing author replies, and use `--include-bots` only when bot comments are intentionally part of the triage. `--ignore-author <login>` can still be repeated for additional noise sources.

The first run should normally establish a baseline instead of emitting all historical comments:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py \
  --repo flagos-ai/FlagGems \
  --state-file .cache/kernelgen-review-state.json \
  --output .cache/kernelgen-review-index.json \
  --baseline
```

## What the collector does

`collect_kernelgen_review_delta.py` searches PRs in `flagos-ai/FlagGems`, keeps only titles starting with `[KernelGen][Nvidia]`, fetches issue comments, inline review comments, and review submission bodies, compares them with the prior state file, and emits a lightweight JSON index of PRs with new or edited reviewer-signal comments.

The output intentionally does not copy reviewer comment bodies. For each changed PR it includes the PR URL, the first changed comment URL/time, a changed-comment count, changed-comment URLs, and non-body metadata for every changed comment. The maintenance agent should open the live PR page and read the current context directly.

The state file is operational data. Do not commit it to the skill repository. Store it as a CI artifact, cache, or file in the maintenance checkout.

## Output contract

The output JSON keeps backward-compatible summary keys and adds enough metadata for a networked maintenance agent to prioritize and route review changes before opening GitHub.

Top-level keys include:

- `repo`, `run_at`, `since`, and `baseline`;
- `filters`, including `ignored_authors`, `include_pr_author`, `include_bots`, `include_edits`, and `lookback_hours`;
- `scanned_prs`, `fetched_comment_count`, `scanned_comments`, `ignored_comment_count`, `changed_pr_count`, and `changed_comment_count`;
- `items`, one entry per PR with changed comments.

Each `items[]` entry includes:

- `pr_number`, `pr_title`, `pr_url`, and `pr_author`;
- `first_changed_comment_url` and `first_changed_at`;
- `changed_comment_count`, `changed_comment_urls`, and `change_types`;
- `changed_comments`, a list of non-body metadata objects.

Each `changed_comments[]` metadata object includes `url`, `change_type`, `kind`, `author`, `created_at`, `updated_at`, and `is_pr_author`. Inline review comments may also include `path` and `line`; review submission bodies may include `state`. The collector must not emit comment `body` text in this index.

## Triage loop

For every emitted PR item:

1. Open `first_changed_comment_url` or `pr_url` and read the live PR context from that point.
2. Confirm that the changed comment is reviewer signal, not author explanation, CI noise, or a duplicate discussion.
3. Identify the scene: implementation, tests, benchmark, registration/yaml, PR body, or review response.
4. Identify the concrete fix pattern. Prefer the fix that would have prevented the comment before PR creation.
5. Classify the rule.
   - Hard: deterministic from local files, git diff, normalized operator context, command output, or PR metadata.
   - Soft: requires semantic code understanding, reviewer preference interpretation, or risk judgment.
6. Apply the update directly to the source of truth.
   - Hard rule: edit the owning script, add a stable rule ID to that script's `RULES` list, implement the check, and ensure failures use `ERROR[<RULE_ID>]`.
   - Soft rule: append one structured entry directly to the existing spec that owns the scene.
7. Check stage ownership in `references/constraint-map.md`; update it only when the new rule changes which subagent is responsible.
8. Validate the skill change by running `--list-rules` for edited hard-rule scripts and by running:

```bash
python flaggems-pr-submit/scripts/skill_meta_gate.py
```

Also check that all relevant prompt templates already force subagents to read the updated spec.

## Soft-rule destinations

Use these direct-to-spec destinations:

| Scene | Destination |
|---|---|
| implementation semantics, wrapper behavior, dtype guards, torch fallback, generated dead code | `references/implementation-review/spec.md` |
| accuracy-test semantics, benchmark fairness, benchmark shape coverage, zero cases, speedup interpretation | `references/shared/test-benchmark.md` |
| registration surfaces, yaml metadata, exported wrapper consistency | `references/register/spec.md` |
| final validation, staging, commit message, PR body, tested-on data, review-response behavior | `references/final-validation/spec.md` |

Embedded soft-rule entries must use the `SOFT-YYYYMMDD-<short-slug>` format documented in `references/soft-constraints.md`.

## Scheduled workflow

The repository may run `.github/workflows/kernelgen-review-intake.yml` every day at 14:00 UTC, which is 23:00 Asia/Tokyo. The workflow restores `.cache/kernelgen-review-state.json`, runs the collector, runs `skill_meta_gate.py`, and uploads `.cache/kernelgen-review-index.json` as an artifact for the maintenance agent.

GitHub scheduled workflows run only when the workflow file exists on the repository default branch. While this workflow exists only on a development branch, use the command above from a maintenance checkout; after promotion to the production/default branch, the nightly schedule becomes active.

The workflow only collects and validates intake data. It does not modify the skill automatically; a networked maintenance agent should consume the artifact, open the referenced PR comments, classify the rule, update the skill, and run the meta gate before committing.

## Commit convention

Use a maintenance commit message that contains the source PR number and the rule class, for example:

```text
Add hard static rule for benchmark op_name drift from FlagGems PR #1234
```

or:

```text
Add soft benchmark rule from FlagGems PR #1234
```

The commit should include the collector output artifact or PR number in the message, not a long copied reviewer transcript.
