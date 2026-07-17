#!/usr/bin/env python3
"""Validate profile-specific content, accessibility, and freshness contracts."""

from datetime import date
from pathlib import Path
import re
import sys


README_PATH = Path("README.md")
EXPECTED_ASSETS = {
    "./assets/hero-dark.svg?v=6",
    "./assets/hero-light.svg?v=6",
    "./assets/yipan-flow-dark.svg?v=8",
    "./assets/yipan-flow-light.svg?v=8",
    "./assets/badge-yipan.svg?v=2",
    "./assets/badge-build-log.svg?v=1",
    "./assets/badge-product-facts.svg?v=1",
    "./assets/badge-feedback.svg?v=2",
}
EXPECTED_IMG_ASSETS = {
    "./assets/hero-light.svg?v=6",
    "./assets/yipan-flow-light.svg?v=8",
    "./assets/badge-yipan.svg?v=2",
    "./assets/badge-build-log.svg?v=1",
    "./assets/badge-product-facts.svg?v=1",
    "./assets/badge-feedback.svg?v=2",
}
REQUIRED_TEXT = (
    "受控内测",
    "Linux 测试最完整",
    "Windows 和 macOS 继续真机测试",
    "核心实现、客户配置与制盘工具不公开",
    "结构示意，不是产品截图",
    "主要调用云端模型",
    "也持续发布本地优先的桌面工具和有趣的硬件项目",
    "DevFlow 只检查 Web 单元测试与前端构建",
    "Desktop Pet 只检查 Web 单元测试与前端构建",
    "两个折叠展示的 ESP32 项目 CI 只检查固件能否按固定配置编译",
    "基于ESP32的多路智能照明控制系统",
    "已完成公开净化",
    "硬件无关源码契约与 ESP32 固件构建已经由",
    "当前 ESP32、四路低压 LED、BH1750、NVS、本机凭据连接、HTTP、倒计时和自动模式尚未按当前公开提交重新真机复测",
    "默认公开固件没有 Wi-Fi 凭据，不启动 Wi-Fi 或 HTTP",
    "本项目不适用于市电、公共/应急照明、安防、消防、医疗、生产控制或无人值守",
    "// OPEN BUILDS",
    "// MORE EXPERIMENTS",
    "// ENGLISH OVERVIEW",
)
REQUIRED_REPOSITORIES = (
    "yipan-showcase",
    "problem-solution-recorder-oss",
    "devflow-recorder",
    "ESP32_RPS_Game",
    "esp32-s3-multimodal-smart-pot",
    "pet-desktop-tauri",
    "hardware-lab",
    "esp32-smart-light-controller",
)
FORBIDDEN_TEXT = (
    "—",
    "–",
    "founder-lab.svg",
    "yipan-feature.svg",
    "// OPEN LAB",
    "// LAB NOTES",
    "SYSTEM ONLINE",
    "| 当前状态 | 平台验证 | 公开范围 |",
    '<td width="50%"',
    "申请体验",
    "咨询 Yi盘",
    "esp32-baby-monitor",
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

    if "| 项目 | 当前事实 |" not in readme:
        problems.append("product facts must use the approved two-column mobile-readable table")
    if not re.search(r"yipan-flow-light\.svg\?v=8[^>]*>\n</picture>\n\n<br>\n\n\*\*Yi盘是一套", readme):
        problems.append("Yi盘 product diagram must keep one explicit visual spacer before its description")
    if readme.count('src="./assets/badge-') != 4:
        problems.append("profile must contain exactly four local brand badges")
    if readme.index("problem-solution-recorder-oss") > readme.index("// MORE EXPERIMENTS"):
        problems.append("Problem Solution Recorder must remain a primary open build")
    for experiment in ("ESP32_RPS_Game", "esp32-s3-multimodal-smart-pot", "pet-desktop-tauri"):
        if readme.index(experiment) < readme.index("// MORE EXPERIMENTS"):
            problems.append(f"{experiment} must remain inside the folded experiments section")

    referenced_assets = set(re.findall(r'(?:src|srcset)="(\./assets/[^"]+\.svg\?v=\d+)"', readme))
    if referenced_assets != EXPECTED_ASSETS:
        missing = sorted(EXPECTED_ASSETS - referenced_assets)
        unexpected = sorted(referenced_assets - EXPECTED_ASSETS)
        if missing:
            problems.append("README is missing SVG references: " + ", ".join(missing))
        if unexpected:
            problems.append("README has unexpected SVG references: " + ", ".join(unexpected))

    image_tags = re.findall(r"<img\b[^>]*>", readme, re.IGNORECASE)
    image_sources: set[str] = set()
    if len(image_tags) != len(EXPECTED_IMG_ASSETS):
        problems.append(f"expected {len(EXPECTED_IMG_ASSETS)} local img tags, found {len(image_tags)}")
    for tag in image_tags:
        alt = re.search(r'alt="([^"]+)"', tag, re.IGNORECASE)
        if alt is None or not alt.group(1).strip():
            problems.append("fallback img is missing non-empty alt text")
        src = re.search(r'src="([^"]+)"', tag, re.IGNORECASE)
        if src is None or not src.group(1).startswith("./assets/"):
            problems.append("img must use a local asset")
        elif src is not None:
            image_sources.add(src.group(1))
    if image_sources != EXPECTED_IMG_ASSETS:
        problems.append("img asset set does not match the approved local assets")

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
