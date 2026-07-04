# Reviewer Feedback Intake

This document defines the nightly maintenance loop for evolving the skill from real `[KernelGen][Nvidia]` review feedback in `flagos-ai/FlagGems`.

## Nightly collection command

Run from a persistent maintenance checkout or CI job where `gh auth status` succeeds:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py \
  --repo flagos-ai/FlagGems \
  --state-file .cache/kernelgen-review-state.json \
  --output .cache/kernelgen-review-index.json \
  --ignore-author github-actions[bot]
```

The first run should normally establish a baseline instead of emitting all historical comments:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py \
  --repo flagos-ai/FlagGems \
  --state-file .cache/kernelgen-review-state.json \
  --output .cache/kernelgen-review-index.json \
  --baseline
```

## What the collector does

`collect_kernelgen_review_delta.py` searches PRs in `flagos-ai/FlagGems`, keeps only titles starting with `[KernelGen][Nvidia]`, fetches issue comments, inline review comments, and review submission bodies, compares them with the prior state file, and emits a lightweight JSON index of PRs with new or edited comments.

The output intentionally does not copy reviewer comment bodies. For each changed PR it includes the PR URL, the first changed comment URL/time, a changed-comment count, and changed-comment URLs. The maintenance agent should open the live PR page and read the current context directly.

The state file is operational data. Do not commit it to the skill repository. Store it as a CI artifact, cache, or file in the maintenance checkout.

## Triage loop

For every emitted PR item:

1. Open `first_changed_comment_url` or `pr_url` and read the live PR context from that point.
2. Identify the scene: implementation, tests, benchmark, registration/yaml, PR body, or review response.
3. Identify the concrete fix pattern. Prefer the fix that would have prevented the comment before PR creation.
4. Classify the rule.
   - Hard: deterministic from local files, git diff, normalized operator context, command output, or PR metadata.
   - Soft: requires semantic code understanding, reviewer preference interpretation, or risk judgment.
5. Apply the update.
   - Hard rule: add or promote it through `references/hard-constraints.md` and the owning script.
   - Soft rule: append one structured entry to `references/shared/reviewer-learned-rules.md`.
6. Check stage ownership in `references/constraint-map.md`; update it only when the new rule changes which subagent is responsible.
7. Validate the skill change by running `--list-rules` for edited hard-rule scripts and by checking that all relevant prompt templates already force subagents to read the updated reference file.

## Commit convention

Use a maintenance commit message that contains the source PR number and the rule class, for example:

```text
Add hard rule for benchmark op_name drift from FlagGems PR #1234
```

or:

```text
Add soft reviewer rule for probability-op validation from FlagGems PR #1234
```

The commit should include the collector output or PR number in the message, not a long copied reviewer transcript.
