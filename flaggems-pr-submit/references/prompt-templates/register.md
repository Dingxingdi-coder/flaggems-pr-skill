# Register Template

The template is:
```
You handle extraction and registration for `{OP}`. Your working directory is `{GEN_WORKTREE}`. Use op_id `{OP_ID}`, module `{MODULE}`, and upstream ref `{UPSTREAM_REF}`.

Skill root is `{SKILL_ROOT}`.

For repository operations, work only inside `{GEN_WORKTREE}`. You may read the skill reference files named below, but you must not inspect or modify other worktrees or the main checkout.

Read `{SKILL_ROOT}/references/rule-structure.md`, `{SKILL_ROOT}/references/shared/reviewer-learned-rules.md`, and `{SKILL_ROOT}/references/register/spec.md`; then follow the spec.

After registration edits, run:
python "{SKILL_ROOT}/scripts/operator_static_gate.py" --op "{OP}" --op-id "{OP_ID}" --module "{MODULE}" --base-ref "{UPSTREAM_REF}"

Return changed files, static gate result, and blocking issues.
```

Note:
* `{...}` are placeholders to be replaced by real values.
