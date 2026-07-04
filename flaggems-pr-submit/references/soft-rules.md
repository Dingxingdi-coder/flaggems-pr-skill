# Soft Rules：AI 提交前自检

这些规则不能完全依赖脚本。子代理在 `extract_from_worktree.py` 后、`submit_operator.py` 前检查。检查结论写入自己的工作记录；发现问题时只修改目标算子相关文件。

## 语义与 dtype

先确认 PyTorch 参考实现实际支持哪些 dtype。`linalg.*`、`special.*`、`igamma/igammac`、`cdist`、仿射变换等经常不支持 Half/BFloat16；不确定时用最小样例验证。若只能测 fp32，在 test/benchmark 中加简短注释说明原因。

浮点结果优先使用 `utils.gems_assert_close(res, ref, dtype, ...)`。不要传 `rtol`；NaN 语义用 `equal_nan=True` 或统计验证，不要写 ad-hoc NaN 过滤逻辑。

## Benchmark 公平性

benchmark 必须比较等价计算量。非 pointwise、backward、带索引或多输出算子，确认 torch wrapper 与 gems wrapper 都执行同一语义路径；backward benchmark 不要把 forward 计入一边而不计入另一边。

pointwise 可用公共 benchmark 封装；非 pointwise 优先从 worktree 提取原始 Benchmark 子类并确认 `set_shapes`、`get_input_iter` 不会被 `--level core` 破坏。不要为了跑通 benchmark 改小计算量或改写语义。

## 生成代码清理

删除未注册、未测试、未调用的函数。删除无意义别名封装、死分支、重复函数和未使用的 `@use_tl_extra` 桩函数。保留 worktree 中有解释价值的注释；新增 hardcode size、shape、dtype 时写明原因。

kernel 的核心计算应走 Triton 或 FlagGems 已有算子。辅助的 shape、dtype、device、内存分配操作可以用 torch；不要用 torch 实现目标算子的核心数学路径。

## 多变体与命名

yaml `id`、pytest mark、benchmark `op_name` 必须完全一致。前导下划线只在 yaml id/mark 中去掉；文件名、函数名、import、`_FULL_CONFIG` 的 aten 名保留。`_out`、`_scalar`、`_tensor`、`_mode` 等变体要分别验证 dispatch 路径，不要只复制同一个测试。

inplace 变体只有在 yaml、test、benchmark、导出和 `_FULL_CONFIG` 都完整时才导出；否则不要暴露未测试函数。

## PR 描述和数据

PR body 必须有 NVIDIA benchmark 的 dtype/case/speedup 信息、Correctness/Tested-on 信息和 Multi-backend Testing 表格或明确原因。不要编造国产 GPU 结果。benchmark 输出 0 case 时先修 benchmark，不创建 PR。

## 平台无关性

避免把 kernel 写死为某个后端，例如只判断 `is_cuda` 或直接依赖 `tl.extra.cuda.libdevice`。若 reviewer 对跨后端兼容提出意见，优先使用 FlagGems 已有 shim 或平台无关工具。
