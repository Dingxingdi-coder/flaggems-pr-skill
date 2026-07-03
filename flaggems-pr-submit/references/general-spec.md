# General Spec

Applies to the main agent and every specialist subagent.

This skill creates initial PRs only. Review follow-up and PR URL backfill are out of scope.

A request can contain one or more operators. The main agent runs one independent PR workflow per operator. Each PR contains one aten operator family.

The user must provide at least one operator. Other context values should be inferred from the current Git checkout, `.worktrees`, nearby norm-name spreadsheets, Git remotes, visible GPUs, and GPU names. Ask the user when inference is missing or ambiguous.

Operator count must be at least one and no larger than the number of GPU slots.

The skill is document-based. Subagents may run project commands, but policies are defined by the skill documents.

Every operator must pass context discovery, naming, conflict checks, branch setup, worktree review, worktree tests, worktree benchmark, extraction, registration, PR-branch validation, formatting checks, PR-branch tests, PR-branch benchmark, commit, push, and PR creation.

Use only target files when staging. Keep branch history simple. Commit messages must not include co-author trailers.

Accuracy tests, core-level benchmark, nonzero cases, and real performance data are required before PR creation. Multi-backend data can be unavailable, but must not be invented.
