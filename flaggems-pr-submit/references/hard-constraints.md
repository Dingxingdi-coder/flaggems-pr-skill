# Hard Constraints

Hard constraints are deterministic rules that can be enforced by a stable command-line interface. A subagent must run the owning script instead of manually re-implementing the check in prose.

## Script interface

Every hard-rule script must satisfy these interface rules:

- exits nonzero when any hard constraint fails;
- prints failures as `ERROR[<RULE_ID>]: <message>`;
- supports `--list-rules` and prints `<RULE_ID><tab><description>`;
- keeps rule IDs stable after publication;
- is referenced from the stage prompt template that must run it.

## Current hard-rule scripts

### `scripts/resolve_op_context.py`

Run during `name-worktree`.

```bash
python "{SKILL_ROOT}/scripts/resolve_op_context.py" --raw-op "{raw_op}" --norm-xlsx "{norm_xlsx}" --worktree-root "{worktree_root}" --upstream "{upstream}" --base-branch "{base_branch}"
```

Rule IDs:

| Rule ID | Constraint |
|---|---|
| `RESOLVE-H001` | Raw operator name is normalized through `规范名.xlsx`. |
| `RESOLVE-H002` | Normalized operator maps to the canonical module and public `op_id`. |
| `RESOLVE-H003` | Generated worktree exists under the configured worktree root. |
| `RESOLVE-H004` | Generated worktree is on the matching `gen-*` branch. |
| `RESOLVE-H005` | Upstream base ref is fetched before conflict checks. |
| `RESOLVE-H006` | Upstream does not already contain the target kernel module. |
| `RESOLVE-H007` | Upstream does not already contain the target yaml id. |

### `scripts/operator_static_gate.py`

Run during `register` and `final-validation`.

```bash
python "{SKILL_ROOT}/scripts/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

Rule IDs:

| Rule ID | Constraint |
|---|---|
| `STATIC-H000` | Static gate can diff against the supplied upstream/base ref. |
| `STATIC-H001` | Branch diff is limited to the target operator file set. |
| `STATIC-H002` | Required kernel, package init, top-level init, and `operators.yaml` files exist. |
| `STATIC-H003` | Target kernel file contains `KernelGen` in the first 10 lines. |
| `STATIC-H004` | Target changed Python files do not contain `print()` debug output. |
| `STATIC-H005` | `conf/operators.yaml` contains exactly one id for the target `op_id`. |
| `STATIC-H006` | At least one changed test file contains `pytest.mark.<op_id>`. |
| `STATIC-H007` | Changed tests do not pass `rtol=` to `gems_assert_close`. |
| `STATIC-H008` | At least one changed benchmark file contains `pytest.mark.<op_id>`. |
| `STATIC-H009` | At least one changed benchmark file sets `op_name` to the target `op_id`. |

## Adding or promoting a hard constraint

Use this path only when the rule is deterministic from local files, git metadata, command output, or the normalized operator context.

1. Pick the owning script. Naming/worktree/upstream-conflict checks belong in `resolve_op_context.py`; target diff, registration, test, benchmark, yaml, and PR-ready static checks belong in `operator_static_gate.py`. If neither script is a natural owner, add a new script with the same interface contract and wire it into the relevant prompt template.
2. Assign a stable rule ID in the owning script and add it to that script's `RULES` list.
3. Emit failures only through the script's rule-aware error helper so output includes `ERROR[<RULE_ID>]`.
4. Update this document and, when ownership changes, `references/constraint-map.md`.
5. If the rule was promoted from reviewer feedback, replace the soft-rule entry in `references/shared/reviewer-learned-rules.md` with a short pointer to the hard-rule ID.
6. Run the script with `--list-rules` and run the normal stage command before committing the skill change.

Do not duplicate a hard rule as prose instructions in multiple stage specs. Stage specs may mention what the script covers, but the executable script and this manifest are the source of truth.
