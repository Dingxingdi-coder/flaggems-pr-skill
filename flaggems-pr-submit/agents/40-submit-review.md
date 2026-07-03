# Submit Agent

Scope: read `references/spec.md`, context JSON, and `scripts/submit_operator.py`.

Input: normalized `op`, context JSON path, and mode.

Create command:

```bash
python <SKILL_DIR>/scripts/submit_operator.py <op> --context <context.json>
```

Push-only command:

```bash
python <SKILL_DIR>/scripts/submit_operator.py <op> --context <context.json> --push-only
```

Responsibilities:

- Run all strict gates again.
- Commit only files selected by the script.
- Push to the context-provided fork remote.
- Create the PR against the context-provided upstream repo and base branch unless using push-only mode.
- Backfill the PR URL into the context-provided norm xlsx.
- Report changes and validation results.

Stop if validation fails, benchmark data is missing, PR body is incomplete, push fails, PR creation fails, or backfill cannot be completed.
