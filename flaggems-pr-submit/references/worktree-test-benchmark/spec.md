# Worktree Test Benchmark Spec

Applies to: worktree-test-benchmark subagent.

All commands run inside `{GEN_WORKTREE}` on the generated branch with the assigned GPU. This subagent does not create commits, push branches, or create pull requests.

Read `references/shared/test-benchmark.md` for the shared accuracy and benchmark rules. Read `references/shared/reviewer-learned-rules.md` before interpreting failures or performance concerns.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{GPU}`: assigned GPU id.

## Return format

Return the exact commands, exit status, pass/fail result, parsed benchmark table, mean speedup, case count, dtype coverage, and any blocking issue.
