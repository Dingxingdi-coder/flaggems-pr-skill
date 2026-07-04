# FlagGems 算子 PR 提交检查清单

子代理在运行 `submit_operator.py` 前检查本文件。脚本已覆盖的硬规则不需要手动重复逐项验证，只要确认脚本已经运行并通过。

## 硬门禁

- [ ] `prepare_operator.py` 已通过，且没有 `upstream_conflict=1`
- [ ] 当前分支为 `pr/<norm_op>`，基于 `upstream/master`
- [ ] worktree 精度测试通过
- [ ] worktree benchmark 通过，且记录了 case 数和 speedup
- [ ] `extract_from_worktree.py` 已生成六个 PR 文件
- [ ] `submit_operator.py` 已运行；其中 `check_operator.py --strict`、多重载一致性、pre-commit、本地测试、benchmark 全部通过
- [ ] 未使用 `--skip-test` 或 `--skip-benchmark` 创建真实 PR

## 六文件范围

- [ ] `src/flag_gems/ops/<module>.py`
- [ ] `src/flag_gems/ops/__init__.py`
- [ ] `src/flag_gems/__init__.py`
- [ ] `tests/test_<op_id>.py`
- [ ] `benchmark/test_<op_id>.py`
- [ ] `conf/operators.yaml`

若需要追加到已有 test/benchmark 文件，确认只追加目标算子的测试/benchmark，不改已有函数语义。

## 软规则自检

- [ ] dtype 范围与 PyTorch 参考实现一致；硬编码 dtype 有注释
- [ ] benchmark 与 torch reference 计算量公平，尤其是非 pointwise/backward/多输出算子
- [ ] yaml `id`、pytest mark、benchmark `op_name` 完全一致
- [ ] 多变体算子的每个 dispatch 路径都有独立 test 和 benchmark
- [ ] kernel 核心计算没有退化成 torch 实现
- [ ] 删除未注册、未测试、未调用的生成代码
- [ ] hardcode size/shape/block 有简短原因
- [ ] 概率、NaN、复数、边界 shape 的测试语义合理
- [ ] PR body 有 Performance、Correctness/Tested-on、Multi-backend Testing 信息
- [ ] 不编造国产 GPU 数据；缺失时说明来源或原因

## Git 与 PR

- [ ] 没有 `git add -A` 或 `git add .`
- [ ] commit message 格式为 `[KernelGen][Nvidia] Add <op> operator with Triton kernel`
- [ ] commit message 无 `Co-Authored-By`
- [ ] PR title 以 `[KernelGen][Nvidia]` 开头
- [ ] PR 创建后已回填 `规范名.xlsx` 的 `代码路径`
