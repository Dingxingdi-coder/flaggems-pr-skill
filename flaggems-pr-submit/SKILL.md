---
name: flaggems-pr-submit
description:This skill should be used when submitting FlagGems **NVIDIA general** operator PRs, reviewing operator code before submission, preparing operator code for PR.
---

# FlagGems 算子 PR 提交 Skill

提交流程：规范名查询 → 建分支 → worktree 测试/benchmark → 提取 worktree 代码(6文件) → PR 数据完整性检查 → 脚本验证 → pre-commit → push → 创建 PR → 回填链接。

## Rules（违反会导致 PR 被拒）

> 25+ 项检查已由 `check_operator.py` 自动执行（详见下方检查表），以下仅列出**模型需主动注意**的规则。

### 流程规则
1. **先跑脚本再 commit** — `check_operator.py --strict` 必须 0 errors
2. **使用规范命名** — 提交前用 `operator_registry.py lookup` 查询
3. **回填 PR 链接** — PR 创建后必须 `operator_registry.py backfill`
4. **PR 描述由脚本生成** — `gen_pr_description.py` 输出 JSON，映射到模板（英文）
5. **PR 前数据完整** — 创建 PR 前必须确认 NVIDIA speedup/case 数、dtype 分表、Multi-backend Testing 信息齐全

### 代码规则
6. **代码必须与 worktree 原版一致** — 不允许重写测试逻辑，仅允许 import 调整和格式化
7. **不删 worktree 现有注释**
8. **下划线命名** — 前导 `_` 的算子，mark/yaml id/文件名去掉下划线，其余保留（详见 `references/naming.md`）
9. **dtype 默认用常量** — test 用 `utils.FLOAT_DTYPES`，benchmark 用 `consts.FLOAT_DTYPES`；CUDA 不支持时可硬编码但必须加注释
10. **非 pointwise benchmark** — 从 worktree 提取 Benchmark 子类，覆盖 `set_shapes`（详见 `references/advanced-rules.md` §1）
11. **hardcode size 需加注释** — kernel BLOCK、test shapes、benchmark shapes 都需注释说明原因
12. **核心计算必须 Triton kernel** — 禁止用 torch 做核心计算（详见 `references/advanced-rules.md` §2）
13. **overloaded ops yaml 拆成独立条目** — 参考 `eq` / `eq_scalar` 模式（详见 `references/advanced-rules.md` §4）

### 提交规则
14. **不修改上游已有测试** — 只新增，不改已有函数
15. **先提交通用版，再提交特化版**
16. **禁止 Co-Authored-By** — commit message 不得包含，否则 CLA CI 不过
17. **每 PR 只含一个 aten 算子** — `git diff --name-only upstream/master..HEAD` 验证

## Environment

**运行环境：宿主机 `baai-sailing-h20-0` 上的 Docker 容器 `dxd`。**

所有命令在容器内执行，无需 SSH 或 `docker exec`。GPU 为 NVIDIA H20，CUDA 13.2，无 conda（FlagGems 通过 pip 安装）。

| Item | Value |
|------|-------|
| Runtime | Docker 容器 `dxd`（宿主机 `baai-sailing-h20-0`） |
| GPU | NVIDIA H20, CUDA 13.2 |
| Repo | `/data/dxd/FlagGems_minimax_2_7_pr` |
| Fork | `Dingxingdi/FlagGems` |
| Upstream | `flagos-ai/FlagGems` |
| Worktrees | `.worktrees/gen-<op>` (687 operators) |
| Branch | `pr/<op>` |
| Push remote | `fork` |
| Token | `` |
| Data | `/data/dxd/规范名.xlsx`, `/data/dxd/第一批pr算子.xlsx` |

每次新会话先 `export GH_TOKEN=""`

**网络代理：** git push/fetch 使用仓库级 http.proxy；`gh`、`curl` 等工具直接运行。如访问 github.com 失败，先检查 GitHub 登录状态和代理配置。

**Codex 认证环境：** Codex 命令环境可能是 `HOME=/data/dxd`，而 `gh` 登录文件在 `/root/.config/gh`。`submit_operator.py` 在 `git push` 和 `gh pr create` 两步会自动复用 `/root/.gitconfig` 与 `/root/.config/gh`（若存在），主命令不需要改。

## Workflow（模型只需调用 3 个命令）

### Phase 0：超参数以及环境变量检查

* 是否提供了容器名：你现在处于宿主机的终端环境中，所以用户给的初始提示词中必须包含容器名；在确定容器名之后，使用 `docker exec -it <container_name> bash` 进入容器环境，之后所有的命令都需要在容器中运行。
* GPU 是否可用：使用 `nvidia-smi` 检查 GPU 是否可用
* 算子名：用户至少需要提供一个要提交的算子，最多提供 GPU 数目个算子（因为每一个算子的 pr 过程至少需要使用一个 GPU）
* `规范名.xlsx` 的路径：`scripts/operator_registry.py` 需要使用 `--norm-xlsx` 参数指定规范名.xlsx 的路径
* 当前仓库是否包含 `origin` 和 `upstream` 两个远程仓库：使用 `git remote -v` 检查，输出应该类似：
  ```
  origin  https://github.com/<user.name>/FlagGems (fetch)
  origin  https://github.com/<user.name>/FlagGems (push)
  upstream        https://github.com/flagos-ai/FlagGems.git (fetch)
  upstream        no_push (push)
  ```

