#!/usr/bin/env python3
"""Deterministic static gate for one generated FlagGems operator PR.

Hard constraints in this file are intentionally identified by stable rule IDs.
When promoting a reviewer-derived rule into this script, add the rule to RULES,
emit failures through add_error(...), and validate this script with
``--list-rules``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str


RULES = [
    Rule("STATIC-H000", "static gate command can diff against the supplied upstream/base ref"),
    Rule("STATIC-H001", "branch diff is limited to the target operator file set"),
    Rule("STATIC-H002", "required kernel, package init, top-level init, and operators.yaml files exist"),
    Rule("STATIC-H003", "target kernel file contains KernelGen in the first 10 lines"),
    Rule("STATIC-H004", "target changed Python files do not contain print() debug output"),
    Rule("STATIC-H005", "conf/operators.yaml contains exactly one id for the target op_id"),
    Rule("STATIC-H006", "at least one changed test file contains pytest.mark.<op_id>"),
    Rule("STATIC-H007", "changed tests do not pass rtol= to gems_assert_close"),
    Rule("STATIC-H008", "at least one changed benchmark file contains pytest.mark.<op_id>"),
    Rule("STATIC-H009", "at least one changed benchmark file sets op_name to the target op_id"),
]


Error = tuple[str, str]


def add_error(errors: list[Error], rule_id: str, message: str) -> None:
    known_rule_ids = {rule.rule_id for rule in RULES}
    if rule_id not in known_rule_ids:
        raise AssertionError(f"unknown hard rule id: {rule_id}")
    errors.append((rule_id, message))


def fail(errors: list[Error]) -> None:
    for rule_id, message in errors:
        print(f"ERROR[{rule_id}]: {message}", file=sys.stderr)
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


def print_rule_list() -> None:
    for rule in RULES:
        print(f"{rule.rule_id}\t{rule.description}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--op")
    parser.add_argument("--op-id")
    parser.add_argument("--module")
    parser.add_argument("--base-ref", default="refs/remotes/upstream/master")
    parser.add_argument("--list-rules", action="store_true", help="print hard-rule IDs enforced by this script")
    args = parser.parse_args()

    if args.list_rules:
        return args

    missing = [name for name in ("op", "op_id", "module") if getattr(args, name) is None]
    if missing:
        parser.error("missing required arguments unless --list-rules is used: " + ", ".join(f"--{name.replace('_', '-')}" for name in missing))
    return args


def main() -> None:
    args = parse_args()
    if args.list_rules:
        print_rule_list()
        return

    errors: list[Error] = []
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
        fail([("STATIC-H000", f"cannot diff against {args.base_ref}: {exc.stderr.strip()}")])

    unrelated = []
    for path in changed:
        if path in required_paths or is_python_under(path, "tests") or is_python_under(path, "benchmark"):
            continue
        unrelated.append(path)
    if unrelated:
        add_error(errors, "STATIC-H001", "branch diff contains unrelated files: " + ", ".join(unrelated))

    missing = [path for path in required_paths if not (root / path).is_file()]
    if missing:
        add_error(errors, "STATIC-H002", "required files are missing: " + ", ".join(missing))

    if (root / kernel).is_file():
        kernel_head = "\n".join(read_text(root / kernel).splitlines()[:10])
        if "KernelGen" not in kernel_head:
            add_error(errors, "STATIC-H003", f"{kernel} does not contain KernelGen in the first 10 lines")

    scan_paths = [path for path in changed if path == kernel or is_python_under(path, "tests") or is_python_under(path, "benchmark")]
    for path in scan_paths:
        full_path = root / path
        if full_path.is_file() and re.search(r"\bprint\s*\(", read_text(full_path)):
            add_error(errors, "STATIC-H004", f"print() appears in {path}")

    yaml_path = root / "conf/operators.yaml"
    if yaml_path.is_file():
        yaml_text = read_text(yaml_path)
        yaml_pattern = rf"(?m)^\s*id:\s*['\"]?{re.escape(args.op_id)}['\"]?\s*$"
        count = len(re.findall(yaml_pattern, yaml_text))
        if count != 1:
            add_error(errors, "STATIC-H005", f"conf/operators.yaml must contain exactly one id for {args.op_id}; found {count}")

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
            add_error(errors, "STATIC-H007", f"gems_assert_close passes rtol in {path}")
    if not test_mark_files:
        add_error(errors, "STATIC-H006", f"no changed test file contains pytest mark {args.op_id}")

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
        add_error(errors, "STATIC-H008", f"no changed benchmark file contains pytest mark {args.op_id}")
    if not benchmark_op_name_files:
        add_error(errors, "STATIC-H009", f"no changed benchmark file sets op_name to {args.op_id}")

    if errors:
        fail(errors)

    print("PASS operator static gate")
    print("enforced hard rules:")
    for rule in RULES:
        print(f"- {rule.rule_id}")
    print("changed files:")
    for path in changed:
        print(f"- {path}")


if __name__ == "__main__":
    main()
