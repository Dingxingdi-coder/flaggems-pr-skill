# Workflow 详细操作指南

本流程与 `SKILL.md` 保持一致：先审查并修复 generated worktree，再测试、提取、提交。旧流程中“代码与 worktree 原版一致”的含义更新为：PR 分支代码必须与“修复后的 worktree”一致，不得在 PR 分支绕过 worktree 手写实现。

## Phase 0: 环境预检

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
nvidia-smi
git remote -v
git fetch upstream master
```

必须确认：

- 当前在容器内，或已经通过 `docker exec -it <container> bash` 进入容器。
- `upstream` 指向 `flagos-ai/FlagGems`。
- `fork` 指向 `Dingxingdi/FlagGems` 且可 push；如果只有 `origin` 是 fork，补齐 `fork` remote。
- `git config user.name` / `git config user.email` 正确。
- `gh` 已登录或 `GH_TOKEN` 可用。

## Phase 1: 规范名和分支

```bash
python <SKILL_DIR>/scripts/operator_registry.py lookup <raw_op> --norm-xlsx /data/dxd/规范名.xlsx
```

脚本输出规范名。若查不到，停止并请用户提供规范名。

检查上游冲突：

```bash
git show upstream/master:src/flag_gems/ops/<module>.py 2>/dev/null
```

该命令应失败。还要检查 yaml id：

```bash
git show upstream/master:conf/operators.yaml | grep -n "id: <op_id>"
```

如果 kernel 文件或 yaml id 已存在，不提交该算子。

创建新 PR 分支：

```bash
git checkout -B pr/<op> upstream/master
```

如果这是已有 PR 的 reviewer 修改，不要重置分支；执行 `git checkout pr/<op>`，然后检查：

```bash
git log --oneline upstream/master..HEAD
git diff --name-only upstream/master..HEAD
```

## Phase 2: Worktree 审查与修复

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr/.worktrees/gen-<op>
```

审查文件：kernel、test、benchmark、两个 `__init__.py`、`conf/operators.yaml`。按 `operator-quality.md` 修复问题。修复原则：

- 实现问题先改 worktree，不直接改 PR 分支。
- 只允许目标算子相关改动。
- 不删有价值注释；不修改上游已有测试函数。
- 修复 test/benchmark 时保留原测试意图，但必须移除 QUICK_MODE、vendor-specific 分支和调试输出。
- 如果 generated 实现本质上是 torch fallback 或错误算法，重写为合规 Triton/FlagGems 实现；无法可靠修复则放弃该算子。

在 worktree 跑测试和 benchmark：

```bash
CUDA_VISIBLE_DEVICES=<N> python -m pytest tests/<test_file>.py -m <op_id> -vs
CUDA_VISIBLE_DEVICES=<N> python -m pytest benchmark/<bench_file>.py -m <op_id> -s --level core
```

记录：dtype、case 数、平均 speedup、失败信息、TFLOPS（如有）。benchmark 0 cases 先修 `core_shapes.yaml`、mark 或 Benchmark `set_shapes`。

## Phase 3: 提取六类文件

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
git checkout pr/<op>
python <SKILL_DIR>/scripts/extract_from_worktree.py <op> --repo-dir /data/dxd/FlagGems_minimax_2_7_pr
```

脚本负责复制 kernel/test/benchmark，并更新：

1. `src/flag_gems/ops/<module>.py`
2. `src/flag_gems/ops/__init__.py`
3. `src/flag_gems/__init__.py`
4. `tests/test_<op_id>.py`
5. `benchmark/test_<op_id>.py`
6. `conf/operators.yaml`

提取后人工检查：

- `operators.yaml` description 是否准确，labels 是否含 `aten` 和 `KernelGen`，stage 是否为 `alpha: '5.1'`。
- 前导下划线命名是否符合 `naming.md`。
- `_FULL_CONFIG` 的 aten name 是否是真实 dispatch 名，overload 是否保留点号。
- append mode 是否只追加目标算子，不改已有测试。
- diff 是否只包含目标算子相关文件。

如果发现需要改实现，回 Phase 2 修 worktree，再重新提取。

## Phase 4: 一站式验证和创建 PR

```bash
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N>
```

脚本执行：

1. `check_operator.py --strict`
2. `check_overload_consistency.py`
3. `pre-commit run --files ...`
4. `pytest tests/test_<op_id>.py`
5. `pytest benchmark/test_<op_id>.py --level core -s`
6. `gen_pr_description.py`
7. 逐文件 `git add` 和 commit
8. push 到 `fork/pr/<op>`
9. `gh pr create` 到 `flagos-ai/FlagGems:master`
10. `operator_registry.py backfill`

不要使用 `--skip-test` 或 `--skip-benchmark` 创建真实 PR。`--dry-run` 只用于调试。

## Phase 5: Reviewer 修改

已有 PR 的修改流程：

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
git checkout pr/<op>
# 回到 .worktrees/gen-<op> 修复并重新提取
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N> \
  --push-only
```

`--push-only` 会验证、commit、push，但不创建新 PR。若 PR body 的性能或测试数据变化，用 `gh pr edit --body-file` 或 GitHub 页面更新。回复 reviewer 时包含：修改摘要、验证命令、关键结果和 commit SHA。

## 失败处理规则

| 失败 | 处理 | 禁止 |
|---|---|---|
| 规范名未找到 | 停止，请用户给规范名 | 猜测命名继续 |
| 上游已有同名实现/yaml id | 停止该算子 | 重复提交 |
| worktree 测试失败 | 修 kernel/test 后重跑 | 降低测试覆盖 |
| benchmark 失败或 0 cases | 修 benchmark/core_shapes | 创建无性能 PR |
| speedup < 0.8 | 优化或放弃 | 降低阈值 |
| check_operator strict 失败 | 修代码再重跑提交脚本 | 手动跳过失败步骤 |
| pre-commit 失败 | 修格式/F401 后重跑 | `git commit --no-verify` |
| PR body 数据缺失 | 补 benchmark/Multi-backend | 编造数据 |
