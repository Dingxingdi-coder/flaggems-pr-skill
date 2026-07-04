# Register Spec

Applies to: register subagent.

There is no separate PR branch. Work only inside `{GEN_WORKTREE}`, which should already be on the target generated branch.

Read `references/rule-structure.md` and `references/shared/reviewer-learned-rules.md` before editing. After registration edits, run `scripts/operator_static_gate.py` exactly as instructed by the prompt template.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{MODULE}`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{UPSTREAM_REF}`: fetched upstream ref produced by the resolver script.

## Expected changed files

The gen branch should normally change these file groups only:

- `src/flag_gems/ops/<module>.py`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- target test file containing `pytest.mark.<op_id>`
- target benchmark file containing `pytest.mark.<op_id>` and `op_name="<op_id>"`
- `conf/operators.yaml`

Append mode is allowed for a related existing test or benchmark file. Preserve existing functions and append only target operator code.

## In-worktree adaptation

If generated files use an old shared-file layout, adapt them inside `{GEN_WORKTREE}` to the current upstream layout expected by FlagGems.

Ensure the kernel has the KernelGen header and only target wrapper exports. Preserve valuable comments.

Create or append the target test file. Use project import style and rename generated `test_accuracy_<op_id>` style functions to `test_<op_id>` when needed.

Create or append the benchmark file. Preserve custom Benchmark subclasses needed for non-pointwise or complex input generation.

Update the ops package import/export list, top-level dispatch registration, and `conf/operators.yaml`.

## Consistency checks

Run the static gate. It mechanically checks changed-file boundary, KernelGen header, `print()`, yaml id uniqueness, pytest mark alignment, benchmark `op_name`, and `gems_assert_close(..., rtol=...)`.

Manually verify semantic consistency not covered by the script:

- exported wrappers are registered, tested, and benchmarked;
- `_out`, inplace, and overload variants are either fully covered or not exported;
- leading underscore and trailing underscore behavior matches the resolver output;
- branch diff does not include unrelated operator logic.

## Return format

Return changed files, registration surfaces touched, static gate command/result, unresolved inconsistencies, and blocking issues.
