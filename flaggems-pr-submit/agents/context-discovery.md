# Context Discovery Agent

Reads: `references/general-spec.md`, `references/context-discovery-spec.md`.

Purpose: collect shared context once for the whole request. Do not modify source files or Git branches.

The agent may inspect the current Git checkout, Git remotes, visible CUDA devices, GPU names, environment variables, and nearby files.

Tasks:

1. Confirm the raw operator list from the user.
2. Infer `repo_dir`, `worktree_root`, `norm_xlsx`, remotes, GitHub repos, base branch, GPU slots, and tested-on text.
3. Verify the operator count is at least one and no larger than the GPU slot count.
4. Assign one GPU per operator for multi-operator runs.
5. Produce a concise context object for the main agent and all operator coordinators.

Stop when any required value cannot be inferred with confidence. Ask the user for that value.
