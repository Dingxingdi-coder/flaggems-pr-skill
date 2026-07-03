#!/usr/bin/env python3
"""Per-operator preflight for FlagGems PR submission."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from op_naming import resolve_op  # noqa: E402
from operator_registry import lookup_norm_name  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"preflight error: {message}")


def run(cmd: list[str], cwd: str, *, check: bool = False) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if check and res.returncode != 0:
        fail(f"command failed: {' '.join(cmd)}\n{res.stdout[-1000:]}\n{res.stderr[-1000:]}")
    return res


def load_context(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        fail(f"context file not found: {p}")
    return json.loads(p.read_text())


def check_upstream_absent(repo: str, remote: str, branch: str, module: str, op_id: str) -> None:
    run(["git", "fetch", remote, branch], cwd=repo, check=True)
    ref = f"{remote}/{branch}"
    kernel_path = f"src/flag_gems/ops/{module}.py"
    kernel = run(["git", "show", f"{ref}:{kernel_path}"], cwd=repo)
    if kernel.returncode == 0:
        fail(f"upstream already has kernel file: {kernel_path}")

    yaml_res = run(["git", "show", f"{ref}:conf/operators.yaml"], cwd=repo)
    if yaml_res.returncode == 0 and f"id: {op_id}" in yaml_res.stdout:
        fail(f"upstream already has operators.yaml id: {op_id}")


def checkout_branch(repo: str, remote: str, branch: str, op: str, *, reset: bool) -> None:
    target = f"pr/{op}"
    if reset:
        run(["git", "checkout", "-B", target, f"{remote}/{branch}"], cwd=repo, check=True)
    else:
        res = run(["git", "checkout", target], cwd=repo)
        if res.returncode != 0:
            fail(f"cannot checkout existing branch {target}; use --create-branch for a new PR")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize operator and check repo/worktree state")
    parser.add_argument("--context", required=True, help="context JSON produced by scripts/context.py")
    parser.add_argument("--op", required=True, help="raw operator name from user request")
    parser.add_argument("--create-branch", action="store_true", help="create/reset pr/<op> from upstream")
    parser.add_argument("--reviewer-update", action="store_true", help="checkout existing pr/<op> without reset")
    args = parser.parse_args()

    if args.create_branch and args.reviewer_update:
        fail("choose only one of --create-branch or --reviewer-update")

    ctx = load_context(args.context)
    repo = str(Path(ctx["repo_dir"]).resolve())
    worktree_root = Path(ctx["worktree_root"]).resolve()
    norm = lookup_norm_name(args.op, ctx["norm_xlsx"])
    names = resolve_op(norm)
    worktree = worktree_root / f"gen-{norm}"
    if not worktree.is_dir():
        alt = worktree_root / f"gen-{names.op_id}"
        if alt.is_dir():
            worktree = alt
        else:
            fail(f"worktree not found: {worktree} or {alt}")

    check_upstream_absent(
        repo,
        ctx["upstream_remote"],
        ctx["base_branch"],
        names.module,
        names.op_id,
    )

    if args.create_branch or args.reviewer_update:
        checkout_branch(
            repo,
            ctx["upstream_remote"],
            ctx["base_branch"],
            norm,
            reset=args.create_branch,
        )

    result = {
        "raw_op": args.op,
        "op": norm,
        "op_id": names.op_id,
        "module": names.module,
        "branch": f"pr/{norm}",
        "worktree": str(worktree),
        "repo_dir": repo,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
