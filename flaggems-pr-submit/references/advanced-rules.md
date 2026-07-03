# Advanced Rules（深层规则详解）

以下规则依赖领域判断或涉及复杂场景，无法由 `check_operator.py` 完全自动化。
每次提交前必须逐项确认。

## 1. 非 pointwise Benchmark 必须从 worktree 提取

CI 用 `--level core` 运行 benchmark 时，`set_shapes` 从 yaml 加载 shapes，
**会覆盖** `GenericBenchmark(shapes=[...])` 构造时传入的参数。

**只有 `UnaryPointwiseBenchmark` / `BinaryPointwiseBenchmark` 可以直接使用。**
其他一律从 worktree 提取原始 Benchmark 子类。

**正确做法**：覆盖 `set_shapes` 防止 CI 替换：
```python
CUSTOM_SHAPES = [((64, 128), (64, 128)), ((128, 256), (128, 256))]

class MyOpBenchmark(base.Benchmark):
    def set_shapes(self, shape_file_path=None):
        self.shapes = CUSTOM_SHAPES

    def get_input_iter(self, cur_dtype):
        for (n1, d), (n2, d2) in self.shapes:
            x1 = torch.randn(n1, d, dtype=cur_dtype, device=self.device)
            x2 = torch.randn(n2, d2, dtype=cur_dtype, device=self.device)
            yield x1, x2
```

**禁止**：`GenericBenchmark` + 自定义 `input_fn`（CI 覆盖 shapes 后解包崩溃）。
参考上游已 merge 的 `benchmark/test_grid_sample.py`。

## 2. 核心计算必须使用 Triton Kernel

kernel 文件中的核心数学运算必须由 `@triton.jit` 函数或 FlagGems 工具完成。

**禁止**（核心计算路径）：
`torch.matmul`, `torch.mm`, `torch.add`, `torch.softmax`, `torch.nn.functional.*` 等

**允许的 torch 操作**（辅助操作）：
- 内存分配：`torch.empty`, `torch.zeros`, `torch.ones`, `torch.full` 及 `*_like`
- Tensor 属性/形状：`.shape`, `.stride()`, `.numel()`, `.dtype`, `.device`, `.ndim`
- 形状操作：`.reshape`, `.view`, `.contiguous()`, `.expand`, `.permute`, `.transpose`
- 类型转换：`.to()`, `.float()`, `.half()`
- 复数辅助：`torch.view_as_real`, `torch.view_as_complex`
- 类型推断：`torch.promote_types`, `torch.result_type`

**允许的内部调用**：
- `flag_gems.utils.pointwise_dynamic`, `flag_gems.ops.*`
- 其他已实现的 FlagGems 算子（组合算子模式）

**`@use_tl_extra` 模式**：
```python
@use_tl_extra
@triton.jit
def lgamma(x):
    pass
```
`pass` 是占位符，`@use_tl_extra` 在 JIT 时用 `tl.math.lgamma` 替换函数体。
只有在 kernel 中被实际调用时才保留；未调用的桩函数必须删除。

## 3. 提取 test 时去掉 QUICK_MODE 和 vendor 分支

从 worktree 提取测试代码时：
- 去掉 `if QUICK_MODE` 条件分支（始终用完整参数）
- 去掉 `if flag_gems.vendor_name == "kunlunxin"/"cambricon"/"mthreads"` 等 vendor 特殊处理
- 始终保留完整参数路径

## 4. 多变体 aten 算子必须拆分为独立条目

如果一个算子有多个 aten overloads（如 `norm`、`norm.Scalar`、`norm.ScalarOpt_dim`），
必须作为独立算子分别处理：

| 位置 | 要求 |
|------|------|
| yaml | 每个变体一个独立 `id` 条目 |
| pytest mark | 每个变体一个独立 mark |
| 测试函数 | 每个变体独立 test，**必须测试不同的 dispatch 路径** |
| benchmark | 每个变体独立 benchmark 函数 |
| `__all__` / `_FULL_CONFIG` | 每个变体独立注册 |

**一致性要求**：`__all__` 导出数 = `_FULL_CONFIG` 条目数 = yaml 条目数 = test 函数数 = benchmark 函数数

**命名**：
- 函数名 snake_case：`norm.Scalar` → `norm_scalar`（不是 `norm_Scalar`）
- yaml `for` 保留 aten dotted 名（`norm.Scalar`），`id` 用 snake_case（`norm_scalar`）

**示例**（参考 `all`/`all_dim`/`all_dims` 模式）：
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

## 5. 多芯片测试表格

PR description 必须包含 Multi-backend Testing 表格。

**数据来源**：`/data/dxd/国产GPU算子测试情况/`

