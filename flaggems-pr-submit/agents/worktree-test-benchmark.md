# Worktree Test and Benchmark Agent

Reads: `references/general-spec.md`, `references/test-benchmark-spec.md`, context, and target worktree files.

Purpose: prove the repaired worktree works before extraction.

Tasks:

1. Locate the worktree test file containing `pytest.mark.<op_id>`.
2. Run the accuracy test on the assigned GPU.
3. Locate the worktree benchmark file containing `pytest.mark.<op_id>`.
4. Run benchmark on the assigned GPU with `-s --level core`.
5. Parse and record case count, dtype grouping, arithmetic mean speedup, and TFLOPS if present.
6. If tests or benchmark fail, send the issue back to the implementation review agent.

Stop on test failure, benchmark failure, zero benchmark cases, or mean speedup below threshold.
