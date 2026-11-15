"""Check every site in sites.yaml and keep one open GitHub issue per outage.

A site is down when any of its URLs fails twice in a row (one retry after a
short pause, so a single blip doesn't page anyone). Down with no open issue:
open "Outage: <name>". Up with an open issue: comment the recovery and close it.

Needs `gh` and GH_TOKEN (the workflow's GITHUB_TOKEN with issues: write).
Run with --dry-run to check sites without touching issues.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import yaml

LABEL = "outage"
RETRY_PAUSE_SECONDS = 20
USER_AGENT = "atibbs-uptime/1.0 (+https://github.com/atibbs/uptime)"


def probe(url: str, timeout: float) -> tuple[bool, str, int]:
    """Return (ok, detail, elapsed_ms) for one GET request."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except Exception as error:  # DNS, TLS, timeout, connection reset
        elapsed = int((time.monotonic() - started) * 1000)
        return False, f"{type(error).__name__}: {error}"[:200], elapsed
    elapsed = int((time.monotonic() - started) * 1000)
    return status < 400, f"HTTP {status}", elapsed


def check_url(url: str, timeout: float) -> dict:
    ok, detail, elapsed = probe(url, timeout)
    if not ok:
        time.sleep(RETRY_PAUSE_SECONDS)
        ok, detail, elapsed = probe(url, timeout)
    return {"url": url, "ok": ok, "detail": detail, "ms": elapsed}


def gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout


def open_outages() -> dict[str, dict]:
    issues = json.loads(
        gh("issue", "list", "--label", LABEL, "--state", "open",
           "--json", "number,title,createdAt", "--limit", "100")
    )
    return {issue["title"]: issue for issue in issues}


def failure_table(results: list[dict]) -> str:
    rows = ["| URL | Result | Time |", "|---|---|---|"]
    for result in results:
        mark = "ok" if result["ok"] else "**down**"
        rows.append(f"| {result['url']} | {mark} ({result['detail']}) | {result['ms']} ms |")
    return "\n".join(rows)


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    config = yaml.safe_load(open("sites.yaml"))
    timeout = float(config.get("timeout_seconds", 20))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    report = []
    for site in config["sites"]:
        results = [check_url(url, timeout) for url in site["urls"]]
        report.append((site, results))

    summary = [f"## Uptime check, {now}", "", "| Site | Status | Slowest |", "|---|---|---|"]
    for site, results in report:
        up = all(r["ok"] for r in results)
        slowest = max(r["ms"] for r in results)
        summary.append(f"| {site['name']} | {'up' if up else '**DOWN**'} | {slowest} ms |")
    print("\n".join(summary))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as handle:
            handle.write("\n".join(summary) + "\n")

    if dry_run:
        return 0

    gh("label", "create", LABEL, "--color", "d73a4a",
       "--description", "A site failed its uptime check", "--force")
    existing = open_outages()
    for site, results in report:
        title = f"Outage: {site['name']}"
        up = all(r["ok"] for r in results)
        issue = existing.get(title)
        if not up and issue is None:
            body = (f"`{site['id']}` failed its uptime check at {now}.\n\n"
                    f"{failure_table(results)}\n\n"
                    "This issue closes itself when the site recovers.")
            gh("issue", "create", "--title", title, "--label", LABEL, "--body", body)
            print(f"Opened: {title}")
        elif up and issue is not None:
            opened = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
            minutes = int((datetime.now(timezone.utc) - opened).total_seconds() // 60)
            gh("issue", "comment", str(issue["number"]), "--body",
               f"Recovered at {now} (down about {minutes} min).\n\n{failure_table(results)}")
            gh("issue", "close", str(issue["number"]))
            print(f"Closed: {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
