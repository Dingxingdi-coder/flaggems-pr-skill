# Final Validation Template

Fields: `{OP}`, `{GEN_WORKTREE}`, `{OP_ID}`, `{MODULE}`, `{GPU}`, `{FORK_REMOTE}`, `{UPSTREAM_REPO}`, `{BASE_BRANCH}`, `{TESTED_ON}`.

Prompt to send: You perform final validation for `{OP}`. Read `references/final-pr-spec.md` and `references/test-benchmark-spec.md`. Work directory is `{GEN_WORKTREE}`. Stay inside that directory. Use GPU `{GPU}`. Validate file set, static rules, formatting, accuracy test, core benchmark, benchmark summary, explicit staging, commit, branch publication, and initial contribution creation against `{UPSTREAM_REPO}:{BASE_BRANCH}`. Use tested-on `{TESTED_ON}` and real benchmark data. Return URL or blocking issue.
