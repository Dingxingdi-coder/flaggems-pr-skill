---
name: flaggems-pr-submit
description: Submit initial FlagGems NVIDIA general operator PRs from generated gen-* worktrees.
---

# FlagGems Initial Operator PR Submission

You are the main agent. Your role is orchestration only: infer shared context, resolve generated worktree context, assign GPU slots, dispatch subagents, collect their results, and stop on blockers. All implementation, validation, registration, and final PR creation work is performed by subagents.

## Rule Model

Hard constraints are mechanically checkable rules. Runtime scripts under `scripts/` are the source of truth. Subagents must run the relevant scripts instead of reimplementing equivalent checks in prose.

Soft constraints require semantic judgment about code, reviewer intent, test behavior, benchmark meaning, registration consistency, or PR truthfulness. They live in `references/general/soft-constraints.md` and in each stage's `soft-constraints.md`.

## Checklist

## Checklist

You MUST create a task for each of these items and complete them in order:

- [ ] **Step 0: Gather Context** — determine available GPU slots, collect raw operator names and norm Excel path and infer repository and worktree roots. Stop if any context is missing.
- [ ] **Step 1: Resolve Operator Context** — for each raw operator, run the context resolver; if it fails, stop that operator and report the error.
- [ ] **Step 2: Dispatch Subagents in Order** — dispatch the subagents; block on failure.

## Workflow

### Get the Context

- Use `nvidia-smi` to determine available GPU slots and tested-on text.
- The user provides at least one raw operator name. The number of operators must not exceed available GPU slots. Treat the provided operator name as `{raw_op}`.
- The user provides the path to `规范名.xlsx` as `{norm_xlsx}`.
- `<repo_root>` is the cwd, `<worktree_root>` is `<repo_root>/.worktrees/`.
- `{skill_root}` is the root of the skill.

If there is any context you don't get, stop and ask the user for it. Do not guess or assume.

### Resolve Operator Context

For each raw operator, run the resolver before dispatching any subagent:

```bash
python "{skill_root}/scripts/name-worktree/resolve_op_context.py" --raw-op "{raw_op}" --norm-xlsx "{norm_xlsx}" --worktree-root "{worktree_root}"
```

If the resolver exits nonzero, stop that operator immediately and report the command, error, and required user input or repair direction.

### Subagent Dispatch

Every operator must be processed by dispatching subagents through the required stages in this exact order: 
* `implementation-review` (prompt in `references/prompt-templates/implementation-review.md`)
* `worktree-test-benchmark` (prompt in `references/prompt-templates/worktree-test-benchmark.md`)
* `register` (prompt in `references/prompt-templates/register.md`)
* `final-validation` (prompt in `references/prompt-templates/final-validation.md`)

Each stage must be run by a subagent using its corresponding prompt template.

Before dispatching any subagent, replace every `{...}` placeholder in the relevant template.

If any stage blocks, stop that operator immediately and report the blocked stage, the command that failed or blocked, the reason, and the required user input or repair direction. 

Do not skip stages, invent benchmark results, or fabricate multi-backend data.
