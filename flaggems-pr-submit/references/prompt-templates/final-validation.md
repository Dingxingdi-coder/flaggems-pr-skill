# Final Validation Prompt Template

Here is the template:
````
You are the `final-validation` subagent for `{OP}`.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{PR_WORKTREE}`, `{PR_BRANCH}`, `{TARGET_FILES}`, `{GPU}`, `{FORK_REMOTE}`, `{UPSTREAM_REF}`, `{TESTED_ON}`, `{SKILL_ROOT}`.

Working directory: `{PR_WORKTREE}` only. DO NOT edit any files out of it.

Read these files before acting:

- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/final-validation/soft-constraints.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

Run this static gate before staging:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Follow the general and final-validation soft constraints. Do not create a PR if any required validation fails or if real test, benchmark, performance, or tested-on data is missing.

Stage only `{TARGET_FILES}`. Do not use `git add -A` or `git add .`.

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.
````
