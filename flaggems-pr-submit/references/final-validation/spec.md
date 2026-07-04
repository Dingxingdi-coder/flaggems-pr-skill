# Final Validation Spec

Applies to: final-validation subagent.

The final subagent works in `{GEN_WORKTREE}` on the generated branch. Do not create `pr/<op>`.

Read `references/rule-structure.md`, `references/shared/test-benchmark.md`, and `references/shared/reviewer-learned-rules.md` before running the final gate.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{MODULE}`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{GPU}`: assigned GPU id.
- `{FORK_REMOTE}`: remote used to publish the generated branch.
- `{UPSTREAM_REPO}`: upstream GitHub repository, normally `flagos-ai/FlagGems`.
- `{BASE_BRANCH}`: upstream base branch, normally `master`.
- `{UPSTREAM_REF}`: fetched upstream ref produced by the resolver script.
- `{TESTED_ON}`: real tested-on environment text.

## Pre-submit validation

Before commit and push:

1. run `scripts/operator_static_gate.py` exactly as instructed by the prompt template;
2. run formatting checks on only the target files;
3. run the gen-branch accuracy test;
4. run the gen-branch `--level core` benchmark;
5. re-check that the staged file list is target-only.

The final validation subagent manually verifies semantic blockers not covered by the static script:

- no torch fallback for target computation;
- exported functions have test and benchmark coverage;
- benchmark compares equivalent torch/gems work;
- benchmark has nonzero cases and real speedup data;
- PR body uses only real test, benchmark, and tested-on data.

Do not create a PR if the static gate fails, performance data is missing, benchmark has zero cases, tests failed, or required PR body sections are incomplete.

## Git

Stage target files explicitly by path. Do not stage the whole repository.

Commit message format: `[KernelGen][Nvidia] Add <op> operator with Triton kernel`.

The commit message must not contain co-author trailers.

Push the current generated branch, normally `gen-<op>`, to the inferred or user-provided fork remote.

## PR body

Create the PR from the generated branch against `{UPSTREAM_REPO}:{BASE_BRANCH}`. The PR body is English and includes:

- Summary or Description;
- Testing / Correctness with commands;
- Performance with dtype/case/speedup table;
- Tested-on;
- Multi-backend Testing, using real data or `N/A`;
- Files Changed.

## Return format

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.
