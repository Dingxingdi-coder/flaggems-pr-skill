# Test and Benchmark Spec

Applies to: `agents/worktree-test-benchmark.md` and the validation part of `agents/final-validate-pr.md`.

## Accuracy tests

Run the worktree accuracy test before extraction and the PR-branch accuracy test after extraction. Use the assigned GPU.

Worktree pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest <test_file> -m <op_id> -vs`.

PR-branch pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest tests/test_<op_id>.py -x -v --timeout=60`.

Failures are blocking. Do not reduce coverage to make the test pass. Fix the worktree implementation or test logic and rerun.

## Benchmark

Run benchmark with `-s --level core` before extraction and after extraction.

Worktree pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest <bench_file> -m <op_id> -s --level core`.

PR-branch pattern: `CUDA_VISIBLE_DEVICES=<gpu> python -m pytest benchmark/test_<op_id>.py -s --level core`.

Benchmark failures are blocking. Benchmark output must contain nonzero successful cases. Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS if present.

## Zero cases

If benchmark reports zero cases or produces no parseable success rows, inspect pytest mark, benchmark `op_name`, `core_shapes.yaml`, and Benchmark `set_shapes` / `get_input_iter` logic.

## Performance threshold

Mean speedup below `0.8x` blocks PR creation. Optimize the kernel or abandon the operator.

## Fairness

The benchmark must compare equivalent torch and gems computation. Backward benchmarks compare equivalent backward work. The benchmark must not hide work on the gems side or add extra work on the torch side.
