# Register Checklist

Use this checklist to enrich your workflow todos and verify the work:

- Locate related existing kernel, test, and benchmark files for the same operator family.
- Check kernel files keep the KernelGen header and export only target wrappers.
- Check exported wrappers are registered, tested, and benchmarked consistently.
- Check `_out`, inplace, and overload variants for full coverage before exporting them.
- Check whether leading underscores or trailing-underscore inplace variants require canonical operator-family files.
- Check generated shared-file layouts against the current upstream FlagGems registration layout.
- Check target files, pytest marks, benchmark `op_name`, yaml id, ops package exports, and top-level dispatch registration describe the same public operator id.
- Check public operator ids and generated file names use the current FlagGems naming style and avoid CamelCase unless required by upstream taxonomy.
- Check sorted insertion points in `conf/operators.yaml`, `src/flag_gems/__init__.py`, and `src/flag_gems/ops/__init__.py`.
- Check whether the target operator is an alias or overload of an existing FlagGems implementation.
- Check whether the target belongs under `src/flag_gems/fused` or `src/flag_gems/ops`.
- Check `conf/operators.yaml` labels, kind, stages, and `for` entries against the current upstream taxonomy.
