# Final PR Spec

Applies to: `agents/final-validate-pr.md`.

## Pre-submit validation

Before commit and push, run formatting checks on only the target files. Then run PR-branch accuracy tests and `--level core` benchmark. Re-check the branch diff against the expected file set.

The final validation agent must manually verify the checks formerly automated by helper scripts:

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

Commit message format:

`[KernelGen][Nvidia] Add <op> operator with Triton kernel`

The commit message must not contain co-author trailers.

Push branch `pr/<op>` to the inferred or user-provided fork remote.

## PR body

Create the PR against the inferred or user-provided upstream repo and base branch. The PR body is English and includes:

- Summary or Description;
- Testing / Correctness with commands;
- Performance with dtype/case/speedup table;
- Tested-on;
- Multi-backend Testing, using real data or `N/A`;
- Files Changed.

Do not create a PR if performance data is missing, benchmark has zero cases, tests failed, or required body sections are incomplete.
