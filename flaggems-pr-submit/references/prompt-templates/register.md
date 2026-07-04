# Registration Template

Use this template for the register subagent.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{UPSTREAM_REF}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Required reference files:

- `{SKILL_ROOT}/references/rule-structure.md`
- `{SKILL_ROOT}/references/register/spec.md`
- `{SKILL_ROOT}/scripts/operator_static_gate.py`

Run this static gate after registration edits:

```bash
python "{SKILL_ROOT}/scripts/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Follow `register/spec.md`, including embedded registration soft rules. Return changed files, registration surfaces touched, static gate command/result, unresolved inconsistencies, and blocking issues.

Note: `{...}` are placeholders to be replaced by real values.
