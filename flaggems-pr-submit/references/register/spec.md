# Register Spec

Applies to: `register` subagent.

There is no separate PR branch. Work only inside `{GEN_WORKTREE}`, which should already be on the target generated branch.

## Required Reading

- `references/general/soft-constraints.md`
- `references/register/spec.md`
- `references/register/soft-constraints.md`

## Expected Changed Files

The generated branch should normally change only these file groups:

- `src/flag_gems/ops/<module>.py`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- target test file containing `pytest.mark.<op_id>`
- target benchmark file containing `pytest.mark.<op_id>` and `op_name="<op_id>"`
- `conf/operators.yaml`

Append mode is allowed for a related existing test or benchmark file. Preserve existing functions and append only target operator code.

## Duties

- Adapt generated files that use an old shared-file layout to the current upstream FlagGems layout.
- Ensure the kernel has the KernelGen header and only target wrapper exports.
- Create or append the target test file using project import style.
- Create or append the benchmark file while preserving required Benchmark subclasses.
- Update the ops package import/export list, top-level dispatch registration, and `conf/operators.yaml`.
- Manually verify exported wrappers are registered, tested, and benchmarked consistently.

## Hard Constraints

After registration edits, run:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

The static gate owns mechanical checks for changed-file boundary, required files, KernelGen header, debug `print()`, yaml id uniqueness, pytest mark alignment, benchmark `op_name` alignment, and `gems_assert_close(..., rtol=...)`.

## Return Format

Return changed files, registration surfaces touched, static gate command and result, unresolved inconsistencies, and blocking issues.
