# Final Check Template

Use this template for the final-validation subagent.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{GPU}`, `{FORK_REMOTE}`, `{UPSTREAM_REPO}`, `{BASE_BRANCH}`, `{UPSTREAM_REF}`, `{TESTED_ON}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Required reference files:

- `{SKILL_ROOT}/references/rule-structure.md`
- `{SKILL_ROOT}/references/shared/test-benchmark.md`
- `{SKILL_ROOT}/references/final-validation/spec.md`
- `{SKILL_ROOT}/scripts/operator_static_gate.py`

Run this static gate before staging:

```bash
python "{SKILL_ROOT}/scripts/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Follow `final-validation/spec.md`, including embedded final soft rules. Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.

Note: `{...}` are placeholders to be replaced by real values.
