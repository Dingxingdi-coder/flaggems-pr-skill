# Register Prompt Template

You are the `register` subagent for `{OP}`.

You are a subagent. Do not read `SKILL.md`; this prompt contains your assignment.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{UPSTREAM_REF}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Read these files before acting:

- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/register/soft-constraints.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

After registration edits, run:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Follow the general and register soft constraints. Return changed files, registration surfaces touched, static gate command and result, unresolved inconsistencies, and blocking issues.

Note: `{...}` are placeholders replaced by the main agent.
