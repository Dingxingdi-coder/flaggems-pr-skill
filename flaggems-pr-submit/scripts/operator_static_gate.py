#!/usr/bin/env python3
"""Deterministic static gate for one generated FlagGems operator PR."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def changed_files(base_ref: str) -> list[str]:
    diff_result = run_git("diff", "--name-only", base_ref)
    untracked_result = run_git("ls-files", "--others", "--exclude-standard")
    paths: list[str] = []
    for result in (diff_result, untracked_result):
        for line in result.stdout.splitlines():
            path = line.strip()
            if path and path not in paths:
                paths.append(path)
    return paths


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_python_under(path: str, directory: str) -> bool:
    return path.startswith(f"{directory}/") and path.endswith(".py")


def contains_pytest_mark(text: str, op_id: str) -> bool:
    return f"pytest.mark.{op_id}" in text or f"mark.{op_id}" in text


def contains_benchmark_op_name(text: str, op_id: str) -> bool:
    pattern = rf"op_name\s*=\s*['\"]{re.escape(op_id)}['\"]"
    return re.search(pattern, text) is not None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--op", required=True)
    parser.add_argument("--op-id", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--base-ref", default="refs/remotes/upstream/master")
    args = parser.parse_args()

    errors: list[str] = []
    root = Path.cwd()
    kernel = f"src/flag_gems/ops/{args.module}.py"
    required_paths = {
        kernel,
        "src/flag_gems/ops/__init__.py",
        "src/flag_gems/__init__.py",
        "conf/operators.yaml",
    }

    try:
        changed = changed_files(args.base_ref)
    except subprocess.CalledProcessError as exc:
        fail([f"cannot diff against {args.base_ref}: {exc.stderr.strip()}"])

    unrelated = []
    for path in changed:
        if path in required_paths or is_python_under(path, "tests") or is_python_under(path, "benchmark"):
            continue
        unrelated.append(path)
    if unrelated:
        errors.append("branch diff contains unrelated files: " + ", ".join(unrelated))

    missing = [path for path in required_paths if not (root / path).is_file()]
    if missing:
        errors.append("required files are missing: " + ", ".join(missing))

    if (root / kernel).is_file():
        kernel_head = "\n".join(read_text(root / kernel).splitlines()[:10])
        if "KernelGen" not in kernel_head:
            errors.append(f"{kernel} does not contain KernelGen in the first 10 lines")

    scan_paths = [path for path in changed if path == kernel or is_python_under(path, "tests") or is_python_under(path, "benchmark")]
    for path in scan_paths:
        full_path = root / path
        if full_path.is_file() and re.search(r"\bprint\s*\(", read_text(full_path)):
            errors.append(f"print() appears in {path}")

    yaml_path = root / "conf/operators.yaml"
    if yaml_path.is_file():
        yaml_text = read_text(yaml_path)
        yaml_pattern = rf"(?m)^\s*id:\s*['\"]?{re.escape(args.op_id)}['\"]?\s*$"
        count = len(re.findall(yaml_pattern, yaml_text))
        if count != 1:
            errors.append(f"conf/operators.yaml must contain exactly one id for {args.op_id}; found {count}")

    test_files = [path for path in changed if is_python_under(path, "tests")]
    benchmark_files = [path for path in changed if is_python_under(path, "benchmark")]

    test_mark_files = []
    for path in test_files:
        full_path = root / path
        if not full_path.is_file():
            continue
        text = read_text(full_path)
        if contains_pytest_mark(text, args.op_id):
            test_mark_files.append(path)
        if re.search(r"gems_assert_close\s*\([\s\S]{0,500}?\brtol\s*=", text):
            errors.append(f"gems_assert_close passes rtol in {path}")
    if not test_mark_files:
        errors.append(f"no changed test file contains pytest mark {args.op_id}")

    benchmark_mark_files = []
    benchmark_op_name_files = []
    for path in benchmark_files:
        full_path = root / path
        if not full_path.is_file():
            continue
        text = read_text(full_path)
        if contains_pytest_mark(text, args.op_id):
            benchmark_mark_files.append(path)
        if contains_benchmark_op_name(text, args.op_id):
            benchmark_op_name_files.append(path)
    if not benchmark_mark_files:
        errors.append(f"no changed benchmark file contains pytest mark {args.op_id}")
    if not benchmark_op_name_files:
        errors.append(f"no changed benchmark file sets op_name to {args.op_id}")

    if errors:
        fail(errors)

    print("PASS operator static gate")
    print("changed files:")
    for path in changed:
        print(f"- {path}")


if __name__ == "__main__":
    main()
