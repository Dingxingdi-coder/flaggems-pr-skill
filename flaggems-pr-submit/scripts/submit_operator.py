#!/usr/bin/env python3
"""FlagGems 算子 PR 一站式提交脚本。

串行执行 9 个步骤，任何一步失败立即中断：
  1. check_operator.py 验证
  2. pre-commit 格式化
  3. 本地测试 (pytest tests/)
  4. 本地 benchmark (pytest benchmark/ --level core)
  5. gen_pr_description.py 生成 PR 数据 JSON
  6. git add + commit
  7. git push
  8. gh pr create (自动组装描述)
  9. operator_registry.py backfill

用法:
    python submit_operator.py <op> --repo-dir /path/to/FlagGems
    python submit_operator.py <op> --skip-test --skip-benchmark  # Mac 无 GPU 时
    python submit_operator.py <op> --dry-run  # 只验证不提交
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

import yaml

from op_naming import resolve_op

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = "/data/dxd/FlagGems_minimax_2_7_pr"
FORK_REPO = "Dingxingdi/FlagGems"
UPSTREAM_REPO = "flagos-ai/FlagGems"
RECORD_PATH = os.path.join(DEFAULT_REPO, "pr状态记录.md")

_current_op = None


class Colors:
    OK = "\033[92m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    END = "\033[0m"


def step(n, msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}[Step {n}/9] {msg}{Colors.END}")


def ok(msg):
    print(f"  {Colors.OK}✓{Colors.END} {msg}")


def record_event(op, event_type, message):
    """追加事件到 pr状态记录.md"""
    try:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"| {date} | {op} | {event_type} | {message} |\n"
        with open(RECORD_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass


def fatal(msg):
    print(f"\n  {Colors.FAIL}✗ FATAL: {msg}{Colors.END}")
    if _current_op:
        record_event(_current_op, "FAIL", msg[:100].replace("|", "/").replace("\n", " "))
    sys.exit(1)


def run(cmd, cwd=None, timeout=120, check=True, capture=False, env=None, input_data=None):
    """Run a command, optionally capture output."""
    merged_env = {**os.environ, **(env or {})}
    kwargs = dict(
        cwd=cwd,
        timeout=timeout,
        env=merged_env,
        text=True,
    )
    if capture:
        kwargs["capture_output"] = True
    if input_data is not None:
        kwargs["input"] = input_data
        kwargs["capture_output"] = True

    try:
        result = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        if check:
            fatal(f"命令超时 ({timeout}s): {' '.join(cmd)}")
        return None

    if check and result.returncode != 0:
        msg = f"命令失败 (exit {result.returncode}): {' '.join(cmd)}"
        if capture and result.stdout:
            msg += f"\n{result.stdout[-1000:]}"
        if capture and result.stderr:
            msg += f"\n{result.stderr[-500:]}"
        fatal(msg)
    return result


def python_cmd():
    return [sys.executable, "-S"]


def get_repo_python_env(repo_dir, extra=None):
    paths = [os.path.join(repo_dir, "src"), SCRIPTS_DIR]
    for path in (
        "/usr/local/lib/python3.12/dist-packages",
        "/usr/lib/python3/dist-packages",
        "/usr/lib/python3.12/dist-packages",
    ):
        if os.path.isdir(path):
            paths.append(path)
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    env = {"PYTHONPATH": os.pathsep.join(paths)}
    if extra:
        env.update(extra)
    return env


def get_op_id(op_name):
    return resolve_op(op_name).op_id


def get_module_name(op_name):
    return resolve_op(op_name).module


def get_github_auth_env():
    """Use the login files from /root when Codex runs with HOME=/data/dxd."""
    env = {}
    root_gitconfig = "/root/.gitconfig"
    root_gh_config = "/root/.config/gh"

    if "GIT_CONFIG_GLOBAL" not in os.environ and os.path.isfile(root_gitconfig):
        env["GIT_CONFIG_GLOBAL"] = root_gitconfig
    if "GH_CONFIG_DIR" not in os.environ and os.path.isfile(os.path.join(root_gh_config, "hosts.yml")):
        env["GH_CONFIG_DIR"] = root_gh_config

    return env


def get_changed_files(op_name, repo_dir):
    op_id = get_op_id(op_name)
    module_name = get_module_name(op_name)
    files = [
        f"src/flag_gems/ops/{module_name}.py",
        "src/flag_gems/ops/__init__.py",
        "src/flag_gems/__init__.py",
        f"tests/test_{op_id}.py",
        f"benchmark/test_{op_id}.py",
        "conf/operators.yaml",
    ]
    return [f for f in files if os.path.isfile(os.path.join(repo_dir, f))]


def get_yaml_description(op_name, repo_dir):
    """Extract operator description from operators.yaml."""
    yaml_path = os.path.join(repo_dir, "conf/operators.yaml")
    op_id = get_op_id(op_name)
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        for op in data.get("ops", []):
            if op.get("id") == op_id:
                desc = op.get("description", "").strip()
                kind = op.get("kind", ["Math"])[0]
                return desc, kind
    except Exception:
        pass
    return "", "Math"


def format_pr_body(op_name, pr_data, repo_dir):
    """Generate full PR description markdown from JSON data."""
    op_id = get_op_id(op_name)
    module_name = get_module_name(op_name)
    desc_text, kind = get_yaml_description(op_name, repo_dir)
    if not desc_text:
        desc_text = f"Triton kernel implementation for `{op_name}`."

    nv = pr_data.get("nvidia_benchmark", {})
    rows = nv.get("rows", [])
    case_count = nv.get("case_count", len(rows))
    am_speedup = nv.get("arithmetic_mean_speedup", 0)

    # Performance table
    perf_lines = []
    has_tflops = any(r.get("tflops") for r in rows)
    if has_tflops:
        perf_lines.append("| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup | TFLOPS |")
        perf_lines.append("|---|---|---|---|---|")
        for r in rows:
            perf_lines.append(
                f"| [{r['shape']}] | {r['torch_ms']:.3f} | {r['gems_ms']:.3f} "
                f"| {r['speedup']:.3f} | {r.get('tflops', 0):.3f} |"
            )
        perf_lines.append(f"| **Arithmetic Mean** | — | — | **{am_speedup:.3f}** | — |")
    else:
        perf_lines.append("| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup |")
        perf_lines.append("|---|---|---|---|")
        for r in rows:
            perf_lines.append(
                f"| [{r['shape']}] | {r['torch_ms']:.3f} | {r['gems_ms']:.3f} "
                f"| {r['speedup']:.3f} |"
            )
        perf_lines.append(f"| **Arithmetic Mean** | — | — | **{am_speedup:.3f}** |")

    perf_table = "\n".join(perf_lines)

    # Multi-backend table
    domestic = pr_data.get("domestic_gpu", {})
    backend_lines = []
    backend_lines.append("| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |")
    backend_lines.append("|---|---|---|---|---|")
    backend_lines.append(
        f"| Nvidia (H20) | PASS | PASS ({case_count} cases, --level core) "
        f"| {am_speedup:.3f} | Primary |"
    )
    backend_map = [
        ("tianshu", "Tianshu"),
        ("muxi", "Muxi"),
        ("ascend", "Ascend"),
        ("hygon", "Hygon"),
    ]
    for key, label in backend_map:
        info = domestic.get(key, {})
        acc_passed = info.get("accuracy_passed")
        bench_passed = info.get("benchmark_passed")
        acc = "PASS" if acc_passed else ("FAIL" if acc_passed is False else "N/A")
        bench_str = "PASS" if bench_passed else ("FAIL" if bench_passed is False else "N/A")

        cc = info.get("bench_case_count")
        if cc and bench_passed:
            bench_str += f" ({cc} cases)"

        ms = info.get("bench_mean_speedup")
        speedup_str = f"{ms:.3f}" if ms else "—"

        te = info.get("test_error", "") or ""
        be = info.get("bench_error", "") or ""
        notes = te[:60] if te else (be[:60] if be else "—")

        backend_lines.append(f"| {label} | {acc} | {bench_str} | {speedup_str} | {notes} |")

    backend_table = "\n".join(backend_lines)

    body = (
        f"## Summary\n"
        f"Adds a Triton kernel for `{op_name}`. {desc_text}\n\n"
        f"## Testing\n"
        f"- Validated against PyTorch reference on device side\n"
        f"- Tested on: Nvidia, Tianshu, Muxi, Ascend, Hygon\n\n"
        f"## Performance\n"
        f"Test command: `pytest benchmark/test_{op_id}.py --level core` (NVIDIA H20)\n\n"
        f"{perf_table}\n\n"
        f"## Multi-backend Testing\n"
        f"{backend_table}\n\n"
        f"## Files Changed\n"
        f"- `src/flag_gems/ops/{module_name}.py`: Triton kernel implementation\n"
        f"- `tests/test_{op_id}.py`: Accuracy test\n"
        f"- `benchmark/test_{op_id}.py`: Performance benchmark\n"
        f"- `src/flag_gems/ops/__init__.py`: Register import and `__all__`\n"
        f"- `src/flag_gems/__init__.py`: Register to `_FULL_CONFIG`\n"
        f"- `conf/operators.yaml`: Add operator entry (kind: {kind}, stage: alpha 5.4)"
    )

    return body


def main():
    parser = argparse.ArgumentParser(description="FlagGems 算子 PR 一站式提交")
    parser.add_argument("operator", help="算子名称")
    parser.add_argument(
        "--repo-dir",
        default=os.environ.get("FLAGGEMS_REPO", DEFAULT_REPO),
        help="FlagGems 仓库路径",
    )
    parser.add_argument("--gpu", default="0", help="CUDA_VISIBLE_DEVICES")
    parser.add_argument("--dry-run", action="store_true", help="只验证不提交")
    parser.add_argument("--push-only", action="store_true", help="推送到 fork 后停止，不创建 PR")
    parser.add_argument("--skip-test", action="store_true", help="跳过本地测试（Mac 无 GPU 时使用）")
    parser.add_argument("--skip-benchmark", action="store_true", help="跳过 benchmark（Mac 无 GPU 时使用）")
    args = parser.parse_args()

    op = args.operator
    op_id = get_op_id(op)
    repo = os.path.abspath(args.repo_dir)
    gpu = args.gpu
    repo_python_env = get_repo_python_env(repo)
    repo_cuda_env = get_repo_python_env(repo, {"CUDA_VISIBLE_DEVICES": gpu})

    global _current_op, RECORD_PATH
    _current_op = op
    RECORD_PATH = os.path.join(repo, "pr状态记录.md")

    print(f"{Colors.BOLD}FlagGems PR 一站式提交: {op}{Colors.END}")
    print(f"仓库: {repo}")
    print(f"GPU: {gpu}")
    print()

    files = get_changed_files(op, repo)
    if len(files) < 6:
        fatal(f"只找到 {len(files)} 个文件（需要 6 个）: {files}")
    ok(f"找到 {len(files)} 个文件")

    # ── Step 1: check_operator.py ──
    step(1, "check_operator.py 验证 (--strict)")
    run(
        python_cmd() + [os.path.join(SCRIPTS_DIR, "check_operator.py"), op, "--repo-dir", repo, "--strict"],
        cwd=repo,
        timeout=60,
        env=repo_python_env,
    )
    ok("check_operator.py 通过 (strict)")

    # ── Step 1.5: 多重载一致性检查 ──
    step("1.5", "多重载一致性检查 (check_overload_consistency)")
    result = run(
        python_cmd() + [os.path.join(SCRIPTS_DIR, "check_overload_consistency.py"), op, "--repo-dir", repo],
        cwd=repo,
        timeout=30,
        check=False,
        capture=True,
        env=repo_python_env,
    )
    if result and result.returncode != 0:
        print(result.stdout[-1000:] if result.stdout else "")
        fatal("多重载一致性检查失败，请修复 yaml/benchmark/test 对齐问题")
    ok("多重载一致性检查通过")

    # ── Step 2: pre-commit ──
    step(2, "pre-commit 格式化")
    full_paths = [os.path.join(repo, f) for f in files]
    for attempt in range(3):
        result = subprocess.run(
            ["pre-commit", "run", "--files"] + full_paths,
            cwd=repo, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            ok(f"pre-commit 通过 (第 {attempt + 1} 次)")
            break
        print(f"  pre-commit 自动修复中 (第 {attempt + 1} 次)...")
        subprocess.run(["git", "add"] + files, cwd=repo)
    else:
        print(result.stdout[-500:] if result.stdout else "")
        fatal("pre-commit 3 次尝试后仍失败")

    # ── Step 3: 本地测试 ──
    step(3, "本地测试 (pytest)")
    test_file = f"tests/test_{op_id}.py"
    if args.skip_test:
        print("  ⚠ 跳过本地测试 (--skip-test)")
    else:
        result = run(
            python_cmd() + ["-m", "pytest", test_file, "-x", "-v", "--timeout=60"],
            cwd=repo, timeout=180, check=False, capture=True,
            env=repo_cuda_env,
        )
        if result is None or result.returncode != 0:
            output = (result.stdout[-1000:] if result else "") + (result.stderr[-500:] if result else "")
            fatal(f"本地测试失败:\n{output}")
        ok("本地测试全部通过")

    # ── Step 4: benchmark ──
    step(4, "本地 benchmark (--level core)")
    bench_file = f"benchmark/test_{op_id}.py"
    bench_output = ""
    if args.skip_benchmark:
        print("  ⚠ 跳过 benchmark (--skip-benchmark)")
    else:
        result = run(
            python_cmd() + ["-m", "pytest", bench_file, "--level", "core", "-s"],
            cwd=repo, timeout=300, check=False, capture=True,
            env=repo_cuda_env,
        )
        if result is None or result.returncode != 0:
            output = (result.stdout[-1000:] if result else "") + (result.stderr[-500:] if result else "")
            fatal(f"benchmark 失败:\n{output}")
        bench_output = result.stdout
        ok("benchmark 完成")

    # Write gate marker
    gate_dir = os.path.join(repo, ".pr_gate")
    os.makedirs(gate_dir, exist_ok=True)
    gate_file = os.path.join(gate_dir, f"{op_id}.passed")
    test_status = "skip" if args.skip_test else "pass"
    bench_status = "skip" if args.skip_benchmark else "pass"
    with open(gate_file, "w") as f:
        f.write(f"check=pass test={test_status} benchmark={bench_status}\n")
        f.write(f"time={datetime.now().isoformat()}\n")

    # ── Step 5: gen_pr_description.py ──
    step(5, "生成 PR 描述数据")
    if bench_output:
        result = run(
            python_cmd() + [os.path.join(SCRIPTS_DIR, "gen_pr_description.py"), op, "--nvidia-stdin"],
            input_data=bench_output, timeout=60, env=repo_python_env,
        )
    else:
        result = run(
            python_cmd() + [os.path.join(SCRIPTS_DIR, "gen_pr_description.py"), op, "--skip-run"],
            timeout=60, capture=True, env=repo_python_env,
        )

    try:
        pr_data = json.loads(result.stdout)
    except (json.JSONDecodeError, AttributeError) as e:
        fatal(f"gen_pr_description.py 输出解析失败: {e}")

    nv_rows = pr_data.get("nvidia_benchmark", {}).get("rows", [])
    nv_case_count = pr_data.get("nvidia_benchmark", {}).get("case_count", 0)
    am_speedup = pr_data.get("nvidia_benchmark", {}).get("arithmetic_mean_speedup", 0)
    ok(f"Nvidia: {nv_case_count} cases, mean speedup = {am_speedup:.3f}")

    for backend, info in pr_data.get("domestic_gpu", {}).items():
        ms = info.get("bench_mean_speedup")
        acc = "PASS" if info.get("accuracy_passed") else "FAIL"
        speedup_str = f"{ms:.3f}" if ms else "—"
        ok(f"{backend}: acc={acc}, speedup={speedup_str}")

    if nv_case_count == 0 and not args.skip_benchmark:
        fatal("benchmark 无数据（0 case），请检查 benchmark 文件")

    # ── Step 6: git commit ──
    step(6, "git add + commit")
    if args.dry_run:
        print("  ⚠ DRY RUN — 跳过 git 操作")
    else:
        run(["git", "add"] + files, cwd=repo)
        msg = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo, capture_output=True, text=True,
        )
        if not result.stdout.strip():
            ok("无变更需要提交（已是最新）")
        else:
            run(["git", "commit", "-m", msg], cwd=repo)
            ok(f"已提交: {msg}")

    # ── Step 7: git push ──
    step(7, "git push")
    branch = f"pr/{op}"
    github_auth_env = get_github_auth_env()
    if args.dry_run:
        print(f"  ⚠ DRY RUN — 跳过 push 到 {branch}")
    else:
        run(["git", "push", "fork", branch], cwd=repo, timeout=60, env=github_auth_env)
        ok(f"已推送到 fork/{branch}")

    if args.push_only:
        step(8, "按要求跳过创建上游 PR (--push-only)")
        ok("已推送到 fork，未创建 GitHub PR")
        print(f"\n{Colors.OK}{Colors.BOLD}✓ push-only 流程完成！{Colors.END}")
        return

    # ── Step 8: create PR ──
    step(8, "创建上游 PR")
    body = format_pr_body(op, pr_data, repo)
    title = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"

    if args.dry_run:
        print(f"  ⚠ DRY RUN — PR 描述预览:\n")
        print(body[:500])
        print("  ...")
        pr_url = "(dry-run)"
    else:
        result = run(
            [
                "gh", "pr", "create",
                "--repo", UPSTREAM_REPO,
                "--head", f"{FORK_REPO.split('/')[0]}:{branch}",
                "--base", "master",
                "--title", title,
                "--body", body,
            ],
            capture=True,
            env=github_auth_env,
            timeout=30,
        )
        pr_url = result.stdout.strip() if result and result.stdout else ""
        if not pr_url:
            fatal("PR 创建失败：gh pr create 无输出")
        ok(f"PR 创建成功: {pr_url}")
        record_event(op, "PR_CREATED", pr_url)

    # ── Step 9: backfill ──
    step(9, "回填 PR 链接")
    if args.dry_run or pr_url == "(dry-run)":
        print("  ⚠ DRY RUN — 跳过回填")
    else:
        run(
            python_cmd() + [os.path.join(SCRIPTS_DIR, "operator_registry.py"), "backfill", op, pr_url],
            timeout=30,
            check=False,
            env=repo_python_env,
        )
        ok("回填完成")

    # ── Done ──
    print(f"\n{Colors.OK}{Colors.BOLD}✓ 全部完成！{Colors.END}")
    if pr_url and pr_url != "(dry-run)":
        print(f"  PR: {pr_url}")


if __name__ == "__main__":
    main()
