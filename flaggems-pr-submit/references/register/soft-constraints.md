# Register Soft Constraints

You must create a task for each of these items and check them in order:

- Append to related existing test or benchmark files only when preserving existing functions and adding target operator coverage.
- Kernel files must keep the KernelGen header and export only target wrappers.
- Exported wrappers must be registered, tested, and benchmarked consistently.
- `_out`, inplace, and overload variants must either be fully covered or remain unexported.
- Leading underscore and trailing underscore behavior must match the resolver output and public operator id.
- Generated shared-file layouts must be adapted to the current upstream FlagGems registration layout inside the generated worktree.
- Target files, pytest marks, benchmark `op_name`, yaml id, ops package exports, and top-level dispatch registration must describe the same public operator id.
