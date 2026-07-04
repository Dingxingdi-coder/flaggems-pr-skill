# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

Entry point: `flaggems-pr-submit/SKILL.md`.

Current design:

- the main agent still dispatches one operator-specific subagent sequence per generated `gen-*` worktree;
- mechanical hard constraints live only in `flaggems-pr-submit/scripts/`; each hard-rule script exposes stable rule IDs through `--list-rules`;
- semantic soft constraints live directly in existing stage and shared specs under `flaggems-pr-submit/references/`;
- reviewer-derived deterministic rules are promoted directly into the owning hard-rule script; reviewer-derived semantic rules are appended to the applicable existing spec instead of a central learned-rule ledger;
- nightly reviewer-feedback intake is documented in `flaggems-pr-submit/references/reviewer-feedback-intake.md` and supported by `flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py`;
- skill-maintenance consistency is checked by `flaggems-pr-submit/scripts/skill_meta_gate.py` so hard-rule scripts, prompt templates, embedded soft-rule entries, and reviewer-feedback intake docs do not drift.
