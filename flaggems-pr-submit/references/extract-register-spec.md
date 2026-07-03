# Extract and Register Spec

Applies to: extract-register subagent.

There is no separate PR branch. Work only inside `{GEN_WORKTREE}`, which should already be on the target `gen-<op>` branch.

## Expected changed files

The gen branch should normally change these file groups only:

- `src/flag_gems/ops/<module>.py`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- `tests/test_<op_id>.py`
- `benchmark/test_<op_id>.py`
- `conf/operators.yaml`

Append mode is allowed for a related existing test or benchmark file. Preserve existing functions and append only target operator code.

## In-worktree adaptation

If generated files use an old shared-file layout, adapt them inside `{GEN_WORKTREE}` to the current upstream layout expected by FlagGems.

Ensure the kernel has the KernelGen header and only target wrapper exports. Preserve valuable comments.

Create or append the target test file. Use project import style and rename generated `test_accuracy_<op_id>` style functions to `test_<op_id>` when needed.

Create or append the benchmark file. Preserve custom Benchmark subclasses needed for non-pointwise or complex input generation.

Update the ops package import/export list, top-level dispatch registration, and `conf/operators.yaml`.

## Consistency checks

- yaml `id` equals pytest mark and benchmark `op_name`;
- exported wrappers are registered, tested, and benchmarked;
- `_out`, inplace, and overload variants are either fully covered or not exported;
- leading underscore and trailing underscore rules match the name spec;
- branch diff does not include unrelated operators.
