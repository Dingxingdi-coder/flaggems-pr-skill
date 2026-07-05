#!/usr/bin/env python3
"""Collect updated [KernelGen][Nvidia] PR metadata for daily skill evolution."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # type: ignore[assignment]

REPO = "flagos-ai/FlagGems"
TITLE_PREFIX = "[KernelGen][Nvidia]"

PR_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $after, states: [OPEN, CLOSED, MERGED], orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        url
        updatedAt
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
    updated_at: datetime


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("timestamp must not be empty")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_iso() -> str:
    return iso_z(datetime.now(timezone.utc))


def run_gh_json(args: list[str]) -> dict[str, Any]:
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI is required; install gh and run `gh auth login` first")
    completed = subprocess.run(["gh", *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise SystemExit("gh command failed: gh " + " ".join(args) + "\n" + message)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("gh returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise SystemExit("gh returned unexpected JSON shape")
    return payload


def query_all_prs(since: datetime | None = None, progress: bool = False) -> list[PullRequest]:
    if progress and tqdm is None:
        raise SystemExit("tqdm is required for --progress; install it with `python -m pip install tqdm`")

    owner, name = REPO.split("/", 1)
    after: str | None = None
    prs: list[PullRequest] = []
    scanned = 0

    pbar = tqdm(desc="Fetching PR pages", unit="page", dynamic_ncols=True) if progress else None

    try:
        while True:
            args = ["api", "graphql", "-f", f"query={PR_QUERY}", "-f", f"owner={owner}", "-f", f"name={name}"]
            if after:
                args.extend(["-f", f"after={after}"])
            payload = run_gh_json(args)
            pull_requests = payload.get("data", {}).get("repository", {}).get("pullRequests", {})

            should_stop = False

            for node in pull_requests.get("nodes", []):
                if not isinstance(node, dict):
                    continue

                updated_at_raw = str(node.get("updatedAt") or "")
                updated_at = parse_timestamp(updated_at_raw)
                scanned += 1

                if since is not None and updated_at <= since:
                    should_stop = True
                    break

                title = str(node.get("title") or "")
                if not title.startswith(TITLE_PREFIX):
                    continue

                prs.append(
                    PullRequest(
                        number=int(node["number"]),
                        title=title,
                        url=str(node.get("url") or ""),
                        updated_at=updated_at,
                    )
                )

            if pbar is not None:
                pbar.update(1)
                pbar.set_postfix(scanned=scanned, matched=len(prs))

            page_info = pull_requests.get("pageInfo", {})
            if should_stop or not page_info.get("hasNextPage"):
                break

            after = page_info.get("endCursor")
            if not after:
                break
    finally:
        if pbar is not None:
            pbar.close()

    return prs


def collect_updated_prs(since: datetime, progress: bool = False) -> list[PullRequest]:
    by_number: dict[int, PullRequest] = {}
    for pr in query_all_prs(since=since, progress=progress):
        if pr.updated_at > since:
            by_number[pr.number] = pr
    return sorted(by_number.values(), key=lambda pr: pr.number)


def run_self_test() -> None:
    assert parse_timestamp("2026-07-04T00:00:00Z") == datetime(2026, 7, 4, tzinfo=timezone.utc)
    assert parse_timestamp("2026-07-04T08:00:00+08:00") == datetime(2026, 7, 4, tzinfo=timezone.utc)
    assert iso_z(datetime(2026, 7, 4, 1, 2, 3, tzinfo=timezone.utc)) == "2026-07-04T01:02:03Z"
    assert PR_QUERY.count("{") == PR_QUERY.count("}")
    print("PASS collect_kernelgen_review_delta self-test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run local timestamp parsing self-test without calling GitHub")
    parser.add_argument("--since", required="--self-test" not in sys.argv, help="UTC or offset timestamp; only PRs with updatedAt greater than this value are printed")
    parser.add_argument("--progress", action="store_true", help="show tqdm progress while querying GitHub")
    args = parser.parse_args()
    if args.self_test:
        return args
    try:
        args.since_dt = parse_timestamp(args.since)
    except ValueError as exc:
        parser.error(f"invalid --since timestamp: {exc}")
    return args


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return

    updated = collect_updated_prs(args.since_dt, progress=args.progress)
    if not updated:
        print(f"No [KernelGen][Nvidia] PRs updated after {args.since}.")
        return

    payload = {
        "generated_at": utc_now_iso(),
        "review_updates_after": iso_z(args.since_dt),
        "prs": [{"number": pr.number, "title": pr.title, "url": pr.url} for pr in updated],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()