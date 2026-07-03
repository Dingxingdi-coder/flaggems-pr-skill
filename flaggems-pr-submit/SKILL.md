---
name: flaggems-pr-submit
description: Use this skill to orchestrate initial FlagGems operator PR creation for generated .worktrees/gen-* operators.
---

# FlagGems 算子初次 PR 提交 Skill

你是主代理，只做统筹。当前版本采用 document-only workflow：skill 包不提供流程脚本入口。子代理可以运行 shell、git、python、pytest、pre-commit、gh 等命令，但检查逻辑来自文档而不是仓库内脚本。

暂不处理 review follow-up，只处理初次创建 PR。

## 输入和推断

用户至少提供一个算子名。可以一次提交多个算子，但算子数不得超过可用 GPU slot 数。GPU 数从 `CUDA_VISIBLE_DEVICES` 或 `nvidia-smi` 推断；推断失败就询问用户。多算子时，每个算子分配一个不同 GPU。

主代理先派遣 `agents/context-discovery.md` 子代理收集上下文。默认值如下：

- `repo_dir`：当前工作目录，必要时用 `git rev-parse --show-toplevel` 修正。
- `worktree_root`：`<repo_dir>/.worktrees`。
- `norm_xlsx`：优先用户提供，其次 `FLAGGEMS_NORM_XLSX`、`<repo_dir>/规范名.xlsx`、`<repo_dir>/../规范名.xlsx`。
- `upstream_remote` / `fork_remote`：从 `git remote -v` 推断；不确定时询问。
- `upstream_repo` / `fork_repo`：从 remote URL 推断。
- `base_branch`：优先 `upstream/master`，其次 `upstream/main`；仍不确定则询问。
- `tested_on`：从 `nvidia-smi` 推断；失败时询问。

推断失败或结果明显不对时，停止并向用户要具体值，不要猜。

## 主代理调度

主代理得到上下文后，对每个规范名算子启动一个 operator coordinator。每个 coordinator 按顺序派遣以下专业子代理：

1. `agents/name-branch.md`：规范名、命名、上游冲突、分支。
2. `agents/implementation-review.md`：worktree kernel/test/benchmark/yaml 静态审查和修复。
3. `agents/worktree-test-benchmark.md`：worktree 精度测试和 `--level core` benchmark。
4. `agents/extract-register.md`：从修复后的 worktree 手动提取并注册六类文件。
5. `agents/final-validate-pr.md`：PR 分支验证、commit、push、创建 PR。

每个子代理只读取总规范、自己的分规范、上下文和目标算子文件。不要把所有文档塞给同一个子代理。

## 规范文件

总规范：`references/general-spec.md`。

分规范：

- `references/context-discovery-spec.md`
- `references/name-branch-spec.md`
- `references/implementation-review-spec.md`
- `references/test-benchmark-spec.md`
- `references/extract-register-spec.md`
- `references/final-pr-spec.md`

约束归属表：`references/constraint-map.md`。

## 失败策略

任何子代理发现阻塞项，当前算子停止。主代理汇总：算子名、失败子代理、失败命令、失败原因、需要用户补充的信息或建议修复方向。不要跳过失败步骤，不要编造 benchmark 或多后端数据。
