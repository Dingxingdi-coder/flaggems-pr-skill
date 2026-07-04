#!/usr/bin/env python3
"""Collect a lightweight index of changed comments on KernelGen Nvidia PRs.

The script uses GitHub CLI authentication. It stores a local JSON snapshot for
incremental detection, but the public output intentionally contains only PR URLs
and changed-comment URLs. A maintainer/agent should open the live PR pages and
read the comments directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_REPO = "flagos-ai/FlagGems"
TITLE_PREFIX = "[KernelGen][Nvidia]"
SEARCH_QUERY_TEMPLATE = "repo:{repo} is:pr KernelGen Nvidia"

PR_SEARCH_QUERY = """
query($searchQuery: String!, $after: String) {
  search(type: ISSUE, first: 100, after: $after, query: $searchQuery) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        url
        updatedAt
        state
        author { login }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    url: str
    updated_at: str
    state: str
    author: str


@dataclass(frozen=True)
class CommentRecord:
    key: str
    pr_number: int
    pr_title: str
    pr_url: str
    kind: str
    comment_id: str
    author: str
    created_at: str
    updated_at: str
    url: str
    body: str
    path: str | None = None
    line: int | None = None
    state: str | None = None

    @property
    def body_hash(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()

    def state_payload(self) -> dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "kind": self.kind,
            "comment_id": self.comment_id,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "url": self.url,
            "body_hash": self.body_hash,
        }


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_gh_json(args: list[str]) -> Any:
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI is required; install gh and run `gh auth login` first")
    completed = subprocess.run(["gh", *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise SystemExit("gh command failed: gh " + " ".join(args) + "\n" + completed.stderr.strip())
    stdout = completed.stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("gh returned non-JSON output for: gh " + " ".join(args)) from exc


def gh_paginated(endpoint: str) -> list[Any]:
    data = run_gh_json(["api", "--paginate", "--slurp", endpoint])
    if data is None:
        return []
    if not isinstance(data, list):
        return [data]
    flattened: list[Any] = []
    for page in data:
        if isinstance(page, list):
            flattened.extend(page)
        elif isinstance(page, dict) and "items" in page and isinstance(page["items"], list):
            flattened.extend(page["items"])
        else:
            flattened.append(page)
    return flattened


def search_kernelgen_prs(repo: str) -> list[PullRequest]:
    query = SEARCH_QUERY_TEMPLATE.format(repo=repo)
    after: str | None = None
    prs: list[PullRequest] = []
    while True:
        args = ["api", "graphql", "-f", f"query={PR_SEARCH_QUERY}", "-f", f"searchQuery={query}"]
        if after:
            args.extend(["-f", f"after={after}"])
        payload = run_gh_json(args)
        search = payload["data"]["search"]
        for node in search["nodes"]:
            if not node:
                continue
            title = node.get("title") or ""
            if not title.startswith(TITLE_PREFIX):
                continue
            prs.append(
                PullRequest(
                    number=int(node["number"]),
                    title=title,
                    url=node.get("url") or "",
                    updated_at=node.get("updatedAt") or "",
                    state=node.get("state") or "",
                    author=(node.get("author") or {}).get("login") or "",
                )
            )
        page_info = search["pageInfo"]
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
    prs.sort(key=lambda pr: pr.number)
    return prs


def user_login(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("login") or "")
    return ""


def body_text(item: dict[str, Any]) -> str:
    return str(item.get("body") or "").strip()


def collect_comments_for_pr(repo: str, pr: PullRequest) -> list[CommentRecord]:
    issue_comments = gh_paginated(f"repos/{repo}/issues/{pr.number}/comments?per_page=100")
    review_comments = gh_paginated(f"repos/{repo}/pulls/{pr.number}/comments?per_page=100")
    reviews = gh_paginated(f"repos/{repo}/pulls/{pr.number}/reviews?per_page=100")

    records: list[CommentRecord] = []
    for item in issue_comments:
        body = body_text(item)
        if not body:
            continue
        comment_id = str(item.get("id"))
        records.append(
            CommentRecord(
                key=f"issue_comment:{comment_id}",
                pr_number=pr.number,
                pr_title=pr.title,
                pr_url=pr.url,
                kind="issue_comment",
                comment_id=comment_id,
                author=user_login(item.get("user")),
                created_at=item.get("created_at") or "",
                updated_at=item.get("updated_at") or item.get("created_at") or "",
                url=item.get("html_url") or pr.url,
                body=body,
            )
        )

    for item in review_comments:
        body = body_text(item)
        if not body:
            continue
        comment_id = str(item.get("id"))
        records.append(
            CommentRecord(
                key=f"review_comment:{comment_id}",
                pr_number=pr.number,
                pr_title=pr.title,
                pr_url=pr.url,
                kind="review_comment",
                comment_id=comment_id,
                author=user_login(item.get("user")),
                created_at=item.get("created_at") or "",
                updated_at=item.get("updated_at") or item.get("created_at") or "",
                url=item.get("html_url") or pr.url,
                body=body,
                path=item.get("path"),
                line=item.get("line") or item.get("original_line"),
            )
        )

    for item in reviews:
        body = body_text(item)
        if not body:
            continue
        comment_id = str(item.get("id"))
        submitted_at = item.get("submitted_at") or ""
        records.append(
            CommentRecord(
                key=f"review:{comment_id}",
                pr_number=pr.number,
                pr_title=pr.title,
                pr_url=pr.url,
                kind="review",
                comment_id=comment_id,
                author=user_login(item.get("user")),
                created_at=submitted_at,
                updated_at=submitted_at,
                url=item.get("html_url") or pr.url,
                body=body,
                state=item.get("state"),
            )
        )

    records.sort(key=lambda record: (parse_ts(record.updated_at) or datetime.min.replace(tzinfo=timezone.utc), record.kind, record.comment_id))
    return records


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_run_at": None, "records": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def is_recent_pr(pr: PullRequest, since: datetime | None, lookback_hours: int) -> bool:
    if since is None:
        return True
    updated_at = parse_ts(pr.updated_at)
    if updated_at is None:
        return True
    return updated_at >= since - timedelta(hours=lookback_hours)


def record_change_type(record: CommentRecord, previous: dict[str, Any] | None, include_edits: bool) -> str | None:
    if previous is None:
        return "new"
    if not include_edits:
        return None
    if previous.get("body_hash") != record.body_hash or previous.get("updated_at") != record.updated_at:
        return "edited"
    return None


def group_changed_records(records: list[tuple[CommentRecord, str]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for record, change_type in records:
        group = grouped.setdefault(
            record.pr_number,
            {
                "pr_number": record.pr_number,
                "pr_title": record.pr_title,
                "pr_url": record.pr_url,
                "first_changed_comment_url": record.url,
                "first_changed_at": record.updated_at,
                "changed_comment_count": 0,
                "changed_comment_urls": [],
                "change_types": [],
            },
        )
        current_first = parse_ts(group["first_changed_at"])
        record_updated = parse_ts(record.updated_at)
        if current_first is None or (record_updated is not None and record_updated < current_first):
            group["first_changed_comment_url"] = record.url
            group["first_changed_at"] = record.updated_at
        group["changed_comment_count"] += 1
        if record.url not in group["changed_comment_urls"]:
            group["changed_comment_urls"].append(record.url)
        if change_type not in group["change_types"]:
            group["change_types"].append(change_type)

    items = list(grouped.values())
    items.sort(key=lambda item: (parse_ts(item["first_changed_at"]) or datetime.max.replace(tzinfo=timezone.utc), item["pr_number"]))
    return items


def render_index(
    *,
    repo: str,
    run_at: str,
    since: datetime | None,
    baseline: bool,
    scanned_prs: int,
    scanned_comments: int,
    changed_records: list[tuple[CommentRecord, str]],
) -> str:
    items = [] if baseline else group_changed_records(changed_records)
    payload = {
        "repo": repo,
        "run_at": run_at,
        "since": since.isoformat().replace("+00:00", "Z") if since else None,
        "baseline": baseline,
        "scanned_prs": scanned_prs,
        "scanned_comments": scanned_comments,
        "changed_pr_count": 0 if baseline else len(items),
        "changed_comment_count": 0 if baseline else sum(item["changed_comment_count"] for item in items),
        "items": items,
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--state-file", default=".kernelgen-review-state.json", type=Path)
    parser.add_argument("--output", type=Path, help="write JSON index to this path; stdout is used when omitted")
    parser.add_argument("--since", help="ISO-8601 timestamp override; otherwise state-file last_run_at is used")
    parser.add_argument("--lookback-hours", type=int, default=36, help="also inspect PRs updated this many hours before --since")
    parser.add_argument("--ignore-author", action="append", default=[], help="ignore comments from this GitHub login; repeatable")
    parser.add_argument("--baseline", action="store_true", help="save the current snapshot without emitting changed-comment items")
    parser.add_argument("--new-only", action="store_true", help="emit only comments absent from the previous state; ignore edited existing comments")
    parser.add_argument("--max-body-chars", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--no-write-state", action="store_true")
    args = parser.parse_args()

    prior_state = load_state(args.state_file)
    since = parse_ts(args.since) if args.since else parse_ts(prior_state.get("last_run_at"))
    previous_records: dict[str, Any] = dict(prior_state.get("records") or {})
    ignored_authors = set(args.ignore_author)

    prs = [pr for pr in search_kernelgen_prs(args.repo) if is_recent_pr(pr, since, args.lookback_hours)]

    all_records: list[CommentRecord] = []
    changed_records: list[tuple[CommentRecord, str]] = []
    new_state_records = dict(previous_records)
    include_edits = not args.new_only

    for pr in prs:
        for record in collect_comments_for_pr(args.repo, pr):
            if record.author in ignored_authors:
                continue
            all_records.append(record)
            change_type = None if args.baseline else record_change_type(record, previous_records.get(record.key), include_edits)
            if change_type:
                changed_records.append((record, change_type))
            new_state_records[record.key] = record.state_payload()

    run_at = utc_now_iso()
    output = render_index(
        repo=args.repo,
        run_at=run_at,
        since=since,
        baseline=args.baseline,
        scanned_prs=len(prs),
        scanned_comments=len(all_records),
        changed_records=changed_records,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if not args.no_write_state:
        save_state(args.state_file, {"last_run_at": run_at, "records": new_state_records})

    print(
        f"scanned_prs={len(prs)} scanned_comments={len(all_records)} changed_comments={0 if args.baseline else len(changed_records)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
