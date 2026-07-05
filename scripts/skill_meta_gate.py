#!/usr/bin/env python3
"""Check structural consistency for the flaggems-pr-skill repository."""

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
    Rule("META-H001", "all subagent prompt templates, specs, and soft-constraints files exist"),
    Rule("META-H002", "general soft constraints exist"),
    Rule("META-H003", "retired central, shared, and reviewer-intake files are absent"),
    Rule("META-H004", "the formal skill directory does not contain README files"),
    Rule("META-H005", "maintenance scripts are not inside flaggems-pr-submit/scripts"),
    Rule("META-H006", "prompt templates require general and own stage reference files"),
    Rule("META-H007", "policy files do not reference retired paths or old script paths"),
    Rule("META-H008", "runtime hard-rule scripts expose stable rule ids"),
    Rule("META-H009", "GitHub Actions reviewer delta workflows are absent"),
]

STAGES = [
    "implementation-review",
    "worktree-test-benchmark",
    "register",
    "final-validation",
]

def path_text(*parts: str) -> str:
    return "/".join(parts)


def retired_md(*parts: str) -> str:
    return "-".join(parts) + ".md"


RETIRED_PATHS = [
    path_text("flaggems-pr-submit", "references", retired_md("reviewer", "feedback", "intake")),
    path_text("flaggems-pr-submit", "references", retired_md("rule", "structure")),
    path_text("flaggems-pr-submit", "references", retired_md("constraint", "map")),
    path_text("flaggems-pr-submit", "references", "soft-constraints.md"),
    path_text("flaggems-pr-submit", "references", "shared"),
    path_text("flaggems-pr-submit", "references", "name-worktree"),
    path_text("flaggems-pr-submit", "references", "prompt-templates", "name-worktree.md"),
]

RETIRED_REFERENCES = [
    path_text("references", retired_md("reviewer", "feedback", "intake")),
    path_text("references", retired_md("rule", "structure")),
    path_text("references", retired_md("constraint", "map")),
    path_text("references", "soft-constraints.md"),
    path_text("references", "shared") + "/",
    path_text("references", "shared", "test-benchmark.md"),
    path_text("references", "name-worktree") + "/",
    path_text("references", "prompt-templates", "name-worktree.md"),
    path_text("flaggems-pr-submit", "scripts", "collect_kernelgen_review_delta.py"),
    path_text("flaggems-pr-submit", "scripts", "skill_meta_gate.py"),
    "{SKILL_ROOT}/" + path_text("scripts", "operator_static_gate.py"),
    "{SKILL_ROOT}/" + path_text("scripts", "resolve_op_context.py"),
    path_text("scripts", "operator_static_gate.py"),
    path_text("scripts", "resolve_op_context.py"),
]

MAINTENANCE_SCRIPT_NAMES = {
    "collect_kernelgen_review_delta.py",
    "skill_meta_gate.py",
}

RUNTIME_HARD_SCRIPTS = [
    ("flaggems-pr-submit/scripts/name-worktree/resolve_op_context.py", r"RESOLVE-H\d{3}"),
    ("flaggems-pr-submit/scripts/general/operator_static_gate.py", r"STATIC-H\d{3}"),
]


Error = tuple[str, str]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def print_rule_list() -> None:
    for rule in RULES:
        print(f"{rule.rule_id}\t{rule.description}")


