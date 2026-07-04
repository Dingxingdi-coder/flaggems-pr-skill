# Implementation Review Spec

Applies to: implementation-review subagent.

This subagent reviews and repairs only the target gen worktree. Generated code is not trusted. Do not inspect or modify other worktrees or the main repository checkout.

Read `references/rule-structure.md` first. Deterministic checks belong to scripts; this stage focuses on semantic review and repair.

Also read `references/shared/reviewer-learned-rules.md` and apply any rules relevant to implementation, tests, or benchmark.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{MODULE}`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{GPU}`: assigned GPU id for local validation when needed.

## Files to inspect inside `{GEN_WORKTREE}`

- `src/flag_gems/ops/<module>.py`
- target test file or file containing `pytest.mark.<op_id>`
- target benchmark file or file containing `pytest.mark.<op_id>`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- `conf/operators.yaml`

## Kernel semantic requirements

The kernel file starts with the KernelGen header. Core computation must use Triton, `pointwise_dynamic`, FlagGems utilities, or existing FlagGems ops. PyTorch may be used only for auxiliary work such as allocation, shape/dtype/device inspection, layout changes, type inference, and complex views.

Blocking semantic issues:

- target computation implemented with PyTorch fallback;
- wrapper only calls the same torch operator or recurses through dispatch;
- Triton kernel exists but is not used by the wrapper;
- duplicate functions or dead exported functions;
- unused `@use_tl_extra` stubs;
- unsupported dtype path without wrapper check or test explanation;
- hardcoded block sizes, shape limits, dtype lists, or platform restrictions without comments.

Mechanical checks such as KernelGen header, `print()`, yaml id, pytest mark, benchmark `op_name`, and `gems_assert_close(..., rtol=...)` are enforced later by `scripts/operator_static_gate.py`; still fix obvious violations here when seen.

## Test semantic requirements

Tests use relative `accuracy_utils` import, `utils.to_reference`, `utils.gems_assert_close`, and `utils.gems_assert_equal`. NaN comparisons use `equal_nan=True`.

Remove quick-mode logic, vendor-specific branches, debug output, and unrelated skips. Probability operators use statistical checks rather than elementwise equality.

## Benchmark semantic requirements

Benchmark uses pytest and the project benchmark base wrappers. Non-pointwise or complex-input benchmarks need a Benchmark subclass whose shape handling still works under `--level core`.

The torch side and gems side must have equivalent arguments, computation, dtype coverage, and forward/backward boundary.

## Repair rule

Fix implementation, test, benchmark, yaml, and worktree registration problems in `{GEN_WORKTREE}` only. Do not patch a different checkout.
