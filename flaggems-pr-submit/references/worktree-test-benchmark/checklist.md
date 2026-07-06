# Worktree Test Benchmark Checklist

You must create a task for each item and check them in order:

- Locate the target accuracy test by confirming it contains `pytest.mark.{OP_ID}`.
- Locate the target benchmark by confirming it contains both `pytest.mark.{OP_ID}` and `op_name="{OP_ID}"`.
- Confirm the target test and benchmark call the public torch or `torch.ops.aten` API inside `flag_gems.use_gems()` for ATen operators.
- Confirm registered tensor and scalar overloads have accuracy coverage for each reachable overload and supported dtype family.
- Confirm successful benchmark output includes at least one successful case and real speedup data.
- Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS when present.
