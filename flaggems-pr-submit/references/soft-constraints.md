# Soft Constraints

Soft constraints are blocking review rules that require code understanding, reviewer intent, or judgment that is not safely reducible to a deterministic local script yet. They are enforced by the main agent or the relevant subagent after reading the stage and shared specs.

## Sources of soft constraints

- Stage-specific specs under `references/<subagent>/spec.md` define the baseline semantic review obligations for that stage.
- Shared specs under `references/shared/` define cross-stage semantic obligations.
- Reviewer-derived soft rules are written directly into the existing spec that owns the scene. Do not create or maintain a separate learned-rule ledger.

## Destination for reviewer-derived soft rules

Put a new soft rule where a future PR-generation agent will read it before the mistake can be made:

| Scene | Destination |
|---|---|
| implementation semantics, torch fallback, wrapper behavior, dtype guard, generated dead code | `references/implementation-review/spec.md` |
| accuracy-test semantics, benchmark fairness, shape coverage, zero cases, performance interpretation | `references/shared/test-benchmark.md` |
| registration surface, yaml metadata, exported wrapper consistency | `references/register/spec.md` |
| final validation, staging, commit, PR body, tested-on data, review-response behavior | `references/final-validation/spec.md` |

If a rule spans multiple scenes, choose the earliest owner that can prevent the reviewer comment. Add only a short pointer in a second spec when the later subagent must re-check the same risk.

## Embedded entry format

Add reviewer-derived soft rules in this structure inside the destination file:

```markdown
### SOFT-YYYYMMDD-<short-slug>

- Source: flagos-ai/FlagGems PR #<number>, <comment kind or reviewer>
- Scene: <when this rule applies>
- Required behavior: <what the generated PR must do>
- Fix pattern: <how the agent should repair it>
- Applies to: implementation | tests | benchmark | registration-yaml | pr-body-review-response
- Promotion candidate: yes | no; <what would make it deterministic>
```

Keep each entry short and concrete. A soft rule should tell the responsible subagent what to inspect and how to repair the common failure mode; it should not become a long transcript of the review.

## Adding a new soft constraint from review feedback

1. Confirm the feedback is new relative to the prior nightly snapshot.
2. Open the live PR/comment URL from the collector output and verify it is reviewer signal, not author explanation or CI noise.
3. Identify the scene and the concrete fix that resolved or should resolve the comment.
4. If the rule requires semantic judgment, append it to the appropriate existing spec using the embedded entry format above.
5. If the rule is deterministic, do not add prose first; promote it directly to the owning hard-rule script.
6. Check whether `references/constraint-map.md` needs an ownership update. Avoid copying the full rule into multiple files.
7. Run `python "{SKILL_ROOT}/scripts/skill_meta_gate.py"` to validate the embedded soft-rule schema and rule ownership links.

## Promotion criteria

Promote a soft constraint to a hard constraint when all of these are true:

- violation can be detected from local repository state, git diff, normalized operator context, command output, or PR metadata;
- false positives are rare enough to block PR creation automatically;
- the fix target is unambiguous enough for the stage owner;
- the rule can be represented by a stable CLI command and a stable rule ID.

If any condition is missing, keep the rule soft and make the responsible subagent explicitly inspect the scene.
