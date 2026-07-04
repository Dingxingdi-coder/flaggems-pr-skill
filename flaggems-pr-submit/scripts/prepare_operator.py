#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys

from op_naming import resolve_op
from operator_registry import DEFAULT_NORM_XLSX, lookup_norm_name

DEFAULT_REPO = os.environ.get("FLAGGEMS_REPO", "/data/dxd/FlagGems_minimax_2_7_pr")


def run_git(repo, args):
    return subprocess.run(["git"] + args, cwd=repo, text=True, capture_output=True)


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def git_show_exists(repo, ref, path):
    return run_git(repo, ["show", f"{ref}:{path}"]).returncode == 0


def git_show_text(repo, ref, path):
    result = run_git(repo, ["show", f"{ref}:{path}"])
    if result.returncode != 0:
        return ""
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description="Preflight one FlagGems operator PR")
    parser.add_argument("operator", help="operator name from user prompt")
    parser.add_argument("--repo-dir", default=DEFAULT_REPO, help="FlagGems repository path")
    parser.add_argument("--norm-xlsx", default=DEFAULT_NORM_XLSX, help="path to 规范名.xlsx")
    parser.add_argument("--create-branch", action="store_true", help="create and checkout pr/<operator> from upstream/master")
    parser.add_argument("--push-remote", default="fork", help="remote used later by submit_operator.py")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo_dir)
    if not os.path.isdir(repo):
        fail(f"repo not found: {repo}")

    inside = run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        fail(f"not a git repository: {repo}")

    op = lookup_norm_name(args.operator, args.norm_xlsx)
    names = resolve_op(op)
    print(f"operator={op}")
    print(f"op_id={names.op_id}")
    print(f"module={names.module}")

    remotes = set(run_git(repo, ["remote"]).stdout.split())
    missing = [remote for remote in ("upstream", args.push_remote) if remote not in remotes]
    if missing:
        fail("missing git remote(s): " + ", ".join(missing))

    fetch = run_git(repo, ["fetch", "upstream", "master"])
    if fetch.returncode != 0:
        fail(fetch.stderr.strip() or "git fetch upstream master failed")

    conflicts = []
    kernel_path = f"src/flag_gems/ops/{names.module}.py"
    if git_show_exists(repo, "upstream/master", kernel_path):
        conflicts.append(kernel_path)

    yaml_text = git_show_text(repo, "upstream/master", "conf/operators.yaml")
    if re.search(rf"^\s*-\s*id:\s*{re.escape(names.op_id)}\s*$", yaml_text, re.MULTILINE):
        conflicts.append(f"conf/operators.yaml id: {names.op_id}")

    top_init = git_show_text(repo, "upstream/master", "src/flag_gems/__init__.py")
    config_names = [item[0] for item in names.config_entries] or [op]
    for config_name in config_names:
        if f'"{config_name}"' in top_init or f"'{config_name}'" in top_init:
            conflicts.append(f"_FULL_CONFIG entry: {config_name}")

    if conflicts:
        print("upstream_conflict=1")
        for item in conflicts:
            print(f"conflict={item}")
        raise SystemExit(2)

    for path in (f"tests/test_{names.op_id}.py", f"benchmark/test_{names.op_id}.py"):
        if git_show_exists(repo, "upstream/master", path):
            print(f"append_target={path}")

    if args.create_branch:
        branch = f"pr/{op}"
        result = run_git(repo, ["checkout", "-b", branch, "upstream/master"])
        if result.returncode != 0:
            fail(result.stderr.strip() or f"cannot create branch {branch}")
        print(f"branch={branch}")

    print("preflight=ok")


if __name__ == "__main__":
    main()
