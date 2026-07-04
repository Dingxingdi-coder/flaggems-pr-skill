# Shared Test and Benchmark Rules

Applies to implementation-review, worktree-test-benchmark, and final-validation subagents.

All commands run inside GEN_WORKTREE on the generated branch with the assigned GPU.

## Accuracy tests

Locate the test file containing pytest mark for the operator. Failures are blocking. Do not reduce coverage to make a test pass.

## Benchmark

Locate the benchmark file containing pytest mark for the operator. Benchmark failures are blocking. Output must contain nonzero successful cases. Record case count, dtype grouping, arithmetic mean speedup, and TFLOPS if present.

## Zero cases

If benchmark reports zero cases or produces no parseable success rows, inspect pytest mark, benchmark op_name, core shapes, and Benchmark shape/input iteration logic.

## Performance threshold

Mean speedup below 0.8x blocks PR creation.

## Fairness

The benchmark must compare equivalent torch and gems computation. Backward benchmarks compare equivalent backward work. The benchmark must not hide work on the gems side or add extra work on the torch side.

## Embedded test and benchmark soft rules

No entries yet. Add future test or benchmark soft rules here using the SOFT-YYYYMMDD-short-slug format from references/soft-constraints.md.

## PR data dependency

The final PR body must use real test commands, real benchmark command, dtype/case grouping, speedup data, and tested-on text collected by these checks.
