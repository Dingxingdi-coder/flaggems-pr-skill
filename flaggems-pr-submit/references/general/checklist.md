# General Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Confirm the operator scope is one ATen or fused operator family and contains no unrelated operator logic.
- Confirm implementation and validation edits stay inside the resolved generated worktree.
- Confirm the generated worktree is the source for the clean PR worktree created from `{UPSTREAM_REF}`.
- Confirm accuracy tests and benchmarks exercise the same public operator id used for yaml, pytest marks, and registration.
- Confirm benchmarks compare equivalent torch and FlagGems work and report nonzero successful cases before PR creation.
- Confirm final PR data comes only from real test commands, benchmark commands, speedup data, and tested-on data collected in the worktree.
