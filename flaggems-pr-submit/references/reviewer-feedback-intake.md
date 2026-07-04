# Reviewer Feedback Intake

Nightly intake collects new reviewer comments from `[KernelGen][Nvidia]` PRs in `flagos-ai/FlagGems`.

Command:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py --repo flagos-ai/FlagGems --state-file .cache/kernelgen-review-state.json --output .cache/kernelgen-review-index.json
```

Use `--baseline` on the first run. The collector output is an index only. It includes `changed_comments` metadata such as `url`, `change_type`, `kind`, `author`, `is_pr_author`, `path`, and `line`. It supports filters including `--include-pr-author` and `--include-bots`.

The maintenance agent must have network access. The index intentionally omits comment bodies, so the agent must open the live PR/comment URL before classifying a rule.

## Triage loop

1. Open the live PR/comment URL.
2. Confirm the comment is reviewer signal rather than author chatter, bot output, CI noise, or a one-off request.
3. Extract the scene, required behavior, and fix pattern.
4. Classify the rule as hard or soft.
5. Hard rule: update the owning script's `RULES` list and implementation.
6. Soft rule: append an embedded soft-rule entry to the existing spec file that owns the scene.
7. Run the edited hard-rule script with `--list-rules` when applicable, then run `python flaggems-pr-submit/scripts/skill_meta_gate.py`.

## Classification boundary

A rule is hard only when a script can detect the violation deterministically from local files, git metadata, normalized operator context, command output, or PR metadata with acceptably low false positives. Otherwise it is soft.

## Required triage record

For every changed reviewer comment that is not ignored, record this information in the maintenance summary or commit message:

```text
pr_number:
comment_url:
reviewer:
scene:
constraint_statement:
fix_pattern:
class: hard | soft
classification_reason:
target_file:
rule_id:
validation_commands:
```

## Soft-rule destinations

| Scene | Destination |
|---|---|
| implementation | `references/implementation-review/spec.md` |
| tests or benchmark | `references/shared/test-benchmark.md` |
| registration or yaml | `references/register/spec.md` |
| final checks or PR body | `references/final-validation/spec.md` |

Embedded soft-rule entries use the format documented in `references/soft-constraints.md`. Do not create a separate learned-rule ledger.
