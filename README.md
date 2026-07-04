# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

Entry point: `flaggems-pr-submit/SKILL.md`.

Current design:

- the main agent still dispatches one operator-specific subagent sequence per generated `gen-*` worktree;
- mechanical hard rules live in `flaggems-pr-submit/scripts/` and are invoked by prompt templates;
- semantic review rules live in `flaggems-pr-submit/references/<subagent>/` and shared docs;
- reviewer-derived soft rules are maintained in `flaggems-pr-submit/references/shared/reviewer-learned-rules.md` and promoted to scripts only when they become deterministic.
