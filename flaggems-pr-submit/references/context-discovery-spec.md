# Context Discovery Spec

Applies to: `agents/context-discovery.md` and the main agent.

The context agent discovers values; it does not modify the repository.

Required output fields:

- raw operator list from the user;
- normalized operator list after name lookup;
- repository root;
- worktree root;
- norm-name spreadsheet path;
- upstream remote and base branch;
- fork remote;
- upstream GitHub repo and fork GitHub repo;
- GPU assignment per normalized operator;
- tested-on string;
- optional multi-backend summary directory.

Inference order:

- repository root: current directory, then `git rev-parse --show-toplevel`;
- worktree root: `<repo_dir>/.worktrees`;
- norm-name spreadsheet: user value, `FLAGGEMS_NORM_XLSX`, nearby `规范名.xlsx` files;
- remotes: inspect `git remote -v`; upstream usually points to `flagos-ai/FlagGems`; fork is the writable user fork;
- base branch: upstream `master`, then upstream `main`, otherwise ask user;
- GPUs: `CUDA_VISIBLE_DEVICES`, then `nvidia-smi`;
- tested-on: GPU name from `nvidia-smi`, plus CUDA/runtime details if available.

Stop when a value cannot be inferred with confidence. Ask the user for the exact value rather than guessing.

The context agent must verify `1 <= operator_count <= gpu_slot_count`. If the request contains too many operators, ask the user to reduce the batch or provide a GPU map with enough slots.
