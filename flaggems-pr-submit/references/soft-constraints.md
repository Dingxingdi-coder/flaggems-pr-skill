# Soft Constraints

Soft constraints are blocking review rules that require code understanding, reviewer intent, or judgment that is not safely reducible to a deterministic local script yet.

## Sources of soft constraints

Soft rules live directly in the spec file that owns the scene. Do not maintain a central learned-rule ledger.

## Destination for reviewer-derived soft rules

| Scene | Destination |
|---|---|
| implementation semantics, torch fallback, wrapper behavior, dtype guard, generated dead code | `references/implementation-review/spec.md` |
| accuracy-test semantics, benchmark fairness, shape coverage, zero cases, performance interpretation | `references/shared/test-benchmark.md` |
| registration surface, yaml metadata, exported wrapper consistency | `references/registration/spec.md` |
| final checks, staging, PR body, tested-on data, review-response behavior | `references/final/spec.md` |

## Embedded entry format

```markdown
### SOFT-YYYYMMDD-<short-slug>

- Source: flagos-ai/FlagGems PR #<number>, <comment kind or reviewer>
- Scene: <when this rule applies>
- Required behavior: <what the generated PR must do>
- Fix pattern: <how the agent should repair it>
- Applies to: implementation | tests | benchmark | registration-yaml | pr-body-review-response
- Promotion candidate: yes | no; <what would make it deterministic>
```

Promote a soft constraint to a hard constraint only when the violation can be detected deterministically by a stable script with a stable rule ID.
