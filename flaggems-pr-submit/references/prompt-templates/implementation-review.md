# Implementation Review Template

The template is:
```
You review and repair the generated implementation for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}`, module `{MODULE}`, and GPU `{GPU}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `references/implementation-review/spec.md` and follow the spec.

Return changed files, fixed issues, remaining risks, and whether tests may run.
```

Note:
* `{...}` are placeholders to be replaced by real values.
