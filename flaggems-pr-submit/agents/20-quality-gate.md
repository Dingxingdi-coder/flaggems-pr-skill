# Quality Gate Agent

Scope: read `references/spec.md`, context JSON, `scripts/worktree_quality_gate.py`, and only the target worktree files.

Input: normalized `op` from preflight JSON and context JSON path.

Command:

```bash
python <SKILL_DIR>/scripts/worktree_quality_gate.py \
  --context <context.json> \
  --op <op>
```

Responsibilities:

- Inspect the generated worktree before extraction.
- Fix generated code in the worktree when it violates spec.
- Check kernel, tests, benchmark, yaml, and registrations for consistency.
- Run worktree accuracy and benchmark commands with the GPU from context.
- Record dtype coverage, benchmark cases, mean speedup, failures, and TFLOPS if present.

Manual review checklist:

- Core computation is Triton/FlagGems, not torch fallback.
- Tests hit the intended dispatch path and use `utils.to_reference`.
- Benchmark uses pytest/base wrappers and is fair between torch and gems.
- `--level core` benchmark has nonzero parsed cases.
- `id` / mark / `op_name` / `_FULL_CONFIG` / yaml `for` align.
- Unsupported dtypes are documented and rejected by wrapper code.
- `_out`, inplace, and overload variants are either fully covered or not exported.

Stop if the worktree remains incorrect, tests fail, benchmark fails, benchmark has zero cases, or speedup is below the threshold and cannot be improved.
