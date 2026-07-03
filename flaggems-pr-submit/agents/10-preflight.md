# Preflight Agent

Scope: read `references/spec.md`, the context JSON, and the preflight script.

Input: context JSON path, raw operator name, and mode (`new PR` or `reviewer update`).

New PR command:

```bash
python <SKILL_DIR>/scripts/preflight.py \
  --context <context.json> \
  --op <raw_op> \
  --create-branch
```

Reviewer update command:

```bash
python <SKILL_DIR>/scripts/preflight.py \
  --context <context.json> \
  --op <raw_op> \
  --reviewer-update
```

Responsibilities:

- Normalize the operator name through the norm xlsx.
- Resolve `op`, `op_id`, `module`, worktree path, and branch name.
- Fetch the user-provided upstream/base and verify no upstream kernel/yaml id conflict.
- Create/reset `pr/<op>` for a new PR, or checkout existing `pr/<op>` for reviewer updates.
- Return the JSON printed by `preflight.py` to the main agent.

Stop if norm lookup fails, worktree does not exist, git remotes are wrong, upstream already contains the operator, or branch preparation fails.