def fail(errors: list[Error]) -> None:
    for rule_id, message in errors:
        print(f"ERROR[{rule_id}]: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files(root: Path, errors: list[Error]) -> None:
    for stage in STAGES:
        required = [
            f"flaggems-pr-submit/references/prompt-templates/{stage}.md",
            f"flaggems-pr-submit/references/{stage}/spec.md",
            f"flaggems-pr-submit/references/{stage}/soft-constraints.md",
        ]
        for rel in required:
            if not (root / rel).is_file():
                errors.append(("META-H001", f"missing required file: {rel}"))


def check_general_soft_constraints(root: Path, errors: list[Error]) -> None:
    rel = "flaggems-pr-submit/references/general/soft-constraints.md"
    if not (root / rel).is_file():
        errors.append(("META-H002", f"missing required file: {rel}"))


def check_retired_paths(root: Path, errors: list[Error]) -> None:
    for rel in RETIRED_PATHS:
        if (root / rel).exists():
            errors.append(("META-H003", f"retired path still exists: {rel}"))


def check_no_skill_readme(root: Path, errors: list[Error]) -> None:
    for path in (root / "flaggems-pr-submit").glob("README*"):
        if path.is_file():
            errors.append(("META-H004", f"README is not allowed under flaggems-pr-submit: {path.relative_to(root).as_posix()}"))


def check_maintenance_script_locations(root: Path, errors: list[Error]) -> None:
    runtime_scripts = root / "flaggems-pr-submit" / "scripts"
    if runtime_scripts.is_dir():
        for path in runtime_scripts.rglob("*"):
            if path.is_file() and path.name in MAINTENANCE_SCRIPT_NAMES:
                errors.append(("META-H005", f"maintenance script is inside runtime scripts: {path.relative_to(root).as_posix()}"))
    for name in MAINTENANCE_SCRIPT_NAMES:
        if not (root / "scripts" / name).is_file():
            errors.append(("META-H005", f"missing top-level maintenance script: scripts/{name}"))


def check_no_reviewer_workflow(root: Path, errors: list[Error]) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in workflows.glob("*"):
        if path.is_file() and "kernelgen-review" in path.name:
            errors.append(("META-H009", f"reviewer delta workflow is not allowed: {path.relative_to(root).as_posix()}"))


def check_prompt_templates(root: Path, errors: list[Error]) -> None:
    general = "{SKILL_ROOT}/references/general/soft-constraints.md"
    for stage in STAGES:
        rel = f"flaggems-pr-submit/references/prompt-templates/{stage}.md"
        path = root / rel
        if not path.is_file():
            continue
        text = read_text(path)
        required = [
            general,
            f"{{SKILL_ROOT}}/references/{stage}/spec.md",
            f"{{SKILL_ROOT}}/references/{stage}/soft-constraints.md",
        ]
        for item in required:
            if item not in text:
                errors.append(("META-H006", f"{rel} does not require reading {item}"))


def iter_checked_text_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for rel in ["README.md", "flaggems-pr-submit/SKILL.md"]:
        path = root / rel
        if path.is_file():
            candidates.append(path)
    for base in [root / "flaggems-pr-submit" / "references"]:
        if base.is_dir():
            candidates.extend(sorted(path for path in base.rglob("*") if path.suffix in {".md", ".py", ".sh", ".yml", ".yaml"}))
    return candidates


def check_retired_references(root: Path, errors: list[Error]) -> None:
    for path in iter_checked_text_files(root):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        for retired in RETIRED_REFERENCES:
            if retired in text:
                errors.append(("META-H007", f"{rel} references retired path or old script path: {retired}"))


def check_runtime_hard_scripts(root: Path, errors: list[Error]) -> None:
    seen: set[str] = set()
    for rel, rule_pattern in RUNTIME_HARD_SCRIPTS:
        path = root / rel
        if not path.is_file():
            errors.append(("META-H008", f"missing runtime hard-rule script: {rel}"))
            continue
        proc = subprocess.run([sys.executable, str(path), "--list-rules"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            errors.append(("META-H008", f"{rel} --list-rules failed: {proc.stderr.strip()}"))
            continue
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2 or not re.fullmatch(rule_pattern, parts[0]) or not parts[1].strip():
                errors.append(("META-H008", f"{rel} emitted malformed rule line: {line!r}"))
                continue
            if parts[0] in seen:
                errors.append(("META-H008", f"duplicate hard-rule id: {parts[0]}"))
            seen.add(parts[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-rules", action="store_true")
    args = parser.parse_args()
    if args.list_rules:
        print_rule_list()
        return

    root = repo_root()
    errors: list[Error] = []
    check_required_files(root, errors)
    check_general_soft_constraints(root, errors)
    check_retired_paths(root, errors)
    check_no_skill_readme(root, errors)
    check_maintenance_script_locations(root, errors)
    check_no_reviewer_workflow(root, errors)
    check_prompt_templates(root, errors)
    check_retired_references(root, errors)
    check_runtime_hard_scripts(root, errors)
    if errors:
        fail(errors)
    print("PASS skill meta gate")


if __name__ == "__main__":
    main()
