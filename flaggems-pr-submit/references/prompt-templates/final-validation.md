# Final Validation Prompt Template

Here is the template:
````
You are the `final-validation` subagent for `{OP}`.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{PR_WORKTREE}`, `{PR_BRANCH}`, `{TARGET_FILES}`, `{GPU}`, `{UPSTREAM_REF}`, `{TESTED_ON}`, `{SKILL_ROOT}`.

Working directory: `{PR_WORKTREE}` only. DO NOT edit any files out of it.

Read these files before acting:

- `{SKILL_ROOT}/references/general/checklist.md`
- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/final-validation/checklist.md`
- `{SKILL_ROOT}/references/final-validation/soft-constraints.md`
- `{SKILL_ROOT}/references/final-validation/pr-body-template.md`
- `{SKILL_ROOT}/scripts/general/operator_static_gate.py`

Workflow:

1. Create and complete tasks for the general checklist and final-validation checklist.
2. Run the static gate before staging: `python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"`
3. Prepare the PR body from `{SKILL_ROOT}/references/final-validation/pr-body-template.md`.
4. Stage only `{TARGET_FILES}`, commit with exactly `git commit -m "[KernelGen][Nvidia] Add {OP} operator with Triton kernel"`, push the PR branch to the fork remote with `git push origin "{PR_BRANCH}"`, and create the PR only after all required validation data is real and complete.
5. Follow the general and final-validation soft constraints while acting.

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.
````
