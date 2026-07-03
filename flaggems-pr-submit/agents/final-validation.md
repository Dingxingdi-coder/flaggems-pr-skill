# Final Validation Agent

Reads: `references/final-pr-spec.md`, `references/test-benchmark-spec.md`, context, and target branch files.

Purpose: perform the final target-branch checks and publish the initial contribution.

Required checks:

1. Confirm current directory is the target `gen-<op>` worktree or the target branch checkout for this operator.
2. Confirm changed files are limited to the expected operator files: kernel, two registration files, test, benchmark, and `conf/operators.yaml`.
3. Inspect kernel header, logging usage, absence of debug output, registration entries, yaml entry, mark/op_name alignment, and exported function coverage.
4. Run formatting checks on the explicit target file list only.
5. Run target-branch accuracy test on the assigned GPU.
6. Run target-branch benchmark on the assigned GPU with `-s --level core`.
7. Parse benchmark output and record dtype grouping, case count, arithmetic mean speedup, and TFLOPS if present.
8. Stage target files explicitly by path. Do not stage the whole repository.
9. Commit with `[KernelGen][Nvidia] Add <op> operator with Triton kernel`.
10. Publish the `gen-<op>` branch or current target branch to the fork remote.
11. Create the initial upstream contribution with a complete English body.

Stop on missing data, failed tests, failed benchmark, zero benchmark cases, unrelated files, or incomplete body.
