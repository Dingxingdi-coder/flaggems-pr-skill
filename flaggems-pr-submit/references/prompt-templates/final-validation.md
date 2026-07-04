# Final Validation Template

The template is:
```
You perform final validation and initial PR creation for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}`, module `{MODULE}`, GPU `{GPU}`, fork remote `{FORK_REMOTE}`, upstream repo `{UPSTREAM_REPO}`, base branch `{BASE_BRANCH}`, upstream ref `{UPSTREAM_REF}`, and tested-on `{TESTED_ON}`.

Skill root is `{SKILL_ROOT}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `{SKILL_ROOT}/references/rule-structure.md`, `{SKILL_ROOT}/references/shared/reviewer-learned-rules.md`, `{SKILL_ROOT}/references/shared/test-benchmark.md`, and `{SKILL_ROOT}/references/final-validation/spec.md`; then follow the spec.

Before staging, run:
python "{SKILL_ROOT}/scripts/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"

Validate formatting, accuracy test, core benchmark, benchmark summary, explicit staging, commit, branch publication, and initial contribution creation against `{UPSTREAM_REPO}:{BASE_BRANCH}`. Use tested-on `{TESTED_ON}` and real benchmark data. Return URL or blocking issue.
```

Note:
* `{...}` are placeholders to be replaced by real values.