### Phase 1: Name Lookup
首先将用户提示词中提到的所有算子名映射成规范算子名。

脚本 `scripts/operator_registry.py` 会直接输出规范算子名。请阅读脚本，理解其使用方法.

如果存在一个算子没有找到规范算子名，停下来（而不是继续接下来的步骤），告诉用户未找到，请用户提供规范算子名。
当得到所有算子的规范名，或者说用户决定不再提交未找到规范算子名的算子时，继续执行下面的步骤。

### Phase 2: Preparation
在得到所有算子的规范名之后，首先确认算子不存在上游：
* `git fetch upstream master` 拉取上游仓库
* `git show upstream/master:src/flag_gems/ops/<op>.py` 预期失败

如果某个算子已经在上游了，停下来，告诉用户算子已存在，并且询问用户是否提交不存在的算子的 pr，不要直接继续执行下面的步骤。
对于每一个要执行 pr 的算子，创建一个新的分支 `pr/<op>`：`git branch pr/<op> upstream/master`

### Phase 3：Worktree Test

在 `<workspace>/.worktrees/gen-<op>` 中跑通精度测试和 benchmark，确认代码本身能跑通再提取：

```bash
cd <workspace>/.worktrees/gen-<op>
CUDA_VISIBLE_DEVICES=<N> python -m pytest tests/<test_file>.py -m <op> -vs
CUDA_VISIBLE_DEVICES=<N> python -m pytest benchmark/<bench_file>.py -m <op> -s --level core
```

记录 Speedup 值，后续填入 PR 描述 Performance 表格。

**Benchmark 记录要求：**
- 必须带 `-s`，否则 pytest 会捕获 stdout，看不到性能数据
- 按 dtype 分别记录 speedup、case 数、是否全 case 通过
- 记录平均 speedup 和核心 case 数，后续传给 PR 描述或国产 GPU 数据脚本
- benchmark 输出 0 cases 时，先检查 `core_shapes.yaml` 是否有对应条目，再检查 Benchmark 子类的 `set_shapes` 是否错误覆写
- 非 pointwise 算子必须确认 benchmark wrapper 与 worktree 原版一致，不能为了跑通 benchmark 改写计算量

### Phase 4: Extract Code
利用 `scripts/extract_from_worktree.py` 从 `<workspace>/.worktrees/gen-<op>` 提取 6 个文件。

阅读 `scripts/extract_from_worktree.py`，理解其使用方法。

脚本完成后检查 operators.yaml 的 description 是否需要补充。

### Phase 2.5: PR 数据完整性检查（创建 PR 前阻塞项）

在进入 Phase 3-7 前，必须确认 PR description 所需数据已经齐全：

- [ ] NVIDIA benchmark 已跑通，且记录 speedup 和 case 数
- [ ] Performance 表格按 dtype 整理，不能只写一个总 speedup
- [ ] `Tested-on` 信息包含 H20/CUDA/运行环境
- [ ] Multi-backend Testing 表格已生成或明确记录无法生成的原因
- [ ] PR body 中不缺 Performance、Correctness、Tested-on、Multi-backend Testing 关键信息

如 `<SKILL_DIR>/scripts/query_domestic_gpu.py` 存在，用它生成国产 GPU 测试表格：

```bash
python <SKILL_DIR>/scripts/query_domestic_gpu.py <op> \
  --nvidia-speedup <avg_speedup>x --nvidia-cases <N> \
  [--variants <alias1> <alias2>]
```

`--nvidia-speedup` 和 `--nvidia-cases` 来自 Phase 1.5 benchmark。`--variants` 用于 JSON 中算子名与 worktree 目录名不同的情况（如 `special_digamma` → `digamma`）。脚本输出的 Markdown 表格直接放入 PR description。

### Phase 3-7: Validate, Test, Submit（一步完成，禁止手动跳过）
```bash
CUDA_VISIBLE_DEVICES=<N> python <SKILL_DIR>/scripts/submit_operator.py <op> \
  --repo-dir /data/dxd/FlagGems_minimax_2_7_pr
```
脚本串行执行 10 步：check_operator → 多重载一致性 → pre-commit → test → benchmark → PR描述生成 → commit → push → 创建 PR → 回填链接。
**任何一步失败立即中断退出。不允许手动执行单独步骤来绕过。**

❌ **禁止跳过测试** — 测试失败说明代码有问题，必须修复后重新提交。
❌ **禁止跳过 benchmark** — 无性能数据的 PR 不提交。benchmark 失败时修复代码或放弃该算子。
❌ **禁止创建数据不完整的 PR** — PR description 缺 speedup/case 数/dtype 表格/Multi-backend 信息时，先补数据再提交。

