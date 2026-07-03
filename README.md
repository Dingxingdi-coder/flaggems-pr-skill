# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

The current design is document-only. The main agent infers context from the user request and working repository, then dispatches specialist subagents per operator. Subagents run project commands directly and follow the agent/spec documents under `flaggems-pr-submit/`.

Entry point: `flaggems-pr-submit/SKILL.md`.
