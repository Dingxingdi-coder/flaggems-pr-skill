# Constraint Ownership Map

Use this map to decide where a new rule belongs. `Hard` means the owning script must enforce it. `Soft` means the responsible agent must inspect it after reading the relevant spec.

| Constraint | Class | Enforcement / source of truth | Owner |
|---|---|---|---|
| Infer repo, worktree root, remotes, GPU, tested-on context | Soft | `SKILL.md` workflow | main agent |
| Keep operator count within GPU slots | Soft | `SKILL.md` workflow | main agent |
| Normalize raw operator names | Hard | `resolve_op_context.py` / `RESOLVE-H001` | `name-worktree` |
| Apply special naming rules | Hard | `resolve_op_context.py` / `RESOLVE-H002` | `name-worktree`, `register`, `final-validation` |
| Confirm target gen worktree and generated branch | Hard | `resolve_op_context.py` / `RESOLVE-H003`, `RESOLVE-H004` | `name-worktree` |
| Fetch upstream and check upstream kernel/yaml conflicts | Hard | `resolve_op_context.py` / `RESOLVE-H005` to `RESOLVE-H007` | `name-worktree` |
| Use the existing generated branch instead of a new PR branch | Soft | `SKILL.md` and stage specs | main agent, `name-worktree`, `final-validation` |
| Keep one PR to one aten operator family | Soft | semantic diff review | all subagents; final owner `final-validation` |
| Keep all subagent edits inside `{GEN_WORKTREE}` | Soft | prompt boundary plus final diff review | all subagents |
| Review and repair generated worktree first | Soft | `implementation-review/spec.md` | `implementation-review` |
| Confirm target computation uses Triton, FlagGems utilities, or valid helper code rather than torch fallback | Soft | semantic code review | `implementation-review`, `final-validation` |
| KernelGen header and debug `print()` absence | Hard | `operator_static_gate.py` / `STATIC-H003`, `STATIC-H004` | `register`, `final-validation` |
| Duplicate functions, dead exports, dtype support, hardcoded parameter comments | Soft | semantic code review | `implementation-review`, `final-validation` |
| Accuracy test mark and no explicit `rtol=` in `gems_assert_close` | Hard | `operator_static_gate.py` / `STATIC-H006`, `STATIC-H007` | `register`, `final-validation` |
| Accuracy test correctness, reference conversion, NaN handling, statistical validation | Soft | `implementation-review/spec.md` and `shared/test-benchmark.md` | `implementation-review`, `worktree-test-benchmark`, `final-validation` |
| Benchmark mark and `op_name` alignment | Hard | `operator_static_gate.py` / `STATIC-H008`, `STATIC-H009` | `register`, `final-validation` |
| Benchmark wrapper fairness, equivalent torch/gems work, nonzero cases, speedup threshold | Soft | `shared/test-benchmark.md` and semantic review | `implementation-review`, `worktree-test-benchmark`, `final-validation` |
| Changed-file boundary and required registration files | Hard | `operator_static_gate.py` / `STATIC-H001`, `STATIC-H002` | `register`, `final-validation` |
| yaml id uniqueness | Hard | `operator_static_gate.py` / `STATIC-H005` | `register`, `final-validation` |
| Exported wrappers are registered, tested, and benchmarked | Soft | semantic registration review | `register`, `final-validation` |
| Formatting checks, explicit staging, commit message | Soft | `final-validation/spec.md` and command output | `final-validation` |
| PR body completeness and truthful performance data | Soft | `final-validation/spec.md` | `final-validation` |
| Review follow-up exclusion for initial PR creation | Soft | `SKILL.md` scope | main agent, `final-validation` |
| Reviewer-derived rule intake and promotion | Soft-to-hard workflow | `reviewer-feedback-intake.md`, `soft-constraints.md`, owning scripts, and existing specs | maintenance agent |
| Skill rule/document/template consistency | Hard | `skill_meta_gate.py` / `META-H001` to `META-H004` | maintenance agent |
