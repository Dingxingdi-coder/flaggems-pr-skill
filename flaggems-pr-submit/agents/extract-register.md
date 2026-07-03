# Extract and Register Agent

Reads: `references/general-spec.md`, `references/extract-register-spec.md`, context, repaired worktree files, and PR branch files.

Purpose: transfer the repaired operator from worktree to the PR branch and register it.

Tasks:

1. Confirm current branch is `pr/<op>`.
2. Copy the repaired kernel into the target ops module path.
3. Create or append the target test file.
4. Create or append the target benchmark file.
5. Update the ops package import and export list.
6. Update top-level dispatch registration.
7. Update `conf/operators.yaml`.
8. Check id, mark, op_name, yaml for, registration, and exported wrapper alignment.
9. Check the diff contains only target operator files.

If this stage reveals a worktree implementation problem, return to the implementation review agent instead of patching a different implementation directly on the PR branch.
