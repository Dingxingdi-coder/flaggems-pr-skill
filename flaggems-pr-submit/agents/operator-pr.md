# Per-Operator PR Agent

Read `references/general-spec.md`, `references/operator-agent-spec.md`, the context JSON, and target worktree files only.

Input: one raw or normalized operator name and the context JSON path.

Command:

```bash
python <SKILL_DIR>/scripts/submit_operator.py <op> --context <context.json>
```

The script runs the initial PR pipeline for this one operator: normalize name, check upstream conflicts, create `pr/<op>`, run static worktree gate, run worktree tests and benchmark, extract repaired worktree, run strict validation, run PR-branch tests and benchmark, commit, push, and create the PR.

If the script stops at the worktree quality gate or worktree tests, inspect and repair the worktree according to `operator-agent-spec.md`, then rerun the same command.

Return to the main agent:

- normalized operator name;
- PR URL on success;
- failed stage, failed command, and concise reason on failure;
- benchmark case count and mean speedup if benchmark ran.

Do not handle review follow-up in this skill version.
