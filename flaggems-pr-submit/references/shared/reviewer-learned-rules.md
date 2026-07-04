# Reviewer-Learned Rules

This file is the soft-rule intake for future maintenance. Update it only from actual `[KernelGen][Nvidia]` PR interaction in `flagos-ai/FlagGems`.

A rule belongs here when it reflects reviewer preference, repository convention, or semantic judgment that is not safely scriptable yet. Keep each entry short, cite the source PR number in the maintenance commit message, and include the concrete fix pattern.

Use this entry format:

```markdown
### SOFT-YYYYMMDD-<short-slug>

- Source: flagos-ai/FlagGems PR #<number>, <comment kind or reviewer>
- Scene: <when this rule applies>
- Required behavior: <what the generated PR must do>
- Fix pattern: <how the agent should repair it>
- Applies to: implementation | tests | benchmark | registration-yaml | pr-body-review-response
- Promotion candidate: yes | no; <what would make it deterministic>
```

## Implementation

No reviewer-derived rules recorded yet.

## Tests

No reviewer-derived rules recorded yet.

## Benchmark

No reviewer-derived rules recorded yet.

## Registration and yaml

No reviewer-derived rules recorded yet.

## PR body and review response

No reviewer-derived rules recorded yet.

## Promotion rule

When a reviewer-learned rule becomes deterministic, move the check to the owning script described in `references/hard-constraints.md`. Replace or supplement the prose entry with the hard-rule ID, the script name, and the condition it covers.
