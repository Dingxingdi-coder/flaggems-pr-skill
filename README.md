# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

The current design is document-only. The main agent infers context from the user request and working repository, then sends filled prompt templates from `flaggems-pr-submit/references/prompt-templates/` to specialist subagents. Subagents run project commands directly and follow the stage-specific rules packaged under `flaggems-pr-submit/references/<subagent>/`.

Entry point: `flaggems-pr-submit/SKILL.md`.
