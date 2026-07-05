# Implementation Review Spec

Applies to: `implementation-review` subagent.

Review and repair generated implementation, tests, benchmark code, yaml-adjacent assumptions, and registration-adjacent code only inside `{GEN_WORKTREE}`.

## Required Reading

- `references/general/soft-constraints.md`
- `references/implementation-review/spec.md`
- `references/implementation-review/soft-constraints.md`

## Duties

- Reject target computation implemented as a PyTorch fallback.
- Check wrapper behavior, dtype guards, duplicate or dead generated functions, tests, benchmark code, yaml assumptions, and registration consistency.
- Preserve target operator behavior while adapting generated code to the current FlagGems project style.
- Repair accuracy tests and benchmarks when semantic issues are visible before execution.

Mechanical checks are owned by runtime scripts. Do not maintain hard-rule inventories in this file.

## Return Format

Return changed files, fixed issues, remaining risks, tests or benchmarks that should run next, and blocking issues.
