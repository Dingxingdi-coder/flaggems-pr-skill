#!/usr/bin/env python3
"""Create and inspect a FlagGems PR skill context file.

The skill must not assume local paths, remotes, GPU IDs, or GitHub repos. The
main agent collects those values from the user, then writes a context JSON that
subagents and scripts consume.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "repo_dir",
    "worktree_root",
    "norm_xlsx",
    "upstream_remote",
    "base_branch",
    "fork_remote",
    "fork_repo",
    "upstream_repo",
    "tested_on",
)


def fail(message: str) -> None:
    raise SystemExit(f"context error: {message}")


def run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def require_path(path: str, label: str, *, file: bool = False, dir: bool = False) -> str:
    if not path:
        fail(f"missing {label}")
    p = Path(path).expanduser().resolve()
    if file and not p.is_file():
        fail(f"{label} is not a file: {p}")
    if dir and not p.is_dir():
        fail(f"{label} is not a directory: {p}")
    return str(p)


def parse_gpu_map(items: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in items or []:
        if ":" not in item:
            fail(f"--gpu-map expects OP:GPU, got {item!r}")
        op, gpu = item.split(":", 1)
        op = op.strip()
        gpu = gpu.strip()
        if not op or not gpu:
            fail(f"invalid --gpu-map item: {item!r}")
        mapping[op] = gpu
    return mapping


def validate_remotes(ctx: dict[str, Any]) -> None:
    repo = ctx["repo_dir"]
    remotes = run(["git", "remote"], cwd=repo)
    if remotes.returncode != 0:
        fail(f"cannot read git remotes in {repo}: {remotes.stderr.strip()}")
    names = set(remotes.stdout.split())
    for key in ("upstream_remote", "fork_remote"):
        if ctx[key] not in names:
            fail(f"git remote {ctx[key]!r} from {key} not found; available: {sorted(names)}")


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    if not args.ops:
        fail("at least one --op is required")
    if not args.gpu and not args.gpu_map:
        fail("provide --gpu for all ops or --gpu-map OP:GPU")

    ctx: dict[str, Any] = {
        "repo_dir": require_path(args.repo_dir, "--repo-dir", dir=True),
        "worktree_root": require_path(args.worktree_root, "--worktree-root", dir=True),
        "norm_xlsx": require_path(args.norm_xlsx, "--norm-xlsx", file=True),
        "ops": args.ops,
        "gpu": args.gpu,
        "gpu_map": parse_gpu_map(args.gpu_map),
        "upstream_remote": args.upstream_remote,
        "base_branch": args.base_branch,
        "fork_remote": args.fork_remote,
        "fork_repo": args.fork_repo,
        "upstream_repo": args.upstream_repo,
        "tested_on": args.tested_on,
        "expected_stage": args.expected_stage,
    }
    if args.domestic_gpu_dir:
        ctx["domestic_gpu_dir"] = require_path(args.domestic_gpu_dir, "--domestic-gpu-dir", dir=True)
    if args.container:
        ctx["container"] = args.container

    for field in REQUIRED_FIELDS:
        if not ctx.get(field):
            fail(f"missing required field: {field}")
    validate_remotes(ctx)
    return ctx


def write_context(args: argparse.Namespace) -> None:
    ctx = build_context(args)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n")
    print(output)


def show_context(args: argparse.Namespace) -> None:
    path = Path(args.context).expanduser().resolve()
    if not path.is_file():
        fail(f"context file not found: {path}")
    data = json.loads(path.read_text())
    print(json.dumps(data, ensure_ascii=False, indent=2))


def add_common_write_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repo-dir", required=True, help="FlagGems repository path")
    p.add_argument("--worktree-root", required=True, help="directory containing gen-<op> worktrees")
    p.add_argument("--norm-xlsx", required=True, help="path to 规范名.xlsx")
    p.add_argument("--op", dest="ops", action="append", required=True, help="raw operator name; repeatable")
    p.add_argument("--gpu", help="default CUDA_VISIBLE_DEVICES value for all ops")
    p.add_argument("--gpu-map", action="append", help="per-op GPU mapping, e.g. add:0")
    p.add_argument("--upstream-remote", required=True, help="git remote for upstream FlagGems")
    p.add_argument("--base-branch", required=True, help="upstream base branch, e.g. master")
    p.add_argument("--fork-remote", required=True, help="push remote for the fork")
    p.add_argument("--fork-repo", required=True, help="GitHub fork repo, owner/name")
    p.add_argument("--upstream-repo", required=True, help="GitHub upstream repo, owner/name")
    p.add_argument("--tested-on", required=True, help="free-form tested-on text used in PR body")
    p.add_argument("--domestic-gpu-dir", help="optional directory containing domestic GPU summaries")
    p.add_argument("--container", help="container name when commands must be run through docker exec")
    p.add_argument("--expected-stage", default="alpha 5.1", help="expected operators.yaml stage")
    p.add_argument("--output", required=True, help="context JSON output path")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="FlagGems PR dynamic context helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    write = sub.add_parser("write", help="validate inputs and write context JSON")
    add_common_write_args(write)
    write.set_defaults(func=write_context)

    show = sub.add_parser("show", help="print a context JSON")
    show.add_argument("--context", required=True)
    show.set_defaults(func=show_context)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
