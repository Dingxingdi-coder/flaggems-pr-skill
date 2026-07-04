# FlagGems PR Review 常见问题

本文件保存历史 review 中反复出现的问题。能脚本化的规则应进入 `scripts/`；不能脚本化的规则保留在这里或 `soft-rules.md`。

## 1. 算子命名

- aten 名需要转换为稳定的 yaml id / pytest mark / benchmark `op_name`，例如 dotted overload 转 snake_case。
- 前导下划线只在 yaml id 和 pytest mark 中去掉；文件名、函数名、import、`_FULL_CONFIG` 的 aten 名保留。
- 尾部下划线表示 inplace 变体，不能随意删除。
- fused 算子以规范名表和 `op_naming.py` 为准。
- yaml `id`、pytest mark、benchmark `op_name` 必须完全一致。

## 2. 测试文件

- 不使用 `print()`；跳过 case 用 `pytest.mark.skip` 并写明原因。
- 不要为了通过测试大幅缩小 coverage；重 shapes 应有必要性。
- 使用 `from . import accuracy_utils as utils` 和 `utils.to_reference()`。
- `gems_assert_close` 不传 `rtol`；NaN 语义用 `equal_nan=True` 或统计方法。

## 3. Benchmark

- 使用项目 benchmark 框架，不写自定义 runner。
- pointwise 可用公共封装；非 pointwise 优先从 worktree 提取 Benchmark 子类。
- `--level core` 下 case 数不能为 0。
- benchmark wrapper 必须与 torch reference 计算量对等。
- dtype 默认使用公共常量；若 PyTorch 不支持某些 dtype，可以硬编码较窄 dtype，但要注释原因。

## 4. 代码质量

- 删除重复函数、死代码、无意义别名封装和未调用的 `@use_tl_extra` 桩函数。
- import 放在文件顶部；删除 F401 未使用 import。
- kernel 中用 `logger.debug`，不用 `print`。
- 文件末尾有换行，行长和 import 顺序交给 pre-commit 修正。

## 5. 上游结构差异

当前上游格式是每算子独立 test/benchmark 文件、`operators.yaml` 使用 `id` 字段、benchmark 使用 `base.*Benchmark` 封装。不能直接 cherry-pick 生成分支代码。

## 6. 多重载对齐

当一个 PR 涉及多个 overload 或变体时，每个 yaml id 必须对应自己的 pytest mark、benchmark `op_name`、测试函数和 benchmark 函数。不要让 `_out`、`_scalar`、`_tensor` 共用错误 mark。

## 7. 平台兼容

若使用 `tl.extra.cuda.libdevice`、`is_cuda` 等后端特定路径，reviewer 可能要求改为 FlagGems shim 或平台无关实现。除非算子确实只能在 NVIDIA 路径工作，否则优先保持跨后端兼容。

## 8. Git 操作

不要 `git add -A` 或 `git add .`。不要 rebase/cherry-pick。分支统一为 `pr/<operator>`。每个 PR 应只包含目标算子相关变更。
