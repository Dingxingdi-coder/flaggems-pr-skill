# General Spec

This file applies to the main agent and every per-operator agent.

## Inputs and defaults

The user must provide at least one operator. The user may provide multiple operators, but the count must not exceed the available GPU slots. If GPU count cannot be inferred, ask for `--gpu` or `--gpu-map`.

Optional values are inferred when possible:

- `repo_dir`: current working directory.
- `worktree_root`: `<repo_dir>/.worktrees`.
- `norm_xlsx`: `--norm-xlsx`, `FLAGGEMS_NORM_XLSX`, `<repo_dir>/规范名.xlsx`, then `<repo_dir>/../规范名.xlsx`.
- `upstream_remote` and `fork_remote`: inferred from `git remote -v`.
- `upstream_repo` and `fork_repo`: inferred from remote URLs.
- `base_branch`: inferred from local upstream refs, otherwise `master`.
- `tested_on`: inferred from `nvidia-smi`, otherwise ask the user.

If inference is ambiguous or wrong, stop and ask the user for the exact value.

## Orchestration

The main agent creates one context JSON with `scripts/context.py`. Then it dispatches one independent operator agent per normalized operator. Each operator agent runs the complete initial PR pipeline for its operator.

The main agent may run operators concurrently only when each operator has a distinct GPU assignment and a distinct `pr/<op>` branch. Otherwise run sequentially.

## Scope

Each PR contains one aten operator family only. Do not include opportunistic cleanup, unrelated generated code, or other operators.

Initial PR creation is in scope. Review follow-up is out of scope for this skill version.

## Git prohibitions

Never use `git add -A`, `git add .`, `git cherry-pick`, or `git rebase`. Commit messages must not contain `Co-Authored-By`.

## Data integrity

Do not submit without successful accuracy tests, successful `--level core` benchmark, nonzero parsed benchmark cases, and real performance data. Multi-backend data may be `N/A` if no summary directory is provided; it must not be fabricated.
