---
name: flaggems-pr-submit
description: Use this skill when reviewing, repairing, testing, and submitting FlagGems NVIDIA general operator PRs generated under Dingxingdi/FlagGems .worktrees/gen-*.
---

# FlagGems 算子 PR 提交 Skill

目标：把 `.worktrees/gen-<op>` 中弱模型生成的算子，先审查并必要修复，再完成精度测试、benchmark、PR 提交和 reviewer 交互。最终 PR 应尽量一次满足 `flagos-ai/FlagGems` review 要求。

## 不可变约束

这些是 spec 约束，不因“简化流程”而放宽。

1. 每个 PR 只提交一个 aten 算子；多算子需求按算子拆成独立分支和独立 PR。
2. 算子名必须先通过 `operator_registry.py lookup` 映射到规范名；后续 branch、mark、yaml id、benchmark `op_name` 等均按规范名和 `op_naming.py` 的规则处理。
3. 分支统一为 `pr/<op>`，基于 `upstream/master`；PR 目标为 `flagos-ai/FlagGems:master`；推送到 `Dingxingdi/FlagGems` 的 `fork` remote。
4. 提交前必须确认上游不存在该算子。若已存在，停止处理该算子。
5. 生成代码不可信。必须先在 `.worktrees/gen-<op>` 内审查并修复，再从该 worktree 提取；PR 中的实现必须来自“已修复的 worktree”，不能在 PR 分支上绕过提取流程重写测试或 benchmark。
6. 不得删除 worktree 中有价值的注释；不得修改上游已有测试函数，只能新增目标算子的测试/benchmark 或按 append mode 追加。
7. kernel 核心计算必须是 Triton/FlagGems 实现；禁止用 `torch.<op>`、`torch.nn.functional.*` 或等价 torch fallback 完成核心计算。
8. 必须有精度测试和 `--level core` benchmark；benchmark 0 cases、benchmark 失败、无 speedup/case 数、PR body 数据不完整时不得创建 PR。
9. PR description 必须包含英文 Summary/Description、Testing/Correctness、Performance、Tested-on、Multi-backend Testing、Files Changed；Performance 要按 dtype/case 记录，不能只写一个总 speedup。
10. `check_operator.py --strict`、多重载一致性检查、pre-commit、本地测试、benchmark 任一步失败，都必须修复后重跑；不得跳过或手动绕过。
11. 禁止 `git add -A`、`git add .`、`git cherry-pick`、`git rebase`、commit message 中的 `Co-Authored-By`。
12. 如果 reviewer 要求修改，仍遵循“先修 worktree、再提取/验证、再 push”的原则；只有纯格式或 PR 文案修改可以直接在 PR 分支处理。

详细规则保留在 `references/`：`operator-quality.md`、`workflow.md`、`naming.md`、`advanced-rules.md`、`pr-template.md`、`pr-checklist.md`、`common-issues.md`。

## 环境约定

默认仓库路径：`/data/dxd/FlagGems_minimax_2_7_pr`。默认 worktree：`/data/dxd/FlagGems_minimax_2_7_pr/.worktrees/gen-<op>`。默认规范名表：`/data/dxd/规范名.xlsx`。运行环境通常是宿主机 `baai-sailing-h20-0` 上的 Docker 容器 `dxd`，GPU 为 NVIDIA H20/CUDA 13.2。

如果当前已经在容器内，所有命令直接执行；如果当前在宿主机，先进入用户指定的容器。开始前必须确认 `nvidia-smi` 可用、`git remote -v` 中有 `upstream` 和可 push 的 `fork` remote、`gh` 已登录或 `GH_TOKEN` 可用。

## 标准流程

