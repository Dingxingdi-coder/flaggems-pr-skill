# Worktree Test Benchmark Soft Constraints

- Accuracy test failures are blocking and must not be hidden by narrowing marks or deleting cases.
- Benchmark failures are blocking and must be investigated through marks, `op_name`, core shapes, and Benchmark input iteration logic.
- For ATen operators, tests and benchmarks should call the public torch or `torch.ops.aten` API inside `flag_gems.use_gems()` rather than invoking `flag_gems.<op>` directly.
- For non-ATen operators, tests and benchmarks should invoke the documented `flag_gems` public API directly and use the documented PyTorch reference expression as the golden reference.
- Avoid custom Benchmark subclasses or wrapper functions when the standard benchmark classes can express the target operator inputs and dispatch.
- Do not add vendor-only skips for pure Triton tests or benchmarks unless the PyTorch reference or backend compiler limitation is concrete and documented.
- Do not leave target tests skipped or xfailed without an operator-scoped reason and a tracking issue when the limitation is unresolved.
