# Operator Agent Spec

This file applies to the per-operator agent.

## Naming

Normalize the raw operator name through `operator_registry.py lookup`. Use `op_naming.py` for `op_id` and module name.

Leading underscore is removed only from pytest mark, yaml `id`, test filename, benchmark filename, test function, and benchmark `op_name`. It is preserved in kernel filename, function name, import, `__all__`, `_FULL_CONFIG` aten name, yaml `for`, and actual torch call name. Trailing underscore is preserved everywhere.

For overloads, yaml `id`, pytest mark, and benchmark `op_name` must be identical. yaml `for` keeps aten dotted names.

## Worktree-first rule

Generated code is untrusted. Inspect and repair `<worktree_root>/gen-<op>` before extraction. PR branch implementation, tests, and benchmarks must come from the repaired worktree through `extract_from_worktree.py`.

Do not bypass worktree extraction by rewriting implementation/test/benchmark directly on the PR branch. Pure formatting and yaml wording can be fixed after extraction.

## Kernel rules

The kernel file starts with the KernelGen header. Core computation must use Triton, `pointwise_dynamic`, FlagGems utilities, or existing FlagGems ops. PyTorch fallback for the target computation is forbidden.

Allowed torch use is auxiliary only: output allocation, shape/stride/dtype/device inspection, view/reshape/permute/contiguous, type inference, and complex view helpers.

No `print()`. Remove duplicate functions, dead exports, meaningless aliases, and unused `@use_tl_extra` stubs. Hardcoded block sizes, shapes, dtype limits, and platform restrictions need comments.

## Accuracy tests

Use relative `accuracy_utils` import, `utils.to_reference()`, `utils.gems_assert_close`, and `utils.gems_assert_equal`. Never pass `rtol` to `gems_assert_close`. NaN comparisons use `equal_nan=True`.

Prefer shared dtype/shape constants. If dtype is restricted, verify PyTorch reference support and document the reason. Remove quick-mode branches, vendor-specific branches, debug output, and unrelated skips.

## Benchmark

Use pytest and `benchmark/base.py` wrappers. Benchmark mark and `op_name` equal yaml `id`. Benchmark must pass with `--level core -s`, produce nonzero parsed cases, and be fair between torch and gems sides.

Mean speedup below `0.8x` blocks submission unless the operator is abandoned.

## YAML and registration

The expected changed files are the kernel, two registration files, test, benchmark, and `conf/operators.yaml`. `operators.yaml` must include accurate description, correct `for`, labels including `aten` and `KernelGen`, valid kind, and the context expected stage.

Every exported wrapper must be registered and covered by tests and benchmarks. Otherwise remove it.
