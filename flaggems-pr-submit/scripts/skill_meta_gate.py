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
    Rule("META-H003", "soft-rule destination paths use the canonical stage specs"),
    Rule("META-H004", "embedded soft-rule entries have the required fields and unique ids"),
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
    "references/name-worktree/spec.md",
    "references/implementation-review/spec.md",
    "references/worktree-test-benchmark/spec.md",
    "references/shared/test-benchmark.md",
    "references/register/spec.md",
    "references/final-validation/spec.md",
    "references/reviewer-feedback-intake.md",
    "references/soft-constraints.md",
    "references/constraint-map.md",
    "references/rule-structure.md",
]

CANONICAL_SOFT_DESTINATIONS = [
    "references/implementation-review/spec.md",
    "references/shared/test-benchmark.md",
    "references/register/spec.md",
    "references/final-validation/spec.md",
]

SOFT_DESTINATION_DOCS = [
    "references/rule-structure.md",
    "references/soft-constraints.md",
    "references/reviewer-feedback-intake.md",
    "references/constraint-map.md",
]

RETIRED_REFERENCES = [
    "references/registration/spec.md",
    "references/final/spec.md",
    "references/shared/reviewer-learned-rules.md",
    "reviewer-learned-rules.md",
]

RETIRED_PATHS = [
    "references/registration/spec.md",
    "references/final/spec.md",
]

SOFT_RULE_FILES = [
    "references/implementation-review/spec.md",
    "references/shared/test-benchmark.md",
    "references/register/spec.md",
    "references/final-validation/spec.md",
]

SOFT_RULE_REQUIRED_FIELDS = [
    "Source",
    "Scene",
    "Required behavior",
    "Fix pattern",
    "Applies to",
    "Promotion candidate",
]


Error = tuple[str, str]


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def repo_root(root: Path) -> Path:
    return root.parent


def print_rule_list() -> None:
    for rule in RULES:
        print(f"{rule.rule_id}\t{rule.description}")


def fail(errors: list[Error]) -> None:
    for rule_id, message in errors:
        print(f"ERROR[{rule_id}]: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_script_rules(root: Path, errors: list[Error]) -> None:
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


def check_paths(root: Path, errors: list[Error]) -> None:
    for rel in REQUIRED_PATHS:
        if not (root / rel).is_file():
            errors.append(("META-H002", f"missing required file: {rel}"))


def iter_policy_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        files.append(skill_md)
    references = root / "references"
    if references.is_dir():
        files.extend(sorted(references.rglob("*.md")))

    repo = repo_root(root)
    readme = repo / "README.md"
    if readme.is_file():
        files.append(readme)
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        files.extend(sorted(path for path in workflows.rglob("*") if path.suffix in {".yml", ".yaml"}))
    return files


def rel_to_repo(path: Path, root: Path) -> str:
    try:
        return path.relative_to(repo_root(root)).as_posix()
    except ValueError:
        return path.as_posix()


def check_canonical_destinations(root: Path, errors: list[Error]) -> None:
    for rel in RETIRED_PATHS:
        if (root / rel).exists():
            errors.append(("META-H003", f"retired spec path still exists: {rel}"))

    for path in iter_policy_text_files(root):
        text = read_text(path)
        for retired in RETIRED_REFERENCES:
            if retired in text:
                errors.append(("META-H003", f"{rel_to_repo(path, root)} references retired path {retired}"))

    for rel in SOFT_DESTINATION_DOCS:
        path = root / rel
        if not path.is_file():
            continue
        text = read_text(path)
        for destination in CANONICAL_SOFT_DESTINATIONS:
            if destination not in text:
                errors.append(("META-H003", f"{rel} does not mention canonical soft-rule destination {destination}"))


def extract_soft_rule_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^### (SOFT-\d{8}-[a-z0-9][a-z0-9-]*)\s*$", text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1), text[start:end]))
    return blocks


def check_soft_entries(root: Path, errors: list[Error]) -> None:
    seen: dict[str, str] = {}
    for rel in SOFT_RULE_FILES:
        path = root / rel
        if not path.is_file():
            continue
        text = read_text(path)
        for rule_id, block in extract_soft_rule_blocks(text):
            if rule_id in seen:
                errors.append(("META-H004", f"duplicate soft rule id {rule_id} in {rel} and {seen[rule_id]}"))
            seen[rule_id] = rel
            for field in SOFT_RULE_REQUIRED_FIELDS:
                if not re.search(rf"(?m)^- {re.escape(field)}:\s+\S", block):
                    errors.append(("META-H004", f"{rel} entry {rule_id} is missing field: {field}"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-rules", action="store_true")
    args = parser.parse_args()
    if args.list_rules:
        print_rule_list()
        return

    root = skill_root()
    errors: list[Error] = []
    check_script_rules(root, errors)
    check_paths(root, errors)
    check_canonical_destinations(root, errors)
    check_soft_entries(root, errors)
    if errors:
        fail(errors)
    print("PASS skill meta gate")


if __name__ == "__main__":
    main()
