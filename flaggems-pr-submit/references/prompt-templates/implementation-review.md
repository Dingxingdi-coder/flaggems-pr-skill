# Implementation Review Template

Fields: `{OP}`, `{GEN_WORKTREE}`, `{OP_ID}`, `{MODULE}`, `{GPU}`.

Prompt to send: You review and repair the generated implementation for `{OP}`. Read `references/implementation-review-spec.md`. Work directory is `{GEN_WORKTREE}`. All file reads and edits must stay inside this directory. Use op_id `{OP_ID}`, module `{MODULE}`, GPU `{GPU}`. Inspect kernel, tests, benchmark, yaml, and registration files. Fix violations in the gen worktree. Return changed files, fixed issues, remaining risks, and whether tests may run.
