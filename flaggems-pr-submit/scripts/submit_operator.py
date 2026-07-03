#!/usr/bin/env python3
"""Context-driven submitter for one FlagGems operator PR.

No repository path, GPU, fork, upstream repo, or tested-on string is assumed.
Provide --context from scripts/context.py or pass the equivalent CLI arguments.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from op_naming import resolve_op

SCRIPTS_DIR = Path(__file__).resolve().parent
MIN_SPEEDUP = 0.8
TOTAL_STEPS = 9
_current_op: str | None = None
_record_path: Path | None = None


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


def record_event(op: str, typ: str, msg: str) -> None:
    if _record_path is None:
        return
    try:
        clean_msg = msg[:100].replace("|", "/").replace("\n", " ")
        with _record_path.open("a") as f:
            f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {op} | {typ} | {clean_msg} |\n")
    except Exception:
        pass


def fatal(msg: str) -> None:
    print(f"\n  {C.FAIL}✗ FATAL: {msg}{C.END}")
    if _current_op:
        record_event(_current_op, "FAIL", msg)
    sys.exit(1)


def run(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    input_data: str | None = None,
) -> subprocess.CompletedProcess[str] | None:
    kwargs: dict[str, Any] = {
        "cwd": str(cwd) if cwd is not None else None,
        "timeout": timeout,
        "env": {**os.environ, **(env or {})},
        "text": True,
    }
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
        out = (res.stdout or "")[-1000:] if capture or input_data is not None else ""
        err = (res.stderr or "")[-500:] if capture or input_data is not None else ""
        fatal(f"command failed (exit {res.returncode}): {' '.join(cmd)}\n{out}\n{err}")
    return res


def py() -> list[str]:
    return [sys.executable, "-S"]


def load_context(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        fatal(f"context file not found: {p}")
    return json.loads(p.read_text())


def resolve_value(args: argparse.Namespace, ctx: dict[str, Any], key: str, label: str) -> str:
    value = getattr(args, key, None) or ctx.get(key)
    if value is None or value == "":
        fatal(f"missing {label}; provide it in --context or as --{key.replace('_', '-')}")
    return str(value)


def gpu_for_op(args: argparse.Namespace, ctx: dict[str, Any], op: str) -> str:
    if args.gpu:
        return args.gpu
    gpu_map = ctx.get("gpu_map") or {}
    if op in gpu_map:
        return str(gpu_map[op])
    if ctx.get("gpu"):
        return str(ctx["gpu"])
    fatal("missing GPU; provide --gpu, context.gpu, or context.gpu_map[op]")
    return ""


def repo_env(repo: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    paths = [str(repo / "src"), str(SCRIPTS_DIR)]
    if os.environ.get("PYTHONPATH"):
        paths.append(os.environ["PYTHONPATH"])
    env = {"PYTHONPATH": os.pathsep.join(paths)}
    if extra:
        env.update(extra)
    return env


def op_id(op: str) -> str:
    return resolve_op(op).op_id


def module_name(op: str) -> str:
    return resolve_op(op).module


def changed_files(op: str, repo: Path) -> list[str]:
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
    return [p for p in paths if (repo / p).is_file()]


def ensure_branch(op: str, repo: Path, dry_run: bool) -> None:
    res = run(["git", "branch", "--show-current"], cwd=repo, check=False, capture=True)
    cur = res.stdout.strip() if res and res.stdout else ""
    expected = f"pr/{op}"
    if cur != expected:
        msg = f"current branch is {cur or '<unknown>'!r}; expected {expected!r}"
        warn(msg) if dry_run else fatal(msg)
    else:
        ok(f"current branch: {cur}")


def yaml_meta(op: str, repo: Path) -> tuple[str, str, str]:
    oid = op_id(op)
    try:
        with (repo / "conf/operators.yaml").open() as f:
            data = yaml.safe_load(f)
        for item in data.get("ops", []):
            if item.get("id") == oid:
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


BENCH_RE = re.compile(r"SUCCESS\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+(?:([\d.eE+-]+)\s+)?[\[{](.+?)[\]}]\s*$")
DTYPE_RE = re.compile(r"Performance Test \(dtype=([^,\)]+)")
SHAPE_RE = re.compile(r"torch\.Size\(\[([^\]]+)\]\)")


def norm_dtype(text: str) -> str:
    text = str(text).strip()
    return text[6:] if text.startswith("torch.") else (text or "all")


def parse_benchmark_output(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cur_dtype = "all"
    for line in text.splitlines():
        dm = DTYPE_RE.search(line)
        if dm:
            cur_dtype = norm_dtype(dm.group(1))
            continue
        m = BENCH_RE.search(line)
        if not m:
            continue
        raw_shape = m.group(5).strip()
        shape_match = SHAPE_RE.findall(raw_shape)
        rows.append(
            {
                "dtype": cur_dtype,
                "shape": shape_match[0] if shape_match else raw_shape,
                "torch_ms": float(m.group(1)),
                "gems_ms": float(m.group(2)),
                "speedup": float(m.group(3)),
                "tflops": float(m.group(4)) if m.group(4) else 0.0,
            }
        )
    return rows


def dtype_summary(rows: list[dict[str, Any]]) -> list[tuple[str, int, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("dtype") or "all"), []).append(float(row["speedup"]))
    return [(dt, len(values), mean(values)) for dt, values in sorted(grouped.items())]


def normalize_key(name: str) -> str:
    for prefix in ("aten::", "aten__"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    is_inplace = name.endswith("_") and not name.endswith("__")
    core = name[:-1] if is_inplace else name
    return "".join(ch.lower() for ch in core if ch.isalnum()) + ("__inplace" if is_inplace else "")


def lookup_domestic_op(ops: dict[str, Any], op: str) -> dict[str, Any] | None:
    names = {op, op_id(op), op.lstrip("_")}
    for name in names:
        if name in ops:
            return ops[name]
    target = {normalize_key(name) for name in names}
    for key, value in ops.items():
        if normalize_key(key) in target:
            return value
    return None


def domestic_na(note: str) -> dict[str, Any]:
    return {
        "accuracy_passed": None,
        "benchmark_passed": None,
        "bench_case_count": None,
        "bench_mean_speedup": None,
        "test_error": note,
        "bench_error": None,
    }


def query_domestic(op: str, root: str | None) -> dict[str, dict[str, Any]]:
    backends = [
        ("tianshu", "天数test_results_*"),
        ("muxi", "沐曦test_results_*"),
        ("ascend", "华为test_*"),
        ("hygon", "海光hygon_test_*"),
    ]
    if not root:
        return {key: domestic_na("domestic_gpu_dir not provided") for key, _ in backends}
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        return {key: domestic_na(f"domestic_gpu_dir not found: {base}") for key, _ in backends}

    result: dict[str, dict[str, Any]] = {}
    for key, pattern in backends:
        dirs = [Path(p) for p in sorted(glob.glob(str(base / pattern))) if Path(p).is_dir()]
        if not dirs:
            result[key] = domestic_na("summary dir not found")
            continue
        summaries = sorted(dirs[-1].glob("summary_*.json"))
        if not summaries:
            result[key] = domestic_na("summary JSON not found")
            continue
        try:
            data = json.loads(summaries[-1].read_text())
        except Exception as exc:
            result[key] = domestic_na(f"summary JSON unreadable: {type(exc).__name__}")
            continue
        op_info = lookup_domestic_op(data.get("operators", {}) or {}, op)
        if not op_info:
            result[key] = domestic_na("operator not in summary")
            continue
        bench_data = (op_info.get("benchmark") or {}).get("data") or []
        speedups = [float(item["speedup"]) for item in bench_data if "speedup" in item]
        result[key] = {
            "accuracy_passed": op_info.get("accuracy_passed"),
            "benchmark_passed": op_info.get("benchmark_passed"),
            "bench_case_count": len(bench_data) if bench_data else None,
            "bench_mean_speedup": round(sum(speedups) / len(speedups), 3) if speedups else None,
            "test_error": None,
            "bench_error": None,
        }
    return result


def dtype_table(rows: list[tuple[str, int, float]]) -> str:
    lines = ["| DType | Cases | Mean Speedup | Notes |", "|---|---:|---:|---|"]
    for dt, count, speedup in rows:
        lines.append(f"| {dt} | {count} | {speedup:.3f}x | — |")
    return "\n".join(lines)


def perf_table(rows: list[dict[str, Any]], am: float) -> str:
    has_tflops = any(float(row.get("tflops") or 0) for row in rows)
    if has_tflops:
        lines = ["| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup | TFLOPS |", "|---|---:|---:|---:|---:|"]
    else:
        lines = ["| Configuration | Torch Latency (ms) | Gems Latency (ms) | Speedup |", "|---|---:|---:|---:|"]
    for row in rows:
        line = f"| [{row['shape']}] | {row['torch_ms']:.3f} | {row['gems_ms']:.3f} | {row['speedup']:.3f}x |"
        if has_tflops:
            line = line[:-1] + f" {row.get('tflops', 0.0):.3f} |"
        lines.append(line)
    lines.append(f"| **Arithmetic Mean** | — | — | **{am:.3f}x** |" + (" — |" if has_tflops else ""))
    return "\n".join(lines)


def backend_table(case_count: int, am: float, domestic: dict[str, dict[str, Any]], tested_on: str) -> str:
    lines = [
        "| Backend | Accuracy Test | Benchmark | Speedup (mean) | Notes |",
        "|---|---|---|---:|---|",
        f"| Nvidia ({tested_on}) | PASS | PASS ({case_count} cases, --level core) | {am:.3f}x | Primary |",
    ]
    labels = {"tianshu": "Tianshu", "muxi": "Muxi", "ascend": "Ascend", "hygon": "Hygon"}
    for key in ("tianshu", "muxi", "ascend", "hygon"):
        info = domestic.get(key, {})
        ap = info.get("accuracy_passed")
        bp = info.get("benchmark_passed")
        acc = "PASS" if ap else ("FAIL" if ap is False else "N/A")
        bench = "PASS" if bp else ("FAIL" if bp is False else "N/A")
        if bp and info.get("bench_case_count"):
            bench += f" ({info['bench_case_count']} cases)"
        speedup = info.get("bench_mean_speedup")
        speedup_s = f"{speedup:.3f}x" if speedup else "—"
        note = str(info.get("test_error") or info.get("bench_error") or "—").replace("|", "/").replace("\n", " ")[:80]
        lines.append(f"| {labels[key]} | {acc} | {bench} | {speedup_s} | {note} |")
    return "\n".join(lines)


def pr_body(op: str, repo: Path, rows: list[dict[str, Any]], domestic: dict[str, dict[str, Any]], tested_on: str) -> str:
    oid = op_id(op)
    mod = module_name(op)
    desc, kind, stage = yaml_meta(op, repo)
    desc = desc or f"Triton kernel implementation for `{op}`."
    case_count = len(rows)
    am = mean(float(row["speedup"]) for row in rows) if rows else 0.0
    drows = dtype_summary(rows)
    dtypes = ", ".join(item[0] for item in drows) if drows else "N/A"
    return (
        "## PR Category\nOperator\n\n"
        "## Type of Change\nNew feature: add a Triton kernel implementation for an aten operator.\n\n"
        f"## Summary\nAdds a Triton kernel for `{op}`. {desc}\n\n"
        f"## Description\nThis PR registers `{op}` in FlagGems, adds accuracy coverage against the PyTorch reference, and adds a core-level benchmark.\n\n"
        f"## Testing / Correctness\n- Accuracy command: `pytest tests/test_{oid}.py -v --timeout=60`\n- Benchmark command: `pytest benchmark/test_{oid}.py --level core -s`\n- Validated against PyTorch reference on device side\n- Tested dtypes: {dtypes}\n\n"
        f"## Performance\nTest command: `pytest benchmark/test_{oid}.py --level core -s` ({tested_on})\n\n{dtype_table(drows)}\n\n{perf_table(rows, am)}\n\n"
        f"## Tested-on\n- {tested_on}\n\n"
        f"## Multi-backend Testing\n{backend_table(case_count, am, domestic, tested_on)}\n\n"
        "## Files Changed\n"
        f"- `src/flag_gems/ops/{mod}.py`: Triton kernel implementation\n"
        f"- `tests/test_{oid}.py`: Accuracy test\n"
        f"- `benchmark/test_{oid}.py`: Performance benchmark\n"
        "- `src/flag_gems/ops/__init__.py`: Register import and `__all__`\n"
        "- `src/flag_gems/__init__.py`: Register to `_FULL_CONFIG`\n"
        f"- `conf/operators.yaml`: Add operator entry (kind: {kind}, stage: {stage})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit one FlagGems operator PR")
    parser.add_argument("operator", help="normalized operator name")
    parser.add_argument("--context", help="context JSON from scripts/context.py")
    parser.add_argument("--repo-dir")
    parser.add_argument("--norm-xlsx")
    parser.add_argument("--gpu")
    parser.add_argument("--fork-remote")
    parser.add_argument("--fork-repo")
    parser.add_argument("--upstream-repo")
    parser.add_argument("--base-branch")
    parser.add_argument("--tested-on")
    parser.add_argument("--domestic-gpu-dir")
    parser.add_argument("--expected-stage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push-only", action="store_true")
    parser.add_argument("--skip-test", action="store_true", help="only allowed with --dry-run")
    parser.add_argument("--skip-benchmark", action="store_true", help="only allowed with --dry-run")
    args = parser.parse_args()

    ctx = load_context(args.context)
    op = args.operator
    oid = op_id(op)
    repo = Path(resolve_value(args, ctx, "repo_dir", "repo_dir")).expanduser().resolve()
    norm_xlsx = resolve_value(args, ctx, "norm_xlsx", "norm_xlsx")
    gpu = gpu_for_op(args, ctx, op)
    fork_remote = resolve_value(args, ctx, "fork_remote", "fork_remote")
    fork_repo = resolve_value(args, ctx, "fork_repo", "fork_repo")
    upstream_repo = resolve_value(args, ctx, "upstream_repo", "upstream_repo")
    base_branch = resolve_value(args, ctx, "base_branch", "base_branch")
    tested_on = resolve_value(args, ctx, "tested_on", "tested_on")
    domestic_dir = args.domestic_gpu_dir or ctx.get("domestic_gpu_dir")
    expected_stage = args.expected_stage or ctx.get("expected_stage") or "alpha 5.1"

    global _current_op, _record_path
    _current_op = op
    _record_path = repo / "pr状态记录.md"

    print(f"{C.BOLD}FlagGems PR submit: {op}{C.END}")
    print(f"repo: {repo}\ngpu: {gpu}\nfork: {fork_repo}\nupstream: {upstream_repo}\n")

    if (args.skip_test or args.skip_benchmark) and not args.dry_run:
        fatal("real PR/push-only cannot use --skip-test or --skip-benchmark")
    if not repo.is_dir():
        fatal(f"repo_dir not found: {repo}")
    if not Path(norm_xlsx).expanduser().is_file():
        fatal(f"norm_xlsx not found: {norm_xlsx}")

    files = changed_files(op, repo)
    if len(files) < 6:
        fatal(f"found {len(files)} files, need 6: {files}")
    ok(f"found changed-file set: {files}")
    ensure_branch(op, repo, args.dry_run)
    penv = repo_env(repo)
    cenv = repo_env(repo, {"CUDA_VISIBLE_DEVICES": gpu})

    step(1, "check_operator.py --strict")
    run(py() + [str(SCRIPTS_DIR / "check_operator.py"), op, "--repo-dir", str(repo), "--strict"], cwd=repo, env=penv, timeout=60)
    ok("check_operator.py passed")

    step(2, "check_overload_consistency.py")
    res = run(py() + [str(SCRIPTS_DIR / "check_overload_consistency.py"), op, "--repo-dir", str(repo)], cwd=repo, env=penv, timeout=30, check=False, capture=True)
    if res and res.returncode != 0:
        print(res.stdout[-1000:] if res.stdout else "")
        fatal("overload consistency failed")
    ok("overload consistency passed")

    step(3, "operators.yaml stage")
    stage = yaml_meta(op, repo)[2]
    if stage != expected_stage:
        fatal(f"operators.yaml stage should be {expected_stage}, got {stage}")
    ok(f"operators.yaml stage = {expected_stage}")

    step(4, "pre-commit")
    full_paths = [str(repo / f) for f in files]
    for i in range(3):
        res = subprocess.run(["pre-commit", "run", "--files"] + full_paths, cwd=repo, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            ok(f"pre-commit passed on attempt {i + 1}")
            break
        print(f"  pre-commit auto-fix attempt {i + 1}")
        subprocess.run(["git", "add"] + files, cwd=repo)
    else:
        print(res.stdout[-500:] if res.stdout else "")
        fatal("pre-commit failed after 3 attempts")

    step(5, "pytest accuracy")
    if args.skip_test:
        warn("dry-run only: skipped accuracy test")
    else:
        res = run(py() + ["-m", "pytest", f"tests/test_{oid}.py", "-x", "-v", "--timeout=60"], cwd=repo, env=cenv, timeout=180, check=False, capture=True)
        if res is None or res.returncode != 0:
            fatal("accuracy test failed:\n" + ((res.stdout[-1000:] if res else "") + (res.stderr[-500:] if res else "")))
        ok("accuracy test passed")

    step(6, "pytest benchmark --level core")
    bench_text = ""
    rows: list[dict[str, Any]] = []
    if args.skip_benchmark:
        warn("dry-run only: skipped benchmark")
    else:
        res = run(py() + ["-m", "pytest", f"benchmark/test_{oid}.py", "--level", "core", "-s"], cwd=repo, env=cenv, timeout=300, check=False, capture=True)
        if res is None or res.returncode != 0:
            fatal("benchmark failed:\n" + ((res.stdout[-1000:] if res else "") + (res.stderr[-500:] if res else "")))
        bench_text = res.stdout
        rows = parse_benchmark_output(bench_text)
        if not rows:
            fatal("benchmark produced 0 parsed cases; check mark, core_shapes.yaml, and Benchmark.set_shapes")
        am = mean(float(row["speedup"]) for row in rows)
        ok(f"benchmark parsed: {len(rows)} cases, mean speedup={am:.3f}")
        if am < MIN_SPEEDUP:
            fatal(f"mean speedup {am:.3f} < {MIN_SPEEDUP:.1f}; optimize or abandon this operator")

    gate_dir = repo / ".pr_gate"
    gate_dir.mkdir(exist_ok=True)
    (gate_dir / f"{oid}.passed").write_text(
        f"check=pass test={'skip' if args.skip_test else 'pass'} benchmark={'skip' if args.skip_benchmark else 'pass'}\n"
        f"time={datetime.now().isoformat()}\n"
    )

    step(7, "PR data")
    if not rows and args.skip_benchmark:
        rows = []
    domestic = query_domestic(op, str(domestic_dir) if domestic_dir else None)
    ok("PR data assembled")

    step(8, "git add + commit + push")
    branch = f"pr/{op}"
    if args.dry_run:
        warn("DRY RUN — skip commit and push")
    else:
        run(["git", "add"] + files, cwd=repo)
        msg = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"
        res = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True)
        if res.stdout.strip():
            run(["git", "commit", "-m", msg], cwd=repo)
            ok(f"committed: {msg}")
        else:
            ok("nothing new to commit")
        run(["git", "push", fork_remote, branch], cwd=repo, timeout=60)
        ok(f"pushed to {fork_remote}/{branch}")
    if args.push_only:
        ok("push-only complete; no new PR created")
        return

    step(9, "create PR + backfill")
    body = pr_body(op, repo, rows, domestic, tested_on)
    title = f"[KernelGen][Nvidia] Add {op} operator with Triton kernel"
    if args.dry_run:
        warn("DRY RUN — PR body preview")
        print(body[:1200] + "\n  ...")
        return
    res = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            upstream_repo,
            "--head",
            f"{fork_repo.split('/')[0]}:{branch}",
            "--base",
            base_branch,
            "--title",
            title,
            "--body",
            body,
        ],
        capture=True,
        timeout=30,
    )
    pr_url = res.stdout.strip() if res and res.stdout else ""
    if not pr_url:
        fatal("gh pr create returned no PR URL")
    ok(f"PR created: {pr_url}")
    record_event(op, "PR_CREATED", pr_url)
    res = run(
        py() + [str(SCRIPTS_DIR / "operator_registry.py"), "backfill", op, pr_url, "--norm-xlsx", norm_xlsx],
        env=penv,
        timeout=30,
        check=False,
        capture=True,
    )
    if res and res.returncode == 0:
        ok("registry backfill complete")
    else:
        warn("registry backfill failed; run operator_registry.py backfill manually")
    print(f"\n{C.OK}{C.BOLD}✓ complete{C.END}\n  PR: {pr_url}")


if __name__ == "__main__":
    main()
