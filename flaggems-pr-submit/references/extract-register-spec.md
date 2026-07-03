# Extract and Register Spec

Applies to: `agents/extract-register.md`.

Extraction happens only after the repaired worktree passes review, accuracy tests, and benchmark.

## Expected PR files

Normally the PR branch changes exactly these six file groups:

- `src/flag_gems/ops/<module>.py`
- `src/flag_gems/ops/__init__.py`
- `src/flag_gems/__init__.py`
- `tests/test_<op_id>.py`
- `benchmark/test_<op_id>.py`
- `conf/operators.yaml`

Append mode is allowed when upstream already has the target test or benchmark file for a related variant. In append mode, preserve existing functions and append only the target operator code.

## Manual extraction

Copy the repaired kernel from worktree to the PR branch. Add the KernelGen header if absent. Preserve valuable comments.

Create or append the target test file. Use project import style and rename generated `test_accuracy_<op_id>` style functions to `test_<op_id>` when needed.

Create or append the benchmark file. Preserve custom Benchmark subclasses needed for non-pointwise or complex input generation.

Update `src/flag_gems/ops/__init__.py`: add import and `__all__` entries for the wrapper functions, not Triton kernel internals. Keep the project ordering style.

Update `src/flag_gems/__init__.py`: add `_FULL_CONFIG` entries using real aten dispatch names. Dotted overload names stay dotted.

Update `conf/operators.yaml`: add accurate `description`, `for`, labels including `aten` and `KernelGen`, valid `kind`, and expected stage from context.

## Consistency checks

- yaml `id` equals pytest mark and benchmark `op_name`;
- exported wrappers are registered, tested, and benchmarked;
- `_out`, inplace, and overload variants are either fully covered or not exported;
- leading underscore and trailing underscore rules match the name spec;
- the branch diff does not include unrelated operators.
