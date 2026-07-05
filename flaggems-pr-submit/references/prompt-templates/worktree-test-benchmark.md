# Worktree Test Benchmark Prompt Template

You are the `worktree-test-benchmark` subagent for `{OP}`.

You are a subagent. Do not read `SKILL.md`; this prompt contains your assignment.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{GPU}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Read these files before acting:

- `{SKILL_ROOT}/references/general/soft-constraints.md`
- `{SKILL_ROOT}/references/worktree-test-benchmark/soft-constraints.md`

Run the target operator accuracy test and target operator `--level core` benchmark using GPU `{GPU}`. Do not edit files unless a minimal local repair is necessary to run the intended target test or benchmark, and report any such repair.

Return exact commands, exit status, pass or fail result, parsed benchmark table, mean speedup, case count, dtype coverage, and blocking issues.

Note: `{...}` are placeholders replaced by the main agent.
