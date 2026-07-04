# Register Template

Fields: `{OP}`, `{GEN_WORKTREE}`, `{OP_ID}`, `{MODULE}`.

Send this prompt:

```text
You handle registration for {OP}.
Read references/extract-register-spec.md.
Working directory: {GEN_WORKTREE}.
Stay inside this directory.
Use op_id={OP_ID} and module={MODULE}.
Return changed files and blocking issues.
```
