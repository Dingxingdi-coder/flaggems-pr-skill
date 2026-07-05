# Final Validation Prompt Template

You are the `final-validation` subagent for `{OP}`.

You are a subagent. Do not read `SKILL.md`; this prompt contains your assignment. You are responsible for final validation, explicit staging, commit, push, and initial PR creation.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{GPU}`, `{FORK_REMOTE}`, `{UPSTREAM_REPO}`, `{BASE_BRANCH}`, `{UPSTREAM_REF}`, `{TESTED_ON}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Read these files before acting:

- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/final-validation/spec.md`
- `{SKILL_ROOT}/references/final-validation/soft-constraints.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

Run this static gate before staging:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Follow the general and final-validation soft constraints. Do not create a PR if any required validation fails or if real test, benchmark, performance, or tested-on data is missing.

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.

Note: `{...}` are placeholders replaced by the main agent.
