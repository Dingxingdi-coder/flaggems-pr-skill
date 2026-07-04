# Registration Spec

Read references/rule-structure.md. Static checks are owned by scripts. Semantic registration and yaml checks stay in this file.

Expected surfaces: target kernel module, ops package exports, top-level dispatch registration, target test file, target benchmark file, and conf/operators.yaml.

Manual checks: exported wrappers are registered, tested, and benchmarked; variants are either fully covered or not exported; branch diff does not include unrelated operator logic.

## Embedded registration soft rules

No entries yet. Add future registration soft rules here using the SOFT-YYYYMMDD-short-slug format from references/soft-constraints.md.
