# Worktree Test Benchmark Soft Constraints

- Accuracy test failures are blocking and must not be hidden by narrowing marks or deleting cases.
- Benchmark failures are blocking and must be investigated through marks, `op_name`, core shapes, and Benchmark input iteration logic.
- For ATen operators, tests and benchmarks should call the public torch or `torch.ops.aten` API inside `flag_gems.use_gems()` rather than invoking `flag_gems.<op>` directly.
- Avoid custom Benchmark subclasses or wrapper functions when the standard benchmark classes can express the target operator inputs and dispatch.
