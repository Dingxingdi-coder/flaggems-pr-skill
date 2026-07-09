# Register Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Locate related existing kernel, test, and benchmark files for the same operator family.
- Check kernel files keep the KernelGen header and export only target wrappers.
- Check exported wrappers are registered, tested, and benchmarked consistently.
- Check `_out`, inplace, and overload variants for full coverage before exporting them.
- Check whether leading underscores or trailing-underscore inplace variants require canonical operator-family files.
- Check generated shared-file layouts against the current upstream FlagGems registration layout.
- Before final validation, verify extracted target tests and benchmarks still preserve the validation intent of the generated worktree; repair extraction-induced validation breakage in `{PR_WORKTREE}` when needed.
- Check target files, pytest marks, benchmark `op_name`, yaml id, ops package exports, and top-level dispatch registration describe the same public operator id.
- Check public operator ids and generated file names use the current FlagGems naming style and avoid CamelCase unless required by upstream taxonomy.
- Check that `conf/operators.yaml` contains explicit `description`, `for`, `labels`, `kind`, and `stages` fields for every target yaml entry before extraction or final validation.
- Check `conf/operators.yaml` descriptions explain operator semantics rather than only restating that a Triton kernel was added.
- Check sorted insertion points in `conf/operators.yaml`, `src/flag_gems/__init__.py`, and `src/flag_gems/ops/__init__.py`.
- Check whether the target operator is an alias or overload of an existing FlagGems implementation.
- Check whether the target belongs under `src/flag_gems/fused` or `src/flag_gems/ops`.
- Check `conf/operators.yaml` labels, kind, stages, and `for` entries against the current upstream taxonomy.
- If `_FULL_CONFIG` or exported wrappers include inplace or overload variants, check that each submitted yaml entry is explicit and has real metadata rather than relying on generated defaults.
- For non-ATen operators, check there is no pseudo-ATen `_FULL_CONFIG` entry and no `aten` label.
