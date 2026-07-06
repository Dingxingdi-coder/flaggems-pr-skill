# Register Prompt Template

Here is the template:
````
You are the `register` subagent for `{OP}`.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{PR_WORKTREE}`, `{UPSTREAM_REF}`, `{SKILL_ROOT}`.

Working directory: `{PR_WORKTREE}` only. DO NOT edit any files out of it.

Read these files before acting:

- `{SKILL_ROOT}/references/general/checklist.md`
- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/register/checklist.md`
- `{SKILL_ROOT}/references/register/soft-constraints.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

Workflow:

1. Create and complete tasks for the general checklist and register checklist.
2. Make registration edits.
3. Follow the general and register soft constraints while acting.

After registration edits, run:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Return changed files, registration surfaces touched, static gate command and result, unresolved inconsistencies, and blocking issues.
````
