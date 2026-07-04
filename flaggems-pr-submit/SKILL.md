---
name: flaggems-pr-submit
description: This skill should be used when submitting FlagGems NVIDIA general operator PRs, reviewing operator code before submission, and preparing operator code for PR.
---

# FlagGems 算子 PR 提交 Skill

目标：把 Dingxingdi/FlagGems 中 `gen-<op>` worktree 里的自动生成 NVIDIA 算子，按 FlagGems 上游格式提交到 `flagos-ai/FlagGems`。不要改变“主代理派遣子代理”的结构：主代理负责分配算子/GPU、收集状态和 PR 链接；每个子代理只负责一个算子的完整 PR 流程。

## 必须保留的流程

主代理先确认算子列表、GPU 分配、`规范名.xlsx` 路径和 FlagGems 仓库路径。若已经在容器内，不要再要求容器名；若实际是在宿主机，先进入用户指定容器后再运行命令。

每个子代理按下面顺序执行，任何硬门禁失败都停止该算子，不要手动绕过。

### 1. Preflight：规范名、远程仓库、upstream 冲突、分支

运行脚本，不要手动拆开做：

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
export FLAGGEMS_NORM_XLSX=/data/dxd/规范名.xlsx
python <SKILL_DIR>/scripts/prepare_operator.py <raw_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --norm-xlsx "$FLAGGEMS_NORM_XLSX" \
  --create-branch
```

脚本输出 `operator=<norm_op>`，后续所有命令都使用这个规范名。若脚本输出 `upstream_conflict=1`，停止该算子并向主代理报告；不要继续提取、提交或创建 PR。

### 2. Worktree 测试与 benchmark

先在生成 worktree 中验证原始生成代码，记录 NVIDIA H20 的 case 数、dtype 维度和 speedup。没有精度测试和 benchmark 结果，不进入提取与提交。

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr/.worktrees/gen-<norm_op>
CUDA_VISIBLE_DEVICES=<N> python -m pytest tests -m <op_id> -vs
CUDA_VISIBLE_DEVICES=<N> python -m pytest benchmark -m <op_id> -s --level core
```

`op_id` 通常是规范名去掉前导下划线；特殊算子以 `prepare_operator.py` 输出为准。benchmark 必须带 `-s`，否则无法取得性能数据。

### 3. Extract：只用脚本提取六个 PR 文件

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
python <SKILL_DIR>/scripts/extract_from_worktree.py <norm_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr
```

该脚本负责 kernel、test、benchmark、`ops/__init__.py`、顶层 `__init__.py`、`operators.yaml`。不要手写 test/benchmark，不要 cherry-pick，不要 rebase。

### 4. Soft review：由 AI 按规范文档检查

硬规则由脚本执行；软规则由子代理在提交前阅读并检查：

```bash
cat <SKILL_DIR>/references/rule-structure.md
cat <SKILL_DIR>/references/soft-rules.md
cat <SKILL_DIR>/references/pr-checklist.md
```

软规则包括 dtype 语义、benchmark 公平性、非 pointwise benchmark 封装、概率算子统计验证、平台无关性、PR 描述完整性等。发现问题就修改目标算子文件，然后进入提交脚本。

### 5. Validate/Test/Submit：一条命令完成硬门禁和 PR

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
export FLAGGEMS_NORM_XLSX=/data/dxd/规范名.xlsx
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <norm_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N>
```

`submit_operator.py` 串行执行 `check_operator.py --strict`、多重载一致性、pre-commit、本地 test、benchmark、PR 描述生成、commit、push、创建 PR、回填 `规范名.xlsx`。任何一步失败都停止；不要手动执行后续步骤来绕过失败。真实提交禁止使用 `--skip-test` 或 `--skip-benchmark`。

## 不必要且应删除的流程

不要要求模型“阅读脚本理解用法”；技能文档必须直接给出应运行的脚本命令。不要在主文档重复列出 `check_operator.py` 已覆盖的 25+ 条 AST/YAML/注册/排序检查。不要手动检查 upstream 是否已有实现、手动插入注册项、手动维护字母序、手动生成 PR body、手动 backfill PR 链接。不要提交 `__pycache__`、`.pyc` 或其它运行产物。

## 规则维护结构

硬规则放脚本：能由仓库文件、git 状态、测试输出或 PR 数据确定真假的规则，进入 `scripts/`。脚本保持最小闭包，只完成当前硬门禁，不额外设计大而全的防御系统。

软规则放文档：需要 reviewer 偏好、领域判断或上下文解释的规则，进入 `references/soft-rules.md` 或相关 reference 文档。后续维护时，从 `flagos-ai/FlagGems` 中 title 以 `[KernelGen][Nvidia]` 开头的 PR 里提取 reviewer 反馈；若反馈可稳定自动判断，升级为脚本检查，否则沉淀为软规则。

## 禁止操作

绝对不要执行 `git add -A` 或 `git add .`。绝对不要 `git cherry-pick`、`git rebase`、提交 `Co-Authored-By`、跳过测试、跳过 benchmark、在 PR description 数据不完整时创建 PR、在脚本失败后继续提交流程。

## References

- `references/rule-structure.md` — 硬规则/软规则划分和后续维护方法
- `references/soft-rules.md` — AI 提交前自检的软规则
- `references/workflow.md` — 子代理单算子流程细节
- `references/pr-template.md` — PR 描述模板、JSON 字段映射
- `references/naming.md` — 下划线算子命名规则对照表
- `references/advanced-rules.md` — 非 pointwise benchmark、多变体算子、国产 GPU 数据等深层规则
- `references/pr-checklist.md` — 提交前检查清单
- `references/common-issues.md` — 历史 review 问题汇总
