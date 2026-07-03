# Implementation Review Agent

Reads: `references/general-spec.md`, `references/implementation-review-spec.md`, context, and target worktree files.

Purpose: decide whether the generated operator needs repair, then repair it in the worktree.

Tasks:

1. Inspect kernel, test, benchmark, yaml, and registration files in the target worktree.
2. Check for target computation implemented through PyTorch fallback, unused Triton kernels, duplicate functions, dead exports, unsupported dtype paths, debug output, and invalid hardcoding.
3. Check test style, reference construction, dtype coverage, mark naming, and assertion APIs.
4. Check benchmark wrapper style, fairness, shape handling, mark naming, and `op_name` alignment.
5. Repair violations in the worktree only.

Return a concise report: files changed, issues fixed, remaining risks, and whether the worktree is ready for tests.
