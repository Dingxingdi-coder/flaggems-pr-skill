# Final Validation Soft Constraints

You must create a task for each of these items and check them in order:

- Stage target files explicitly by path and never stage the whole repository.
- Re-check that the staged file list is target-only before committing.
- Commit messages must use `[KernelGen][Nvidia] Add <op> operator with Triton kernel` and must not contain co-author trailers.
- Do not create a PR if static gates fail, performance data is missing, benchmark cases are zero, tests fail, or required PR body sections are incomplete.
- Do not create a PR when exported functions lack matching test and benchmark coverage.
- Do not create a PR when the benchmark compares non-equivalent torch and FlagGems work.
- The PR body must be English and include summary, testing or correctness, performance, tested-on, multi-backend testing, and files changed.
