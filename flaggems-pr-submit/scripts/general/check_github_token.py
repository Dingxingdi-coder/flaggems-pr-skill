#!/usr/bin/env python3
"""Check that a GitHub token is available without revealing it."""

from __future__ import annotations

import os
import sys


TOKEN_ENV_NAMES = ("GH_TOKEN", "GITHUB_TOKEN")


def main() -> None:
    for name in TOKEN_ENV_NAMES:
        value = os.environ.get(name)
        if value and value.strip():
            print(f"GITHUB_TOKEN_ENV={name}")
            return

    print(
        "ERROR: GitHub token is required; set GH_TOKEN or GITHUB_TOKEN in the agent environment and do not paste or print the token.",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
