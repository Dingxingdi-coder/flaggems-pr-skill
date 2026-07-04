# Worktree Test Benchmark Template

The template is:
```
You run worktree tests and benchmark for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}` and GPU `{GPU}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `references/worktree-test-benchmark/spec.md` and follow the spec.

Locate the test and benchmark files for this op, run the required commands, parse case count, dtype grouping, mean speedup, and TFLOPS when present. Return commands and results.
```

Note:
* `{...}` are placeholders to be replaced by real values.
