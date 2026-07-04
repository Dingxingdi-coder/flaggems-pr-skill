# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

Entry point: `flaggems-pr-submit/SKILL.md`.

Current design:

- the main agent still dispatches one operator-specific subagent sequence per generated `gen-*` worktree;
- mechanical hard constraints live in `flaggems-pr-submit/scripts/`, expose stable rule IDs, and are indexed by `flaggems-pr-submit/references/hard-constraints.md`;
- semantic soft constraints live in `flaggems-pr-submit/references/<subagent>/`, `flaggems-pr-submit/references/shared/`, and `flaggems-pr-submit/references/soft-constraints.md`;
- reviewer-derived soft rules are maintained in `flaggems-pr-submit/references/shared/reviewer-learned-rules.md` and promoted to scripts only when they become deterministic;
- nightly reviewer-feedback intake is documented in `flaggems-pr-submit/references/reviewer-feedback-intake.md` and supported by `flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py`.
