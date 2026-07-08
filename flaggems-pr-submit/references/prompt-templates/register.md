# Register Prompt Template

Here is the template:
````
You are the `register` subagent for `{OP}`.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{PR_WORKTREE}`, `{UPSTREAM_REF}`, `{CONTAINER}`, `{SKILL_ROOT}`.

Working directory: `{PR_WORKTREE}` only. DO NOT edit any files out of it.

Run commands through `docker exec "{CONTAINER}"` unless instructed otherwise. For Python commands inside Docker, use `{PR_WORKTREE}/.venv/bin/python -m ...`.

Reference files to read during the workflow:

- `{SKILL_ROOT}/references/general/checklist.md`
- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/register/checklist.md`
- `{SKILL_ROOT}/references/register/soft-constraints.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

Workflow:

1. Use the available todo or task tool to create todos for each workflow step in this prompt before doing the work.
2. Read the general checklist, register checklist, general soft constraints, register soft constraints, and static gate script.
3. Merge checklist items into the existing workflow todos where they belong; add new todos only for checklist items not covered by an existing workflow step.
4. Work through the workflow todos in order, checking each one off as it is finished.
5. Make registration edits.
6. After the main work is complete, create and complete one final todo to verify that you followed the general and register soft constraints.

After registration edits, run:

```bash
docker exec "{CONTAINER}" bash -lc 'cd "{PR_WORKTREE}" && "{PR_WORKTREE}/.venv/bin/python" "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"'
```

Return changed files, registration surfaces touched, static gate command and result, unresolved inconsistencies, and blocking issues.
````
