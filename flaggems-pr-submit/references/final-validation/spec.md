# Final Validation Spec

Applies to: `final-validation` subagent.

The final validation subagent works in `{GEN_WORKTREE}` on the generated branch. Do not create `pr/<op>`.

## Required Reading

- `references/general/soft-constraints.md`
- `references/final-validation/spec.md`
- `references/final-validation/soft-constraints.md`

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{MODULE}`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `{GEN_WORKTREE}`: generated worktree path.
- `{GPU}`: assigned GPU id.
- `{FORK_REMOTE}`: remote used to publish the generated branch.
- `{UPSTREAM_REPO}`: upstream GitHub repository, normally `flagos-ai/FlagGems`.
- `{BASE_BRANCH}`: upstream base branch, normally `master`.
- `{UPSTREAM_REF}`: fetched upstream ref produced by the resolver script.
- `{TESTED_ON}`: real tested-on environment text.

## Pre-submit Validation

Before commit and push:

1. Run the static gate exactly as instructed by the prompt template.
2. Run formatting checks on only the target files.
3. Run the generated-branch accuracy test.
4. Run the generated-branch `--level core` benchmark.
5. Re-check that the staged file list is target-only.

Manually verify semantic blockers not covered by the static gate:

- no torch fallback for target computation;
- exported functions have test and benchmark coverage;
- benchmark compares equivalent torch and FlagGems work;
- benchmark has nonzero cases and real speedup data;
- PR body uses only real test, benchmark, and tested-on data.

## Git and PR

Stage target files explicitly by path. Do not stage the whole repository.

Commit message format:

```text
[KernelGen][Nvidia] Add <op> operator with Triton kernel
```

Push the current generated branch to `{FORK_REMOTE}` and create the initial PR against `{UPSTREAM_REPO}:{BASE_BRANCH}`.

The PR body is English and includes summary, testing or correctness, performance, tested-on, multi-backend testing, and files changed.

## Hard Constraints

Before staging, run:

```bash
python "{SKILL_ROOT}/scripts/general/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"
```

## Return Format

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.
