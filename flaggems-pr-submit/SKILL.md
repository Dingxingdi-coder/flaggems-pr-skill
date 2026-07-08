---
name: flaggems-pr-submit
description: Submit initial FlagGems NVIDIA general operator PRs from generated gen-* worktrees.
---
# FlagGems Initial Operator PR Submission

You are the main agent. Your role is orchestration only: infer shared context, resolve generated worktree context, assign GPU slots, dispatch subagents, run the deterministic PR-worktree preparation script, collect results, and stop on blockers. All implementation, validation, registration, and final draft PR creation work is performed by subagents.

## Rule Model

Hard constraints are mechanically checkable rules. Runtime scripts under `scripts/` are the source of truth. Subagents must run the relevant scripts instead of reimplementing equivalent checks in prose.

Checklists are ordered environment, code, validation-data, and registration consistency checks that subagents must complete before acting. They live in `references/general/checklist.md` and in each stage's `checklist.md`.

Soft constraints require semantic judgment about code, reviewer intent, test behavior, benchmark meaning, registration consistency, or PR truthfulness while a subagent acts. They live in `references/general/soft-constraints.md` and in each stage's `soft-constraints.md`.

## Subagents Principles

Before dispatching any subagent, replace every `{...}` placeholder in the relevant template.

The main agent must not do subagent work or read stage-specific subagent reference files. When dispatching a subagent, remind it to stay within its assigned stage and not perform other stages' duties.

All workflow shell commands, including main-agent commands, must run through `docker exec "{CONTAINER}"` unless the user explicitly says otherwise. For Python, pytest, and benchmark commands inside Docker, subagents must use the assigned worktree's virtual environment Python, such as `{GEN_WORKTREE}/.venv/bin/python -m ...` or `{PR_WORKTREE}/.venv/bin/python -m ...`.

If any stage blocks, stop that operator immediately and report the blocked stage, the command that failed or blocked, the reason, and the required user input or repair direction.

Do not skip stages, invent benchmark results, or fabricate multi-backend data.

## Checklist

You MUST create a task for each of these items and complete them in order:

- [ ] **Step 0: Gather Context** — determine available GPU slots, confirm a GitHub token is available, collect raw operator names and infer repository and worktree roots. Stop if any context is missing.
- [ ] **Step 1: Resolve Operator Context** — for each raw operator, run the context resolver; if it fails, stop that operator and report the error.
- [ ] **Step 2: Implementation Review and Worktree Validation** — dispatch `implementation-review` and `worktree-test-benchmark`; block on failure.
- [ ] **Step 3: Prepare PR Worktree** — main agent runs the deterministic clean PR worktree script; block on failure.
- [ ] **Step 4: Register and Final Validation** — dispatch `register` and `final-validation`; block on failure.

## Workflow

### Get the Context

- Get the Docker container name for running commands from the user. Run all workflow shell commands through `docker exec "{CONTAINER}"` unless the user explicitly says otherwise. Tell the subagents to do so as well.
- Use `docker exec "{CONTAINER}" nvidia-smi` to determine available GPU slots and tested-on text.
- Confirm a GitHub token is available inside the Docker container by running `docker exec "{CONTAINER}" bash -lc 'python "{skill_root}/scripts/general/check_github_token.py"'`. The token must be available to commands executed in that container through `GH_TOKEN` or `GITHUB_TOKEN`; never print the token value, run `gh auth login`, or persist credentials on the shared machine.
- The user provides at least one raw operator name that identifies an existing `gen-*` worktree or branch. The number of operators must not exceed available GPU slots. Treat the provided operator name as `{raw_op}`.
- `<repo_root>` is the cwd, `<worktree_root>` is `<repo_root>/.worktrees/`.
- `{skill_root}` is the root of the skill.

If there is any context mentioned above you don't get, stop and ask the user for it. Do not guess or assume.

### Resolve Operator Context

For each raw operator, run the resolver before dispatching any subagent:

```bash
docker exec "{CONTAINER}" bash -lc 'python "{skill_root}/scripts/name-worktree/resolve_op_context.py" --raw-op "{raw_op}" --worktree-root "{worktree_root}"'
```

If the resolver exits nonzero or cannot complete exactly as invoked above, stop that operator immediately and report the command, error, and required user input or repair direction.

If the resolver reports that upstream already contains the operator, also report any `UPSTREAM_PR_URL`, `UPSTREAM_COMMIT`, and `UPSTREAM_EVIDENCE` lines it prints.

The resolver also reports `IS_ATEN`, `PUBLIC_API`, `REFERENCE`, `REFERENCE_ARGS`, `LABELS`, and `DESCRIPTION`. Preserve these values and pass them to all later subagent prompts. For `IS_ATEN=false`, do not describe the operator as `aten::{OP_ID}` and do not add an `aten` label.

After resolving each operator context and before dispatching subagents for `{GEN_WORKTREE}`, create or refresh a worktree-local virtual environment:

```bash
docker exec "{CONTAINER}" bash -lc 'cd "{GEN_WORKTREE}" && python -m venv --system-site-packages .venv && unset PIP_CONSTRAINT && PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ .venv/bin/python -m pip install -e .'
```

### Implementation Review and Worktree Validation

Every operator must first be processed by dispatching subagents through these stages in this exact order:

* `implementation-review` (prompt in `references/prompt-templates/implementation-review.md`)
* `worktree-test-benchmark` (prompt in `references/prompt-templates/worktree-test-benchmark.md`)

### Prepare PR Worktree

You MUST run this step directly. Do not dispatch a subagent for this step.

Create a clean PR worktree from `{UPSTREAM_REF}`, then extract the target operator files from `{GEN_WORKTREE}` into it:

```bash
docker exec "{CONTAINER}" bash -lc 'python "{skill_root}/scripts/prepare-pr-worktree/prepare_pr_worktree.py" \
  --op "{OP}" \
  --op-id "{OP_ID}" \
  --module "{MODULE}" \
  --is-aten "{IS_ATEN}" \
  --labels "{LABELS}" \
  --yaml-description "{DESCRIPTION}" \
  --repo-root "{repo_root}" \
  --worktree-root "{worktree_root}" \
  --gen-worktree "{GEN_WORKTREE}" \
  --upstream-ref "{UPSTREAM_REF}"'
```

If this command exits nonzero or cannot complete exactly as invoked above, stop that operator immediately and report the command, error, and required user input or repair direction.

The command must output `{PR_BRANCH}`, `{PR_WORKTREE}`, and `{TARGET_FILES}`. Use these values for all later stages.

After the PR worktree is prepared and before dispatching subagents for `{PR_WORKTREE}`, create or refresh a worktree-local virtual environment:

```bash
docker exec "{CONTAINER}" bash -lc 'cd "{PR_WORKTREE}" && python -m venv --system-site-packages .venv && unset PIP_CONSTRAINT && PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ .venv/bin/python -m pip install -e .'
```

### Register and Final Validation

After the PR worktree is prepared, dispatch subagents through these stages in this exact order:

* `register` (prompt in `references/prompt-templates/register.md`)
* `final-validation` (prompt in `references/prompt-templates/final-validation.md`)

Do not dispatch `register` or `final-validation` against `{GEN_WORKTREE}`. They must use `{PR_WORKTREE}`.
