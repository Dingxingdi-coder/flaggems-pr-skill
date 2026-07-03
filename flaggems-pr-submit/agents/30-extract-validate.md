# Extract and Validate Agent

Scope: read `references/spec.md`, context JSON, `scripts/extract_operator.py`, and validation output.

Input: normalized `op` from preflight JSON and context JSON path.

Commands:

```bash
python <SKILL_DIR>/scripts/extract_operator.py --context <context.json> --op <op>
python <SKILL_DIR>/scripts/submit_operator.py <op> --context <context.json> --dry-run
```

Responsibilities:

- Extract the repaired worktree into the current `pr/<op>` branch.
- Confirm the diff is limited to the target operator's expected files.
- Run strict validation with `submit_operator.py --dry-run`.
- If extraction exposes implementation, test, or benchmark defects, report them so the worktree can be repaired and extracted again.

Expected files are the kernel, two registration files, test file, benchmark file, and `conf/operators.yaml`.

Stop if extraction fails, strict check fails, pre-commit fails, accuracy test fails, benchmark fails, parsed benchmark case count is zero, or the diff includes unrelated files.
