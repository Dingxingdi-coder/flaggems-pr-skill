# Register Soft Constraints

- Append to related existing kernel, test, and benchmark files for the same operator family only when preserving existing functions and adding target operator coverage.
- Kernel files must keep the KernelGen header and export only target wrappers.
- Exported wrappers must be registered, tested, and benchmarked consistently.
- `_out`, inplace, and overload variants must either be fully covered or remain unexported.
- Leading underscores remain part of public operator ids when required, but trailing-underscore inplace variants must use the canonical non-suffixed operator-family files.
- Generated shared-file layouts must be adapted to the current upstream FlagGems registration layout inside the generated worktree.
- Validation-file repairs should preserve the generated worktree's tested behavior and benchmark methodology, scoped to `{OP_ID}`; do not invent new coverage or change operator semantics to make validation pass.
- Treat failures caused by extraction losing surrounding validation context as extraction repairs; treat failures after the target operator actually executes as validation blockers unless the cause is clearly test harness breakage.
- Target files, pytest marks, benchmark `op_name`, yaml id, ops package exports, and top-level dispatch registration must describe the same public operator id.
- Keep new entries in `conf/operators.yaml`, `src/flag_gems/__init__.py`, and `src/flag_gems/ops/__init__.py` in the surrounding sorted order.
- When a target operator is an alias or overload of an existing FlagGems implementation, register and cover the existing implementation instead of adding duplicate wrappers, kernels, tests, or benchmarks.
- Do not let extraction scripts synthesize yaml metadata such as labels, kind, stages, descriptions, `for` targets, or inplace entries; populate them from upstream taxonomy and target semantics.
- Place non-ATen fused operators under `src/flag_gems/fused` when they are model/framework fusions. Non-ATen public math or reduction APIs may remain under `src/flag_gems/ops` when that matches the current upstream taxonomy. Keep ATen overrides under `src/flag_gems/ops`.
- Populate `conf/operators.yaml` labels, kind, stages, and `for` entries from the current upstream taxonomy for the actual public Torch or fused operator.
- Use lower snake-case public operator ids for generated fused or custom operators unless the upstream taxonomy requires a different spelling.
- Non-ATen operators must not be registered as pseudo-ATen overrides in `_FULL_CONFIG` and must not carry the `aten` yaml label.
