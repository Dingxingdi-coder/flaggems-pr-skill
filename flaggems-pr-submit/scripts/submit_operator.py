#!/usr/bin/env python3
"""Strict one-shot submitter for FlagGems KernelGen operator PRs."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from statistics import mean

import yaml

from op_naming import resolve_op

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = "/data/dxd/FlagGems_minimax_2_7_pr"
DEFAULT_NORM_XLSX = os.environ.get("FLAGGEMS_NORM_XLSX", "/data/dxd/规范名.xlsx")
FORK_REPO = "Dingxingdi/FlagGems"
UPSTREAM_REPO = "flagos-ai/FlagGems"
MIN_SPEEDUP = 0.8
TOTAL_STEPS = 10
RECORD_PATH = os.path.join(DEFAULT_REPO, "pr状态记录.md")
_current_op = None


class C:
    OK = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def step(n, msg):
    print(f"\n{C.CYAN}{C.BOLD}[Step {n}/{TOTAL_STEPS}] {msg}{C.END}")


def ok(msg):
    print(f"  {C.OK}✓{C.END} {msg}")


def warn(msg):
    print(f"  {C.WARN}⚠{C.END} {msg}")


def record_event(op, typ, msg):
    try:
        with open(RECORD_PATH, "a") as f:
            f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {op} | {typ} | {msg[:100].replace('|', '/').replace(chr(10), ' ')} |\n")
    except Exception:
        pass


def fatal(msg):
    print(f"\n  {C.FAIL}✗ FATAL: {msg}{C.END}")
    if _current_op:
        record_event(_current_op, "FAIL", msg)
    sys.exit(1)


def run(cmd, cwd=None, timeout=120, check=True, capture=False, env=None, input_data=None):
    kwargs = {"cwd": cwd, "timeout": timeout, "env": {**os.environ, **(env or {})}, "text": True}
    if capture:
        kwargs["capture_output"] = True
    if input_data is not None:
        kwargs["input"] = input_data
        kwargs["capture_output"] = True
    try:
        res = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        if check:
            fatal(f"命令超时 ({timeout}s): {' '.join(cmd)}")
        return None
    if check and res.returncode != 0:
        out = (getattr(res, "stdout", "") or "")[-1000:]
        err = (getattr(res, "stderr", "") or "")[-500:]
        fatal(f"命令失败 (exit {res.returncode}): {' '.join(cmd)}\n{out}\n{err}")
    return res


def py():
    return [sys.executable, "-S"]


def repo_env(repo, extra=None):
    paths = [os.path.join(repo, "src"), SCRIPTS_DIR]
    for p in ("/usr/local/lib/python3.12/dist-packages", "/usr/lib/python3/dist-packages", "/usr/lib/python3.12/dist-packages"):
        if os.path.isdir(p):
            paths.append(p)
    if os.environ.get("PYTHONPATH"):
        paths.append(os.environ["PYTHONPATH"])
    env = {"PYTHONPATH": os.pathsep.join(paths)}
    if extra:
        env.update(extra)
    return env


def auth_env():
    env = {}
    if "GIT_CONFIG_GLOBAL" not in os.environ and os.path.isfile("/root/.gitconfig"):
        env["GIT_CONFIG_GLOBAL"] = "/root/.gitconfig"
    if "GH_CONFIG_DIR" not in os.environ and os.path.isfile("/root/.config/gh/hosts.yml"):
        env["GH_CONFIG_DIR"] = "/root/.config/gh"
    return env


def op_id(op):
    return resolve_op(op).op_id


def module_name(op):
    return resolve_op(op).module


def changed_files(op, repo):
    oid = op_id(op)
    mod = module_name(op)
    paths = [
        f"src/flag_gems/ops/{mod}.py",
        "src/flag_gems/ops/__init__.py",
        "src/flag_gems/__init__.py",
        f"tests/test_{oid}.py",
        f"benchmark/test_{oid}.py",
        "conf/operators.yaml",
    ]
    return [p for p in paths if os.path.isfile(os.path.join(repo, p))]


def ensure_branch(op, repo, dry_run):
    res = run(["git", "branch", "--show-current"], cwd=repo, check=False, capture=True)
    cur = res.stdout.strip() if res and res.stdout else ""
    exp = f"pr/{op}"
    if cur != exp:
        msg = f"当前分支是 '{cur or '<unknown>'}'，预期 '{exp}'"
        warn(msg) if dry_run else fatal(msg)
    else:
        ok(f"当前分支: {cur}")


def yaml_meta(op, repo):
    oid = op_id(op)
    try:
        with open(os.path.join(repo, "conf/operators.yaml")) as f:
            data = yaml.safe_load(f)
        for item in data.get("ops", []):
            if item.get("id") == oid:
                kind = item.get("kind") or ["Math"]
                kind = kind[0] if isinstance(kind, list) else str(kind)
                stage = "unknown"
                stages = item.get("stages") or []
                if stages and isinstance(stages[0], dict):
                    k, v = next(iter(stages[0].items()))
                    stage = f"{k} {v}"
                return (item.get("description") or "").strip(), kind, stage
    except Exception:
        pass
    return "", "Math", "unknown"


DTYPE_RE = re.compile(r"Performance Test \(dtype=([^,\)]+)")
SUCCESS_RE = re.compile(r"^\s*SUCCESS\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)(?:\s+([\d.eE+-]+))?")


def norm_dtype(s):
    s = str(s).strip()
    return s[6:] if s.startswith("torch.") else (s or "all")


def dtype_rows(bench_text, fallback_cases, fallback_speedup):
    cur = None
    stats = {}
    for line in bench_text.splitlines():
        m = DTYPE_RE.search(line)
        if m:
            cur = norm_dtype(m.group(1))
            stats.setdefault(cur, [])
            continue
        m = SUCCESS_RE.search(line)
        if m:
            stats.setdefault(cur or "all", []).append(float(m.group(3)))
    if not stats and fallback_cases:
        stats["all"] = [fallback_speedup] * int(fallback_cases)
    return [(dt, len(v), mean(v)) for dt, v in sorted(stats.items()) if v]


def dtype_table(rows):
    lines = ["| DType | Cases | Mean Speedup | Notes |", "|---|---:|---:|---|"]
    if not rows:
        lines.append("| all | 0 | — | No parsed benchmark rows |")
    for dt, cases, speedup in rows:
        lines.append(f"| {dt} | {cases} | {speedup:.3f}x | — |")
    return "\n".join(lines)


def perf_table(rows, am):
    has_tflops = any(float(r.get("tflops") or 0) for r in rows)
    if has_tflops:
        lines = ["| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup | TFLOPS |", "|---|---:|---:|---:|---:|"]
    else:
        lines = ["| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup |", "|---|---:|---:|---:|"]
    for r in rows:
        shape = r.get("shape", "")
        base = f"| [{shape}] | {float(r.get('torch_ms') or 0):.3f} | {float(r.get('gems_ms') or 0):.3f} | {float(r.get('speedup') or 0):.3f}x |"
        if has_tflops:
            base = base[:-1] + f" {float(r.get('tflops') or 0):.3f} |"
        lines.append(base)
    lines.append(f"| **Arithmetic Mean** | — | — | **{am:.3f}x** |" + (" — |" if has_tflops else ""))
    return "\n".join(lines)


def backend_table(case_count, am, pr_data):
    lines = [
        "| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |",
        "|---|---|---|---:|---|",
        f"| Nvidia (H20) | PASS | PASS ({case_count} cases, --level core) | {am:.3f}x | Primary |",
    ]
    for key, label in (("tianshu", "Tianshu"), ("muxi", "Muxi"), ("ascend", "Ascend"), ("hygon", "Hygon")):
        info = pr_data.get("domestic_gpu", {}).get(key, {})
        ap = info.get("accuracy_passed")
        bp = info.get("benchmark_passed")
        acc = "PASS" if ap else ("FAIL" if ap is False else "N/A")
        bench = "PASS" if bp else ("FAIL" if bp is False else "N/A")
        if bp and info.get("bench_case_count"):
            bench += f" ({info['bench_case_count']} cases)"
        ms = info.get("bench_mean_speedup")
        sp = f"{ms:.3f}x" if ms else "—"
        note = str(info.get("test_error") or info.get("bench_error") or "—").replace("|", "/").replace("\n", " ")[:80]
        lines.append(f"| {label} | {acc} | {bench} | {sp} | {note} |")
    return "\n".join(lines)


def pr_body(op, pr_data, repo, bench_text):
    oid = op_id(op)
    mod = module_name(op)
    desc, kind, stage = yaml_meta(op, repo)
    desc = desc or f"Triton kernel implementation for `{op}`."
    nv = pr_data.get("nvidia_benchmark", {})
    rows = nv.get("rows", [])
    cases = int(nv.get("case_count", len(rows)) or 0)
    am = float(nv.get("arithmetic_mean_speedup", 0) or 0)
    drows = dtype_rows(bench_text, cases, am)
    dtypes = ", ".join(r[0] for r in drows) if drows else "N/A"
    return (
        "## PR Category\nOperator\n\n"
        "## Type of Change\nNew feature: add a Triton kernel implementation for an aten operator.\n\n"
        f"## Summary\nAdds a Triton kernel for `{op}`. {desc}\n\n"
        f"## Description\nThis PR registers `{op}` in FlagGems, adds accuracy coverage against the PyTorch reference, and adds a core-level benchmark.\n\n"
        f"## Testing / Correctness\n- Accuracy command: `pytest tests/test_{oid}.py -v --timeout=60`\n- Benchmark command: `pytest benchmark/test_{oid}.py --level core -s`\n- Validated against PyTorch reference on device side\n- Tested dtypes: {dtypes}\n\n"
        f"## Performance\nTest command: `pytest benchmark/test_{oid}.py --level core -s` (NVIDIA H20)\n\n{dtype_table(drows)}\n\n{perf_table(rows, am)}\n\n"
        "## Tested-on\n- NVIDIA H20, CUDA 13.2\n\n"
        f"## Multi-backend Testing\n{backend_table(cases, am, pr_data)}\n\n"
        "## Files Changed\n"
        f"- `src/flag_gems/ops/{mod}.py`: Triton kernel implementation\n"
        f"- `tests/test_{oid}.py`: Accuracy test\n"
        f"- `benchmark/test_{oid}.py`: Performance benchmark\n"
        "- `src/flag_gems/ops/__init__.py`: Register import and `__all__`\n"
        "- `src/flag_gems/__init__.py`: Register to `_FULL_CONFIG`\n"
        f"- `conf/operators.yaml`: Add operator entry (kind: {kind}, stage: {stage})"
    )


def main():
    parser = argparse.ArgumentParser(description="Submit one FlagGems operator PR")
    parser.add_argument("operator", help="normalized operator name")
    parser.add_argument("--repo-dir", default=os.environ.get("FLAGGEMS_REPO", DEFAULT_REPO))
    parser.add_argument("--norm-xlsx", default=DEFAULT_NORM_XLSX)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push-only", action="store_true")
    parser.add_argument("--skip-test", action="store_true", help="only allowed with --dry-run")
    parser.add_argument("--skip-benchmark", action="store_true", help="only allowed with --dry-run")
    args = parser.parse_args()

    op = args.operator
    oid = op_id(op)
    repo = os.path.abspath(args.repo_dir)
    penv = repo_env(repo)
    cenv = repo_env(repo, {"CUDA_VISIBLE_DEVICES": args.gpu})
    global _current_op, RECORD_PATH
    _current_op = op
    RECORD_PATH = os.path.join(repo, "pr状态记录.md")

    print(f"{C.BOLD}FlagGems PR 一站式提交: {op}{C.END}")
    print(f"仓库: {repo}\nGPU: {args.gpu}\n")

    if (args.skip_test or args.skip_benchmark) and not args.dry_run:
        fatal("真实 PR 或 push-only 不允许 --skip-test/--skip-benchmark；只能用于 --dry-run 调试")
    files = changed_files(op, repo)
    if len(files) < 6:
        fatal(f"只找到 {len(files)} 个文件（需要 6 个）: {files}")
    ok(f"找到 {len(files)} 个文件")
    ensure_branch(op, repo, args.dry_run)

    step(1, "check_operator.py 验证 (--strict)")
    run(py() + [os.path.join(SCRIPTS_DIR, "check_operator.py"), op, "--repo-dir", repo, "--strict"], cwd=repo, env=penv, timeout=60)
    ok("check_operator.py 通过")

    step(2, "多重载一致性检查")
    res = run(py() + [os.path.join(SCRIPTS_DIR, "check_overload_consistency.py"), op, "--repo-dir", repo], cwd=repo, env=penv, timeout=30, check=False, capture=True)
    if res and res.returncode != 0:
        print(res.stdout[-1000:] if res.stdout else "")
        fatal("多重载一致性检查失败")
    ok("多重载一致性检查通过")

    step(3, "operators.yaml stage 检查")
    stage = yaml_meta(op, repo)[2]
    if stage != "alpha 5.1":
        fatal(f"operators.yaml stage 应为 alpha 5.1，当前为 {stage}")
    ok("operators.yaml stage = alpha 5.1")

    step(4, "pre-commit")
    full_paths = [os.path.join(repo, f) for f in files]
    for i in range(3):
        res = subprocess.run(["pre-commit", "run", "--files"] + full_paths, cwd=repo, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            ok(f"pre-commit 通过 (第 {i + 1} 次)")
            break
        print(f"  pre-commit 自动修复中 (第 {i + 1} 次)...")
        subprocess.run(["git", "add"] + files, cwd=repo)
    else:
        print(res.stdout[-500:] if res.stdout else "")
        fatal("pre-commit 3 次尝试后仍失败")

    step(5, "本地测试")
    if args.skip_test:
        warn("跳过测试，仅 dry-run 调试")
    else:
        res = run(py() + ["-m", "pytest", f"tests/test_{oid}.py", "-x", "-v", "--timeout=60"], cwd=repo, env=cenv, timeout=180, check=False, capture=True)
        if res is None or res.returncode != 0:
            fatal("本地测试失败:\n" + ((res.stdout[-1000:] if res else "") + (res.stderr[-500:] if res else "")))
        ok("本地测试通过")

    step(6, "本地 benchmark (--level core)")
    bench_text = ""
    if args.skip_benchmark:
        warn("跳过 benchmark，仅 dry-run 调试")
    else:
        res = run(py() + ["-m", "pytest", f"benchmark/test_{oid}.py", "--level", "core", "-s"], cwd=repo, env=cenv, timeout=300, check=False, capture=True)
        if res is None or res.returncode != 0:
            fatal("benchmark 失败:\n" + ((res.stdout[-1000:] if res else "") + (res.stderr[-500:] if res else "")))
        bench_text = res.stdout
        ok("benchmark 完成")

    os.makedirs(os.path.join(repo, ".pr_gate"), exist_ok=True)
    with open(os.path.join(repo, ".pr_gate", f"{oid}.passed"), "w") as f:
        f.write(f"check=pass test={'skip' if args.skip_test else 'pass'} benchmark={'skip' if args.skip_benchmark else 'pass'}\n")
        f.write(f"time={datetime.now().isoformat()}\n")

    step(7, "生成 PR 描述数据")
    if bench_text:
        res = run(py() + [os.path.join(SCRIPTS_DIR, "gen_pr_description.py"), op, "--nvidia-stdin"], input_data=bench_text, env=penv, timeout=60)
    else:
        res = run(py() + [os.path.join(SCRIPTS_DIR, "gen_pr_description.py"), op, "--skip-run"], capture=True, env=penv, timeout=60)
    try:
        pdata = json.loads(res.stdout)
    except (AttributeError, json.JSONDecodeError) as e:
        fatal(f"gen_pr_description.py 输出解析失败: {e}")
    nv = pdata.get("nvidia_benchmark", {})
    cases = int(nv.get("case_count", 0) or 0)
    am = float(nv.get("arithmetic_mean_speedup", 0) or 0)
    ok(f"Nvidia: {cases} cases, mean speedup = {am:.3f}")
    if not args.skip_benchmark:
        if cases == 0:
            fatal("benchmark 无数据（0 case），请检查 benchmark、mark 和 core_shapes.yaml")
        if am < MIN_SPEEDUP:
            fatal(f"平均 speedup {am:.3f} < {MIN_SPEEDUP:.1f}，请优化 kernel 或放弃该算子")

    step(8, "git add + commit")
    if args.dry_run:
        warn("DRY RUN — 跳过 commit")
    else:
        run(["git", "add"] + files, cwd=repo)
        msg = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"
        res = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True)
        if res.stdout.strip():
            run(["git", "commit", "-m", msg], cwd=repo)
            ok(f"已提交: {msg}")
        else:
            ok("无变更需要提交")

    step(9, "git push")
    branch = f"pr/{op}"
    if args.dry_run:
        warn(f"DRY RUN — 跳过 push 到 {branch}")
    else:
        run(["git", "push", "fork", branch], cwd=repo, env=auth_env(), timeout=60)
        ok(f"已推送到 fork/{branch}")
    if args.push_only:
        ok("已推送到 fork，按 --push-only 跳过创建 PR")
        return

    step(10, "创建 PR + 回填")
    body = pr_body(op, pdata, repo, bench_text)
    title = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"
    if args.dry_run:
        warn("DRY RUN — PR body 预览")
        print(body[:1200] + "\n  ...")
        return
    res = run(["gh", "pr", "create", "--repo", UPSTREAM_REPO, "--head", f"{FORK_REPO.split('/')[0]}:{branch}", "--base", "master", "--title", title, "--body", body], capture=True, env=auth_env(), timeout=30)
    pr_url = res.stdout.strip() if res and res.stdout else ""
    if not pr_url:
        fatal("PR 创建失败：gh pr create 无输出")
    ok(f"PR 创建成功: {pr_url}")
    record_event(op, "PR_CREATED", pr_url)
    res = run(py() + [os.path.join(SCRIPTS_DIR, "operator_registry.py"), "backfill", op, pr_url, "--norm-xlsx", args.norm_xlsx], env=penv, timeout=30, check=False, capture=True)
    ok("回填完成") if res and res.returncode == 0 else warn("回填失败，请手动执行 operator_registry.py backfill")
    print(f"\n{C.OK}{C.BOLD}✓ 全部完成！{C.END}\n  PR: {pr_url}")


if __name__ == "__main__":
    main()
