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


SPECIAL_OPS = {
    "ReduceL2": ("reduce_l2", "reduce_l2"),
    "reduce_l2": ("reduce_l2", "reduce_l2"),
    "max_pool2d_with_indices_backward": ("max_pool2d_with_indices", "max_pool2d_with_indices_backward"),
    "matmul_layer_norm": ("Matmul_Layer_Norm", "matmul_layernorm"),
    "__and__": ("_and_", "and_op"),
}

NON_ATEN_TARGETS = {
    "reduce_l2": {
        "public_api": "flag_gems.reduce_l2",
        "reference": "torch.linalg.vector_norm",
        "reference_args": "ord=2, dim=None, keepdim=False",
        "labels": "KernelGen,reduction,experimental",
        "description": "Computes the global L2 norm of the input tensor.",
    },
}


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


def resolve_module_and_id(op: str) -> tuple[str, str]:
    if op in SPECIAL_OPS:
        return SPECIAL_OPS[op]
    module = op.rstrip("_") if op.endswith("_") and not is_dunder_operator(op) else op
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
    is_aten: bool = True
    public_api: str = ""
    reference: str = ""
    reference_args: str = ""
    labels: str = ""
    description: str = ""


@dataclass(frozen=True)
class YamlCandidate:
    op_id: str
    keys: set[str]


@dataclass(frozen=True)
class CanonicalTarget:
    module: str
    op_id: str
    path: Path
    evidence: str


def branch_for(worktree: Path) -> str | None:
    result = run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def query_keys_for(op: str) -> set[str]:
    module, op_id = resolve_module_and_id(op)
    return {normalize_name(op), normalize_name(module), normalize_name(op_id)}


def identity_keys_for(op: str) -> set[str]:
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
                candidates.append(YamlCandidate(op_id=op_id, keys=candidate_keys))
    return candidates


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
    keys = query_keys_for(raw_op) | query_keys_for(branch_op)
    candidates = yaml_candidates(worktree, keys)

    if len(candidates) > 1:
        found = ", ".join(f"OP_ID={candidate.op_id}" for candidate in candidates)
        fail(f"multiple operator yaml entries matched {raw_op}; candidates: {found}")

    op_id = candidates[0].op_id if candidates else fallback_op_id
    imports = module_imports(worktree)
    module = imports.get(op_id) or fallback_module
    metadata = NON_ATEN_TARGETS.get(normalize_name(op_id)) or NON_ATEN_TARGETS.get(normalize_name(module))
    if metadata:
        return OperatorContext(
            op=branch_op,
            op_id=op_id,
            module=module,
            is_aten=False,
            public_api=metadata["public_api"],
            reference=metadata["reference"],
            reference_args=metadata["reference_args"],
            labels=metadata["labels"],
            description=metadata["description"],
        )
    return OperatorContext(op=branch_op, op_id=op_id, module=module)


def imported_flaggems_op_targets(tree: ast.AST) -> dict[str, tuple[str, str]]:
    targets: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        if node.module == "flag_gems.ops":
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                targets[local_name] = (alias.name, alias.name)
            continue
        prefix = "flag_gems.ops."
        if not node.module or not node.module.startswith(prefix):
            continue
        module = node.module.removeprefix(prefix)
        if not module or "." in module:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            targets[local_name] = (module, alias.name)
    return targets


