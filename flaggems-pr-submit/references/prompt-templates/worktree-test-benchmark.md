# Worktree Test Benchmark Template

The template is:
```
You run worktree tests and benchmark for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}` and GPU `{GPU}`.

Skill root is `{SKILL_ROOT}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `{SKILL_ROOT}/references/rule-structure.md`, `{SKILL_ROOT}/references/shared/reviewer-learned-rules.md`, `{SKILL_ROOT}/references/shared/test-benchmark.md`, and `{SKILL_ROOT}/references/worktree-test-benchmark/spec.md`; then follow the spec.

Locate the test and benchmark files for this op, run the required commands, parse case count, dtype grouping, mean speedup, and TFLOPS when present. Return commands and results.
```

Note:
* `{...}` are placeholders to be replaced by real values.
