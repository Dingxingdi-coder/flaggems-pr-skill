#!/usr/bin/env python3
"""Resolve one generated FlagGems operator worktree and check upstream conflicts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SPECIAL_OPS = {
    "max_pool2d_with_indices_backward": ("max_pool2d_with_indices", "max_pool2d_with_indices_backward"),
    "matmul_layer_norm": ("Matmul_Layer_Norm", "matmul_layernorm"),
    "__and__": ("_and_", "and_op"),
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def strip_aten(name: object) -> str:
    text = "" if name is None else str(name).strip()
    return text[6:] if text.startswith("aten::") else text


def run_git(worktree: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(worktree), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def is_dunder_operator(op: str) -> bool:
    return op.startswith("__") and op.endswith("__")


def resolve_module_and_id(op: str) -> tuple[str, str]:
    if op in SPECIAL_OPS:
        return SPECIAL_OPS[op]
    module = op.rstrip("_") if op.endswith("_") and not is_dunder_operator(op) else op
    return module, op.lstrip("_")


def expected_branches(op: str, op_id: str) -> set[str]:
    return {f"gen-{op}", f"gen-{op_id}"}


def branch_for(worktree: Path) -> str | None:
    result = run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def resolve_worktree(worktree_root: Path, op: str, op_id: str) -> tuple[Path, str]:
    expected = expected_branches(op, op_id)
    candidates = [worktree_root / branch for branch in sorted(expected)]

    matches: list[tuple[Path, str]] = []
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        branch = branch_for(candidate)
        if branch in expected:
            matches.append((candidate.resolve(), branch))

    if not matches and worktree_root.is_dir():
        for candidate in sorted(worktree_root.glob("gen-*")):
            if candidate in candidates or not candidate.is_dir():
                continue
            branch = branch_for(candidate)
            if branch in expected:
                matches.append((candidate.resolve(), branch))

    if not matches:
        tried = ", ".join(str(path) for path in candidates)
        fail(f"generated worktree not found for {op}; tried {tried} and scanned {worktree_root}/gen-* branches")
    if len(matches) > 1:
        found = ", ".join(f"{path} ({branch})" for path, branch in matches)
        fail(f"multiple generated worktrees matched {op}: {found}")
    return matches[0]


def check_branch(worktree: Path, op: str, op_id: str) -> str:
    result = run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD")
    branch = result.stdout.strip()
    expected = expected_branches(op, op_id)
    if branch not in expected:
        fail(f"worktree branch is {branch}, expected one of {sorted(expected)}")
    return branch


def fetch_upstream(worktree: Path, upstream: str, base_branch: str) -> str:
    ref = f"refs/remotes/{upstream}/{base_branch}"
    try:
        run_git(worktree, "fetch", upstream, f"{base_branch}:{ref}")
    except subprocess.CalledProcessError as exc:
        fail(f"cannot fetch {upstream}/{base_branch}: {exc.stderr.strip()}")
    return ref


def upstream_has_path(worktree: Path, base_ref: str, path: str) -> bool:
    result = run_git(worktree, "cat-file", "-e", f"{base_ref}:{path}", check=False)
    return result.returncode == 0


def upstream_has_yaml_id(worktree: Path, base_ref: str, op_id: str) -> bool:
    result = run_git(worktree, "show", f"{base_ref}:conf/operators.yaml", check=False)
    if result.returncode != 0:
        fail(f"cannot read conf/operators.yaml from {base_ref}")
    target_lines = {f"id: {op_id}", f"id: '{op_id}'", f'id: "{op_id}"'}
    for line in result.stdout.splitlines():
        if line.strip() in target_lines:
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-op", required=True)
    parser.add_argument("--worktree-root", type=Path, required=True)
    parser.add_argument("--upstream", default="upstream")
    parser.add_argument("--base-branch", default="main")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    op = strip_aten(args.raw_op)
    module, op_id = resolve_module_and_id(op)
    worktree, _branch = resolve_worktree(args.worktree_root, op, op_id)
    branch = check_branch(worktree, op, op_id)
    base_ref = fetch_upstream(worktree, args.upstream, args.base_branch)

    kernel_path = f"src/flag_gems/ops/{module}.py"
    if upstream_has_path(worktree, base_ref, kernel_path) and not (op.endswith("_") and not is_dunder_operator(op)):
        fail(f"upstream already has {kernel_path}")
    if upstream_has_yaml_id(worktree, base_ref, op_id):
        fail(f"upstream already has yaml id {op_id}")

    print(f"OP={op}")
    print(f"OP_ID={op_id}")
    print(f"MODULE={module}")
    print(f"GEN_WORKTREE={worktree}")
    print(f"GEN_BRANCH={branch}")
    print(f"UPSTREAM_REF={base_ref}")


if __name__ == "__main__":
    main()
