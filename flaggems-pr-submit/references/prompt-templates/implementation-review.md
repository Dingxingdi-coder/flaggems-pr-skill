# Implementation Review Template

Use this template for the implementation-review subagent.

Inputs: `{OP}`, `{OP_ID}`, `{MODULE}`, `{GEN_WORKTREE}`, `{GPU}`, `{SKILL_ROOT}`.

Working directory: `{GEN_WORKTREE}` only.

Required reference files:

- `{SKILL_ROOT}/references/rule-structure.md`
- `{SKILL_ROOT}/references/shared/test-benchmark.md`
- `{SKILL_ROOT}/references/implementation-review/spec.md`

The subagent follows those specs, including embedded soft rules relevant to implementation, tests, or benchmark repair.

Return changed files, fixed issues, remaining risks, and whether tests may run.

Note: `{...}` are placeholders to be replaced by real values.
