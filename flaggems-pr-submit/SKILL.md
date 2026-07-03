---
name: flaggems-pr-submit
description: Orchestrate initial FlagGems operator PR creation directly from generated .worktrees/gen-* branches.
---

# FlagGems 算子初次 PR 提交 Skill

主代理只做统筹。当前版本是 document-only workflow：skill 包不提供流程脚本入口。子代理可以运行 shell、git、python、pytest、pre-commit、gh 等命令；检查逻辑来自文档和项目文件。

本版本只处理初次创建 PR，不处理 review follow-up，不创建 `pr/<op>` 分支。所有工作都在对应算子的 `gen-<op>` worktree/branch 内完成，最终 PR 也从该 gen branch 发起。

## 输入和推断

用户至少提供一个算子名。可以一次提交多个算子，但算子数不得超过可用 GPU slot 数。GPU 数从 `CUDA_VISIBLE_DEVICES` 或 `nvidia-smi` 推断；推断失败就询问用户。多算子时，每个算子分配一个不同 GPU。

主代理自己完成环境和输入检查，不派专门子代理。默认值：

- `repo_dir`：当前工作目录，必要时用 Git repo root 修正。
- `worktree_root`：`<repo_dir>/.worktrees`。
- `norm_xlsx`：用户提供值、`FLAGGEMS_NORM_XLSX` 或附近 `规范名.xlsx`。
- `upstream_remote` / `fork_remote`：从 Git remotes 推断。
- `upstream_repo` / `fork_repo`：从 remote URL 推断。
- `base_branch`：优先 upstream master，其次 upstream main；仍不确定则询问。
- `tested_on`：从 GPU 信息推断；失败时询问。

推断失败或结果明显不对时，停止并向用户要具体值。

## 主代理调度

主代理得到上下文后，对每个规范名算子启动一个 operator coordinator。每个 coordinator 的工作目录固定为该算子的 gen worktree。子代理不允许操作其他 worktree 或主仓库目录。

每个 coordinator 按顺序派遣：

1. `agents/name-worktree.md`：规范名、命名、gen worktree、上游冲突。
2. `agents/implementation-review.md`：gen worktree 内 kernel/test/benchmark/yaml 静态审查和修复。
3. `agents/worktree-test-benchmark.md`：gen worktree 精度测试和 core benchmark。
4. `agents/extract-register.md`：在 gen worktree 内整理目标六类文件和注册项。
5. `agents/final-validation.md`：gen branch 最终验证、提交、push、创建 PR。

主代理派遣时必须把对应模板中的 `{OP}`、`{RAW_OP}`、`{GEN_WORKTREE}`、`{OP_ID}`、`{MODULE}`、`{GPU}` 等占位符替换为真实值。

## 规范文件

每个子代理读取自己的分规范，不再读取统一 general 规范。

分规范：`name-worktree-spec.md`、`implementation-review-spec.md`、`test-benchmark-spec.md`、`extract-register-spec.md`、`final-pr-spec.md`。

约束归属表：`references/constraint-map.md`。

## 失败策略

任何子代理发现阻塞项，当前算子停止。主代理汇总算子名、失败子代理、失败命令、失败原因、需要用户补充的信息或建议修复方向。不要跳过失败步骤，不要编造 benchmark 或多后端数据。
