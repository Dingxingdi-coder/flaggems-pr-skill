# Final Validation Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Run the static gate before staging.
- Confirm static gates pass, tests pass, benchmark cases are nonzero, and performance data is present.
- Confirm accuracy results, benchmark results, per-case benchmark rows, mean speedup, dtype coverage, tested-on data, and multi-backend status are present.
- Confirm exported functions have matching test and benchmark coverage.
- Confirm the benchmark compares equivalent torch and FlagGems work.
- Confirm staged `conf/operators.yaml` entries have explicit `description`, `for`, `labels`, `kind`, and `stages` values and do not contain script-synthesized placeholder metadata.
- Confirm the PR body contains summary, testing, performance, multi-backend testing, and files changed sections.
- Confirm the performance table has one row per successful benchmark case plus an Arithmetic Mean row computed from successful case speedups.
- Confirm the staged file list contains only `{TARGET_FILES}` before committing.
- Confirm any temporary PR body file is not staged.
- For non-ATen operators, the PR body must use the documented public API and reference expression, and no staged yaml label may be `aten`.
