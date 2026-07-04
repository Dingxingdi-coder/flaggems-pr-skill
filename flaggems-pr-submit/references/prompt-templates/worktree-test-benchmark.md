# Worktree Test Benchmark Template

Fields: `{OP}`, `{GEN_WORKTREE}`, `{OP_ID}`, `{GPU}`.

Prompt to send: You run worktree tests and benchmark for `{OP}`. Read `references/test-benchmark-spec.md`. Work directory is `{GEN_WORKTREE}`. Do not operate outside that directory. Use op_id `{OP_ID}` and GPU `{GPU}`. Locate the test and benchmark files for this op, run the required commands, parse case count, dtype grouping, mean speedup, and TFLOPS when present. Return commands and results.
