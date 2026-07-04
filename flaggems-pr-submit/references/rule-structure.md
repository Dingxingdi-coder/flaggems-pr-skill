# Rule Structure and Maintenance Model

This skill keeps the existing main-agent dispatching specialist subagents structure. The maintainable boundary is the rule type, not the number of subagents.

## Necessary process

The PR flow must keep these steps for every operator:

1. infer execution context from the working repository: GPU slots, fork remote, upstream remote, upstream base branch, worktree root, and tested-on text;
2. normalize the raw operator name with `规范名.xlsx`;
3. resolve the generated worktree and verify it is on the matching `gen-*` branch;
4. fetch upstream and stop when upstream already has the target kernel module or yaml `id`;
5. repair generated implementation, tests, benchmark, yaml, and registration in the target gen worktree only;
6. run operator accuracy tests and the operator `--level core` benchmark on the assigned GPU;
7. run deterministic static gates before staging;
8. stage target files explicitly, commit on the generated branch, push that branch, and create the initial PR against `flagos-ai/FlagGems:<base>`.

## Unnecessary process

Do not keep these as skill steps:

- creating a separate `pr/<op>` branch when the generated `gen-*` branch is already the PR branch;
- asking the user for values that can be inferred from `git remote -v`, `nvidia-smi`, or the resolver script output;
- manually repeating deterministic name, worktree, upstream conflict, yaml-id, mark/op_name, and changed-file checks when a script covers them;
- duplicating the same test and benchmark rules in multiple stage-specific documents;
- inspecting or editing the main checkout or other generated worktrees from a subagent;
- staging the whole repository with `git add .`;
- broad benchmark sweeps unrelated to the target operator.

## Rule types

### Mechanical hard rules

Mechanical hard rules are deterministic checks with a stable command-line interface. They belong under `scripts/`, and subagents must run the script instead of reimplementing the check in prose.

Current scripts:

- `scripts/resolve_op_context.py`: norm-name lookup, special-op mapping, generated worktree resolution, branch check, upstream fetch, upstream kernel/yaml conflict check.
- `scripts/operator_static_gate.py`: target file-set boundary, KernelGen header, `print()` ban, yaml-id uniqueness, pytest mark alignment, benchmark `op_name` alignment, and `gems_assert_close(..., rtol=...)` ban.

### Semantic review rules

Semantic review rules are still blocking when clearly violated, but they require code understanding. Keep them in stage specs under `references/<subagent>/` or shared specs under `references/shared/`.

Examples: target computation must not be a PyTorch fallback, benchmark torch/gems work must be equivalent, probability operators need statistical validation, and unsupported dtype paths need a wrapper check or a test explanation.

### Reviewer-learned soft rules

Rules learned from `[KernelGen][Nvidia]` PR reviews are maintained in `references/shared/reviewer-learned-rules.md`. Add a rule there only after it is observed in contributor/reviewer interaction. If a reviewer-learned rule becomes deterministic and stable, move it into a script and leave a short pointer in the document.
