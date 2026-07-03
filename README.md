# flaggems-pr-skill

This repository contains the `flaggems-pr-submit` skill.

The current design is context-driven. The main agent creates a context JSON with `flaggems-pr-submit/scripts/context.py`, then dispatches one operator agent per operator. Each operator agent runs the full initial PR pipeline through `flaggems-pr-submit/scripts/submit_operator.py`.

Entry point: `flaggems-pr-submit/SKILL.md`.
