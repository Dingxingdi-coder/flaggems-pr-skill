# Register Soft Constraints

- Exported wrappers must be registered, tested, and benchmarked consistently.
- `_out`, inplace, and overload variants must either be fully covered or remain unexported.
- Leading underscore and trailing underscore behavior must match the resolver output and public operator id.
- Generated shared-file layouts must be adapted to the current upstream FlagGems registration layout inside the generated worktree.
