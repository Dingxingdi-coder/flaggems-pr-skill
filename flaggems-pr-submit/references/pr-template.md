# PR Description Template

PR description 必须使用英文。所有 Performance、Correctness、Multi-backend 数据必须来自本地命令或日志解析，不得编造。

## gh 命令模板

```bash
gh pr create \
  --repo flagos-ai/FlagGems \
  --head Dingxingdi:pr/<op> \
  --base master \
  --title "[KernelGen][Nvidia] Add <op> operator with Triton kernel" \
  --body "$(cat <<'EOF'
## PR Category
Operator

## Type of Change
New feature: add a Triton kernel implementation for an aten operator.

## Summary
Adds a Triton kernel for `<op>`. <one-line description>.

## Description
This PR registers `<op>` in FlagGems, adds accuracy coverage against the PyTorch reference, and adds a core-level benchmark.

## Testing / Correctness
- Accuracy command: `pytest tests/test_<op>.py -m <op> -vs`
- Benchmark command: `pytest benchmark/test_<op>.py -m <op> -s --level core`
- Validated against PyTorch reference on device side
- Tested dtypes: `<dtype list>`

## Performance
Test command: `pytest benchmark/test_<op>.py --level core -s` (NVIDIA H20)

| DType | Cases | Mean Speedup | Notes |
|---|---:|---:|---|
| float32 | <N> | <speedup>x | <notes> |
| float16 | <N> | <speedup>x | <notes> |
| bfloat16 | <N> | <speedup>x | <notes> |

| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup | TFLOPS |
|---|---:|---:|---:|---:|
| <shape1> | <torch_ms> | <gems_ms> | <speedup>x | <tflops> |
| **Arithmetic Mean** | — | — | **<am_speedup>x** | — |

## Tested-on
- NVIDIA H20, CUDA 13.2

## Multi-backend Testing
| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |
|---|---|---|---:|---|
| Nvidia (H20) | PASS | PASS (<N> cases, --level core) | <am_speedup>x | Primary |
| Tianshu | <PASS/FAIL/N/A> | <PASS/FAIL/N/A> | <speedup/—> | <notes> |
| Muxi | <PASS/FAIL/N/A> | <PASS/FAIL/N/A> | <speedup/—> | <notes> |
| Ascend | <PASS/FAIL/N/A> | <PASS/FAIL/N/A> | <speedup/—> | <notes> |
| Hygon | <PASS/FAIL/N/A> | <PASS/FAIL/N/A> | <speedup/—> | <notes> |

## Files Changed
- `src/flag_gems/ops/<module>.py`: Triton kernel implementation
- `tests/test_<op>.py`: Accuracy test
- `benchmark/test_<op>.py`: Performance benchmark
- `src/flag_gems/ops/__init__.py`: Register import and `__all__`
- `src/flag_gems/__init__.py`: Register to `_FULL_CONFIG`
- `conf/operators.yaml`: Add operator entry (stage: alpha 5.1)
EOF
)"
```

## JSON 字段映射

`gen_pr_description.py` 输出的 JSON 字段映射到模板：

| 模板位置 | JSON 字段 |
|---|---|
| Performance 明细行 | `nvidia_benchmark.rows[]` (`shape`, `torch_ms`, `gems_ms`, `speedup`, `tflops`) |
| Arithmetic Mean | `nvidia_benchmark.arithmetic_mean_speedup` |
| Performance case 数 | `nvidia_benchmark.case_count` |
| Multi-backend PASS/FAIL | `domestic_gpu.<backend>.accuracy_passed` / `benchmark_passed` |
| Multi-backend Speedup | `domestic_gpu.<backend>.bench_mean_speedup` |
| Multi-backend case 数 | `domestic_gpu.<backend>.bench_case_count` |
| Multi-backend Notes | `domestic_gpu.<backend>.test_error` / `bench_error`，截短至一句话 |

## 填写规则

- 全部用英文。
- Performance 数据必须来自 `--level core` benchmark 或 `gen_pr_description.py`。
- Performance 要尽量按 dtype 汇总 case 数和平均 speedup；不能只有一句 “speedup is X”。
- 输出含 TFLOPS 时保留 TFLOPS 列；没有 TFLOPS 时可删除该列。
- 国产 GPU 表格来自 `/data/dxd/国产GPU算子测试情况/` 或脚本解析结果；没有数据填 `N/A`，不得编造。
- 通过时 Notes 填 `—`；benchmark 未运行填 `N/A`；Speedup 无数据填 `—`。
- Notes 中失败原因截短至一句话，如 `CompilationError`，不要粘完整 traceback。
- Testing 段统一写 `Validated against PyTorch reference on device side`，并补充实际命令和 tested-on 信息。
