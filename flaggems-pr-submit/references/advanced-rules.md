# Advanced Rules（深层规则）

这些规则需要 Coding Agent 主动判断；`check_operator.py` 不能完全自动化。提交前必须排查。

## 1. Worktree-first 修复原则

`.worktrees/gen-<op>` 是提取来源，但弱模型输出不是可信实现。发现实现、测试或 benchmark 问题时，先修 worktree，再用 `extract_from_worktree.py` 提取到 PR 分支。PR 分支不得绕过 worktree 手写一套不一致实现。

允许在 PR 分支直接处理的只有：pre-commit 自动格式化、未使用 import 删除、PR body 更新、纯文档/description 微调。涉及算法、测试逻辑、benchmark 输入逻辑的修改应回到 worktree。

## 2. 非 pointwise Benchmark

CI 和本地提交都用 `--level core`。`Benchmark.set_shapes()` 会从 `core_shapes.yaml` 加载 shapes，可能覆盖构造函数传入的 shapes。因此复杂输入结构必须显式处理 shape 加载。

推荐做法：保留并修复 worktree 的 Benchmark 子类，必要时覆盖 `set_shapes`：

```python
CUSTOM_SHAPES = [((64, 128), (64, 128)), ((128, 256), (128, 256))]

class MyOpBenchmark(base.Benchmark):
    def set_shapes(self, shape_file_path=None):
        self.shapes = CUSTOM_SHAPES
        self.shape_desc = "input_shape, other_shape"

    def get_input_iter(self, cur_dtype):
        for (m, n), (m2, n2) in self.shapes:
            x = torch.randn(m, n, dtype=cur_dtype, device=self.device)
            y = torch.randn(m2, n2, dtype=cur_dtype, device=self.device)
            yield x, y
```

`base.GenericBenchmark(input_fn=...)` 只适用于 shape tuple 能直接生成输入的简单场景，并且必须通过 `pytest benchmark/test_<op>.py -s --level core` 证明非 0 cases。不要用 GenericBenchmark 掩盖复杂输入的 `set_shapes` 问题。

## 3. 核心计算必须使用 Triton/FlagGems

kernel 文件中的核心数学运算必须由 `@triton.jit` 函数、FlagGems 工具、`pointwise_dynamic` 或已实现的 FlagGems 算子完成。

禁止在核心计算路径使用：`torch.matmul`、`torch.mm`、`torch.add`、`torch.softmax`、`torch.nn.functional.*`、`torch.<target_op>` 等。

允许的 torch 辅助操作：

- 内存分配：`torch.empty`、`torch.zeros`、`torch.ones`、`torch.full` 及 `*_like`。
- Tensor 属性：`.shape`、`.stride()`、`.numel()`、`.dtype`、`.device`、`.ndim`。
- 形状操作：`.reshape`、`.view`、`.contiguous()`、`.expand`、`.permute`、`.transpose`。
- 类型转换或推断：`.to()`、`.float()`、`.half()`、`torch.promote_types`、`torch.result_type`。
- 复数辅助：`torch.view_as_real`、`torch.view_as_complex`。

`@use_tl_extra` 桩函数只有被 kernel 实际调用时才保留；未使用的桩函数必须删除。

## 4. Test 提取清理

从 worktree 提取测试时要去掉：

- `QUICK_MODE` 分支。
- `flag_gems.vendor_name == ...` 的 vendor 特殊分支。
- 调试输出和无关 skip。
- 手写 `.cpu()`、`.to(torch.float64)` reference。

始终保留完整参数路径，使用 `utils.to_reference()` 和 `utils.gems_assert_close/equal`。

## 5. 多变体 aten 算子

如果一个算子有多个 aten overloads，如 `norm`、`norm.Scalar`、`norm.ScalarOpt_dim`，必须按 dispatch 路径拆分并对齐：

