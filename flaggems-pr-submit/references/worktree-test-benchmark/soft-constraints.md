# Worktree Test Benchmark Soft Constraints

You must create a task for each of these items and check them in order:

- Locate the target accuracy test by confirming it contains `pytest.mark.{OP_ID}`.
- Locate the target benchmark by confirming it contains both `pytest.mark.{OP_ID}` and `op_name="{OP_ID}"`.
- Accuracy test failures are blocking and must not be bypassed by narrowing marks or deleting cases.
- Benchmark failures are blocking and must be investigated through marks, `op_name`, core shapes, and Benchmark input iteration logic.
- Successful benchmark output must include at least one successful case and real speedup data.
- Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS when present.
