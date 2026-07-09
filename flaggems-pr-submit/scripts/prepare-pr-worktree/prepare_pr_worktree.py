#!/usr/bin/env python3
"""Create a clean PR worktree and extract target operator files into it."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PR_BASE_REPO_SLUG = "flagos-ai/FlagGems-Experimental"
PR_BASE_REMOTE_URL = f"https://github.com/{PR_BASE_REPO_SLUG}.git"
PR_BASE_BRANCH = "infra-ci"
PR_BASE_REF = f"refs/remotes/pr-base/{PR_BASE_BRANCH}"


TARGET_FILES = (
    "src/flag_gems/ops/{module}.py",
    "src/flag_gems/ops/__init__.py",
    "src/flag_gems/__init__.py",
    "tests/test_{op_id}.py",
    "benchmark/test_{op_id}.py",
    "conf/operators.yaml",
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, end="")
        fail(f"command failed: {' '.join(cmd)}\n{exc.stderr.strip()}")


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd)


def fetch_pr_base(repo_root: Path) -> str:
    run(
        [
            "git",
            "fetch",
            PR_BASE_REMOTE_URL,
            f"+refs/heads/{PR_BASE_BRANCH}:{PR_BASE_REF}",
        ],
        repo_root,
    )
    return PR_BASE_REF


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--op", required=True)
    parser.add_argument("--op-id", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--is-aten", choices=("true", "false"), required=True)
    parser.add_argument("--labels", default="")
    parser.add_argument("--yaml-description", default="")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--worktree-root", type=Path, required=True)
    parser.add_argument("--gen-worktree", type=Path, required=True)
    parser.add_argument("--upstream-ref", default="")
    return parser.parse_args()


def branch_exists(repo_root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
    )
    return result.returncode == 0


def worktree_path_for_branch(repo_root: Path, branch: str) -> Path | None:
    result = git(repo_root, "worktree", "list", "--porcelain")
    current_path: Path | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ")).resolve()
        elif line == f"branch refs/heads/{branch}" and current_path is not None:
            return current_path
    return None


def ensure_pr_worktree(repo_root: Path, worktree_root: Path, branch: str, upstream_ref: str) -> Path:
    target_path = (worktree_root / branch.replace("/", "-")).resolve()
    existing_path = worktree_path_for_branch(repo_root, branch)
    if existing_path is not None:
        fail(f"branch {branch} is already checked out at {existing_path}; remove it before preparing a new PR worktree")

    if branch_exists(repo_root, branch):
        fail(f"branch {branch} already exists; remove it before preparing a new PR worktree")

    if target_path.exists():
        fail(f"target PR worktree path already exists but is not registered to {branch}: {target_path}")

    git(repo_root, "worktree", "add", "-b", branch, str(target_path), upstream_ref)
    return target_path


def cleanup_created_pr_worktree(repo_root: Path, pr_worktree: Path, branch: str) -> None:
    print(
        f"Cleaning up failed PR worktree created in this run: {pr_worktree} ({branch})",
        file=sys.stderr,
    )
    subprocess.run(["git", "worktree", "remove", "--force", str(pr_worktree)], cwd=repo_root, check=False)
    subprocess.run(["git", "branch", "-D", branch], cwd=repo_root, check=False)


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    worktree_root = args.worktree_root.resolve()
    gen_worktree = args.gen_worktree.resolve()
    if not repo_root.is_dir():
        fail(f"repo root does not exist: {repo_root}")
    if not gen_worktree.is_dir():
        fail(f"generated worktree does not exist: {gen_worktree}")

    pr_branch = f"pr/{args.op_id}"
    base_ref = fetch_pr_base(repo_root)
    pr_worktree: Path | None = None
    try:
        pr_worktree = ensure_pr_worktree(repo_root, worktree_root, pr_branch, base_ref)

        script_dir = Path(__file__).resolve().parent
        extract_script = script_dir / "extract_from_worktree.py"
        extract_cmd = [
            sys.executable,
            str(extract_script),
            args.op,
            "--op-id",
            args.op_id,
            "--module",
            args.module,
            "--source-worktree",
            str(gen_worktree),
            "--repo-dir",
            str(pr_worktree),
            "--is-aten",
            args.is_aten,
        ]
        for label in [item.strip() for item in args.labels.split(",") if item.strip()]:
            extract_cmd.extend(["--yaml-label", label])
        if args.yaml_description:
            extract_cmd.extend(["--yaml-description", args.yaml_description])
        run(extract_cmd, repo_root)
    except SystemExit:
        if pr_worktree is not None:
            cleanup_created_pr_worktree(repo_root, pr_worktree, pr_branch)
        raise

    target_files = [template.format(module=args.module, op_id=args.op_id) for template in TARGET_FILES]
    print(f"PR_BRANCH={pr_branch}")
    print(f"PR_WORKTREE={pr_worktree}")
    print("TARGET_FILES=" + ",".join(target_files))


if __name__ == "__main__":
    main()
