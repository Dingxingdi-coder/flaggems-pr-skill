# Name and Branch Spec

Applies to: `agents/name-branch.md`.

## Name lookup

Map every raw operator name to its normalized name using the norm-name spreadsheet. The spreadsheet must contain columns for original operator name and normalized operator name. A normalized name that is absent or empty is a blocking issue.

The agent may use a short Python inspection command with `openpyxl`, or manually inspect the xlsx, to find the normalized name. The query should strip an optional `aten::` prefix before matching.

## Naming surfaces

For ordinary ops: module name equals normalized operator name; public op id equals normalized name with leading underscores removed.

Special cases that appeared in the old helper logic:

| normalized op | module | public op id |
|---|---|---|
| `max_pool2d_with_indices_backward` | `max_pool2d_with_indices` | `max_pool2d_with_indices_backward` |
| `matmul_layer_norm` | `Matmul_Layer_Norm` | `matmul_layernorm` |
| `__and__` | `_and_` | `and_op` |

Leading underscore is removed only from pytest mark, yaml `id`, test filename, benchmark filename, test function, and benchmark `op_name`. It is preserved in kernel filename, function name, import, `__all__`, `_FULL_CONFIG` aten name, yaml `for`, and actual torch call name. Trailing underscore is preserved everywhere.

## Upstream conflict

Fetch the upstream base branch. The target operator must not already exist in upstream as a kernel file or yaml id. Check the kernel path `src/flag_gems/ops/<module>.py` and search upstream `conf/operators.yaml` for `id: <op_id>`. If either exists, stop this operator.

## Branch

Create a fresh branch for initial PR creation: `pr/<op>` based on `<upstream_remote>/<base_branch>`. The branch must contain only this operator's work. Cherry-pick and rebase are outside this workflow.
