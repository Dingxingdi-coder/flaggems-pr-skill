# Constraint Ownership Map

| Constraint | Responsible subagent |
|---|---|
| Infer repo, worktree, remotes, GPU, tested-on context | `context-discovery` |
| Keep operator count within GPU slots | `context-discovery`, main agent |
| Normalize raw operator names | `name-branch` |
| Apply underscore and special naming rules | `name-branch`, `extract-register`, `final-validate-pr` |
| Check upstream kernel and yaml conflicts | `name-branch` |
| Create `pr/<op>` from upstream base | `name-branch` |
| Keep one PR to one aten operator family | all operator subagents; final owner `final-validate-pr` |
| Review and repair generated worktree first | `implementation-review` |
| Confirm target computation uses Triton or FlagGems implementation | `implementation-review`, `final-validate-pr` |
| Kernel header, logging, duplicate functions, dead exports | `implementation-review`, `final-validate-pr` |
| dtype support and hardcoded parameter comments | `implementation-review`, `worktree-test-benchmark` |
| Accuracy test style and correctness | `implementation-review`, `worktree-test-benchmark`, `final-validate-pr` |
| Benchmark wrapper style, fairness, and nonzero cases | `implementation-review`, `worktree-test-benchmark`, `final-validate-pr` |
| Extract only target files and register all surfaces | `extract-register` |
| yaml id, mark, op_name, and registration alignment | `extract-register`, `final-validate-pr` |
| Formatting checks, explicit staging, commit message | `final-validate-pr` |
| PR body completeness and truthful performance data | `final-validate-pr` |
| Review follow-up exclusion | main agent, `final-validate-pr` |
