# Name and Branch Agent

Reads: `references/general-spec.md`, `references/name-branch-spec.md`, and context.

Purpose: prepare one normalized operator for work.

Tasks:

1. Map the raw operator name to the normalized operator name using the norm-name spreadsheet.
2. Derive `module` and `op_id`, including documented special cases.
3. Locate the worktree `gen-<op>` or `gen-<op_id>`.
4. Fetch the upstream base branch.
5. Verify upstream does not already contain the target kernel file or yaml id.
6. Create branch `pr/<op>` from the upstream base.

Return to the operator coordinator: normalized op, op id, module, worktree path, branch, and any stop reason.
