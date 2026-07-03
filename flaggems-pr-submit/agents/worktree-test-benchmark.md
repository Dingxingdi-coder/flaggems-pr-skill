# Worktree Test and Benchmark Agent

Template fields: `{OP}`, `{GEN_WORKTREE}`, `{OP_ID}`, `{GPU}`.

The main agent tells this subagent to read `references/test-benchmark-spec.md`, enter `{GEN_WORKTREE}`, use `{GPU}`, and report commands plus results.

Responsibilities:

1. Locate the worktree test file containing `pytest.mark.<op_id>`.
2. Run the accuracy test on the assigned GPU.
3. Locate the worktree benchmark file containing `pytest.mark.<op_id>`.
4. Run benchmark on the assigned GPU with `-s --level core`.
5. Parse and record case count, dtype grouping, arithmetic mean speedup, and TFLOPS if present.
6. Report the failing command and concise reason when a command fails.

Stop on test failure, benchmark failure, zero benchmark cases, or mean speedup below threshold.
