# General Soft Constraints

You must create a task for each of these items and check them in order:

- Keep one PR scoped to one ATen or fused operator family and do not include unrelated operator logic.
- Keep implementation and worktree validation edits inside the resolved generated worktree.
- Use the generated worktree only as the source. Create a clean PR worktree from `{UPSTREAM_REF}` and submit only the target operator files.
- Do not replace target computation with a PyTorch fallback.
- Do not reduce accuracy coverage or benchmark coverage merely to make validation pass.
- Accuracy tests and benchmarks must exercise the same public operator id used for yaml, pytest marks, and registration.
- Benchmarks must compare equivalent torch and FlagGems work and must report nonzero successful cases before PR creation.
- The final PR body must use only real test commands, benchmark commands, speedup data, and tested-on data collected in the worktree.