| 目录 pattern | Backend |
|------|---------|
| `天数test_results_*/` | Tianshu |
| `沐曦test_results_*/` | Muxi |
| `华为test_*/` | Ascend |
| `海光hygon_test_*/` | Hygon |

**文件命名**：`<op>_test.log`（精度）、`<op>_bench.log`（benchmark）、华为可能 `aten__<op>_test.log`

**表格格式**：
```markdown
| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |
|---|---|---|---|---|
| Nvidia (H20) | PASS | PASS (N cases, --level core) | X.XX | Primary |
| Tianshu | PASS/FAIL | PASS (N cases) | X.XX | error if FAIL |
| Muxi | PASS/FAIL | PASS (N cases) | X.XX | — |
| Ascend | PASS/FAIL | N/A | — | — |
| Hygon | PASS/FAIL | PASS (N cases) | X.XX | — |
```

**解析规则**：
- 从 log 尾部 `N passed, M failed` 判断 PASS/FAIL
- 从 bench.log 的 `SUCCESS ... <speedup>` 行提取 speedup，计算算术平均值

## 6. 追加模式（Append Mode）

**先检查 upstream 是否已有同名文件：**
```bash
git show upstream/master:tests/test_<op>.py 2>/dev/null
git show upstream/master:benchmark/test_<op>.py 2>/dev/null
```

**如果已存在**（如 `bernoulli_` 已占用 `test_bernoulli.py`）：
- 保留原文件所有已有代码不动
- 新增测试追加到文件末尾
- shapes/dtypes 与同文件已有测试保持一致
- `input_fn` 用描述性命名（如 `bernoulli_input_fn`，不要用泛型 `input_fn`）
- 代码组织：每个 `input_fn` 紧跟对应的 `test_perf_*` 函数

**如果不存在**：创建新的独立文件。

## 7. dtype 检测规则

**以下算子类型通常不支持 Half/BFloat16**：
- `linalg.*`（eig、eigvals、inv、cholesky、svd 等）
- `special.*`（bessel_j1、airy_ai、gammaincc 等）
- `igamma` / `igammac`
- `cdist` / `_euclidean_dist`
- 仿射变换类（affine_grid 等）

**检测方法**：
```python
torch.<op>(torch.randn(..., dtype=torch.float16))  # 报错则不支持
```

**原则**：如果不确定，默认用 `[torch.float32]` 更安全。
使用硬编码 `[torch.float32]` 时，benchmark 不需要 `import consts`。

## 8. gems_assert_close API

```python
gems_assert_close(res, ref, dtype, equal_nan=False, reduce_dim=1, atol=1e-4)
```

**不接受 `rtol` 参数**。传 `rtol` 会 `TypeError: unexpected keyword argument`。
NaN 比较用 `equal_nan=True`，不要自定义 NaN 判断逻辑。

## 9. Data Sources

| 文件 | 用途 | 关键列 |
|------|------|--------|
| `/data/dxd/规范名.xlsx` Sheet1 | 规范命名映射 + PR 链接记录 | `算子名`, `算子名（规范命名）`, `代码路径` |
| `/data/dxd/第一批pr算子.xlsx` Sheet1 | 待提交算子列表 + 加速比 | `算子名称`(含aten::前缀), `加速比` |
| `<SKILL_DIR>/../nvidia.xlsx` Sheet1 | NV 规范名 + 加速比 | `算子名（规范命名）`, `英伟达 (黎远柱)`, `代码路径` |

## 10. 其他重要规则

- **benchmark 统一 `--level core`** — 与 CI 对齐，PR Performance 表格必须用此结果
- **benchmark 有 TFLOPS 也要加** — 输出含 TFLOPS 时必须在 Performance 表格体现
- **测试函数名格式** — 用 `test_XXX`，不要 `test_accuracy_XXX` / `test_perf_XXX` 等前缀后缀
- **不修改已有测试函数** — 只新增，不改已有函数
- **不要显式 to_cpu/to_fp64** — 统一用 `to_reference()` 完成参考值转换
- **本地定义测试参数要加注释** — 说明为什么不能用 `accuracy_utils` 中的公共变量
- **无效 if/else 分支清理** — pointwise_dynamic 已处理类型分发时不需要 isinstance 判断
- **block_size 等超参避免 hardcode** — 使用 `@triton.autotune`，hardcode 需记录原因
- **未注册/未测试的函数必须删除** — kernel 中只保留该算子需要的函数
- **无意义别名封装删除** — 不要 `_j1 = tl_extra_shim.j1`，直接内联调用
- **先通用后特化** — 特化版本依赖通用版时不可一起提交
- **概率算子用统计验证** — dropout/bernoulli/rand 用 mean/variance，不用精确比较
