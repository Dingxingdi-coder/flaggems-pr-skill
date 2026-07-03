# Constraint Ownership Map

| Constraint | Owner |
|---|---|
| Infer repo, worktree root, remotes, GPU, tested-on context | main agent |
| Keep operator count within GPU slots | main agent |
| Normalize raw operator names | `name-worktree` |
| Apply underscore and special naming rules | `name-worktree`, `register`, `final-validation` |
| Confirm target gen worktree and generated branch | `name-worktree` |
| Check upstream kernel and yaml conflicts | `name-worktree` |
| Use the existing generated branch instead of a new PR branch | main agent, `name-worktree`, `final-validation` |
| Keep one PR to one aten operator family | all subagents; final owner `final-validation` |
| Keep all subagent edits inside `{GEN_WORKTREE}` | all subagents |
| Review and repair generated worktree first | `implementation-review` |
| Confirm target computation uses Triton or FlagGems implementation | `implementation-review`, `final-validation` |
| Kernel header, logging, duplicate functions, dead exports | `implementation-review`, `final-validation` |
| dtype support and hardcoded parameter comments | `implementation-review`, `worktree-test-benchmark` |
| Accuracy test style and correctness | `implementation-review`, `worktree-test-benchmark`, `final-validation` |
| Benchmark wrapper style, fairness, and nonzero cases | `implementation-review`, `worktree-test-benchmark`, `final-validation` |
| Organize target files and register all surfaces in gen branch | `register` |
| yaml id, mark, op_name, and registration alignment | `register`, `final-validation` |
| Formatting checks, explicit staging, commit message | `final-validation` |
| PR body completeness and truthful performance data | `final-validation` |
| Review follow-up exclusion | main agent, `final-validation` |
