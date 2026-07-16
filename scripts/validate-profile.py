#!/usr/bin/env python3
"""Validate profile-specific content, accessibility, and freshness contracts."""

from datetime import date
from pathlib import Path
import re
import sys


README_PATH = Path("README.md")
EXPECTED_ASSETS = {
    "./assets/hero-dark.svg?v=2",
    "./assets/hero-light.svg?v=2",
    "./assets/yipan-flow-dark.svg?v=2",
    "./assets/yipan-flow-light.svg?v=2",
}
REQUIRED_TEXT = (
    "受控内测",
    "Linux 测试最完整",
    "Windows 和 macOS 继续真机测试",
    "核心实现、客户配置与制盘工具不公开",
    "结构示意，不是产品截图",
    "主要调用云端模型",
    "DevFlow 和 Desktop Pet 只检查 Web 单元测试与前端构建",
    "ESP32 只检查固件能否按固定配置编译",
)
REQUIRED_REPOSITORIES = (
    "yipan-showcase",
    "problem-solution-recorder-oss",
    "devflow-recorder",
    "ESP32_RPS_Game",
    "pet-desktop-tauri",
)
FORBIDDEN_TEXT = (
    "—",
    "–",
    "founder-lab.svg",
    "yipan-feature.svg",
)


def main() -> int:
    readme = README_PATH.read_text(encoding="utf-8")
    problems: list[str] = []

    for text in REQUIRED_TEXT:
        if text not in readme:
            problems.append(f"missing required visible fact: {text}")
    for repository in REQUIRED_REPOSITORIES:
        if f"github.com/rongyishuaige7/{repository}" not in readme:
            problems.append(f"missing required repository link: {repository}")
    for text in FORBIDDEN_TEXT:
        if text in readme:
            problems.append(f"forbidden stale or stylistic text: {text}")

    referenced_assets = set(re.findall(r'(?:src|srcset)="(\./assets/[^"]+\.svg\?v=\d+)"', readme))
    if referenced_assets != EXPECTED_ASSETS:
        missing = sorted(EXPECTED_ASSETS - referenced_assets)
        unexpected = sorted(referenced_assets - EXPECTED_ASSETS)
        if missing:
            problems.append("README is missing SVG references: " + ", ".join(missing))
        if unexpected:
            problems.append("README has unexpected SVG references: " + ", ".join(unexpected))

    image_tags = re.findall(r"<img\b[^>]*>", readme, re.IGNORECASE)
    if len(image_tags) != 2:
        problems.append(f"expected 2 fallback img tags, found {len(image_tags)}")
    for tag in image_tags:
        alt = re.search(r'alt="([^"]+)"', tag, re.IGNORECASE)
        if alt is None or not alt.group(1).strip():
            problems.append("fallback img is missing non-empty alt text")
        src = re.search(r'src="([^"]+)"', tag, re.IGNORECASE)
        if src is None or not src.group(1).startswith("./assets/"):
            problems.append("fallback img must use a local asset")

    verified = re.search(r"最后核对：\*\*(\d{4}-\d{2}-\d{2})\*\*", readme)
    if verified is None:
        problems.append("missing last-verified date")
    else:
        verified_date = date.fromisoformat(verified.group(1))
        age = (date.today() - verified_date).days
        if age < -1:
            problems.append(f"last-verified date is in the future: {verified_date}")
        elif age > 90:
            problems.append(f"last-verified date is stale by {age} days")
        elif age > 45:
            print(f"WARNING last-verified date is {age} days old", file=sys.stderr)

    if problems:
        print("Profile validation failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print("Profile content, accessibility, assets, and freshness contracts are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
