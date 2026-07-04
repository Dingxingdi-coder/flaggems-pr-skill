# 规则组织：硬规则脚本化，软规则文档化

这个技能会长期根据 `[KernelGen][Nvidia]` PR 中 contributor 与 reviewer 的互动维护。维护时不要把所有反馈都塞进主流程；先判断规则类型，再决定落点。

## 硬规则

硬规则满足两个条件：结论可由本地仓库文件、git 状态、测试输出、benchmark 输出或 PR 元数据确定；修复方向不依赖 reviewer 偏好。硬规则放入 `scripts/`，并在 `SKILL.md` 的流程中要求 Agent 运行脚本。

当前硬规则入口：

| 阶段 | 脚本 | 范围 |
|---|---|---|
| preflight | `prepare_operator.py` | 规范名、远程仓库、`upstream/master` 冲突、PR 分支 |
| 名称表 | `operator_registry.py` | 规范名查询、PR 链接回填 |
| 提取 | `extract_from_worktree.py` | 六文件提取和注册插入 |
| 静态门禁 | `check_operator.py` | kernel/test/benchmark/yaml/config/git diff 等确定性检查 |
| 多重载 | `check_overload_consistency.py` | yaml id、pytest mark、benchmark op_name 对齐 |
| PR 数据 | `gen_pr_description.py` | benchmark 解析和 PR body 数据 |
| 提交 | `submit_operator.py` | strict check、pre-commit、test、benchmark、commit、push、PR、backfill |

新增硬规则时，脚本只做最小闭包：检查一个明确事实，输出清楚错误，不顺手增加无关功能。

## 软规则

软规则需要语义判断、性能公平性判断、上游 reviewer 偏好或算子上下文。软规则放入 `references/soft-rules.md`、`advanced-rules.md`、`common-issues.md` 等文档，让 AI 在提交前自检。

例子：dtype 是否应限制为 fp32、非 pointwise benchmark 是否与 torch wrapper 计算量对等、概率算子是否应统计验证、description 是否足够精确、reviewer 对某类写法是否有偏好。

## 从 review 反馈维护技能

处理新的 reviewer 反馈时按这个顺序：

1. 抽取 reviewer 明确要求的修改点和原因。
2. 判断是否可自动验证；可验证则加入对应脚本，不可验证则加入软规则文档。
3. 若同一软规则反复出现且判断条件稳定，再升级成脚本。
4. 更新 `pr-checklist.md`，但不要把脚本已覆盖的细节重复写回 `SKILL.md`。
5. 保留“主代理派遣子代理”的流程边界：主代理分发与汇总，子代理执行单算子硬门禁和软自检。
