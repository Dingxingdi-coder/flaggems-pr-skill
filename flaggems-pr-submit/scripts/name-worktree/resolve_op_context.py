#!/usr/bin/env python3
"""Resolve one generated FlagGems operator worktree and check upstream conflicts."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from difflib import get_close_matches
import re
import subprocess
import sys
from pathlib import Path

import yaml

PR_BASE_REPO_SLUG = "flagos-ai/FlagGems-Experimental"
PR_BASE_REMOTE_URL = f"https://github.com/{PR_BASE_REPO_SLUG}.git"
PR_BASE_BRANCH = "infra-ci"
PR_BASE_REF = f"refs/remotes/pr-base/{PR_BASE_BRANCH}"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def strip_aten(name: object) -> str:
    text = "" if name is None else str(name).strip()
    return text[6:] if text.startswith("aten::") else text


def normalize_name(name: object) -> str:
    text = strip_aten(name)
    if text.startswith("gen-"):
        text = text[4:]
    if text.endswith(".py"):
        text = text[:-3]
    return text.replace("-", "_").casefold()


def compact_name_key(name: object) -> str:
    return re.sub(r"[^0-9a-z]+", "", normalize_name(name))


def identity_name_keys(*names: str) -> set[str]:
    keys = {normalize_name(name) for name in names}
    keys.update(compact_name_key(name) for name in names)
    return keys


def run_git(worktree: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(worktree), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_gh(worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=worktree,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def is_dunder_operator(op: str) -> bool:
    return op.startswith("__") and op.endswith("__")


def is_trailing_underscore_operator(op: str) -> bool:
    return op.endswith("_") and not is_dunder_operator(op)


def resolve_module_and_id(op: str) -> tuple[str, str]:
    module = op.rstrip("_") if is_trailing_underscore_operator(op) else op
    return module, op.lstrip("_")


def expected_branches(op: str, op_id: str) -> set[str]:
    return {f"gen-{op}", f"gen-{op_id}"}


@dataclass(frozen=True)
class GenCandidate:
    branch: str
    op: str
    worktree: Path | None

    @property
    def keys(self) -> set[str]:
        return identity_keys_for(self.op)


@dataclass(frozen=True)
class OperatorContext:
    op: str
    op_id: str
    module: str
    is_aten: bool
    public_api: str = ""
    reference: str = ""
    reference_args: str = ""
    labels: str = ""
    description: str = ""


@dataclass(frozen=True)
class YamlCandidate:
    op_id: str
    keys: set[str]
    for_values: tuple[str, ...]
    labels: tuple[str, ...]
    description: str
    reference: str
    reference_args: str


def branch_for(worktree: Path) -> str | None:
    result = run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def query_keys_for(op: str) -> set[str]:
    module, op_id = resolve_module_and_id(op)
    return {normalize_name(op), normalize_name(module), normalize_name(op_id)}


def identity_keys_for(op: str) -> set[str]:
    if is_trailing_underscore_operator(op):
        return {normalize_name(op)}
    _module, op_id = resolve_module_and_id(op)
    return identity_name_keys(op, op_id)


def gen_branches(repo_root: Path) -> list[str]:
    result = run_git(repo_root, "branch", "--format=%(refname:short)", "--list", "gen-*")
    return [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("gen-")]


def registered_worktrees(repo_root: Path) -> dict[str, Path]:
    result = run_git(repo_root, "worktree", "list", "--porcelain")
    by_branch: dict[str, Path] = {}
    current_path: Path | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ")).resolve()
        elif line.startswith("branch refs/heads/gen-") and current_path is not None:
            branch = line.removeprefix("branch refs/heads/")
            by_branch[branch] = current_path
    return by_branch


def fallback_worktree_for_branch(worktree_root: Path, branch: str) -> Path | None:
    candidate = worktree_root / branch
    if not candidate.is_dir():
        return None
    if branch_for(candidate) != branch:
        return None
    return candidate.resolve()


def collect_gen_candidates(repo_root: Path, worktree_root: Path) -> list[GenCandidate]:
    worktrees = registered_worktrees(repo_root)
    candidates: list[GenCandidate] = []
    for branch in gen_branches(repo_root):
        op = branch.removeprefix("gen-")
        worktree = worktrees.get(branch) or fallback_worktree_for_branch(worktree_root, branch)
        candidates.append(GenCandidate(branch=branch, op=op, worktree=worktree))
    return candidates


def resolve_worktree(repo_root: Path, worktree_root: Path, raw_op: str) -> tuple[Path, str, str]:
    keys = identity_keys_for(raw_op)
    candidates = collect_gen_candidates(repo_root, worktree_root)
    matches = [candidate for candidate in candidates if keys & candidate.keys]

    if not matches:
        available = sorted({key for candidate in candidates for key in candidate.keys})
        close = get_close_matches(sorted(keys)[0], available, n=8, cutoff=0.6)
        hint = f"; close normalized gen-* matches: {', '.join(close)}" if close else ""
        fail(f"generated gen-* branch not found for {raw_op}; normalized keys: {sorted(keys)}{hint}")
    if len(matches) > 1:
        found = ", ".join(
            f"{candidate.branch}"
            + (f" at {candidate.worktree}" if candidate.worktree is not None else " (no registered worktree)")
            + f" via keys {sorted(keys & candidate.keys)}"
            for candidate in matches
        )
        fail(f"multiple gen-* branches matched {raw_op}; normalized keys {sorted(keys)} matched: {found}")

    match = matches[0]
    if match.worktree is None:
        fail(
            f"matched {match.branch} for {raw_op}, but it has no usable worktree under {worktree_root}; "
            f"check `git worktree list` or recreate the worktree for that branch"
        )
    return match.worktree, match.branch, match.op


def yaml_entries_from_text(text: str) -> list[dict]:
    data = yaml.safe_load(text) or {}
    if isinstance(data, dict):
        entries = data.get("ops", [])
    else:
        entries = data
    return [entry for entry in entries if isinstance(entry, dict)]


def yaml_candidates(worktree: Path, keys: set[str]) -> list[YamlCandidate]:
    yaml_path = worktree / "conf/operators.yaml"
    if not yaml_path.is_file():
        return []

    candidates: list[YamlCandidate] = []
    for entry in yaml_entries_from_text(yaml_path.read_text()):
        names = [entry.get("id"), entry.get("name")]
        names.extend(entry.get("for") or [])
        candidate_keys = {normalize_name(name) for name in names if name}
        if keys & candidate_keys:
            op_id = str(entry.get("id") or entry.get("name") or next(iter(entry.get("for") or []), "")).strip()
            if op_id:
                for_values = tuple(str(name).strip() for name in (entry.get("for") or []) if str(name).strip())
                labels = tuple(str(label).strip() for label in (entry.get("labels") or []) if str(label).strip())
                description = str(entry.get("description") or "").strip()
                reference = str(entry.get("reference") or "").strip()
                reference_args = str(entry.get("reference_args") or "").strip()
                candidates.append(
                    YamlCandidate(
                        op_id=op_id,
                        keys=candidate_keys,
                        for_values=for_values,
                        labels=labels,
                        description=description,
                        reference=reference,
                        reference_args=reference_args,
                    )
                )
    return candidates


def aten_schema_exists(name: str) -> bool:
    text = strip_aten(name)
    if not text:
        return False
    op_name, sep, overload = text.partition(".")
    if not sep:
        overload = ""

    try:
        import torch

        packet = getattr(torch.ops.aten, op_name)
        overloads = set(packet.overloads())
    except Exception:
        return False

    if overload:
        return overload in overloads
    return bool(overloads)


def exported_public_api(worktree: Path, op_id: str) -> str:
    init_path = worktree / "src/flag_gems/__init__.py"
    if not init_path.is_file():
        return ""

    try:
        tree = ast.parse(init_path.read_text())
    except SyntaxError:
        return ""

    target = normalize_name(op_id)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if not node.module.startswith("flag_gems.ops"):
            continue
        for alias in node.names:
            public_name = alias.asname or alias.name
            if normalize_name(public_name) == target:
                return f"flag_gems.{public_name}"
    return ""


def module_imports(worktree: Path) -> dict[str, str]:
    init_path = worktree / "src/flag_gems/ops/__init__.py"
    if not init_path.is_file():
        return {}

    tree = ast.parse(init_path.read_text())
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        prefix = "flag_gems.ops."
        if not node.module.startswith(prefix):
            continue
        module = node.module.removeprefix(prefix)
        for alias in node.names:
            imports[alias.name] = module
    return imports


def resolve_operator_context(worktree: Path, raw_op: str, branch_op: str) -> OperatorContext:
    fallback_module, fallback_op_id = resolve_module_and_id(branch_op)
    if is_trailing_underscore_operator(raw_op):
        keys = {normalize_name(raw_op)}
    else:
        keys = query_keys_for(raw_op) | query_keys_for(branch_op)
    candidates = yaml_candidates(worktree, keys)

    if len(candidates) > 1:
        found = ", ".join(f"OP_ID={candidate.op_id}" for candidate in candidates)
        fail(f"multiple operator yaml entries matched {raw_op}; candidates: {found}")

    op_id = candidates[0].op_id if candidates else fallback_op_id
    imports = module_imports(worktree)
    module = imports.get(op_id) or fallback_module
    labels = candidates[0].labels if candidates else ()
    description = candidates[0].description if candidates else ""
    reference = candidates[0].reference if candidates else ""
    reference_args = candidates[0].reference_args if candidates else ""
    schema_names = (op_id, module, branch_op, *(candidates[0].for_values if candidates else ()))
    if any(aten_schema_exists(schema_name) for schema_name in schema_names):
        return OperatorContext(
            op=branch_op,
            op_id=op_id,
            module=module,
            is_aten=True,
            labels=",".join(labels),
            description=description,
        )

    # No exact ATen schema means this is a non-ATen target. The resolver only
    # performs mechanical worktree identity resolution; semantic metadata such
    # as public API, reference expression, labels, and description is completed
    # by implementation-review/register stages.
    public_api = exported_public_api(worktree, op_id)
    return OperatorContext(
        op=branch_op,
        op_id=op_id,
        module=module,
        is_aten=False,
        public_api=public_api,
        reference=reference,
        reference_args=reference_args,
        labels=",".join(labels),
        description=description,
    )


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


def fetch_pr_base(worktree: Path) -> str:
    try:
        run_git(
            worktree,
            "fetch",
            PR_BASE_REMOTE_URL,
            f"+refs/heads/{PR_BASE_BRANCH}:{PR_BASE_REF}",
        )
    except subprocess.CalledProcessError as exc:
        fail(f"cannot fetch {PR_BASE_REPO_SLUG}:{PR_BASE_BRANCH}: {exc.stderr.strip()}")
    return PR_BASE_REF


def upstream_has_path(worktree: Path, base_ref: str, path: str) -> bool:
    result = run_git(worktree, "cat-file", "-e", f"{base_ref}:{path}", check=False)
    return result.returncode == 0


def upstream_has_yaml_id(worktree: Path, base_ref: str, op_id: str) -> bool:
    result = run_git(worktree, "show", f"{base_ref}:conf/operators.yaml", check=False)
    if result.returncode != 0:
        fail(f"cannot read conf/operators.yaml from {base_ref}")
    target = normalize_name(op_id)
    for entry in yaml_entries_from_text(result.stdout):
        names = [entry.get("id"), entry.get("name")]
        names.extend(entry.get("for") or [])
        if any(normalize_name(name) == target for name in names if name):
            return True
    return False


def github_repo_slug(worktree: Path, remote: str) -> str:
    if "/" in remote and not remote.startswith(("http://", "https://", "git@")):
        return remote
    result = run_git(worktree, "remote", "get-url", remote, check=False)
    url = result.stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return "flagos-ai/FlagGems-Experimental"


def pr_url_for_commit(worktree: Path, repo: str, commit: str) -> str | None:
    pr = run_gh(
        worktree,
        "api",
        f"repos/{repo}/commits/{commit}/pulls",
        "-H",
        "Accept: application/vnd.github+json",
        "--jq",
        ".[0].html_url",
    )
    if pr.returncode == 0 and pr.stdout.strip():
        return pr.stdout.strip()

    message = run_git(worktree, "show", "-s", "--format=%B", commit, check=False)
    match = re.search(r"\(#(\d+)\)", message.stdout)
    if not match:
        return None
    pr_number = match.group(1)

    pr_view = run_gh(worktree, "pr", "view", pr_number, "--repo", repo, "--json", "url", "--jq", ".url")
    if pr_view.returncode == 0 and pr_view.stdout.strip():
        return pr_view.stdout.strip()
    return f"https://github.com/{repo}/pull/{pr_number}"


def matching_yaml_line(text: str, op_id: str) -> int | None:
    target = normalize_name(op_id)
    for index, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"\s*(?:-\s*)?(?:id|name)\s*:\s*(.+?)\s*$", line)
        if match and normalize_name(match.group(1).strip("\"'")) == target:
            return index
        match = re.match(r"\s*-\s*(.+?)\s*$", line)
        if match and normalize_name(match.group(1).strip("\"'")) == target:
            return index
    return None


def first_commit_from_log(worktree: Path, *args: str) -> str | None:
    result = run_git(worktree, "log", "--format=%H", "--reverse", *args, check=False)
    if result.returncode != 0:
        return None
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)


def operator_source_details(worktree: Path, base_ref: str, op_id: str, module: str, remote: str) -> dict[str, str]:
    repo = github_repo_slug(worktree, remote)
    kernel_path = f"src/flag_gems/ops/{module}.py"

    if upstream_has_path(worktree, base_ref, kernel_path):
        commit = first_commit_from_log(worktree, "--diff-filter=A", base_ref, "--", kernel_path)
        if commit:
            details = {
                "OP_SOURCE_KIND": "implementation",
                "OP_SOURCE_PATH": kernel_path,
                "OP_SOURCE_COMMIT": commit,
            }
            pr_url = pr_url_for_commit(worktree, repo, commit)
            if pr_url:
                details["OP_SOURCE_PR_URL"] = pr_url
            return details

    yaml_path = "conf/operators.yaml"
    for needle in (f"name: {op_id}", f"id: {op_id}"):
        commit = first_commit_from_log(worktree, f"-S{needle}", base_ref, "--", yaml_path)
        if commit:
            details = {
                "OP_SOURCE_KIND": "yaml",
                "OP_SOURCE_PATH": yaml_path,
                "OP_SOURCE_COMMIT": commit,
            }
            pr_url = pr_url_for_commit(worktree, repo, commit)
            if pr_url:
                details["OP_SOURCE_PR_URL"] = pr_url
            return details

    return {}


def upstream_yaml_conflict_details(worktree: Path, base_ref: str, op_id: str, module: str, remote: str) -> dict[str, str]:
    path = "conf/operators.yaml"
    result = run_git(worktree, "show", f"{base_ref}:{path}", check=False)
    if result.returncode != 0:
        return {}

    line = matching_yaml_line(result.stdout, op_id)
    if line is None:
        details = {"UPSTREAM_EVIDENCE": f"{base_ref}:{path} contains {op_id}"}
        details.update(operator_source_details(worktree, base_ref, op_id, module, remote))
        return details

    details = {"UPSTREAM_EVIDENCE": f"{base_ref}:{path}:{line} contains {op_id}"}
    blame = run_git(worktree, "blame", "-L", f"{line},{line}", "--porcelain", base_ref, "--", path, check=False)
    if blame.returncode != 0 or not blame.stdout.strip():
        details.update(operator_source_details(worktree, base_ref, op_id, module, remote))
        return details

    commit = blame.stdout.split()[0]
    details["UPSTREAM_COMMIT"] = commit

    repo = github_repo_slug(worktree, remote)
    pr_url = pr_url_for_commit(worktree, repo, commit)
    if pr_url:
        details["UPSTREAM_PR_URL"] = pr_url

    details.update(operator_source_details(worktree, base_ref, op_id, module, remote))
    return details


def fail_upstream(message: str, details: dict[str, str]) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    for key, value in details.items():
        print(f"{key}={value}", file=sys.stderr)
    raise SystemExit(1)


def upstream_has_registered_op(worktree: Path, base_ref: str, op_id: str) -> bool:
    target = normalize_name(op_id)
    for path in ("src/flag_gems/__init__.py", "src/flag_gems/ops/__init__.py"):
        result = run_git(worktree, "show", f"{base_ref}:{path}", check=False)
        if result.returncode != 0:
            continue
        if target in {normalize_name(name) for name in set(re.findall(r"\b\w+\b", result.stdout))}:
            return True
    return False


def fail_if_upstream_has_raw_op(worktree: Path, raw_op: str, base_ref: str) -> None:
    module, op_id = resolve_module_and_id(raw_op)
    kernel_path = f"src/flag_gems/ops/{module}.py"

    if upstream_has_yaml_id(worktree, base_ref, op_id):
        fail_upstream(
            f"upstream already has yaml id {op_id}",
            upstream_yaml_conflict_details(worktree, base_ref, op_id, module, PR_BASE_REPO_SLUG),
        )
    if upstream_has_registered_op(worktree, base_ref, op_id):
        fail_upstream(
            f"upstream already registers operator {op_id}",
            operator_source_details(worktree, base_ref, op_id, module, PR_BASE_REPO_SLUG),
        )
    if upstream_has_path(worktree, base_ref, kernel_path) and not (raw_op.endswith("_") and not is_dunder_operator(raw_op)):
        fail_upstream(
            f"upstream already has {kernel_path}",
            operator_source_details(worktree, base_ref, op_id, module, PR_BASE_REPO_SLUG),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-op", required=True)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--worktree-root", type=Path, required=True)
    parser.add_argument("--upstream", default="upstream")
    parser.add_argument("--base-branch", default="master")
    parser.add_argument("--check-upstream", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = (args.repo_root or args.worktree_root.parent).resolve()
    worktree_root = args.worktree_root.resolve()
    raw_op = strip_aten(args.raw_op)
    base_ref = fetch_pr_base(repo_root)
    if args.check_upstream:
        fail_if_upstream_has_raw_op(repo_root, raw_op, base_ref)
    worktree, _branch, branch_op = resolve_worktree(repo_root, worktree_root, raw_op)
    context = resolve_operator_context(worktree, raw_op, branch_op)
    branch = check_branch(worktree, context.op, context.op_id)

    kernel_path = f"src/flag_gems/ops/{context.module}.py"
    if args.check_upstream:
        if upstream_has_yaml_id(worktree, base_ref, context.op_id):
            fail_upstream(
                f"upstream already has yaml id {context.op_id}",
                upstream_yaml_conflict_details(worktree, base_ref, context.op_id, context.module, PR_BASE_REPO_SLUG),
            )
        if upstream_has_registered_op(worktree, base_ref, context.op_id):
            fail(f"upstream already registers operator {context.op_id}")
        if upstream_has_path(worktree, base_ref, kernel_path) and not (context.op.endswith("_") and not is_dunder_operator(context.op)):
            fail(f"upstream already has {kernel_path}")

    print(f"OP={context.op}")
    print(f"OP_ID={context.op_id}")
    print(f"MODULE={context.module}")
    print(f"IS_ATEN={str(context.is_aten).lower()}")
    print(f"PUBLIC_API={context.public_api}")
    print(f"REFERENCE={context.reference}")
    print(f"REFERENCE_ARGS={context.reference_args}")
    print(f"LABELS={context.labels}")
    print(f"DESCRIPTION={context.description}")
    print(f"GEN_WORKTREE={worktree}")
    print(f"GEN_BRANCH={branch}")
    print(f"UPSTREAM_REF={base_ref}")


if __name__ == "__main__":
    main()
