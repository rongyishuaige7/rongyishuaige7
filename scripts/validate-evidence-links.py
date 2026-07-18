#!/usr/bin/env python3
"""Validate fixed GitHub Actions evidence links against live branch semantics."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen

OWNER = "rongyishuaige7"
LINK = re.compile(
    rf"https://github\.com/{OWNER}/(?P<repo>[A-Za-z0-9_.-]+)/actions/runs/(?P<run>\d+)"
)
EXPECTED = {
    "problem-solution-recorder-oss": {"workflow": "validate.yml", "events": {"push", "workflow_dispatch"}},
    "devflow-recorder": {"workflow": "ci.yml", "events": {"push", "workflow_dispatch"}},
    "ESP32_RPS_Game": {"workflow": "ci.yml", "events": {"push", "workflow_dispatch"}},
    "esp32-s3-multimodal-smart-pot": {"workflow": "firmware.yml", "events": {"push", "workflow_dispatch"}},
    "pet-desktop-tauri": {"workflow": "ci.yml", "events": {"push", "workflow_dispatch"}},
    "esp32-s3-smart-agriculture-monitoring-system": {"workflow": "validate.yml", "events": {"push", "workflow_dispatch"}},
    "stm32f103-ov7670-smart-door-reminder-system": {"workflow": "validate.yml", "events": {"push", "workflow_dispatch"}},
    "stm32f103-wardrobe-environment-monitoring-ventilation-system": {"workflow": "validate.yml", "events": {"push", "workflow_dispatch"}},
    "raspberry-pi-home-environment-activity-monitoring-demo": {"workflow": "ci.yml", "events": {"push", "workflow_dispatch"}},
}


def api(path: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token and shutil.which("gh"):
        completed = subprocess.run(
            ["gh", "api", path.lstrip("/")],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rongyishuaige7-profile-evidence-check",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"https://api.github.com{path}",
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def main() -> int:
    links = {(match.group("repo"), match.group("run")) for match in LINK.finditer(Path("README.md").read_text())}
    problems: list[str] = []
    for repo, run_id in sorted(links):
        expected = EXPECTED.get(repo)
        if not expected:
            problems.append(f"{repo}: no expected workflow semantics configured")
            continue
        run = api(f"/repos/{OWNER}/{repo}/actions/runs/{run_id}")
        path = run.get("path", "").split("@", 1)[0]
        if path != f".github/workflows/{expected['workflow']}":
            problems.append(f"{repo} run {run_id}: expected {expected['workflow']}, got {path or 'unknown'}")
        if run.get("event") not in expected["events"]:
            problems.append(f"{repo} run {run_id}: unexpected event {run.get('event')}")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            problems.append(f"{repo} run {run_id}: not completed/success")
        metadata = api(f"/repos/{OWNER}/{repo}")
        branch = metadata.get("default_branch")
        if not branch:
            problems.append(f"{repo}: missing default branch")
            continue
        head = api(f"/repos/{OWNER}/{repo}/commits/{branch}").get("sha")
        if run.get("head_sha") != head:
            problems.append(
                f"{repo} run {run_id}: evidence head {run.get('head_sha')} "
                f"does not match {branch} HEAD {head}"
            )

    if problems:
        print("Evidence-link verification failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print(f"Verified workflow semantics for {len(links)} fixed Actions evidence links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
