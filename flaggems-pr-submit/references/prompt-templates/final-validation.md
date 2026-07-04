# Final Validation Template

The template is:
```
You perform final validation and initial PR creation for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}`, module `{MODULE}`, GPU `{GPU}`, fork remote `{FORK_REMOTE}`, upstream repo `{UPSTREAM_REPO}`, base branch `{BASE_BRANCH}`, and tested-on `{TESTED_ON}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `references/final-validation/spec.md` and follow the spec.

Validate file set, static rules, formatting, accuracy test, core benchmark, benchmark summary, explicit staging, commit, branch publication, and initial contribution creation against `{UPSTREAM_REPO}:{BASE_BRANCH}`. Use tested-on `{TESTED_ON}` and real benchmark data. Return URL or blocking issue.
```

Note:
* `{...}` are placeholders to be replaced by real values.
