# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

The current design is context-driven. The skill does not assume local workspace paths, GPU IDs, remotes, fork repository, upstream repository, or tested-on strings. A main agent first creates a context JSON with `flaggems-pr-submit/scripts/context.py`, then delegates each phase to a small agent document under `flaggems-pr-submit/agents/`.

Entry point: `flaggems-pr-submit/SKILL.md`.
