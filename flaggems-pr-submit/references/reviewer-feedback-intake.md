# Reviewer Feedback Intake

Nightly intake collects new reviewer comments from `[KernelGen][Nvidia]` PRs in `flagos-ai/FlagGems`.

Command:

```bash
python flaggems-pr-submit/scripts/collect_kernelgen_review_delta.py --repo flagos-ai/FlagGems --state-file .cache/kernelgen-review-state.json --output .cache/kernelgen-review-index.json
```

Use `--baseline` on the first run. The collector output is an index only. It includes `changed_comments` metadata such as `url`, `change_type`, `kind`, `author`, `is_pr_author`, `path`, and `line`. It supports filters including `--include-pr-author` and `--include-bots`.

Triage loop:

1. Open the live PR/comment URL.
2. Confirm the comment is reviewer signal.
3. Extract the scene and fix pattern.
4. Classify the rule as hard or soft.
5. Hard rule: update the owning script.
6. Soft rule: update the existing spec file that owns the scene.
7. Run the edited script with `--list-rules` when applicable, then run `python flaggems-pr-submit/scripts/skill_meta_gate.py`.

Soft-rule destinations:

| Scene | Destination |
|---|---|
| implementation | `references/implementation-review/spec.md` |
| tests or benchmark | `references/shared/test-benchmark.md` |
| registration or yaml | `references/registration/spec.md` |
| final checks or PR body | `references/final/spec.md` |

Embedded soft-rule entries use the format documented in `references/soft-constraints.md`.
