# Worktree Test Benchmark Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Locate the target accuracy test by confirming it contains `pytest.mark.{OP_ID}`.
- Locate the target benchmark by confirming it contains both `pytest.mark.{OP_ID}` and `op_name="{OP_ID}"`.
- Confirm the target test and benchmark call the public torch or `torch.ops.aten` API inside `flag_gems.use_gems()` for ATen operators.
- Confirm registered tensor and scalar overloads have accuracy coverage for each reachable overload and supported dtype family.
- For inplace operators, confirm tests assert that the original tensor is mutated and returned, including pointer or identity checks when PyTorch aliasing semantics require them.
- Check any explicit error branch added by the implementation has a reachable accuracy or error-path test.
- Check skips and xfails are operator-scoped, justified by a concrete backend or reference limitation, and do not hide target coverage.
- Confirm successful benchmark output includes at least one successful case and real speedup data.
- Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS when present.