| 位置 | 要求 |
|---|---|
| yaml | 每个独立 dispatch 一个 `id` 条目 |
| pytest mark | 与 yaml `id` 完全一致 |
| 测试函数 | 每个变体独立测试真实 dispatch 路径 |
| benchmark | 每个变体独立函数，`op_name` 与 yaml `id` 一致 |
| `__all__` / `_FULL_CONFIG` | 每个导出 wrapper 都有对应注册 |

命名：函数名 snake_case，yaml `for` 保留 aten dotted 名，yaml `id` 用 snake_case。

示例：

```yaml
- id: norm
  for:
    - norm
- id: norm_scalar
  for:
    - norm.Scalar
- id: norm_scalaropt_dim
  for:
    - norm.ScalarOpt_dim
```

## 6. 多芯片测试表格

PR description 必须包含 Multi-backend Testing 表格。数据来源为 `/data/dxd/国产GPU算子测试情况/` 或 `gen_pr_description.py` / `query_domestic_gpu.py` 的解析结果。

| 目录 pattern | Backend |
|---|---|
| `天数test_results_*/` | Tianshu |
| `沐曦test_results_*/` | Muxi |
| `华为test_*/` | Ascend |
| `海光hygon_test_*/` | Hygon |

解析规则：从 log 尾部 `N passed, M failed` 判断 accuracy；从 bench log 的 `SUCCESS ... <speedup>` 行计算平均 speedup。缺失数据填 `N/A` 或 `—`，不得编造。

## 7. Append Mode

先检查上游是否已有同名 test/benchmark 文件：

```bash
git show upstream/master:tests/test_<op_id>.py 2>/dev/null
git show upstream/master:benchmark/test_<op_id>.py 2>/dev/null
```

如果已存在：

- 保留原文件所有已有代码不动。
- 新测试/benchmark 追加到文件末尾。
- shapes/dtypes 与同文件已有测试风格一致。
- `input_fn` 用描述性命名，例如 `bernoulli_input_fn`，不要用泛型 `input_fn`。
- 每个 helper 紧跟对应 test/benchmark 函数，避免污染其他算子。

如果不存在，创建新的独立文件。

## 8. dtype 检测

以下算子类型通常不支持 Half/BFloat16，需要先用 PyTorch reference 验证：

- `linalg.*`：eig、eigvals、inv、cholesky、svd 等。
- `special.*`：bessel、airy、gammainc 系列等。
- `igamma` / `igammac`。
- `cdist` / `_euclidean_dist`。
- 仿射变换类，如 affine_grid。

检测方式：

```python
torch.<op>(torch.randn(..., dtype=torch.float16, device="cuda"))
```

如果 PyTorch 不支持，测试/benchmark 可限制到 `[torch.float32]`，但必须加注释，且 wrapper 应明确拒绝不支持 dtype。

## 9. gems_assert_close API

```python
gems_assert_close(res, ref, dtype, equal_nan=False, reduce_dim=1, atol=1e-4)
```

不接受 `rtol` 参数。NaN 比较用 `equal_nan=True`。

## 10. Data Sources

| 文件 | 用途 | 关键列 |
|---|---|---|
| `/data/dxd/规范名.xlsx` Sheet1 | 规范命名映射 + PR 链接记录 | `算子名`, `算子名（规范命名）`, `代码路径` |
| `/data/dxd/第一批pr算子.xlsx` Sheet1 | 待提交算子列表 + 加速比 | `算子名称`, `加速比` |
| `<SKILL_DIR>/../nvidia.xlsx` Sheet1 | NV 规范名 + 加速比 | `算子名（规范命名）`, `英伟达 (黎远柱)`, `代码路径` |

## 11. 其他高频规则

- benchmark 统一 `--level core`。
- benchmark 有 TFLOPS 时 PR 表格保留 TFLOPS。
- 测试函数名用 `test_<id>`。
- 不修改已有测试函数。
- 本地定义测试参数要加注释。
- `pointwise_dynamic` 已处理类型分发时，删除多余 `isinstance` 分支。
- 未注册/未测试的函数必须删除。
- 先提交通用版，再提交依赖它的特化版。
- 概率算子用统计验证。
