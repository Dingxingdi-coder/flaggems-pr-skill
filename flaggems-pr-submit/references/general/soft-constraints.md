# General Soft Constraints

- Keep implementation, validation, registration, and final submission edits inside the working directory assigned to the current stage.
- Use the generated worktree only as the source for target operator files, and submit only those target operator files from the clean PR worktree.
- Do not replace target computation with a PyTorch fallback.
- Do not reduce accuracy coverage or benchmark coverage merely to make validation pass.
- The final PR body must use only real test commands, benchmark commands, speedup data, and tested-on data collected in the worktree.
