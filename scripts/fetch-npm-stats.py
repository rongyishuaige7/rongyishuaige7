#!/usr/bin/env python3
"""Fetch the public npm figures shown on the DSH Usage card into data/npm-stats.json.

Uses only the standard library and npm's public, unauthenticated endpoints. Every
field is checked before anything is written; on any failure the script exits
non-zero and leaves the existing file untouched, so the refresh workflow fails
visibly instead of committing a guess.
"""

from datetime import date
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

PACKAGE = "@rongyi7/dsh-stats"
OUTPUT = Path("data/npm-stats.json")
DOWNLOADS_URL = f"https://api.npmjs.org/downloads/point/last-month/{PACKAGE}"
REGISTRY_URL = f"https://registry.npmjs.org/{quote(PACKAGE, safe='@')}"
SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
RETRY_DELAYS = (2, 6)


def fail(message: str) -> None:
    print(f"npm stats refresh failed: {message}", file=sys.stderr)
    sys.exit(1)


def fetch_json(url: str, accept: str = "application/json") -> dict:
    headers = {"Accept": accept, "User-Agent": "rongyishuaige7-profile-readme"}
    last_error: Exception | None = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError("response is not a JSON object")
            return data
        except Exception as error:  # network, HTTP and JSON errors all retry the same way
            last_error = error
            if attempt < len(RETRY_DELAYS):
                time.sleep(RETRY_DELAYS[attempt])
    fail(f"{url}: {last_error}")
    raise AssertionError("unreachable")


def iso_day(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        fail(f"{field} is not an ISO date: {value!r}")
        raise AssertionError("unreachable")


def collect() -> dict:
    downloads = fetch_json(DOWNLOADS_URL)
    registry = fetch_json(REGISTRY_URL, "application/vnd.npm.install-v1+json")

    if downloads.get("package") != PACKAGE:
        fail(f"downloads response names {downloads.get('package')!r}")
    count = downloads.get("downloads")
    if type(count) is not int or count < 0:
        fail(f"downloads is not a non-negative integer: {count!r}")
    start = iso_day(downloads.get("start"), "downloads start")
    end = iso_day(downloads.get("end"), "downloads end")
    if not start < end <= date.today():
        fail(f"downloads window {start}..{end} is not a past range")
    if (end - start).days + 1 != 30:
        fail(f"downloads window {start}..{end} must cover exactly 30 days, inclusive")

    if registry.get("name") != PACKAGE:
        fail(f"registry response names {registry.get('name')!r}")
    latest = (registry.get("dist-tags") or {}).get("latest")
    versions = registry.get("versions")
    if not isinstance(versions, dict) or not versions:
        fail("registry response has no versions")
    if not isinstance(latest, str) or not SEMVER.fullmatch(latest) or latest not in versions:
        fail(f"latest dist-tag is not a published semver version: {latest!r}")

    return {
        "package": PACKAGE,
        "downloads_last_month": count,
        "downloads_start": start.isoformat(),
        "downloads_end": end.isoformat(),
        "latest": latest,
        "version_count": len(versions),
    }


def main() -> int:
    stats = collect()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}: {stats['downloads_last_month']} downloads to {stats['downloads_end']}, "
          f"latest {stats['latest']}, {stats['version_count']} versions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
