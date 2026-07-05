# Worktree Test Benchmark Soft Constraints

You must create a task for each of these items and check them in order:

- Locate the target accuracy test by confirming it contains `pytest.mark.{OP_ID}`.
- Locate the target benchmark by confirming it contains both `pytest.mark.{OP_ID}` and `op_name="{OP_ID}"`.
- Accuracy test failures are blocking and must not be hidden by narrowing marks or deleting cases.
- Benchmark failures are blocking and must be investigated through marks, `op_name`, core shapes, and Benchmark input iteration logic.
- Successful benchmark output must include at least one successful case and real speedup data.
- Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS when present.
- For ATen operators, tests and benchmarks should call the public torch or `torch.ops.aten` API inside `flag_gems.use_gems()` rather than invoking `flag_gems.<op>` directly.
- Avoid custom Benchmark subclasses or wrapper functions when the standard benchmark classes can express the target operator inputs and dispatch.
- For registered tensor and scalar overloads, accuracy tests must cover each reachable overload and dtype family supported by the operator.
