# FlagGems PR Review 常见问题

以下来自历史 PR review。提交前逐条排查；如与 `operator-quality.md` 冲突，以更严格的规则为准。

## 1. 算子命名

- aten 名要转换为合法 snake_case：`a.out` → `a_out`，`a.self_out` → `a_self_out`。
- 前导下划线只在 pytest mark、yaml `id`、test/benchmark 文件名中去掉：`_foo` → `foo`。
- kernel 文件名、函数名、import、`__all__`、`_FULL_CONFIG` aten name、yaml `for` 保留前导下划线。
- 尾部下划线表示 inplace，始终保留：`bernoulli_` → `bernoulli_`。
- fused 算子以 fused 算子自身命名，不用内部 reference 名。
- 禁止随意 mark；yaml `id` = pytest mark = benchmark `op_name`。
- 提交前检查冲突：`grep -n "id: <op_id>" conf/operators.yaml`。

## 2. 测试文件

- 禁止 `print()`；需要跳过用 `@pytest.mark.skip(reason=...)`。
- 测试函数名用 `test_<op_id>`，不要保留 `test_accuracy_` 前缀。
- 使用 `from . import accuracy_utils as utils`。
- Golden reference 用 `utils.to_reference()`，不要手写 `.cpu()` / `.to(torch.float64)`。
- `gems_assert_close` 禁止传 `rtol`；NaN 用 `equal_nan=True`。
- mark 必须与 yaml id 严格一致。例如 `special_erfcx` 不能写成 `@pytest.mark.erfcx`。
- 测试 shapes 不要过重；若不能用公共 shape/dtype 常量，写注释说明。
- 概率算子用统计验证，不做逐元素精确比较。

## 3. Benchmark

- 必须使用 pytest + `benchmark/base.py` 封装；禁止自定义 benchmark 框架。
- 一元 pointwise：`base.UnaryPointwiseBenchmark`。
- 二元 pointwise：`base.BinaryPointwiseBenchmark`。
- Reduction：`base.UnaryReductionBenchmark`。
- 非 pointwise、自定义输入、backward、out/inplace、多输入结构复杂的算子：保留并修复 worktree 的 Benchmark 子类，确保 `--level core` 非 0 cases。
- `base.GenericBenchmark(input_fn=...)` 只用于简单 shape 驱动输入；必须通过 `pytest benchmark/test_<op>.py -s --level core` 证明不被 shape 覆盖破坏。
- dtype 默认用 `consts.FLOAT_DTYPES`；PyTorch/reference 不支持时可以硬编码有限 dtype，但必须注释并删除未使用的 `consts` import。
- Benchmark 公平性：torch op 和 gems op 参数、计算量、forward/backward 边界一致，不能为了 speedup 改少 gems 侧工作。
- benchmark 输出 0 cases 时，优先检查 `core_shapes.yaml`、pytest mark、Benchmark `set_shapes`。

## 4. Kernel 代码质量

- 使用 `logger.debug`，禁止 `print()`。
- 删除重复函数、死代码、无意义 wrapper、未使用 import。
- import 放文件顶部，不在函数中间 import。
- 纯 Triton kernel 不需要 `import torch`；如果只用于类型注解或辅助分配，确保 flake8 不报 F401。
- 核心计算不能使用 torch fallback；允许 torch 做输出分配、shape/dtype/device 查询和 reshape 等辅助工作。
- `@use_tl_extra` 桩函数只有实际被 kernel 调用时保留。
- libdevice 兼容性：若使用 `tl.extra.cuda.libdevice`，优先考虑 `tl_extra_shim`，避免 reviewer 要求跨后端兼容时返工。
- 硬编码 BLOCK、shape 上限、dtype 列表必须有注释；可配置项优先外置。

## 5. 文件与格式

- 维持项目命名约定和字母序，不随意重排已有列表。
- 文件末尾必须有换行，行长度不超过项目限制。
- 新增算子一般只改六类文件：kernel、两个注册文件、test、benchmark、operators.yaml。
- 绝不使用 `git add -A` 或 `git add .`，只能逐文件 stage。
- 不要修改上游已有测试函数；append mode 只在文件末尾追加目标算子相关代码。

## 6. 上游结构差异

当前上游结构与早期 worktree 可能不同，不能 cherry-pick：

| 项目 | 旧生成格式 | 上游当前要求 |
|---|---|---|
| 测试文件 | 共享文件追加 | 每算子独立文件，必要时 append mode |
| Benchmark | 共享文件或自定义脚本 | pytest + `benchmark/base.py` 封装 |
| operators.yaml | `name` 字段 | `id` 字段 |
| 命名 | 随 generated 代码 | `op_naming.py` + `naming.md` |

## 7. pre-commit 常见问题

| Hook | 常见问题 | 修复 |
|---|---|---|
| end-of-file-fixer | 文件末尾缺换行 | 自动修复后重新 stage |
| trailing-whitespace | 行尾空白 | 自动修复后重新 stage |
| isort | import 顺序 | 自动修复后重新 stage |
| black | 格式 | 自动修复后重新 stage |
| flake8 F401 | 未使用 import | 删除多余 import |

## 8. 多重载对齐

当一个 PR 涉及多个 dispatch 变体（如 `_out`、`_scalar`、`_tensor`、`_mode`、`_backward`），如果 yaml 中拆成独立 `id`，每个变体都必须有一致的 mark 和 benchmark `op_name`。

错误：

```python
@pytest.mark.reflection_pad3d
...
op_name="reflection_pad3d"
```

用于 `reflection_pad3d_out` 变体时应改为：

```python
@pytest.mark.reflection_pad3d_out
...
op_name="reflection_pad3d_out"
```

规则：yaml `id` = pytest mark = benchmark `op_name`。

## 9. PR 与 git

- 分支命名：`pr/<operator>`。
- 每个分支基于 `upstream/master`。
- commit message：`[KernelGen][Nvidia] Add <op> operator with Triton kernel`。
- 禁止 `Co-Authored-By`，否则 CLA CI 可能失败。
- 禁止 `git cherry-pick`、`git rebase`。
- PR body 必须包含真实测试、benchmark、Multi-backend 数据；不能编造国产 GPU 结果。
