---
name: flaggems-pr-submit
description: Use this skill to orchestrate initial FlagGems operator PR creation for generated .worktrees/gen-* operators.
---

# FlagGems 算子初次 PR 提交 Skill

你是主代理，只做统筹。每个算子交给一个独立 operator 子代理完成初次 PR 全流程。暂不处理 review follow-up。

## 输入和自动推断

用户至少提供一个算子名。可以一次提交多个算子，但算子数不得超过可用 GPU slot 数；否则停止并要求用户减少算子或提供更多 GPU。

不要硬编码工作目录、worktree 目录、remote 或仓库名。先用 `scripts/context.py` 自动推断：

- `repo_dir` 默认当前工作目录。
- `worktree_root` 默认 `<repo_dir>/.worktrees`。
- `norm_xlsx` 从 `--norm-xlsx`、`FLAGGEMS_NORM_XLSX`、`<repo_dir>/规范名.xlsx`、`<repo_dir>/../规范名.xlsx` 推断。
- `upstream_remote` / `fork_remote` 从 `git remote -v` 推断。
- `upstream_repo` / `fork_repo` 从 remote URL 推断。
- `base_branch` 优先从本地 upstream ref 推断，否则默认 `master`。
- GPU 从 `CUDA_VISIBLE_DEVICES` 或 `nvidia-smi` 推断；多个算子自动分配不同 GPU。
- `tested_on` 从 `nvidia-smi` 推断；失败时向用户询问。

推断失败或结果明显不对时，停止并询问用户，不要猜。

生成 context：

```bash
python <SKILL_DIR>/scripts/context.py write \
  --op <raw_op_1> \
  --op <raw_op_2>
```

必要时补充参数，例如：

```bash
python <SKILL_DIR>/scripts/context.py write \
  --repo-dir <repo_dir> \
  --worktree-root <worktree_root> \
  --norm-xlsx <norm_xlsx> \
  --gpu-map <op1>:0 \
  --gpu-map <op2>:1 \
  --upstream-remote <upstream> \
  --fork-remote <fork> \
  --output <repo_dir>/.pr_context.json
```

## 主代理调度

读取 context 中的 `ops`。对每个规范名算子派遣一个子代理，子代理只读取：

- `agents/operator-pr.md`
- `references/general-spec.md`
- `references/operator-agent-spec.md`
- context JSON
- 当前算子的 worktree 文件

每个子代理运行：

```bash
python <SKILL_DIR>/scripts/submit_operator.py <op> --context <context.json>
```

该脚本覆盖初次 PR 的完整流程：规范名确认、上游冲突检查、创建 `pr/<op>`、worktree 静态 gate、worktree 测试和 benchmark、提取、strict check、pre-commit、PR 分支测试和 benchmark、commit、push、创建 PR。

如果子代理失败，主代理只汇总失败阶段、失败命令、失败原因和需要用户补充的信息。不要跳过失败步骤。

## 总规范和分规范

总规范在 `references/general-spec.md`。每个 operator 子代理还必须遵守 `references/operator-agent-spec.md`。

关键约束：单 PR 单 aten 算子；先修 worktree 再提取；禁止 torch fallback；必须通过精度测试和 `--level core` benchmark；benchmark 0 cases 或无真实性能数据不得提交；禁止 `git add -A`、`git add .`、`git cherry-pick`、`git rebase`、`Co-Authored-By`。
