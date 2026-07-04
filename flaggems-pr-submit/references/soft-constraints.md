# Soft Constraints

Soft constraints are blocking review rules that require code understanding, reviewer intent, or judgment that is not safely reducible to a deterministic local script yet. They are enforced by the main agent or the relevant subagent after reading the stage specs.

## Sources of soft constraints

- Stage-specific specs under `references/<subagent>/spec.md` define the baseline semantic review obligations for that stage.
- Shared specs under `references/shared/` define cross-stage semantic obligations.
- `references/shared/reviewer-learned-rules.md` is the append-only intake for rules learned from `[KernelGen][Nvidia]` PR reviews.

## Entry format for reviewer-learned rules

Add reviewer-derived soft rules in this structure:

```markdown
### SOFT-YYYYMMDD-<short-slug>

- Source: flagos-ai/FlagGems PR #<number>, <comment kind or reviewer>
- Scene: <when this rule applies>
- Required behavior: <what the generated PR must do>
- Fix pattern: <how the agent should repair it>
- Applies to: implementation | tests | benchmark | registration-yaml | pr-body-review-response
- Promotion candidate: yes | no; <what would make it deterministic>
```

Keep each entry short and concrete. A soft rule should tell the subagent what to inspect and how to repair the common failure mode; it should not become a long transcript of the review.

## Adding a new soft constraint from review feedback

1. Confirm the feedback is new relative to the prior nightly snapshot.
2. Identify the scene and the concrete fix that resolved or should resolve the comment.
3. If the rule requires semantic judgment, append it to the appropriate section of `references/shared/reviewer-learned-rules.md` using the entry format above.
4. If the rule is deterministic, do not add prose first; promote it directly to a hard-rule script and add a pointer entry only when useful for traceability.
5. Check whether a stage spec needs a one-line pointer because the rule changes a subagent's responsibility boundary. Avoid copying the full rule into multiple files.

## Promotion criteria

Promote a soft constraint to a hard constraint when all of these are true:

- violation can be detected from local repository state, git diff, normalized operator context, command output, or PR metadata;
- false positives are rare enough to block PR creation automatically;
- the fix target is unambiguous enough for the stage owner;
- the rule can be represented by a stable CLI command and a stable rule ID.

If any condition is missing, keep the rule soft and make the subagent explicitly inspect the scene.
