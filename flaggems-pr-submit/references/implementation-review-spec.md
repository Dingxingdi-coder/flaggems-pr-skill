# Implementation Review Spec

Applies to: implementation-review subagent.

This subagent reviews and repairs only the target gen worktree. Generated code is not trusted. Do not inspect or modify other worktrees or the main repository checkout.

## Files to inspect inside `{GEN_WORKTREE}`

- `src/flag_gems/ops/<module>.py`
- target test file or file containing `pytest.mark.<op_id>`
- target benchmark file or file containing `pytest.mark.<op_id>`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- `conf/operators.yaml`

## Kernel requirements

The kernel file starts with the KernelGen header. Core computation must use Triton, `pointwise_dynamic`, FlagGems utilities, or existing FlagGems ops. PyTorch may be used only for auxiliary work such as allocation, shape/dtype/device inspection, layout changes, type inference, and complex views.

Blocking issues:

- target computation implemented with PyTorch fallback;
- wrapper only calls the same torch operator or recurses through dispatch;
- Triton kernel exists but is not used by the wrapper;
- duplicate functions or dead exported functions;
- `print()` in kernel, tests, or benchmark;
- unused `@use_tl_extra` stubs;
- unsupported dtype path without wrapper check or test explanation;
- hardcoded block sizes, shape limits, dtype lists, or platform restrictions without comments.

## Test requirements

Tests use relative `accuracy_utils` import, `utils.to_reference`, `utils.gems_assert_close`, and `utils.gems_assert_equal`. `gems_assert_close` must not receive `rtol`. NaN comparisons use `equal_nan=True`.

Remove quick-mode logic, vendor-specific branches, debug output, and unrelated skips. Probability operators use statistical checks rather than elementwise equality.

## Benchmark requirements

Benchmark uses pytest and the project benchmark base wrappers. The pytest mark and benchmark `op_name` must equal yaml `id`. Non-pointwise or complex-input benchmarks need a Benchmark subclass whose shape handling still works under `--level core`.

The torch side and gems side must have equivalent arguments, computation, dtype coverage, and forward/backward boundary.

## Repair rule

Fix implementation, test, benchmark, yaml, and worktree registration problems in `{GEN_WORKTREE}` only. Do not patch a different checkout.
