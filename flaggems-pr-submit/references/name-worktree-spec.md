# Name and Worktree Spec

Applies to: `agents/name-worktree.md`.

The subagent works only inside the target gen worktree and may inspect upstream state. It must not create any branch and must not edit files.

## Name lookup

Normalize the raw operator name with the norm-name spreadsheet. The query strips an optional `aten::` prefix. If the spreadsheet has no match or the normalized name is empty, stop.

The spreadsheet must have a column named `算子名` and a column whose header contains `规范命名`.

## Naming surfaces

For ordinary ops: module name equals normalized operator name; public op id equals normalized name with leading underscores removed.

Special known mappings:

| normalized op | module | public op id |
|---|---|---|
| `max_pool2d_with_indices_backward` | `max_pool2d_with_indices` | `max_pool2d_with_indices_backward` |
| `matmul_layer_norm` | `Matmul_Layer_Norm` | `matmul_layernorm` |
| `__and__` | `_and_` | `and_op` |

Leading underscore is removed only from pytest mark, yaml `id`, test filename, benchmark filename, test function, and benchmark `op_name`. It is preserved in kernel filename, function name, import, `__all__`, `_FULL_CONFIG` aten name, yaml `for`, and actual torch call name. Trailing underscore is preserved everywhere.

## Gen worktree

The target directory is `<worktree_root>/gen-<op>` or, when generated output used the public id, `<worktree_root>/gen-<op_id>`. The current Git branch inside that worktree must be a generated branch corresponding to the operator, normally `gen-<op>`.

All later subagents operate inside this gen worktree. Do not create `pr/<op>`.

## Upstream conflict

Fetch upstream base if needed. Check upstream for `src/flag_gems/ops/<module>.py` and yaml `id: <op_id>`. If either exists, stop this operator.
