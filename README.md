# flaggems-pr-skill

This repository maintains the `flaggems-pr-submit` skill.

`flaggems-pr-submit/` is the formal skill directory. It is only for initial PR submission of FlagGems NVIDIA general operators generated from `gen-*` worktrees.

Top-level `scripts/` contains skill maintenance tools. These tools are not part of the runtime PR submission skill and must not be copied into `flaggems-pr-submit/`.

## Reviewer Delta

Make sure you login to GitHub CLI with `gh auth login` before running the collector.

Collect PRs that may contain new review signal:

```bash
python scripts/collect_kernelgen_review_delta.py --since 2026-07-04T00:00:00Z > ~/.cache/daily_collect.json
```

The collector uses the local `gh` CLI, queries open, closed, and merged PRs in `flagos-ai/FlagGems`, filters titles with `title.startswith("[KernelGen][Nvidia]")`, and prints only PR metadata for PRs with `updatedAt > --since`. It does not keep a state file, read comment bodies, classify reviewers, classify authors, or filter bots.

When the collector prints JSON, paste that JSON into the cloud daily evolution agent. When there are no matching updates, it prints:

```text
No [KernelGen][Nvidia] PRs updated after <since>.
```

## Daily Evolution Agent Prompt

Copy this prompt for the cloud agent, then paste the JSON output from `scripts/collect_kernelgen_review_delta.py`.

```text
You are maintaining the skill repository for `Dingxingdi-coder/flaggems-pr-submit`.

Do not use the `flaggems-pr-submit` skill. This is skill maintenance, not a FlagGems PR submission.

The user will paste JSON produced by `scripts/collect_kernelgen_review_delta.py`. Use the internet to open each listed PR in `flagos-ai/FlagGems`. Focus on review and discussion updates after `review_updates_after`, including newly added or edited discussion content. Decide for yourself which updates are effective reviewer feedback.

Only preserve constraints that generalize to future `[KernelGen][Nvidia]` PRs. Ignore one-off issues. Do not duplicate feedback already covered by existing constraints; improve an existing rule or script only when needed.

Classify before editing:

- hard vs soft;
- checklist vs soft when the rule belongs in a subagent reference;
- general vs a specific subagent stage.

A hard constraint must be stable, low false-positive and low false-negative, and mechanically checkable by a local script. Otherwise prefer a soft constraint.

Write checklist items for environment, code, validation-data, or registration consistency checks that a subagent must complete before acting.

Write soft constraints for behavioral limits a subagent must follow while acting.

Write checklist items only to one of these files:

- `flaggems-pr-submit/references/general/checklist.md`
- `flaggems-pr-submit/references/implementation-review/checklist.md`
- `flaggems-pr-submit/references/worktree-test-benchmark/checklist.md`
- `flaggems-pr-submit/references/register/checklist.md`
- `flaggems-pr-submit/references/final-validation/checklist.md`

Write soft constraints only to one of these files:

- `flaggems-pr-submit/references/general/soft-constraints.md`
- `flaggems-pr-submit/references/implementation-review/soft-constraints.md`
- `flaggems-pr-submit/references/worktree-test-benchmark/soft-constraints.md`
- `flaggems-pr-submit/references/register/soft-constraints.md`
- `flaggems-pr-submit/references/final-validation/soft-constraints.md`

Each soft constraint must be one clear actionable sentence. Do not include reviewer sources, examples, counterexamples, or long explanations in the soft-constraints files.

Write or modify hard constraints only in the owning runtime script under `flaggems-pr-submit/scripts/`. Hard-rule scripts should print direct, actionable error text; do not add rule IDs or metadata-only list commands.

Do not modify this README during daily maintenance unless the maintenance workflow itself changes.

When finished, run `python scripts/skill_meta_gate.py`.

Return a concise summary of the constraints changed.
```
