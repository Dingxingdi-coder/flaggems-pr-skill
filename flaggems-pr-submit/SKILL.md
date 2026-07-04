---
name: flaggems-pr-submit
description: Orchestrate initial FlagGems operator PR creation directly from generated .worktrees/gen-* branches.
---

# FlagGems 算子初次 PR 提交 Skill

你是主代理，只做统筹，派遣子代理对每一个算子提 pr
子代理可以运行 shell、git、python、pytest、pre-commit、gh 等命令；检查逻辑来自文档和项目文件。

只处理初次创建 PR。所有工作都在对应算子的 `gen-<op>` worktree/branch 内完成，最终 PR 也从该 gen branch 发起。

## Workflow

### 输入和推断

* 使用 `nvidia-smi` 检查 GPU 状态和数量，推断 tested_on
* 用户至少提供一个算子名。可以一次提交多个算子，但算子数不得超过可用 GPU slot 数。多算子时，每个算子分配一个不同 GPU。用户提供的都是原始算子名，即 `<raw_op>`
* `<repo_root>`为当前工作目录，`<worktree_root>` 为 `<repo_root>/.worktrees/`
* 使用 `gti remote -v` 查看远程仓库地址，理想状况应该类似：
    ```
    origin  https://github.com/<username>/FlagGems (fetch)
    origin  https://github.com/<username>/FlagGems (push)
    upstream        https://github.com/flagos-ai/FlagGems.git (fetch)
    upstream        no_push (push)
    ```
  从而可以确定 `<upstream>`和 `<base_branch>` （`<base_branch>` 是 `<upstream>` 的 master 分支） 
* 要求用户提供 `规范名.xlsx` 的路径，即 `<norm_xlsx>`

上述所涉及的内容，如果存在推断失败或者用户没有提供，停下来，向用户询问，直到获取到所有必要信息，再进行下一步

### 派遣子代理

对每个算子派遣一组子代理，他们的工作目录固定为该算子的 gen worktree。

1. `references/prompt-templates/name-worktree.md`
2. `references/prompt-templates/implementation-review.md`
3. `references/prompt-templates/worktree-test-benchmark.md`
4. `references/prompt-templates/register.md`
5. `references/prompt-templates/final-validation.md`

主代理派遣时必须把模板中的 `{OP}`、`{RAW_OP}`、`{GEN_WORKTREE}`、`{OP_ID}`、`{MODULE}`、`{GPU}` 等占位符替换为真实值，再把替换后的完整提示词发送给子代理。子代理只在 `{GEN_WORKTREE}` 内工作，除上游只读检查外不访问其他目录。

## 失败策略

任何子代理发现阻塞项，当前算子停止。主代理汇总算子名、失败子代理、失败命令、失败原因、需要用户补充的信息或建议修复方向。不要跳过失败步骤，不要编造 benchmark 或多后端数据。
