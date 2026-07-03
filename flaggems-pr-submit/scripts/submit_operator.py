#!/usr/bin/env python3
"""Run the initial PR pipeline for one FlagGems operator.

The script is context-driven and intentionally handles only first-time PR
creation. Review follow-up and PR URL backfill are out of scope.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from op_naming import resolve_op  # noqa: E402
from operator_registry import lookup_norm_name  # noqa: E402

MIN_SPEEDUP = 0.8
TOTAL_STEPS = 8


class C:
    OK = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def step(n: int, msg: str) -> None:
    print(f"\n{C.CYAN}{C.BOLD}[Step {n}/{TOTAL_STEPS}] {msg}{C.END}")


def ok(msg: str) -> None:
    print(f"  {C.OK}✓{C.END} {msg}")


def warn(msg: str) -> None:
    print(f"  {C.WARN}⚠{C.END} {msg}")


def fatal(msg: str) -> None:
    raise SystemExit(f"\n  {C.FAIL}✗ FATAL: {msg}{C.END}")


def run(cmd: list[str], cwd: Path | None = None, *, timeout: int = 120, check: bool = True, capture: bool = False, env: dict[str, str] | None = None, input_data: str | None = None) -> subprocess.CompletedProcess[str] | None:
    kwargs: dict[str, Any] = {"cwd": str(cwd) if cwd else None, "timeout": timeout, "text": True, "env": {**os.environ, **(env or {})}}
    if capture:
        kwargs["capture_output"] = True
    if input_data is not None:
        kwargs["input"] = input_data
        kwargs["capture_output"] = True
    try:
        res = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        if check:
            fatal(f"command timed out ({timeout}s): {' '.join(cmd)}")
        return None
    if check and res.returncode != 0:
        out = (res.stdout or "")[-1200:] if capture or input_data is not None else ""
        err = (res.stderr or "")[-800:] if capture or input_data is not None else ""
        fatal(f"command failed (exit {res.returncode}): {' '.join(cmd)}\n{out}\n{err}")
    return res


def py() -> list[str]:
    return [sys.executable, "-S"]


def load_context(path: str) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        fatal(f"context file not found: {p}")
    return json.loads(p.read_text())


def repo_env(repo: Path, gpu: str | None = None) -> dict[str, str]:
    env = {"PYTHONPATH": os.pathsep.join([str(repo / "src"), str(SCRIPT_DIR), os.environ.get("PYTHONPATH", "")])}
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = gpu
    return env


def op_names(op: str):
    return resolve_op(op)


def normalize_op(raw: str, ctx: dict[str, Any]) -> str:
    if raw in (ctx.get("ops") or []):
        return raw
    raw_to_norm = ctx.get("raw_to_norm") or {}
    if raw in raw_to_norm:
        return raw_to_norm[raw]
    return lookup_norm_name(raw, ctx["norm_xlsx"])


def gpu_for_op(op: str, ctx: dict[str, Any]) -> str:
    gpu_map = ctx.get("gpu_map") or {}
    if op in gpu_map:
        return str(gpu_map[op])
    if ctx.get("gpu"):
        return str(ctx["gpu"])
    detected = ctx.get("detected_gpus") or []
    ops = ctx.get("ops") or [op]
    if op in ops and detected:
        return str(detected[ops.index(op)])
    fatal(f"no GPU assigned for {op}")


def find_marked_file(root: Path, subdir: str, op_id: str) -> Path:
    exact = root / subdir / f"test_{op_id}.py"
    if exact.is_file():
        return exact
    mark = f"pytest.mark.{op_id}"
    for path in sorted((root / subdir).glob("*.py")):
        try:
            if mark in path.read_text():
                return path
        except UnicodeDecodeError:
            continue
    fatal(f"cannot find {subdir} file for mark {op_id} under {root}")


def ensure_worktree_link(repo: Path, worktree_root: Path) -> None:
    expected = repo / ".worktrees"
    if expected.exists():
        if expected.resolve() != worktree_root.resolve():
            fatal(f"repo .worktrees points to {expected.resolve()}, but context worktree_root is {worktree_root.resolve()}")
        return
    expected.symlink_to(worktree_root, target_is_directory=True)
    ok(f"created .worktrees symlink -> {worktree_root}")


def upstream_absent(repo: Path, ctx: dict[str, Any], op: str) -> None:
    names = op_names(op)
    remote = ctx["upstream_remote"]
    base = ctx["base_branch"]
    run(["git", "fetch", remote, base], cwd=repo, timeout=120)
    ref = f"{remote}/{base}"
    kernel_path = f"src/flag_gems/ops/{names.module}.py"
    if run(["git", "show", f"{ref}:{kernel_path}"], cwd=repo, check=False, capture=True).returncode == 0:
        fatal(f"upstream already has {kernel_path}")
    yaml_res = run(["git", "show", f"{ref}:conf/operators.yaml"], cwd=repo, check=False, capture=True)
    if yaml_res and yaml_res.returncode == 0 and f"id: {names.op_id}" in yaml_res.stdout:
        fatal(f"upstream already has yaml id: {names.op_id}")
    ok("upstream conflict check passed")


def checkout_branch(repo: Path, ctx: dict[str, Any], op: str) -> None:
    branch = f"pr/{op}"
    ref = f"{ctx['upstream_remote']}/{ctx['base_branch']}"
    run(["git", "checkout", "-B", branch, ref], cwd=repo)
    ok(f"checked out {branch} from {ref}")


def changed_files(op: str, repo: Path) -> list[str]:
    names = op_names(op)
    paths = [
        f"src/flag_gems/ops/{names.module}.py",
        "src/flag_gems/ops/__init__.py",
        "src/flag_gems/__init__.py",
        f"tests/test_{names.op_id}.py",
        f"benchmark/test_{names.op_id}.py",
        "conf/operators.yaml",
    ]
    return [p for p in paths if (repo / p).is_file()]


def yaml_meta(op: str, repo: Path) -> tuple[str, str, str]:
    target = op_names(op).op_id
    try:
        data = yaml.safe_load((repo / "conf/operators.yaml").read_text())
        for item in data.get("ops", []):
            if item.get("id") == target:
                kind = item.get("kind") or ["Math"]
                kind_s = kind[0] if isinstance(kind, list) else str(kind)
                stage = "unknown"
                stages = item.get("stages") or []
                if stages and isinstance(stages[0], dict):
                    k, v = next(iter(stages[0].items()))
                    stage = f"{k} {v}"
                return (item.get("description") or "").strip(), kind_s, stage
    except Exception:
        pass
    return "", "Math", "unknown"


def patch_stage(repo: Path, op: str, expected_stage: str) -> None:
    parts = expected_stage.split()
    if len(parts) != 2:
        fatal(f"bad expected_stage: {expected_stage}")
    expected = f"      - {parts[0]}: '{parts[1]}'\n"
    target = op_names(op).op_id
    path = repo / "conf/operators.yaml"
    lines = path.read_text().splitlines(keepends=True)
    out: list[str] = []
    i = 0
    in_target = False
    changed = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("  - id: "):
            entry_id = line.strip().split(":", 1)[1].strip()
            in_target = entry_id == target or entry_id.startswith(f"{target}_")
        if in_target and line.startswith("    stages:"):
            out.append(line)
            i += 1
            old: list[str] = []
            while i < len(lines) and lines[i].startswith("      - "):
                old.append(lines[i])
                i += 1
            if old != [expected]:
                out.append(expected)
                changed = True
            else:
                out.extend(old)
            continue
        out.append(line)
        i += 1
    if changed:
        path.write_text("".join(out))
        ok(f"normalized yaml stage to {expected_stage}")


BENCH_RE = re.compile(r"SUCCESS\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+(?:([\d.eE+-]+)\s+)?[\[{](.+?)[\]}]\s*$")
DTYPE_RE = re.compile(r"Performance Test \(dtype=([^,\)]+)")
SHAPE_RE = re.compile(r"torch\.Size\(\[([^\]]+)\]\)")


def parse_benchmark(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dtype = "all"
    for line in text.splitlines():
        dm = DTYPE_RE.search(line)
        if dm:
            dtype = dm.group(1).replace("torch.", "")
            continue
        m = BENCH_RE.search(line)
        if not m:
            continue
        raw_shape = m.group(5).strip()
        shape_match = SHAPE_RE.findall(raw_shape)
        rows.append({"dtype": dtype, "shape": shape_match[0] if shape_match else raw_shape, "torch_ms": float(m.group(1)), "gems_ms": float(m.group(2)), "speedup": float(m.group(3)), "tflops": float(m.group(4)) if m.group(4) else 0.0})
    return rows


def query_domestic(op: str, root: str | None) -> dict[str, dict[str, Any]]:
    labels = {"tianshu": "天数test_results_*", "muxi": "沐曦test_results_*", "ascend": "华为test_*", "hygon": "海光hygon_test_*"}
    if not root:
        return {k: {"note": "N/A"} for k in labels}
    base = Path(root).expanduser().resolve()
    result: dict[str, dict[str, Any]] = {}
    for key, pattern in labels.items():
        dirs = [Path(p) for p in sorted(glob.glob(str(base / pattern))) if Path(p).is_dir()]
        if not dirs:
            result[key] = {"note": "N/A"}
            continue
        summaries = sorted(dirs[-1].glob("summary_*.json"))
        if not summaries:
            result[key] = {"note": "summary missing"}
            continue
        try:
            data = json.loads(summaries[-1].read_text())
        except Exception:
            result[key] = {"note": "summary unreadable"}
            continue
        ops = data.get("operators", {}) or {}
        info = ops.get(op) or ops.get(op_names(op).op_id) or ops.get(op.lstrip("_"))
        if not info:
            result[key] = {"note": "operator not found"}
            continue
        bench_data = (info.get("benchmark") or {}).get("data") or []
        speedups = [float(x["speedup"]) for x in bench_data if "speedup" in x]
        result[key] = {"accuracy_passed": info.get("accuracy_passed"), "benchmark_passed": info.get("benchmark_passed"), "bench_case_count": len(bench_data) if bench_data else None, "bench_mean_speedup": round(sum(speedups) / len(speedups), 3) if speedups else None, "note": "—"}
    return result


def tables(rows: list[dict[str, Any]], domestic: dict[str, dict[str, Any]], tested_on: str) -> tuple[str, str, str]:
    by_dtype: dict[str, list[float]] = {}
    for r in rows:
        by_dtype.setdefault(r["dtype"], []).append(r["speedup"])
    dtype_lines = ["| DType | Cases | Mean Speedup | Notes |", "|---|---:|---:|---|"]
    for dt, values in sorted(by_dtype.items()):
        dtype_lines.append(f"| {dt} | {len(values)} | {mean(values):.3f}x | — |")
    has_tflops = any(r.get("tflops") for r in rows)
    perf_lines = ["| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup |" + (" TFLOPS |" if has_tflops else ""), "|---|---:|---:|---:|" + ("---:|" if has_tflops else "")]
    for r in rows:
        line = f"| [{r['shape']}] | {r['torch_ms']:.3f} | {r['gems_ms']:.3f} | {r['speedup']:.3f}x |"
        if has_tflops:
            line = line[:-1] + f" {r['tflops']:.3f} |"
        perf_lines.append(line)
    am = mean(r["speedup"] for r in rows)
    perf_lines.append(f"| **Arithmetic Mean** | — | — | **{am:.3f}x** |" + (" — |" if has_tflops else ""))
    backend_labels = {"tianshu": "Tianshu", "muxi": "Muxi", "ascend": "Ascend", "hygon": "Hygon"}
    backend_lines = ["| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |", "|---|---|---|---:|---|", f"| Nvidia ({tested_on}) | PASS | PASS ({len(rows)} cases, --level core) | {am:.3f}x | Primary |"]
    for key, label in backend_labels.items():
        info = domestic.get(key, {})
        ap = info.get("accuracy_passed")
        bp = info.get("benchmark_passed")
        acc = "PASS" if ap else ("FAIL" if ap is False else "N/A")
        bench = "PASS" if bp else ("FAIL" if bp is False else "N/A")
        if bp and info.get("bench_case_count"):
            bench += f" ({info['bench_case_count']} cases)"
        speed = info.get("bench_mean_speedup")
        backend_lines.append(f"| {label} | {acc} | {bench} | {speed:.3f}x | {info.get('note', '—')} |" if speed else f"| {label} | {acc} | {bench} | — | {info.get('note', '—')} |")
    return "\n".join(dtype_lines), "\n".join(perf_lines), "\n".join(backend_lines)


def pr_body(op: str, repo: Path, rows: list[dict[str, Any]], domestic: dict[str, dict[str, Any]], tested_on: str) -> str:
    names = op_names(op)
    desc, kind, stage = yaml_meta(op, repo)
    desc = desc or f"Triton kernel implementation for `{op}`."
    dtype_table, perf_table, backend_table = tables(rows, domestic, tested_on)
    dtypes = ", ".join(sorted({r["dtype"] for r in rows}))
    return (
        "## PR Category\nOperator\n\n"
        "## Type of Change\nNew feature: add a Triton kernel implementation for an aten operator.\n\n"
        f"## Summary\nAdds a Triton kernel for `{op}`. {desc}\n\n"
        f"## Description\nThis PR registers `{op}` in FlagGems, adds accuracy coverage against the PyTorch reference, and adds a core-level benchmark.\n\n"
        f"## Testing / Correctness\n- Accuracy command: `pytest tests/test_{names.op_id}.py -v --timeout=60`\n- Benchmark command: `pytest benchmark/test_{names.op_id}.py --level core -s`\n- Validated against PyTorch reference on device side\n- Tested dtypes: {dtypes}\n\n"
        f"## Performance\nTest command: `pytest benchmark/test_{names.op_id}.py --level core -s` ({tested_on})\n\n{dtype_table}\n\n{perf_table}\n\n"
        f"## Tested-on\n- {tested_on}\n\n"
        f"## Multi-backend Testing\n{backend_table}\n\n"
        "## Files Changed\n"
        f"- `src/flag_gems/ops/{names.module}.py`: Triton kernel implementation\n"
        f"- `tests/test_{names.op_id}.py`: Accuracy test\n"
        f"- `benchmark/test_{names.op_id}.py`: Performance benchmark\n"
        "- `src/flag_gems/ops/__init__.py`: Register import and `__all__`\n"
        "- `src/flag_gems/__init__.py`: Register to `_FULL_CONFIG`\n"
        f"- `conf/operators.yaml`: Add operator entry (kind: {kind}, stage: {stage})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run initial FlagGems operator PR pipeline")
    parser.add_argument("operator", help="raw or normalized operator name")
    parser.add_argument("--context", required=True, help="context JSON from context.py")
    parser.add_argument("--dry-run", action="store_true", help="validate and render PR body; skip commit/push/PR create")
    args = parser.parse_args()

    ctx = load_context(args.context)
    repo = Path(ctx["repo_dir"]).expanduser().resolve()
    worktree_root = Path(ctx["worktree_root"]).expanduser().resolve()
    op = normalize_op(args.operator, ctx)
    names = op_names(op)
    gpu = gpu_for_op(op, ctx)
    worktree = worktree_root / f"gen-{op}"
    if not worktree.is_dir():
        alt = worktree_root / f"gen-{names.op_id}"
        worktree = alt if alt.is_dir() else worktree
    if not worktree.is_dir():
        fatal(f"worktree not found for {op}: {worktree}")

    print(f"{C.BOLD}FlagGems initial PR: {op}{C.END}")
    print(f"repo={repo}\nworktree={worktree}\ngpu={gpu}\n")
    penv = repo_env(repo)
    cenv = repo_env(repo, gpu)

    step(1, "preflight")
    upstream_absent(repo, ctx, op)
    checkout_branch(repo, ctx, op)
    ensure_worktree_link(repo, worktree_root)

    step(2, "worktree quality gate")
    run(py() + [str(SCRIPT_DIR / "worktree_quality_gate.py"), "--context", args.context, "--op", op], cwd=repo, env=penv, timeout=60)

    step(3, "worktree accuracy and benchmark")
    test_file = find_marked_file(worktree, "tests", names.op_id)
    bench_file = find_marked_file(worktree, "benchmark", names.op_id)
    run(py() + ["-m", "pytest", str(test_file.relative_to(worktree)), "-m", names.op_id, "-vs"], cwd=worktree, env=cenv, timeout=240)
    bench_res = run(py() + ["-m", "pytest", str(bench_file.relative_to(worktree)), "-m", names.op_id, "-s", "--level", "core"], cwd=worktree, env=cenv, timeout=360, capture=True)
    worktree_rows = parse_benchmark(bench_res.stdout if bench_res else "")
    if not worktree_rows:
        fatal("worktree benchmark produced 0 parsed cases")
    ok(f"worktree benchmark cases={len(worktree_rows)}, mean speedup={mean(r['speedup'] for r in worktree_rows):.3f}")

    step(4, "extract repaired worktree")
    run(py() + [str(SCRIPT_DIR / "extract_from_worktree.py"), op, "--repo-dir", str(repo)], cwd=repo, env=penv, timeout=120)
    patch_stage(repo, op, ctx.get("expected_stage", "alpha 5.1"))

    step(5, "strict static validation and formatting")
    files = changed_files(op, repo)
    if len(files) < 6:
        fatal(f"expected 6 target files after extraction, got {files}")
    run(py() + [str(SCRIPT_DIR / "check_operator.py"), op, "--repo-dir", str(repo), "--strict"], cwd=repo, env=penv, timeout=80)
    run(py() + [str(SCRIPT_DIR / "check_overload_consistency.py"), op, "--repo-dir", str(repo)], cwd=repo, env=penv, timeout=40)
    for attempt in range(3):
        res = subprocess.run(["pre-commit", "run", "--files"] + [str(repo / f) for f in files], cwd=repo, capture_output=True, text=True, timeout=80)
        if res.returncode == 0:
            ok(f"pre-commit passed on attempt {attempt + 1}")
            break
        subprocess.run(["git", "add"] + files, cwd=repo)
    else:
        fatal("pre-commit failed after 3 attempts")

    step(6, "PR-branch accuracy and benchmark")
    run(py() + ["-m", "pytest", f"tests/test_{names.op_id}.py", "-x", "-v", "--timeout=60"], cwd=repo, env=cenv, timeout=240)
    bench_res = run(py() + ["-m", "pytest", f"benchmark/test_{names.op_id}.py", "--level", "core", "-s"], cwd=repo, env=cenv, timeout=360, capture=True)
    rows = parse_benchmark(bench_res.stdout if bench_res else "")
    if not rows:
        fatal("PR-branch benchmark produced 0 parsed cases")
    am = mean(r["speedup"] for r in rows)
    if am < MIN_SPEEDUP:
        fatal(f"mean speedup {am:.3f} < {MIN_SPEEDUP}; optimize or abandon")
    ok(f"PR benchmark cases={len(rows)}, mean speedup={am:.3f}")

    step(7, "commit and push")
    branch = f"pr/{op}"
    if args.dry_run:
        warn("dry run: skip commit and push")
    else:
        run(["git", "add"] + files, cwd=repo)
        res = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True)
        if res.stdout.strip():
            run(["git", "commit", "-m", f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"], cwd=repo)
        run(["git", "push", ctx["fork_remote"], branch], cwd=repo, timeout=120)
        ok(f"pushed {branch} to {ctx['fork_remote']}")

    step(8, "create PR")
    domestic = query_domestic(op, ctx.get("domestic_gpu_dir"))
    body = pr_body(op, repo, rows, domestic, ctx["tested_on"])
    if args.dry_run:
        print(body[:1500] + "\n...")
        return
    res = run(["gh", "pr", "create", "--repo", ctx["upstream_repo"], "--head", f"{ctx['fork_repo'].split('/')[0]}:{branch}", "--base", ctx["base_branch"], "--title", f"[KernelGen][Nvidia] Add {op} operator with Triton kernel", "--body", body], cwd=repo, capture=True, timeout=60)
    pr_url = res.stdout.strip() if res and res.stdout else ""
    if not pr_url:
        fatal("gh pr create returned no URL")
    print(f"\n{C.OK}{C.BOLD}✓ PR created{C.END}: {pr_url}")


if __name__ == "__main__":
    main()
