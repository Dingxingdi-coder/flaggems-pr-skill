# Final Validation Soft Constraints

- Stage target files explicitly by path and never stage the whole repository.
- Commit messages must use `[KernelGen][Nvidia] Add <op> operator with Triton kernel` and must not contain co-author trailers.
- Do not create a PR if static gates fail, performance data is missing, benchmark cases are zero, tests fail, or required PR body sections are incomplete.
- The PR body must be English and include summary, testing or correctness, performance, tested-on, multi-backend testing, and files changed.
