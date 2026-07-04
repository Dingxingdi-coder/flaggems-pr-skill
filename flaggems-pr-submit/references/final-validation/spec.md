# Final Validation Spec

Applies to: final-validation subagent.

The final subagent works in `{GEN_WORKTREE}` on the generated branch. Do not create `pr/<op>`.

## Inputs

- `{OP}`: normalized operator name.
- `{OP_ID}`: public operator id used by pytest mark, yaml id, test file, benchmark file, and benchmark `op_name`.
- `{MODULE}`: target module/kernel filename stem under `src/flag_gems/ops/`.
- `{GEN_WORKTREE}`: generated worktree path for this operator.
- `{GPU}`: assigned GPU id.
- `{FORK_REMOTE}`: remote used to publish the generated branch.
- `{UPSTREAM_REPO}`: upstream GitHub repository, normally `flagos-ai/FlagGems`.
- `{BASE_BRANCH}`: upstream base branch, normally `master`.
- `{TESTED_ON}`: real tested-on environment text.

## Local specs to read

Before PR creation, also follow `references/final-validation/test-benchmark.md` for the accuracy and benchmark rules used by this final gate.

## Pre-submit validation

Before commit and push, run formatting checks on only the target files. Then run gen-branch accuracy tests and `--level core` benchmark. Re-check the branch diff against the expected file set.

The final validation subagent manually verifies:

- kernel file exists and starts with KernelGen header;
- no `print()` in kernel/test/benchmark;
- wrapper registration exists in both registration files;
- yaml entry is complete and unique;
- yaml `id`, pytest mark, and benchmark `op_name` align;
- no torch fallback for target computation;
- no `gems_assert_close(..., rtol=...)`;
- no unrelated operator files in diff;
- exported functions have test and benchmark coverage;
- benchmark has nonzero cases and real speedup data.

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

Do not create a PR if performance data is missing, benchmark has zero cases, tests failed, or required body sections are incomplete.

## Return format

Return the PR URL, exact validation commands, target files staged, commit hash, benchmark summary, and any blocking issue.
