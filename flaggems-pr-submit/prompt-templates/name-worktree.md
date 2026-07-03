# Name Worktree Template

Fields: `{RAW_OP}`, `{REPO_DIR}`, `{WORKTREE_ROOT}`, `{NORM_XLSX}`, `{UPSTREAM_REMOTE}`, `{BASE_BRANCH}`.

Prompt to send: You handle name and worktree checks for `{RAW_OP}`. Read `references/name-worktree-spec.md`. Use repo `{REPO_DIR}`, worktree root `{WORKTREE_ROOT}`, norm xlsx `{NORM_XLSX}`, and upstream `{UPSTREAM_REMOTE}/{BASE_BRANCH}`. Find normalized op, op_id, module, and gen worktree. Stay inside the gen worktree except for upstream read-only checks. Do not create any branch. Return normalized names, worktree path, current branch, and conflict status.
