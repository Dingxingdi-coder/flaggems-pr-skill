# Final Validation PR Body Template

The PR body must be English and follow this structure:

```markdown
## Summary

Briefly describe the added Triton kernel and target operator.

## Testing

- Include the exact accuracy command and pass result.
- Mention the tested device or backend.

## Performance

Test command: `<exact benchmark command>` (`<primary backend/device>`)

| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup | TFLOPS |
|---|---:|---:|---:|---:|
| `<configuration>` | `<torch latency>` | `<gems latency>` | `<speedup>` | `<tflops or —>` |
| **Arithmetic Mean** | — | — | **`<mean speedup>`** | — |

## Multi-backend Testing

| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |
|---|---|---|---|---|
| Nvidia (`<device>`) | PASS | PASS (`<case count>` cases, --level core) | `<mean speedup>` | Primary |
| Tianshu | N/A | N/A | — | Not run |
| Muxi | N/A | N/A | — | Not run |
| Ascend | N/A | N/A | — | Not run |
| Hygon | N/A | N/A | — | Not run |

## Files Changed

- `<target file>`: `<role>`
```

Use `—` for TFLOPS when the benchmark output does not report TFLOPS.
