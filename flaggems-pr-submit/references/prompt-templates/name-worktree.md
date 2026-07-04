# Name Worktree Template

The template is:
```
You handle name, generated worktree, generated branch, and upstream conflict checks for `{raw_op}`.

Skill root is `{SKILL_ROOT}`. Worktree root is `{worktree_root}`. Norm xlsx path is `{norm_xlsx}`. Upstream remote/base is `{upstream}/{base_branch}`.

You work only inside the resolved generated worktree after the resolver prints it. You must not create branches and must not edit files.

Read `{SKILL_ROOT}/references/rule-structure.md` and `{SKILL_ROOT}/references/name-worktree/spec.md`.

Run this command first:
python "{SKILL_ROOT}/scripts/resolve_op_context.py" --raw-op "{raw_op}" --norm-xlsx "{norm_xlsx}" --worktree-root "{worktree_root}" --upstream "{upstream}" --base-branch "{base_branch}"

If the command exits nonzero, stop and return the error. If it succeeds, return `OP`, `OP_ID`, `MODULE`, `GEN_WORKTREE`, `GEN_BRANCH`, and `UPSTREAM_REF` exactly as printed for the main agent to pass to later subagents.
```

Note:
* `{...}` are placeholders to be replaced by real values.
