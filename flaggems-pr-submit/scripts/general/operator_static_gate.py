#!/usr/bin/env python3
"""Deterministic static gate for one generated FlagGems operator PR."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path


Error = str


def add_error(errors: list[Error], message: str) -> None:
    errors.append(message)


def fail(errors: list[Error]) -> None:
    for message in errors:
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


def is_runtime_source(path: str) -> bool:
    return is_python_under(path, "src/flag_gems/ops") or is_python_under(path, "src/flag_gems/fused")


def is_dunder_operator(op_id: str) -> bool:
    return op_id.startswith("__") and op_id.endswith("__")


def is_trailing_underscore_variant(op_id: str) -> bool:
    return op_id.endswith("_") and not is_dunder_operator(op_id)


def contains_pytest_mark(text: str, op_id: str) -> bool:
    return f"pytest.mark.{op_id}" in text or f"mark.{op_id}" in text


def contains_benchmark_op_name(text: str, op_id: str) -> bool:
    pattern = rf"op_name\s*=\s*['\"]{re.escape(op_id)}['\"]"
    return re.search(pattern, text) is not None


def literal_call_strings(text: str, attr_name: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != attr_name:
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.append(arg.value)
    return values


def check_logger_messages(path: str, text: str, errors: list[Error]) -> None:
    for message in literal_call_strings(text, "debug"):
        if not message.startswith("GEMS "):
            continue
        if re.fullmatch(r"GEMS [A-Z0-9_]+", message):
            continue
        add_error(
            errors,
            f"logger.debug message {message!r} in {path} must use 'GEMS <OP_NAME_UPPER>' with uppercase words joined by underscores",
        )


def check_no_cuda_specific_device_checks(path: str, text: str, errors: list[Error]) -> None:
    if ".is_cuda" in text:
        add_error(errors, f"CUDA-specific .is_cuda appears in {path}; use flag_gems.device or backend-neutral device handling")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--op", required=True)
    parser.add_argument("--op-id", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--base-ref", default="refs/remotes/upstream/master")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors: list[Error] = []
    root = Path.cwd()
    ops_kernel = f"src/flag_gems/ops/{args.module}.py"
    fused_kernel = f"src/flag_gems/fused/{args.module}.py"
    existing_target_kernels = {path for path in (ops_kernel, fused_kernel) if (root / path).is_file()}
    using_fused = fused_kernel in existing_target_kernels and ops_kernel not in existing_target_kernels

    required_paths = {
        "src/flag_gems/__init__.py",
        "conf/operators.yaml",
    }
    if using_fused:
        kernel = fused_kernel
    else:
        kernel = ops_kernel
        required_paths.add("src/flag_gems/ops/__init__.py")
    required_paths.add(kernel)

    try:
        changed = changed_files(args.base_ref)
    except subprocess.CalledProcessError as exc:
        fail([f"cannot diff against {args.base_ref}: {exc.stderr.strip()}"])

    if ops_kernel in changed and fused_kernel in changed:
        add_error(errors, f"target source appears in both {ops_kernel} and {fused_kernel}; keep exactly one implementation location")

    unrelated = []
    allowed_target_sources = {ops_kernel, fused_kernel}
    for path in changed:
        if path in required_paths or path in allowed_target_sources or is_python_under(path, "tests") or is_python_under(path, "benchmark"):
            continue
        unrelated.append(path)
    if unrelated:
        add_error(errors, "branch diff contains unrelated files: " + ", ".join(unrelated))

    missing = [path for path in required_paths if not (root / path).is_file()]
    if missing:
        add_error(errors, "required files are missing: " + ", ".join(missing))

    if (root / kernel).is_file():
        kernel_head = "\n".join(read_text(root / kernel).splitlines()[:10])
        if "KernelGen" not in kernel_head:
            add_error(errors, f"{kernel} does not contain KernelGen in the first 10 lines")

    if is_trailing_underscore_variant(args.op_id):
        family_id = args.op_id.rstrip("_")
        trailing_paths = {
            f"src/flag_gems/ops/{args.op_id}.py": f"src/flag_gems/ops/{family_id}.py",
            f"tests/test_{args.op_id}.py": f"tests/test_{family_id}.py",
            f"benchmark/test_{args.op_id}.py": f"benchmark/test_{family_id}.py",
        }
        for bad_path, good_path in trailing_paths.items():
            if bad_path in changed:
                add_error(errors, f"{bad_path} uses a trailing-underscore family file name; use {good_path} for inplace variant {args.op_id}")

    scan_paths = [
        path
        for path in changed
        if is_runtime_source(path) or is_python_under(path, "tests") or is_python_under(path, "benchmark")
    ]
    for path in scan_paths:
        full_path = root / path
        if not full_path.is_file():
            continue
        text = read_text(full_path)
        if re.search(r"\bprint\s*\(", text):
            add_error(errors, f"print() appears in {path}")
        if is_runtime_source(path):
            check_no_cuda_specific_device_checks(path, text, errors)
            check_logger_messages(path, text, errors)

    yaml_path = root / "conf/operators.yaml"
    if yaml_path.is_file():
        yaml_text = read_text(yaml_path)
        yaml_pattern = rf"(?m)^\s*(?:-\s*)?id:\s*['\"]?{re.escape(args.op_id)}['\"]?\s*$"
        count = len(re.findall(yaml_pattern, yaml_text))
        if count != 1:
            add_error(errors, f"conf/operators.yaml must contain exactly one id for {args.op_id}; found {count}")

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
            add_error(errors, f"gems_assert_close passes rtol in {path}")
    if not test_mark_files:
        add_error(errors, f"no changed test file contains pytest mark {args.op_id}")

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
        add_error(errors, f"no changed benchmark file contains pytest mark {args.op_id}")
    if not benchmark_op_name_files:
        add_error(errors, f"no changed benchmark file sets op_name to {args.op_id}")

    if errors:
        fail(errors)

    print("PASS operator static gate")
    print("changed files:")
    for path in changed:
        print(f"- {path}")


if __name__ == "__main__":
    main()
