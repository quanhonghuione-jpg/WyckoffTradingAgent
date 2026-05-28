#!/usr/bin/env python3
"""Dispatch the Tail Buy GitHub Actions workflow (needs GITHUB_PAT with actions:write)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

REPO = "YoungCan-Wang/WyckoffTradingAgent"
WORKFLOW_FILE = "tail_buy_1420.yml"
DEFAULT_REF = "main"


def _github_token() -> str:
    for key in ("GITHUB_PAT", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def main() -> int:
    token = _github_token()
    if not token:
        print("Set GITHUB_PAT (or GH_TOKEN) with repo actions:write to dispatch Tail Buy.", file=sys.stderr)
        return 1

    ref = os.getenv("TAIL_BUY_WORKFLOW_REF", DEFAULT_REF).strip() or DEFAULT_REF
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    req = urllib.request.Request(
        url,
        data=json.dumps({"ref": ref}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Tail Buy workflow dispatched on {ref} (HTTP {resp.status})")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"Dispatch failed: HTTP {exc.code}\n{body}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
