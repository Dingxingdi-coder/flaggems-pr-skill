#!/usr/bin/env python3
"""Consistency gate for the flaggems-pr-submit skill itself.

This script is for skill maintenance, not for generated operator PR validation.
It catches drift between hard-rule scripts, rule manifests, prompt templates, and
reviewer-learned soft-rule entries.
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
    Rule("META-H001", "hard-constraint manifest matches rule IDs exposed by hard-rule scripts"),
    Rule("META-H002", "stage prompt templates invoke the required hard-rule scripts and reviewer-learned rules"),
    Rule("META-H003", "reviewer-learned soft-rule entries follow the required schema"),
    Rule("META-H004", "reviewer-feedback intake document describes the collector metadata contract"),
]

HARD_RULE_SCRIPTS = [
    "scripts/resolve_op_context.py",
    "scripts/operator_static_gate.py",
    "scripts/skill_meta_gate.py",
]

REQUIRED_TEMPLATE_REFERENCES = {
    "references/prompt-templates/name-worktree.md": ["rule-structure.md", "name-worktree/spec.md", "resolve_op_context.py"],
    "references/prompt-templates/implementation-review.md": ["rule-structure.md", "reviewer-learned-rules.md", "implementation-review/spec.md"],
    "references/prompt-templates/worktree-test-benchmark.md": [
        "rule-structure.md",
        "reviewer-learned-rules.md",
        "shared/test-benchmark.md",
        "worktree-test-benchmark/spec.md",
    ],
    "references/prompt-templates/register.md": ["rule-structure.md", "reviewer-learned-rules.md", "register/spec.md", "operator_static_gate.py"],
    "references/prompt-templates/final-validation.md": [
        "rule-structure.md",
        "reviewer-learned-rules.md",
        "shared/test-benchmark.md",
        "final-validation/spec.md",
        "operator_static_gate.py",
    ],
}

SOFT_REQUIRED_FIELDS = [
    "Source",
    "Scene",
    "Required behavior",
    "Fix pattern",
    "Applies to",
    "Promotion candidate",
]

INTAKE_REQUIRED_TERMS = [
    "changed_comments",
    "change_type",
    "kind",
    "author",
    "is_pr_author",
    "path",
    "line",
    "--include-pr-author",
    "--include-bots",
]

Error = tuple[str, str]


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def add_error(errors: list[Error], rule_id: str, message: str) -> None:
    known_rule_ids = {rule.rule_id for rule in RULES}
    if rule_id not in known_rule_ids:
        raise AssertionError(f"unknown meta rule id: {rule_id}")
    errors.append((rule_id, message))


def fail(errors: list[Error]) -> None:
    for rule_id, message in errors:
        print(f"ERROR[{rule_id}]: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def print_rule_list() -> None:
    for rule in RULES:
        print(f"{rule.rule_id}\t{rule.description}")


def list_rules_from_script(root: Path, script_relative_path: str) -> dict[str, str]:
    completed = subprocess.run(
        [sys.executable, str(root / script_relative_path), "--list-rules"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{script_relative_path} --list-rules failed: {completed.stderr.strip()}")

    rules: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        try:
            rule_id, description = line.split("\t", 1)
        except ValueError as exc:
            raise RuntimeError(f"{script_relative_path} emitted a malformed --list-rules line: {line!r}") from exc
        if rule_id in rules:
            raise RuntimeError(f"{script_relative_path} emits duplicate rule id {rule_id}")
        rules[rule_id] = description
    if not rules:
        raise RuntimeError(f"{script_relative_path} emitted no rules")
    return rules


def check_hard_manifest(root: Path, errors: list[Error]) -> None:
    try:
        manifest = read_text(root, "references/hard-constraints.md")
    except FileNotFoundError:
        add_error(errors, "META-H001", "references/hard-constraints.md is missing")
        return

    script_rule_ids: dict[str, str] = {}
    for script in HARD_RULE_SCRIPTS:
        if script not in manifest:
            add_error(errors, "META-H001", f"hard-constraints.md does not reference {script}")
        try:
            rules = list_rules_from_script(root, script)
        except RuntimeError as exc:
            add_error(errors, "META-H001", str(exc))
            continue
        for rule_id in rules:
            if rule_id in script_rule_ids:
                add_error(errors, "META-H001", f"rule id {rule_id} is emitted by both {script_rule_ids[rule_id]} and {script}")
            script_rule_ids[rule_id] = script

    documented_ids = set(re.findall(r"\b(?:RESOLVE|STATIC|META)-H\d{3}\b", manifest))
    emitted_ids = set(script_rule_ids)
    missing = sorted(emitted_ids - documented_ids)
    orphaned = sorted(documented_ids - emitted_ids)
    if missing:
        add_error(errors, "META-H001", "hard-constraints.md is missing emitted rule ids: " + ", ".join(missing))
    if orphaned:
        add_error(errors, "META-H001", "hard-constraints.md documents rule ids not emitted by scripts: " + ", ".join(orphaned))


def check_prompt_templates(root: Path, errors: list[Error]) -> None:
    for template, required_terms in REQUIRED_TEMPLATE_REFERENCES.items():
        path = root / template
        if not path.is_file():
            add_error(errors, "META-H002", f"prompt template is missing: {template}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [term for term in required_terms if term not in text]
        if missing:
            add_error(errors, "META-H002", f"{template} is missing required references: {', '.join(missing)}")


def soft_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            if current_heading is not None:
                current_lines.append(line)
            continue
        if not in_fence and line.startswith("### "):
            if current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = line.strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_lines))
    return [(heading, lines) for heading, lines in sections if heading.startswith("### SOFT-")]


def check_soft_rule_schema(root: Path, errors: list[Error]) -> None:
    path = root / "references/shared/reviewer-learned-rules.md"
    if not path.is_file():
        add_error(errors, "META-H003", "references/shared/reviewer-learned-rules.md is missing")
        return

    for heading, lines in soft_sections(path.read_text(encoding="utf-8")):
        if not re.fullmatch(r"### SOFT-\d{8}-[a-z0-9-]+", heading):
            add_error(errors, "META-H003", f"soft-rule heading has invalid format: {heading}")
            continue
        body = "\n".join(lines)
        missing = [field for field in SOFT_REQUIRED_FIELDS if re.search(rf"(?m)^- {re.escape(field)}:\s*\S", body) is None]
        if missing:
            add_error(errors, "META-H003", f"{heading} is missing required fields: {', '.join(missing)}")


def check_intake_contract(root: Path, errors: list[Error]) -> None:
    path = root / "references/reviewer-feedback-intake.md"
    if not path.is_file():
        add_error(errors, "META-H004", "references/reviewer-feedback-intake.md is missing")
        return
    text = path.read_text(encoding="utf-8")
    missing = [term for term in INTAKE_REQUIRED_TERMS if term not in text]
    if missing:
        add_error(errors, "META-H004", "reviewer-feedback-intake.md is missing collector contract terms: " + ", ".join(missing))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-rules", action="store_true", help="print meta-rule IDs enforced by this script")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list_rules:
        print_rule_list()
        return

    root = skill_root()
    errors: list[Error] = []
    check_hard_manifest(root, errors)
    check_prompt_templates(root, errors)
    check_soft_rule_schema(root, errors)
    check_intake_contract(root, errors)

    if errors:
        fail(errors)

    print("PASS skill meta gate")
    print("enforced meta rules:")
    for rule in RULES:
        print(f"- {rule.rule_id}")


if __name__ == "__main__":
    main()
