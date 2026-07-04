---
name: flaggems-pr-submit
description: Orchestrate initial FlagGems operator PR creation directly from generated .worktrees/gen-* branches.
---

# FlagGems 算子初次 PR 提交 Skill

你是主代理，只做统筹，继续派遣子代理对每一个算子提交 PR。子代理可以运行 shell、git、python、pytest、pre-commit、gh 等命令；规则来源是本 skill 的脚本、规范文档和目标项目文件。

只处理初次创建 PR。所有工作都在对应算子的 `gen-*` worktree/branch 内完成，最终 PR 也从该 gen branch 发起。不要创建额外的 `pr/<op>` 分支。

## 结构原则

本 skill 按规则类型维护，而不是把所有规则堆在提示词里：

- 硬约束是脚本可判定的机械规则，放在 `scripts/`，并登记在 `references/hard-constraints.md`；子代理必须运行脚本，不要手写等价检查；
- 软约束是需要主代理或子代理理解代码、reviewer 意图或性能语义后判断的规则，放在 `references/<subagent>/`、`references/shared/`，维护约定见 `references/soft-constraints.md`；
- 从 reviewer 反馈沉淀的新规则先按 `references/reviewer-feedback-intake.md` 分流：可稳定脚本化的进入硬约束脚本，不可稳定脚本化的进入 `references/shared/reviewer-learned-rules.md`。

维护规则边界见 `references/rule-structure.md`，当前责任表见 `references/constraint-map.md`。

## Workflow

### 输入和推断

* `{SKILL_ROOT}` 是本 skill 目录 `flaggems-pr-submit/` 的绝对路径。主代理派遣子代理时必须传入它。
* 使用 `nvidia-smi` 检查 GPU 状态和数量，推断 tested_on。
* 用户至少提供一个算子名。可以一次提交多个算子，但算子数不得超过可用 GPU slot 数。多算子时，每个算子分配一个不同 GPU。用户提供的都是原始算子名，即 `<raw_op>`。
* `<repo_root>` 为当前工作目录，`<worktree_root>` 为 `<repo_root>/.worktrees/`。
* 使用 `git remote -v` 查看远程仓库地址，理想状况应该类似：
    ```
    origin  https://github.com/<username>/FlagGems (fetch)
    origin  https://github.com/<username>/FlagGems (push)
    upstream        https://github.com/flagos-ai/FlagGems.git (fetch)
    upstream        no_push (push)
    ```
  从而确定 `{FORK_REMOTE}`、`{upstream}`、`{UPSTREAM_REPO}` 和 `{base_branch}`。`{upstream}` 是本地 upstream remote 名，`{base_branch}` 通常是 `master`，`{UPSTREAM_REPO}` 通常是 `flagos-ai/FlagGems`。
* 要求用户提供 `规范名.xlsx` 的路径，即 `<norm_xlsx>`。

上述内容只有在无法从命令或用户已有输入中获得时才询问用户。不要询问可以由脚本或仓库状态确定的信息。

### 必要流程

每个算子都必须经过以下流程；任一阻塞则停止该算子：

1. `name-worktree`：运行 resolver 脚本完成规范命名、worktree 解析、gen 分支检查和 upstream 冲突检查。
2. `implementation-review`：只在目标 gen worktree 内审查和修复实现、测试、benchmark、yaml 和注册相关问题。
3. `worktree-test-benchmark`：运行目标算子的 accuracy test 和 `--level core` benchmark，收集真实结果。
4. `register`：完成注册面一致性修复，并运行静态 gate 脚本。
5. `final-validation`：再次运行静态 gate、格式化/测试/benchmark、显式 stage、commit、push，并创建初始 PR。

### 派遣子代理

对每个算子派遣一组子代理，他们的工作目录固定为该算子的 gen worktree。主代理按顺序发送以下模板：

1. `references/prompt-templates/name-worktree.md`
2. `references/prompt-templates/implementation-review.md`
3. `references/prompt-templates/worktree-test-benchmark.md`
4. `references/prompt-templates/register.md`
5. `references/prompt-templates/final-validation.md`

主代理派遣时必须替换模板中出现的所有 `{...}` 占位符：

* 所有模板都使用 `{SKILL_ROOT}`。
* `name-worktree` 使用 `{raw_op}`、`{worktree_root}`、`{norm_xlsx}`、`{upstream}`、`{base_branch}`，并由 resolver 脚本产出后续子代理需要的 `{OP}`、`{OP_ID}`、`{MODULE}`、`{GEN_WORKTREE}`、`{GEN_BRANCH}`、`{UPSTREAM_REF}`。
* 后续子代理使用 `{OP}`、`{GEN_WORKTREE}`、`{OP_ID}`、`{MODULE}`、`{GPU}`。`register` 和 `final-validation` 还使用 `{UPSTREAM_REF}`。
* `final-validation` 额外使用 `{FORK_REMOTE}`、`{UPSTREAM_REPO}`、`{BASE_BRANCH}`、`{TESTED_ON}`。
* 每个模板只描述子代理边界、必须运行的脚本和应读取的专属规范目录；具体规则以 `references/` 下的文件和 `scripts/` 为准。

子代理只在 `{GEN_WORKTREE}` 内做仓库操作；允许只读访问本 skill 的 reference 文件和运行本 skill 的 scripts；除 upstream 只读检查外不访问其他目录。

## 失败策略

任何子代理发现阻塞项，当前算子停止。主代理汇总算子名、失败子代理、失败命令、失败原因、需要用户补充的信息或建议修复方向。不要跳过失败步骤，不要编造 benchmark 或多后端数据。
