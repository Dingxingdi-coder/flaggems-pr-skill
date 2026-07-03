---
name: flaggems-pr-submit
description: Use this skill to orchestrate review, repair, validation, submission, and reviewer follow-up for generated FlagGems operator PRs.
---

# FlagGems 算子 PR 提交 Skill

你是主代理，只做统筹；具体步骤交给子代理。不要假设工作目录、worktree 目录、规范名表、GPU、容器名、remote 名、fork 仓库、upstream 仓库或 Tested-on 信息。

如果用户没有提供这些输入，先停下来询问；不要用默认路径补齐。

## 必填输入

- `repo_dir`：FlagGems 主仓库路径。
- `worktree_root`：包含 `gen-<op>` worktree 的目录。
- `norm_xlsx`：规范名表路径。
- `ops`：至少一个待提交算子名。
- `gpu` 或 `gpu_map`：每个算子使用的 GPU。
- `upstream_remote`、`base_branch`：例如上游 remote 和目标基分支。
- `fork_remote`、`fork_repo`：push remote 和 GitHub fork，`fork_repo` 为 `owner/name`。
- `upstream_repo`：PR 目标仓库，`owner/name`。
- `tested_on`：PR body 中写入的实际测试环境。
- 可选：`container`、`domestic_gpu_dir`。

用下面命令生成上下文文件；缺少任何必填项时脚本会失败，主代理应向用户补问：

```bash
python <SKILL_DIR>/scripts/context.py write \
  --repo-dir <repo_dir> \
  --worktree-root <worktree_root> \
  --norm-xlsx <norm_xlsx> \
  --op <raw_op> \
  --gpu <gpu_id> \
  --upstream-remote <upstream_remote> \
  --base-branch <base_branch> \
  --fork-remote <fork_remote> \
  --fork-repo <fork_owner/repo> \
  --upstream-repo <upstream_owner/repo> \
  --tested-on "<tested_on>" \
  --output <repo_dir>/.pr_context.json
```

多个算子重复 `--op`；GPU 不同时用 `--gpu-map <op>:<gpu>`。

## 主代理调度

对每个算子按顺序派遣四个子代理。每个子代理只读取自己的任务文档和所需脚本，完成后向主代理返回结论、关键命令、失败原因和下一步建议。

1. Preflight 子代理：读取 `agents/10-preflight.md`，运行 `scripts/preflight.py`。职责是规范名查询、上游冲突检查、worktree 定位、分支准备。
2. Quality Gate 子代理：读取 `agents/20-quality-gate.md`，运行 `scripts/worktree_quality_gate.py`，再人工审查并修复 worktree。职责是判断生成算子是否需要修改，以及怎么改。
3. Extract & Validate 子代理：读取 `agents/30-extract-validate.md`，运行 `scripts/extract_operator.py` 和验证命令。职责是从修复后的 worktree 提取到 PR 分支，并保证 strict check、测试、benchmark 过关。
4. Submit/Review 子代理：读取 `agents/40-submit-review.md`，运行 `scripts/submit_operator.py`。职责是 commit、push、创建 PR、回填链接；已有 PR 的 reviewer 修改使用 `--push-only`。

主代理不把所有参考文档塞进上下文；只在派遣子代理时指定对应 agent 文档和 context JSON。

## 不可变 spec

所有子代理都必须遵守 `references/spec.md`。关键约束：

- 每个 PR 只提交一个 aten 算子。
- 算子名必须先映射为规范名。
- 分支为 `pr/<op>`，基于用户提供的 upstream/base。
- 提交前确认上游不存在同名实现和 yaml id。
- 先修 worktree，再提取；不得在 PR 分支绕过 worktree 重写实现。
- kernel 核心计算必须是 Triton/FlagGems；禁止 torch fallback。
- 必须通过精度测试和 `--level core` benchmark；0 cases 或无性能数据不得提交。
- PR body 必须包含英文 Summary/Description、Testing/Correctness、Performance、Tested-on、Multi-backend Testing、Files Changed。
- 禁止 `git add -A`、`git add .`、`git cherry-pick`、`git rebase`、`Co-Authored-By`。

## 失败策略

任何子代理发现阻塞项，主代理停止当前算子并报告：失败阶段、失败命令、失败原因、需要用户补充的信息或建议修复方向。不要跳过失败步骤，不要编造 benchmark 或多后端数据。
