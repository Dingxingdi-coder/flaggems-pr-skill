# Name and Worktree Spec

Applies to: name-worktree subagent.

This stage is a mechanical gate. Run `scripts/resolve_op_context.py` first and treat a nonzero exit as blocking.

## Resolver command

Run from any directory:

```bash
python "{SKILL_ROOT}/scripts/resolve_op_context.py" --raw-op "{raw_op}" --norm-xlsx "{norm_xlsx}" --worktree-root "{worktree_root}" --upstream "{upstream}" --base-branch "{base_branch}"
```

The script prints these values for the main agent:

- `OP`: normalized operator name.
- `OP_ID`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `MODULE`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `GEN_WORKTREE`: generated worktree path.
- `GEN_BRANCH`: generated branch name.
- `UPSTREAM_REF`: fetched upstream ref used by later static gates.

## Scripted hard checks

The resolver covers:

- strip optional `aten::` prefix from the raw operator name;
- lookup in `规范名.xlsx`, requiring a `算子名` column and a column whose header contains `规范命名`;
- special-op mapping from normalized name to module and public op id;
- generated worktree resolution under `<worktree_root>/gen-<op>` or `<worktree_root>/gen-<op_id>`;
- generated branch check against `gen-<op>` or `gen-<op_id>`;
- upstream fetch;
- upstream conflict check for `src/flag_gems/ops/<module>.py` and yaml `id: <op_id>`.

## Special ops

Special-op mapping is a mechanical rule. The source of truth is the `SPECIAL_OPS` table in `scripts/resolve_op_context.py`. Update it there only; do not maintain a second mapping table in prose.

## Manual fallback

Do not manually redo resolver logic. If the script fails because required input is missing, return the missing input. If the script fails because of a real conflict or invalid worktree, stop the operator.
