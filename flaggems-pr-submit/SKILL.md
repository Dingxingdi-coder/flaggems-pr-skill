---
name: flaggems-pr-submit
description: Submit initial FlagGems NVIDIA general operator PRs from generated gen-* worktrees.
---
# FlagGems Initial Operator PR Submission

You are the main agent. Your role is orchestration only: infer shared context, resolve generated worktree context, assign GPU slots, dispatch subagents, run the deterministic PR-worktree preparation script, collect results, and stop on blockers. All implementation, validation, registration, and final PR creation work is performed by subagents.

## Rule Model

Hard constraints are mechanically checkable rules. Runtime scripts under `scripts/` are the source of truth. Subagents must run the relevant scripts instead of reimplementing equivalent checks in prose.

Soft constraints require semantic judgment about code, reviewer intent, test behavior, benchmark meaning, registration consistency, or PR truthfulness. They live in `references/general/soft-constraints.md` and in each stage's `soft-constraints.md`.

## Subagents Principles

Before dispatching any subagent, replace every `{...}` placeholder in the relevant template.

If any stage blocks, stop that operator immediately and report the blocked stage, the command that failed or blocked, the reason, and the required user input or repair direction.

Do not skip stages, invent benchmark results, or fabricate multi-backend data.

## Checklist

You MUST create a task for each of these items and complete them in order:

- [ ] **Step 0: Gather Context** — determine available GPU slots, collect raw operator names and infer repository and worktree roots. Stop if any context is missing.
- [ ] **Step 1: Resolve Operator Context** — for each raw operator, run the context resolver; if it fails, stop that operator and report the error.
- [ ] **Step 2: Implementation Review and Worktree Validation** — dispatch `implementation-review` and `worktree-test-benchmark`; block on failure.
- [ ] **Step 3: Prepare PR Worktree** — main agent runs the deterministic clean PR worktree script; block on failure.
- [ ] **Step 4: Register and Final Validation** — dispatch `register` and `final-validation`; block on failure.

## Workflow

### Get the Context

- Use `nvidia-smi` to determine available GPU slots and tested-on text.
- The user provides at least one raw operator name that identifies an existing `gen-*` worktree or branch. The number of operators must not exceed available GPU slots. Treat the provided operator name as `{raw_op}`.
- `<repo_root>` is the cwd, `<worktree_root>` is `<repo_root>/.worktrees/`.
- `{skill_root}` is the root of the skill.

If there is any context you don't get, stop and ask the user for it. Do not guess or assume.

### Resolve Operator Context

For each raw operator, run the resolver before dispatching any subagent:

```bash
python "{skill_root}/scripts/name-worktree/resolve_op_context.py" --raw-op "{raw_op}" --worktree-root "{worktree_root}"
```

If the resolver exits nonzero or cannot complete exactly as invoked above, stop that operator immediately and report the command, error, and required user input or repair direction.

### Implementation Review and Worktree Validation

Every operator must first be processed by dispatching subagents through these stages in this exact order:

* `implementation-review` (prompt in `references/prompt-templates/implementation-review.md`)
* `worktree-test-benchmark` (prompt in `references/prompt-templates/worktree-test-benchmark.md`)

### Prepare PR Worktree

The main agent MUST run this step directly. Do not dispatch a subagent for this step.

Create a clean PR worktree from `{UPSTREAM_REF}`, then extract the target operator files from `{GEN_WORKTREE}` into it:

```bash
python "{skill_root}/scripts/prepare-pr-worktree/prepare_pr_worktree.py" \
  --op "{OP}" \
  --op-id "{OP_ID}" \
  --module "{MODULE}" \
  --repo-root "{repo_root}" \
  --worktree-root "{worktree_root}" \
  --gen-worktree "{GEN_WORKTREE}" \
  --upstream-ref "{UPSTREAM_REF}"
```

If this command exits nonzero or cannot complete exactly as invoked above, stop that operator immediately and report the command, error, and required user input or repair direction.

The command must output `{PR_BRANCH}`, `{PR_WORKTREE}`, and `{TARGET_FILES}`. Use these values for all later stages.

### Register and Final Validation

After the PR worktree is prepared, dispatch subagents through these stages in this exact order:

* `register` (prompt in `references/prompt-templates/register.md`)
* `final-validation` (prompt in `references/prompt-templates/final-validation.md`)

Do not dispatch `register` or `final-validation` against `{GEN_WORKTREE}`. They must use `{PR_WORKTREE}`.
