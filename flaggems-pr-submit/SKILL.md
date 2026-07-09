---
name: flaggems-pr-submit
description: Submit initial FlagGems NVIDIA general operator PRs from generated gen-* worktrees.
---
# FlagGems Initial Operator PR Submission

You are the main agent. Your role is orchestration and source-metadata gating: infer shared context, resolve generated worktree context, repair generated-worktree source metadata when resolver or extraction cannot identify the target, assign GPU slots, dispatch subagents, run the deterministic PR-worktree preparation script, collect results, and stop on blockers. Implementation, validation, registration, and final draft PR creation work is performed by subagents.

## Rule Model

Hard constraints are mechanically checkable rules. Runtime scripts under `scripts/` are the source of truth. Subagents must run the relevant scripts instead of reimplementing equivalent checks in prose.

Checklists are ordered environment, code, validation-data, and registration consistency checks that subagents must complete before acting. They live in `references/general/checklist.md` and in each stage's `checklist.md`.

Soft constraints require semantic judgment about code, reviewer intent, test behavior, benchmark meaning, registration consistency, or PR truthfulness while a subagent acts. They live in `references/general/soft-constraints.md` and in each stage's `soft-constraints.md`.

## Subagents Principles

Before dispatching any subagent, replace every `{...}` placeholder in the relevant template.

The main agent must not do subagent implementation, validation, registration, or PR drafting work, and must not read stage-specific subagent reference files during the normal workflow. Source-metadata repair needed for resolver or extraction is main-agent work, not subagent work. When dispatching a subagent, remind it to stay within its assigned stage and not perform other stages' duties.

All workflow shell commands, including main-agent commands, must run through `docker exec "{CONTAINER}"` unless the user explicitly says otherwise. For Python, pytest, and benchmark commands inside Docker, subagents must use the assigned worktree's virtual environment Python, such as `{GEN_WORKTREE}/.venv/bin/python -m ...` or `{PR_WORKTREE}/.venv/bin/python -m ...`.

If any stage blocks, stop that operator immediately and report the blocked stage, the command that failed or blocked, the reason, and the required user input or repair direction.

Do not skip stages, invent benchmark results, or fabricate multi-backend data.

## Checklist

You MUST create a task for each of these items and complete them in order:

- [ ] **Step 0: Gather Context** — determine available GPU slots, confirm a GitHub token is available, collect raw operator names and infer repository and worktree roots. Stop if any context is missing.
- [ ] **Step 1: Resolve Operator Context** — for each raw operator, run the context resolver; if it fails because source metadata is missing or inconsistent, locate the generated worktree, repair only the source metadata needed to identify the target, rerun the resolver, and stop that operator if the resolver still fails.
- [ ] **Step 2: Implementation Review and Worktree Validation** — dispatch `implementation-review` and `worktree-test-benchmark`; block on failure.
- [ ] **Step 3: Prepare PR Worktree** — main agent runs the deterministic clean PR worktree script; if extraction fails because source metadata is missing or inconsistent, repair only the generated-worktree source metadata needed for extraction, rerun the failed command, and block if it still fails.
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
docker exec "{CONTAINER}" bash -lc 'python "{skill_root}/scripts/name-worktree/resolve_op_context.py" --raw-op "{raw_op}" --worktree-root "{worktree_root}" --check-upstream'
```

If the resolver exits nonzero or cannot complete exactly as invoked above, the main agent must first determine whether this is a generated-worktree source-metadata problem before stopping. Do not dispatch a subagent while the resolver is failing.

For resolver failures, perform this main-agent repair gate:

1. If `--check-upstream` reports an upstream conflict in the current PR base or legacy `flagos-ai/FlagGems`, stop immediately and report all printed `UPSTREAM_*` and `OP_SOURCE_*` lines. Do not treat upstream conflicts as metadata-repair failures or infer PR URLs manually.
2. Locate the candidate generated worktree from git `gen-*` branches, registered worktrees, and directories under `{worktree_root}`. If no candidate or multiple candidates match `{raw_op}`, stop that operator and report the command, error, candidates, and required user input.
3. Inspect only target-identification surfaces in that generated worktree: `conf/operators.yaml`, `src/flag_gems/__init__.py`, `src/flag_gems/ops/__init__.py`, candidate files under `src/flag_gems/ops/`, target pytest marks and test names, target benchmark entries, and `torch.ops.aten` overload names. This inspection is for identity metadata only.
4. If the resolver could not classify `{raw_op}` and the inspection identifies a single corresponding operator identity, rerun the resolver with that corresponding operator as `{raw_op}` before repairing metadata or stopping. Preserve the resolver output and report any upstream-conflict evidence it prints.
5. If the generated worktree has a single supported target identity but missing or inconsistent source metadata, repair that metadata in `{GEN_WORKTREE}`. Valid main-agent repairs are limited to metadata and naming needed by resolver or extraction: YAML operator entries, labels, descriptions, `for` targets, public API/reference metadata for non-ATen targets, import/export/registration names, target source filename, pytest marks or test function names, and benchmark operator names. Do not rewrite kernel algorithms, validation logic, benchmark methodology, registration policy, or PR text in this gate.
6. For ATen targets, the repaired metadata must identify an exact `torch.ops.aten` schema or overload. Do not retarget to the nearest ATen schema automatically when evidence is ambiguous; report the closest candidate schemas and stop for human repair.
7. For non-ATen targets, the repaired metadata must identify the submitted public target consistently enough for resolver and extraction to proceed. Preserve resolver output as source metadata; do not require the resolver to synthesize public API, reference, or downstream-use documentation that is not present in the generated worktree.
8. Rerun the resolver exactly as invoked above after each repair. If it still exits nonzero, stop that operator and report the command, error, what was inspected or repaired, and the required user input or repair direction.

The resolver also reports `IS_ATEN`, `PUBLIC_API`, `REFERENCE`, `REFERENCE_ARGS`, `LABELS`, and `DESCRIPTION`. Preserve these values and pass them to all later subagent prompts, even when some optional non-ATen fields are empty. For `IS_ATEN=false`, do not describe the operator as `aten::{OP_ID}` and do not add an `aten` label.

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
docker exec "{CONTAINER}" bash -lc 'DESC_FILE=$(mktemp) && trap "rm -f \"$DESC_FILE\"" EXIT && cat > "$DESC_FILE" <<'"'"'EOF'"'"'
{DESCRIPTION}
EOF
python "{skill_root}/scripts/prepare-pr-worktree/prepare_pr_worktree.py" \
  --op "{OP}" \
  --op-id "{OP_ID}" \
  --module "{MODULE}" \
  --is-aten "{IS_ATEN}" \
  --labels "{LABELS}" \
  --yaml-description-file "$DESC_FILE" \
  --repo-root "{repo_root}" \
  --worktree-root "{worktree_root}" \
  --gen-worktree "{GEN_WORKTREE}" \
  --upstream-ref "{UPSTREAM_REF}"'
```

If this command exits nonzero or cannot complete exactly as invoked above, the main agent must first determine whether extraction failed because generated-worktree source metadata is missing or inconsistent. If so, repair only the metadata and naming surfaces listed in the resolver repair gate, rerun the same prepare command, and stop the operator if the command still fails. If the failure is not a source-metadata or target-identification failure, stop that operator immediately and report the command, error, and required user input or repair direction.

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
