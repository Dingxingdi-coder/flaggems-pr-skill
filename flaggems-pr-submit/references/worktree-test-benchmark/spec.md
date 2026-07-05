# Worktree Test Benchmark Spec

Applies to: `worktree-test-benchmark` subagent.

Run the target operator accuracy test and target operator `--level core` benchmark inside `{GEN_WORKTREE}` on the assigned GPU.

## Required Reading

- `references/general/soft-constraints.md`
- `references/worktree-test-benchmark/spec.md`
- `references/worktree-test-benchmark/soft-constraints.md`

## Duties

- Locate the test file containing `pytest.mark.{OP_ID}`.
- Locate the benchmark file containing `pytest.mark.{OP_ID}` and `op_name="{OP_ID}"`.
- Run accuracy tests with the assigned GPU.
- Run the target benchmark with `--level core` and the assigned GPU.
- Parse successful benchmark rows and report case count, dtype coverage, arithmetic mean speedup, and TFLOPS when present.

Do not mark the stage successful when tests fail, benchmark execution fails, benchmark output has zero successful cases, or speedup data is missing.

## Return Format

Return exact commands, exit status, pass or fail result, parsed benchmark table, mean speedup, case count, dtype coverage, and blocking issues.
