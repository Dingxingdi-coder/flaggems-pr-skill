#!/usr/bin/env python3
"""Meta gate for the flaggems-pr-submit skill."""

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
    Rule("META-H001", "hard-rule scripts expose valid rule ids through --list-rules"),
    Rule("META-H002", "required prompt and spec files exist"),
]

HARD_RULE_SCRIPTS = [
    "scripts/resolve_op_context.py",
    "scripts/operator_static_gate.py",
    "scripts/skill_meta_gate.py",
]

REQUIRED_PATHS = [
    "references/prompt-templates/name-worktree.md",
    "references/prompt-templates/implementation-review.md",
    "references/prompt-templates/worktree-test-benchmark.md",
    "references/prompt-templates/register.md",
    "references/prompt-templates/final-validation.md",
    "references/implementation-review/spec.md",
    "references/shared/test-benchmark.md",
    "references/registration/spec.md",
    "references/final/spec.md",
    "references/reviewer-feedback-intake.md",
    "references/soft-constraints.md",
    "references/constraint-map.md",
]


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def print_rule_list() -> None:
    for rule in RULES:
        print(f"{rule.rule_id}\t{rule.description}")


def fail(errors: list[tuple[str, str]]) -> None:
    for rule_id, message in errors:
        print(f"ERROR[{rule_id}]: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_script_rules(root: Path, errors: list[tuple[str, str]]) -> None:
    seen: set[str] = set()
    for rel in HARD_RULE_SCRIPTS:
        path = root / rel
        if not path.is_file():
            errors.append(("META-H001", f"missing script: {rel}"))
            continue
        proc = subprocess.run([sys.executable, str(path), "--list-rules"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            errors.append(("META-H001", f"{rel} --list-rules failed: {proc.stderr.strip()}"))
            continue
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2 or not re.fullmatch(r"(?:RESOLVE|STATIC|META)-H\d{3}", parts[0]) or not parts[1].strip():
                errors.append(("META-H001", f"{rel} emitted malformed rule line: {line!r}"))
                continue
            if parts[0] in seen:
                errors.append(("META-H001", f"duplicate rule id: {parts[0]}"))
            seen.add(parts[0])


def check_paths(root: Path, errors: list[tuple[str, str]]) -> None:
    for rel in REQUIRED_PATHS:
        if not (root / rel).is_file():
            errors.append(("META-H002", f"missing required file: {rel}"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-rules", action="store_true")
    args = parser.parse_args()
    if args.list_rules:
        print_rule_list()
        return

    root = skill_root()
    errors: list[tuple[str, str]] = []
    check_script_rules(root, errors)
    check_paths(root, errors)
    if errors:
        fail(errors)
    print("PASS skill meta gate")


if __name__ == "__main__":
    main()
