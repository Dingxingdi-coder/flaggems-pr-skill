# Workflow 详细操作指南

本文件描述一个子代理处理一个算子的流程。主代理只负责分配算子/GPU、收集结果和失败原因。

## Phase 0：输入与环境

必要输入：原始算子名、可用 GPU 编号、FlagGems 仓库路径、`规范名.xlsx` 路径。默认仓库路径：`/data/dxd/FlagGems_minimax_2_7_pr`。默认规范名表：`/data/dxd/规范名.xlsx`。

若命令已经在容器内运行，不需要 SSH 或 `docker exec`。若实际在宿主机，先进入用户指定容器，再执行后续命令。

## Phase 1：Preflight

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
export FLAGGEMS_NORM_XLSX=/data/dxd/规范名.xlsx
python <SKILL_DIR>/scripts/prepare_operator.py <raw_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --norm-xlsx "$FLAGGEMS_NORM_XLSX" \
  --create-branch
```

该脚本完成四件事：查询规范名；检查 `upstream` 和提交用 remote；fetch `upstream/master`；检查 upstream 是否已有实现或注册；创建并 checkout `pr/<norm_op>`。脚本失败时停止。

输出字段：`operator=<norm_op>`、`op_id=<op_id>`、`module=<module>`。后续命令使用这些值。

## Phase 2：Worktree 测试与 benchmark

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr/.worktrees/gen-<norm_op>
CUDA_VISIBLE_DEVICES=<N> python -m pytest tests -m <op_id> -vs
CUDA_VISIBLE_DEVICES=<N> python -m pytest benchmark -m <op_id> -s --level core
```

记录 dtype、case 数、平均 speedup 和失败 case。benchmark 必须带 `-s`。若 benchmark 输出 0 case，检查 `core_shapes.yaml`、pytest mark 和 Benchmark 子类的 `set_shapes`。

## Phase 3：Extract Code

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
python <SKILL_DIR>/scripts/extract_from_worktree.py <norm_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr
```

脚本准备六个 PR 文件：

1. `src/flag_gems/ops/<module>.py`
2. `src/flag_gems/ops/__init__.py`
3. `src/flag_gems/__init__.py`
4. `tests/test_<op_id>.py`
5. `benchmark/test_<op_id>.py`
6. `conf/operators.yaml`

提取后只允许做必要修复：import、格式、description、dtype 注释、benchmark 公平性修复、review 规则要求的语义修复。不要手写替代 worktree 的 test/benchmark。

## Phase 4：Soft Review

```bash
cat <SKILL_DIR>/references/rule-structure.md
cat <SKILL_DIR>/references/soft-rules.md
cat <SKILL_DIR>/references/pr-checklist.md
```

逐项检查软规则。重点看 dtype 语义、非 pointwise benchmark、概率/NaN 语义、多变体一致性、平台无关性、PR 描述数据完整性。

## Phase 5：Validate/Test/Submit

```bash
cd /data/dxd/FlagGems_minimax_2_7_pr
export FLAGGEMS_NORM_XLSX=/data/dxd/规范名.xlsx
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <norm_op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr \
  --gpu <N>
```

脚本内部会执行 strict 检查、多重载一致性、pre-commit、本地 test、benchmark、PR 描述生成、commit、push、创建 PR、回填链接。失败后修复原因并重新运行同一命令，不要手动跳到后续步骤。

## 失败处理

| 失败场景 | 处理方式 | 禁止做法 |
|---|---|---|
| preflight 发现 upstream 冲突 | 停止该算子并报告 | 继续提交同名算子 |
| worktree test/benchmark 失败 | 修复生成代码或放弃该算子 | 提取后硬凑 |
| `check_operator.py` 失败 | 修复代码后重新运行 submit 脚本 | 手动跳过检查 |
| pre-commit 失败 | 修复格式或未使用 import | 跳过 pre-commit |
| benchmark 0 case | 修 benchmark mark/shapes | 用 0 case 创建 PR |
| PR 描述缺性能数据 | 补齐 benchmark 数据 | 编造数据 |
| backfill 失败 | 单独运行 `operator_registry.py backfill` | 视为 PR 失败 |

## Git 注意事项

只允许逐文件 stage；不要 `git add -A` 或 `git add .`。不要 cherry-pick 或 rebase。commit message 不得包含 `Co-Authored-By`。