### 0. 会话预检

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
nvidia-smi
git remote -v
git fetch upstream master
```

确认 remote 语义：`upstream` 指向 `flagos-ai/FlagGems`；`fork` 指向 `Dingxingdi/FlagGems`。如果只有 `origin` 是 Dingxingdi fork，先补齐或别名为 `fork`，否则 `submit_operator.py` 会在 push 阶段失败。

### 1. 规范名查询与上游冲突检查

```bash
python <SKILL_DIR>/scripts/operator_registry.py lookup <raw_op> --norm-xlsx /data/dxd/规范名.xlsx
```

使用输出的规范名 `<op>` 继续。若查不到规范名，停止并要求用户提供规范名。然后检查上游是否已有实现：

```bash
git show upstream/master:src/flag_gems/ops/<module>.py
```

该命令预期失败。`<module>` 按 `scripts/op_naming.py` 解析；普通算子等于 `<op>`，前导下划线保留在 kernel 文件名中。若上游已有同名实现或 yaml id 冲突，停止该算子。

创建或切换分支：

```bash
git checkout -B pr/<op> upstream/master
```

只有在确认该 PR 分支没有需要保留的人工提交时才使用 `-B`。已有 reviewer 交互中的分支不要重置，改为 `git checkout pr/<op>` 并检查 `git log upstream/master..HEAD`。

### 2. Worktree 审查与修复

进入生成 worktree：

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr/.worktrees/gen-<op>
```

按 `references/operator-quality.md` 审查 kernel、test、benchmark、yaml、注册项。弱模型输出只要存在下列问题就必须先修：核心 torch fallback、重复/未使用函数、错误 dtype、错误 mark/yaml id、测试未覆盖真实 dispatch、benchmark 计算量不公平、非 pointwise benchmark 用错封装、0 case、硬编码超参无说明、未处理 out/inplace/overload、PR 会修改上游已有测试等。

修复必须优先发生在 worktree 内。修复后在 worktree 跑精度和 benchmark：

```bash
CUDA_VISIBLE_DEVICES=<N> python -m pytest tests/<test_file>.py -m <op_id> -vs
CUDA_VISIBLE_DEVICES=<N> python -m pytest benchmark/<bench_file>.py -m <op_id> -s --level core
```

记录每个 dtype 的 case 数、平均 speedup、失败 case 和 TFLOPS（如输出包含）。benchmark 输出 0 cases 时，先查 `core_shapes.yaml` 和 Benchmark `set_shapes`，不得继续提交。

### 3. 提取到 PR 分支

回到主仓库和目标分支：

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
git checkout pr/<op>
python <SKILL_DIR>/scripts/extract_from_worktree.py <op> --repo-dir /data/dxd/FlagGems_minimax_2_7_pr
```

提取后只应涉及六类文件：kernel、`src/flag_gems/ops/__init__.py`、`src/flag_gems/__init__.py`、test、benchmark、`conf/operators.yaml`。检查 yaml description、labels、stage、append mode、`_FULL_CONFIG` aten name、下划线命名、多重载对齐。

如果提取结果暴露实现问题，回到 Phase 2 修 worktree，再重新提取。不要在 PR 分支上手写一个与 worktree 不一致的新实现。

### 4. 验证与首次提交

```bash
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N>
```

脚本串行执行：`check_operator.py --strict` → 多重载一致性检查 → pre-commit → pytest → benchmark → PR 数据生成 → commit → push → `gh pr create` → PR 链接回填。任何一步失败即停止。修复后重新运行同一命令。

不得使用 `--skip-test` 或 `--skip-benchmark` 提交真实 PR。`--dry-run` 只用于调试，不代表可提交。若 benchmark 平均 speedup < 0.8，先优化 kernel；无法优化则放弃该算子，不要降低阈值。

### 5. Reviewer 交互

收到 reviewer comment 后，先复现问题，再修复 worktree，并重新提取到 `pr/<op>`。已有 PR 不再重新创建，使用：

```bash
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N> \
  --push-only
```

如果 Performance 或 Multi-backend 数据变化，更新 PR body。回复 reviewer 时说明修改点、验证命令和关键结果；不要在未修复时把线程标记 resolved。

## 失败处理

| 场景 | 处理 |
|---|---|
| 规范名未找到 | 停止，请用户给规范名 |
| 上游已有实现或 yaml id 冲突 | 停止该算子 |
| worktree 测试/benchmark 失败 | 修复生成实现后重跑 |
| benchmark 0 cases | 修 `core_shapes.yaml`、mark、Benchmark `set_shapes` |
| `check_operator.py --strict` 失败 | 修代码，重新提取，重新运行提交脚本 |
| pre-commit 多次失败 | 手动修格式/F401，再运行提交脚本 |
| PR body 数据不完整 | 补齐 benchmark 和 Multi-backend 数据后再创建 PR |
| 回填失败 | 手动执行 `operator_registry.py backfill <op> <pr_url>`；非阻塞但必须补做 |
