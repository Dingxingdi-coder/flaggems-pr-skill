#!/usr/bin/env python3
"""Build a dynamic context JSON for the FlagGems PR skill.

Only operator names are mandatory. Other values are inferred from cwd, git
remotes, environment variables, and nvidia-smi when possible. If inference is
ambiguous or impossible, the script fails with the exact value to ask from the
user.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from operator_registry import lookup_norm_name  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"context error: {message}")


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def parse_repo(url: str) -> str | None:
    text = url.strip()
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.\s]+)(?:\.git)?$",
        r"api\.github\.com/repos/([^/]+)/([^/\s]+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return None


def git_remotes(repo: Path) -> dict[str, dict[str, str]]:
    res = run(["git", "remote", "-v"], cwd=repo)
    if res.returncode != 0:
        fail(f"cannot read git remotes in {repo}: {res.stderr.strip()}")
    remotes: dict[str, dict[str, str]] = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, url, typ = parts[0], parts[1], parts[2].strip("()")
        remotes.setdefault(name, {})[typ] = url
    return remotes


def infer_remote(remotes: dict[str, dict[str, str]], *, upstream: bool) -> str | None:
    preferred = ["upstream"] if upstream else ["fork", "origin"]
    for name in preferred:
        if name in remotes:
            return name
    for name, urls in remotes.items():
        repo = parse_repo(urls.get("fetch", "") or urls.get("push", "") or "") or ""
        is_flagos = repo.lower() == "flagos-ai/flaggems"
        if upstream and is_flagos:
            return name
        if not upstream and not is_flagos and urls.get("push") and urls.get("push") != "no_push":
            return name
    return None


def remote_repo(remotes: dict[str, dict[str, str]], name: str, label: str) -> str:
    if name not in remotes:
        fail(f"git remote {name!r} for {label} not found; available={sorted(remotes)}")
    url = remotes[name].get("push") if label == "fork" else remotes[name].get("fetch")
    url = url or remotes[name].get("fetch") or remotes[name].get("push") or ""
    parsed = parse_repo(url)
    if not parsed:
        fail(f"cannot infer GitHub repo from remote {name!r} url {url!r}; provide --{label}-repo")
    return parsed


def infer_base_branch(repo: Path, upstream_remote: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    for branch in ("master", "main"):
        res = run(["git", "rev-parse", "--verify", f"{upstream_remote}/{branch}"], cwd=repo)
        if res.returncode == 0:
            return branch
    return "master"


def detect_gpu_ids() -> list[str]:
    env_visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if env_visible:
        ids = [x.strip() for x in env_visible.split(",") if x.strip()]
        if ids:
            return ids
    res = run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"])
    if res.returncode == 0:
        ids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if ids:
            return ids
    return []


def detect_tested_on(gpu_ids: list[str], explicit: str | None) -> str:
    if explicit:
        return explicit
    res = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if res.returncode == 0:
        names = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if names:
            return f"NVIDIA {names[0]}"
    if gpu_ids:
        return "NVIDIA GPU"
    fail("cannot infer tested-on environment; provide --tested-on")


def find_norm_xlsx(repo: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file():
            fail(f"--norm-xlsx is not a file: {p}")
        return p
    env = os.environ.get("FLAGGEMS_NORM_XLSX")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_file():
            return p
    candidates = [repo / "规范名.xlsx", repo.parent / "规范名.xlsx"]
    for p in candidates:
        if p.is_file():
            return p.resolve()
    fail("cannot infer norm xlsx; provide --norm-xlsx or FLAGGEMS_NORM_XLSX")


def parse_gpu_map(items: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in items or []:
        if ":" not in item:
            fail(f"--gpu-map expects OP:GPU, got {item!r}")
        op, gpu = item.split(":", 1)
        mapping[op.strip()] = gpu.strip()
    return {k: v for k, v in mapping.items() if k and v}


def normalize_ops(raw_ops: list[str], norm_xlsx: Path) -> tuple[list[str], dict[str, str]]:
    ops: list[str] = []
    raw_to_norm: dict[str, str] = {}
    for raw in raw_ops:
        norm = lookup_norm_name(raw, str(norm_xlsx))
        raw_to_norm[raw] = norm
        if norm not in ops:
            ops.append(norm)
    return ops, raw_to_norm


def assign_gpus(ops: list[str], raw_to_norm: dict[str, str], explicit_gpu: str | None, raw_gpu_map: dict[str, str]) -> tuple[str | None, dict[str, str], list[str]]:
    detected = detect_gpu_ids()
    if raw_gpu_map:
        result: dict[str, str] = {}
        for raw, gpu in raw_gpu_map.items():
            result[raw_to_norm.get(raw, raw)] = gpu
        missing = [op for op in ops if op not in result]
        if missing and explicit_gpu:
            for op in missing:
                result[op] = explicit_gpu
        if missing and not explicit_gpu:
            fail(f"missing GPU mapping for ops: {missing}")
        return explicit_gpu, result, detected
    if explicit_gpu:
        return explicit_gpu, {}, detected
    if not detected:
        fail("cannot infer GPUs; provide --gpu or --gpu-map")
    if len(ops) > len(detected):
        fail(f"too many ops for detected GPUs: ops={len(ops)}, GPUs={len(detected)}")
    return None, {op: detected[i] for i, op in enumerate(ops)}, detected


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    if not args.ops:
        fail("provide at least one --op")
    repo = Path(args.repo_dir or os.getcwd()).expanduser().resolve()
    if not repo.is_dir():
        fail(f"repo_dir is not a directory: {repo}")
    worktree_root = Path(args.worktree_root).expanduser().resolve() if args.worktree_root else repo / ".worktrees"
    if not worktree_root.is_dir():
        fail(f"worktree_root is not a directory: {worktree_root}")
    norm_xlsx = find_norm_xlsx(repo, args.norm_xlsx)
    ops, raw_to_norm = normalize_ops(args.ops, norm_xlsx)

    remotes = git_remotes(repo)
    upstream_remote = args.upstream_remote or infer_remote(remotes, upstream=True)
    fork_remote = args.fork_remote or infer_remote(remotes, upstream=False)
    if not upstream_remote:
        fail("cannot infer upstream remote; provide --upstream-remote")
    if not fork_remote:
        fail("cannot infer fork remote; provide --fork-remote")
    upstream_repo = args.upstream_repo or remote_repo(remotes, upstream_remote, "upstream")
    fork_repo = args.fork_repo or remote_repo(remotes, fork_remote, "fork")
    base_branch = infer_base_branch(repo, upstream_remote, args.base_branch)

    gpu, gpu_map, detected_gpus = assign_gpus(ops, raw_to_norm, args.gpu, parse_gpu_map(args.gpu_map))
    if len(ops) < 1:
        fail("at least one operator is required")
    available_count = len(gpu_map) if gpu_map else (len(detected_gpus) or 1)
    if len(ops) > available_count:
        fail(f"too many operators: {len(ops)} ops for {available_count} available GPU slots")

    ctx: dict[str, Any] = {
        "repo_dir": str(repo),
        "worktree_root": str(worktree_root),
        "norm_xlsx": str(norm_xlsx),
        "raw_ops": args.ops,
        "ops": ops,
        "raw_to_norm": raw_to_norm,
        "gpu": gpu,
        "gpu_map": gpu_map,
        "detected_gpus": detected_gpus,
        "upstream_remote": upstream_remote,
        "base_branch": base_branch,
        "fork_remote": fork_remote,
        "fork_repo": fork_repo,
        "upstream_repo": upstream_repo,
        "tested_on": detect_tested_on(detected_gpus, args.tested_on),
        "expected_stage": args.expected_stage,
    }
    if args.domestic_gpu_dir:
        p = Path(args.domestic_gpu_dir).expanduser().resolve()
        if not p.is_dir():
            fail(f"domestic_gpu_dir is not a directory: {p}")
        ctx["domestic_gpu_dir"] = str(p)
    if args.container:
        ctx["container"] = args.container
    return ctx


def write_context(args: argparse.Namespace) -> None:
    ctx = build_context(args)
    output = Path(args.output).expanduser().resolve() if args.output else Path(ctx["repo_dir"]) / ".pr_context.json"
    output.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n")
    print(output)


def show_context(args: argparse.Namespace) -> None:
    path = Path(args.context).expanduser().resolve()
    if not path.is_file():
        fail(f"context file not found: {path}")
    print(json.dumps(json.loads(path.read_text()), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="FlagGems PR context helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    write = sub.add_parser("write", help="write context JSON")
    write.add_argument("--repo-dir", help="default: current working directory")
    write.add_argument("--worktree-root", help="default: <repo_dir>/.worktrees")
    write.add_argument("--norm-xlsx", help="default: env or nearby norm xlsx")
    write.add_argument("--op", dest="ops", action="append", required=True)
    write.add_argument("--gpu", help="one CUDA_VISIBLE_DEVICES value for all ops")
    write.add_argument("--gpu-map", action="append", help="OP:GPU; repeatable")
    write.add_argument("--upstream-remote")
    write.add_argument("--base-branch")
    write.add_argument("--fork-remote")
    write.add_argument("--fork-repo")
    write.add_argument("--upstream-repo")
    write.add_argument("--tested-on")
    write.add_argument("--domestic-gpu-dir")
    write.add_argument("--container")
    write.add_argument("--expected-stage", default="alpha 5.1")
    write.add_argument("--output", help="default: <repo_dir>/.pr_context.json")
    write.set_defaults(func=write_context)

    show = sub.add_parser("show", help="print context JSON")
    show.add_argument("--context", required=True)
    show.set_defaults(func=show_context)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