def is_docstring_statement(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def is_logger_statement(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False
    func = statement.value.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id in {"logger", "logging"}
    )


def direct_return_call_name(function: ast.FunctionDef) -> str | None:
    return_names: list[str] = []
    for index, statement in enumerate(function.body):
        if index == 0 and is_docstring_statement(statement):
            continue
        if is_logger_statement(statement):
            continue
        if not isinstance(statement, ast.Return):
            return None
        call = statement.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            return None
        return_names.append(call.func.id)
    if len(return_names) != 1:
        return None
    return return_names[0]


def op_key_matches_text(keys: set[str], text: object) -> bool:
    normalized = normalize_name(text)
    compact = compact_name_key(text)
    tokens = {token for token in normalized.split("_") if token}
    tokens.update(compact_name_key(token) for token in tokens)
    return normalized in keys or compact in keys or bool(tokens & keys)


def attr_chain(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*attr_chain(node.value), node.attr]
    return []


def torch_op_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        node = node.func
    chain = attr_chain(node)
    if len(chain) == 2 and chain[0] == "torch":
        return chain[1]
    if len(chain) == 4 and chain[:3] == ["torch", "nn", "functional"]:
        return chain[3]
    return None


def target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in node.elts:
            names.extend(target_names(element))
        return names
    if isinstance(node, ast.Attribute):
        return [node.attr]
    return []


def is_reference_assignment(statement: ast.stmt) -> bool:
    targets: list[str] = []
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            targets.extend(target_names(target))
    elif isinstance(statement, ast.AnnAssign):
        targets.extend(target_names(statement.target))
    else:
        return False
    return any("ref" in name.casefold() or "expect" in name.casefold() for name in targets)


def assigned_value(statement: ast.stmt) -> ast.AST | None:
    if isinstance(statement, ast.Assign):
        return statement.value
    if isinstance(statement, ast.AnnAssign):
        return statement.value
    return None


def function_mentions_flaggems_op(function: ast.FunctionDef, keys: set[str]) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        chain = attr_chain(node.func)
        if len(chain) == 2 and chain[0] == "flag_gems" and op_key_matches_text(keys, chain[1]):
            return True
    return False


def is_context_function(function: ast.FunctionDef, keys: set[str]) -> bool:
    if op_key_matches_text(keys, function.name):
        return True
    for decorator in function.decorator_list:
        chain = attr_chain(decorator)
        if chain and op_key_matches_text(keys, chain[-1]):
            return True
    return function_mentions_flaggems_op(function, keys)


def string_value(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def collect_reference_targets_from_python(source_path: Path, context: OperatorContext) -> set[tuple[str, str]]:
    try:
        tree = ast.parse(source_path.read_text())
    except SyntaxError:
        return set()

    keys = identity_name_keys(context.op, context.op_id, context.module)
    targets: set[tuple[str, str]] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not is_context_function(node, keys):
            continue
        for statement in ast.walk(node):
            if isinstance(statement, (ast.Assign, ast.AnnAssign)) and is_reference_assignment(statement):
                op_name = torch_op_name(assigned_value(statement))
                if op_name:
                    targets.add(resolve_module_and_id(op_name))
            if isinstance(statement, ast.Call):
                call_chain = attr_chain(statement.func)
                if call_chain and call_chain[-1] == "UnaryReductionBenchmark":
                    op_name_value = None
                    torch_op_value = None
                    for keyword in statement.keywords:
                        if keyword.arg == "op_name":
                            op_name_value = string_value(keyword.value)
                        elif keyword.arg == "torch_op":
                            torch_op_value = torch_op_name(keyword.value)
                    if op_name_value and torch_op_value and op_key_matches_text(keys, op_name_value):
                        targets.add(resolve_module_and_id(torch_op_value))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Tuple) or len(node.elts) < 2:
            continue
        op_name_value = string_value(node.elts[0])
        torch_op_value = torch_op_name(node.elts[1])
        if op_name_value and torch_op_value and op_key_matches_text(keys, op_name_value):
            targets.add(resolve_module_and_id(torch_op_value))

    return targets


def detect_reference_target(worktree: Path, context: OperatorContext) -> CanonicalTarget | None:
    roots = [worktree / "tests", worktree / "benchmark"]
    candidates: dict[tuple[str, str], Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for source_path in root.rglob("*.py"):
            for target in collect_reference_targets_from_python(source_path, context):
                if identity_name_keys(*target) == identity_name_keys(context.module, context.op_id):
                    continue
                candidates.setdefault(target, source_path)

    if len(candidates) > 1:
        found = ", ".join(f"{module}.{op_id}" for module, op_id in sorted(candidates))
        fail(f"multiple torch reference targets detected for {context.op_id}: {found}")
    if not candidates:
        return None

    (module, op_id), source_path = next(iter(candidates.items()))
    return CanonicalTarget(
        module=module,
        op_id=op_id,
        path=source_path,
        evidence=f"{source_path}: {context.op_id} uses torch.{op_id} as its reference operator",
    )


def detect_direct_wrapper_target(worktree: Path, module: str, op_id: str) -> CanonicalTarget | None:
    source_path = worktree / f"src/flag_gems/ops/{module}.py"
    if not source_path.is_file():
        return None

    try:
        tree = ast.parse(source_path.read_text())
    except SyntaxError as exc:
        fail(f"cannot parse {source_path}: {exc}")

    imports = imported_flaggems_op_targets(tree)
    if not imports:
        return None

    function_keys = identity_name_keys(module, op_id)
    targets: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if normalize_name(node.name) not in function_keys and compact_name_key(node.name) not in function_keys:
            continue
        local_name = direct_return_call_name(node)
        if local_name is None or local_name not in imports:
            continue
        target_module, target_op_id = imports[local_name]
        if identity_name_keys(target_module, target_op_id) == identity_name_keys(module, op_id):
            continue
        targets.add((target_module, target_op_id))

    if len(targets) > 1:
        found = ", ".join(f"{target_module}.{target_op_id}" for target_module, target_op_id in sorted(targets))
        fail(f"multiple direct wrapper targets detected for {op_id} in {source_path}: {found}")
    if not targets:
        return None

    target_module, target_op_id = next(iter(targets))
    return CanonicalTarget(
        module=target_module,
        op_id=target_op_id,
        path=source_path,
        evidence=f"{source_path}: {op_id} directly returns {target_op_id}(...)",
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


def fail_if_upstream_has_raw_op(worktree: Path, raw_op: str, upstream: str, base_branch: str) -> None:
    module, op_id = resolve_module_and_id(raw_op)
    base_ref = fetch_upstream(worktree, upstream, base_branch)
    kernel_path = f"src/flag_gems/ops/{module}.py"

    if upstream_has_yaml_id(worktree, base_ref, op_id):
        fail_upstream(
            f"upstream already has yaml id {op_id}",
            upstream_yaml_conflict_details(worktree, base_ref, op_id, module, upstream),
        )
    if upstream_has_registered_op(worktree, base_ref, op_id):
        fail_upstream(
            f"upstream already registers operator {op_id}",
            operator_source_details(worktree, base_ref, op_id, module, upstream),
        )
    if upstream_has_path(worktree, base_ref, kernel_path) and not (raw_op.endswith("_") and not is_dunder_operator(raw_op)):
        fail_upstream(
            f"upstream already has {kernel_path}",
            operator_source_details(worktree, base_ref, op_id, module, upstream),
        )


def canonical_conflict_details(details: dict[str, str], context: OperatorContext, target: CanonicalTarget) -> dict[str, str]:
    result = {
        "CANONICAL_EVIDENCE": target.evidence,
    }
    result.update(details)
    return result


def fail_if_upstream_has_canonical_target(
    worktree: Path,
    base_ref: str,
    context: OperatorContext,
    target: CanonicalTarget,
    remote: str,
) -> None:
    kernel_path = f"src/flag_gems/ops/{target.module}.py"
    if upstream_has_yaml_id(worktree, base_ref, target.op_id):
        fail_upstream(
            f"{context.op_id} maps to upstream yaml id {target.op_id}",
            canonical_conflict_details(
                upstream_yaml_conflict_details(worktree, base_ref, target.op_id, target.module, remote),
                context,
                target,
            ),
        )
    if upstream_has_registered_op(worktree, base_ref, target.op_id):
        fail_upstream(
            f"{context.op_id} maps to upstream operator {target.op_id}",
            canonical_conflict_details(
                operator_source_details(worktree, base_ref, target.op_id, target.module, remote),
                context,
                target,
            ),
        )
    if upstream_has_path(worktree, base_ref, kernel_path):
        fail_upstream(
            f"{context.op_id} maps to upstream {kernel_path}",
            canonical_conflict_details(
                operator_source_details(worktree, base_ref, target.op_id, target.module, remote),
                context,
                target,
            ),
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
    if args.check_upstream:
        fail_if_upstream_has_raw_op(repo_root, raw_op, args.upstream, args.base_branch)
    worktree, _branch, branch_op = resolve_worktree(repo_root, worktree_root, raw_op)
    context = resolve_operator_context(worktree, raw_op, branch_op)
    branch = check_branch(worktree, context.op, context.op_id)
    base_ref = f"refs/remotes/{args.upstream}/{args.base_branch}"
    if args.check_upstream:
        base_ref = fetch_upstream(worktree, args.upstream, args.base_branch)

    wrapper_target = detect_direct_wrapper_target(worktree, context.module, context.op_id)
    if wrapper_target is None:
        wrapper_target = detect_reference_target(worktree, context)
    if args.check_upstream and wrapper_target is not None:
        fail_if_upstream_has_canonical_target(worktree, base_ref, context, wrapper_target, args.upstream)

    kernel_path = f"src/flag_gems/ops/{context.module}.py"
    if args.check_upstream:
        if upstream_has_yaml_id(worktree, base_ref, context.op_id):
            fail_upstream(
                f"upstream already has yaml id {context.op_id}",
                upstream_yaml_conflict_details(worktree, base_ref, context.op_id, context.module, args.upstream),
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