可选参数：
- `--dry-run` — 只验证不提交（调试用，仍会运行测试和 benchmark）

## 模型必须人工检查的规则（无法自动化）

- [ ] **dtype 预检测** — 该算子 PyTorch 参考实现是否支持 Half/BFloat16？
- [ ] **benchmark 类选择** — 非 pointwise 算子是否使用了正确的封装类？
- [ ] **无效分支清理** — pointwise_dynamic 已处理类型分发时，是否有多余的 isinstance 判断？
- [ ] **不修改上游已有测试** — 新增算子时是否无意中改动了同文件中其他算子的测试？
- [ ] **概率算子** — dropout/bernoulli/rand 等是否用统计方法验证（mean/variance）？
- [ ] **多变体一致性** — `__all__` 导出数 = `_FULL_CONFIG` 条目数 = yaml 条目数 = test 函数数 = benchmark 函数数
- [ ] **inplace 变体配套** — 导出的 `_` 后缀函数必须有 yaml id + test + benchmark，否则不要导出
- [ ] **benchmark 公平性** — torch wrapper 与 gems op 计算量是否对等？backward benchmark 是否只跑了 backward？
- [ ] **autotune config 外置** — 是否有 inline `triton.Config([...])` 列表？应移到 `tune_configs.yaml`
- [ ] **benchmark shapes 外置** — `get_input_iter` 中硬编码的 shapes 是否应放到 `core_shapes.yaml`？
- [ ] **平台无关** — kernel 中是否有 `is_cuda` 等平台 hardcode？应只检查 device 一致性
- [ ] **fused 算子目录** — fused 类算子是否放在了 `src/flag_gems/fused/` 而非 `ops/`？
- [ ] **KernelGen label** — yaml 条目（含 `_out` 变体）labels 是否包含 `KernelGen`？
- [ ] **PR 分支纯净** — `git log upstream/master..HEAD` 是否只有目标算子的 commits？
- [ ] **PR 描述完整性** — 是否包含 NVIDIA dtype 分表、speedup/case 数、Tested-on、Multi-backend Testing？

## 强制执行策略

- **check_operator warning = error** — `submit_operator.py` 使用 `--strict` 模式
- **AI 生成代码不可信** — anti-hack Layer 2 验证 kernel 是否真正使用 Triton 计算
- **异常自动记录** — `submit_operator.py` 的 `fatal()` 自动追加事件到 `pr状态记录.md`

## 失败处理（确定性规则，无需判断）

| 失败场景 | 处理方式 | 禁止的做法 |
|---------|---------|-----------|
| check_operator 报 error | 修复代码后重新运行脚本 | ❌ 手动执行后续步骤 |
| pre-commit 3 次后仍失败 | 手动修复格式问题（通常是 F401） | ❌ 跳过 pre-commit |
| 本地测试失败 | 修复 kernel/test 代码后重新运行脚本 | ❌ 跳过测试 |
| benchmark 失败 | 修复 benchmark 代码后重新运行脚本 | ❌ 提交无性能数据的 PR |
| benchmark 输出 0 cases | 检查 `core_shapes.yaml`、pytest mark、`set_shapes` 覆写逻辑 | ❌ 用 0 cases 结果创建 PR |
| speedup < 0.8 | 优化 kernel 性能或放弃该算子 | ❌ 降低阈值 |
| PR description 缺性能数据 | 回到 Phase 1.5/2.5 补齐 speedup、case 数和表格 | ❌ 创建空 Performance PR |
| 国产 GPU 表格生成失败 | 记录失败原因；若上游要求多后端数据，修复脚本/数据后再提交 | ❌ 编造测试数据 |
| PR 创建失败 | 检查 token/网络后重试 | ❌ 手动用 gh 命令绕过 |
| 回填失败 | 手动执行 `operator_registry.py backfill` | 可接受，非阻塞 |

## 禁止的操作（❌ 表示绝对禁止，不是建议）

- ❌ `git add -A` 或 `git add .` — 687 worktrees 会被误加
- ❌ `git cherry-pick` — worktree 代码结构与上游不同
- ❌ `git rebase` — 分支已基于 upstream/master
- ❌ `Co-Authored-By` 在 commit message 中 — CLA CI 会失败
- ❌ 手动编写 test/benchmark 代码 — 必须从 worktree 提取
- ❌ 手动执行 submit_operator.py 的单个步骤来绕过失败
- ❌ 在脚本失败后继续提交流程
- ❌ 在 PR description 数据不完整时创建 PR

## References

- `references/workflow.md` — Phase 2 六文件详细模板、代码 review 要点
- `references/pr-template.md` — PR 描述模板、JSON 字段映射
- `references/naming.md` — 下划线算子命名规则对照表
- `references/advanced-rules.md` — 非 pointwise benchmark、多变体算子、国产GPU数据等深层规则
- `references/pr-checklist.md` — 提交前逐项检查清单
- `references/common-issues.md` — 历史 review 问题汇总
