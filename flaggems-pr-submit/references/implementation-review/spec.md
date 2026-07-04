# Implementation Review Spec

Applies to implementation-review subagent.

Required reading:

- references/rule-structure.md
- references/shared/test-benchmark.md

Main duties:

- Review and repair generated implementation only inside the target generated worktree.
- Reject target computation implemented as a PyTorch fallback.
- Check wrapper behavior, dtype guards, duplicate or dead generated functions, tests, benchmark code, yaml, and registration consistency.
- Mechanical checks are owned by scripts. Do not duplicate hard-rule inventories here.

## Embedded implementation soft rules

No entries yet. Add future implementation soft rules here using the SOFT-YYYYMMDD-short-slug format from references/soft-constraints.md.
