# Worktree Test Benchmark Spec

Applies to: worktree-test-benchmark subagent.

All commands run inside `{GEN_WORKTREE}` on the generated branch with the assigned GPU. This subagent does not create commits, push branches, or create pull requests.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{GPU}`: assigned GPU id.

## Accuracy tests

Locate the test file containing `pytest.mark.<op_id>`. Prefer `tests/test_<op_id>.py` if present.

Command pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest <test_file> -m <op_id> -vs`.

Failures are blocking. Do not reduce coverage to make the test pass. Fix implementation or test logic and rerun.

## Benchmark

Locate the benchmark file containing `pytest.mark.<op_id>`. Prefer `benchmark/test_<op_id>.py` if present.

Command pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest <bench_file> -m <op_id> -s --level core`.

Benchmark failures are blocking. Output must contain nonzero successful cases. Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS if present.

## Zero cases

If benchmark reports zero cases or produces no parseable success rows, inspect pytest mark, benchmark `op_name`, `core_shapes.yaml`, and Benchmark `set_shapes` / `get_input_iter` logic.

## Performance threshold

Mean speedup below `0.8x` blocks PR creation. Optimize the kernel or abandon the operator.

## Fairness

The benchmark must compare equivalent torch and gems computation. Backward benchmarks compare equivalent backward work. The benchmark must not hide work on the gems side or add extra work on the torch side.

## Return format

Return the exact commands, exit status, pass/fail result, parsed benchmark table, mean speedup, case count, dtype coverage, and any blocking issue.
