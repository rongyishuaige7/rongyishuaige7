#!/usr/bin/env python3
"""Validate profile-specific content, accessibility, and freshness contracts."""

from datetime import date
from pathlib import Path
import re
import struct
import sys


README_PATH = Path("README.md")
STRIP_ASSETS = (Path("assets/hardware-strip-dark.svg"), Path("assets/hardware-strip-light.svg"))
HERO_ASSETS = (Path("assets/hero-dark.svg"), Path("assets/hero-light.svg"))
SCREENSHOTS = (Path("assets/dsh-timeline-dark.png"), Path("assets/dsh-timeline-light.png"))
MAX_SCREENSHOT_BYTES = 150 * 1024
PHOTO_STRIP = Path("assets/hardware-featured.webp")
MAX_PHOTO_BYTES = 160 * 1024
# WebP chunks that can carry EXIF or XMP metadata.
FORBIDDEN_WEBP_CHUNKS = {b"EXIF", b"XMP "}
# PNG chunks that can carry EXIF, comments, or editor metadata.
FORBIDDEN_PNG_CHUNKS = {b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME"}
EXPECTED_ASSETS = {
    "./assets/hero-dark.svg?v=11",
    "./assets/hero-light.svg?v=11",
    "./assets/yipan-flow-dark.svg?v=12",
    "./assets/yipan-flow-light.svg?v=12",
    "./assets/dsh-card-dark.svg?v=1",
    "./assets/dsh-card-light.svg?v=1",
    "./assets/hardware-strip-dark.svg?v=1",
    "./assets/hardware-strip-light.svg?v=1",
    "./assets/badge-studio.svg?v=1",
    "./assets/badge-build-log.svg?v=1",
    "./assets/badge-yipan.svg?v=2",
    "./assets/badge-product-facts.svg?v=1",
    "./assets/badge-feedback.svg?v=2",
    "./assets/badge-hardware.svg?v=1",
}
EXPECTED_IMG_ASSETS = {
    "./assets/hero-light.svg?v=11",
    "./assets/yipan-flow-light.svg?v=12",
    "./assets/dsh-card-light.svg?v=1",
    "./assets/hardware-strip-light.svg?v=1",
    "./assets/dsh-timeline-light.png?v=1",
    "./assets/hardware-featured.webp?v=1",
    "./assets/badge-studio.svg?v=1",
    "./assets/badge-build-log.svg?v=1",
    "./assets/badge-yipan.svg?v=2",
    "./assets/badge-product-facts.svg?v=1",
    "./assets/badge-feedback.svg?v=2",
    "./assets/badge-hardware.svg?v=1",
}
# The three homepage lanes, in order, then the folded English overview.
LANE_MARKERS = ("// 01 CARRY", "// 02 SEE", "// 03 TOUCH", "// ENGLISH OVERVIEW")
REQUIRED_TEXT = (
    "受控内测",
    "Linux 测试最完整",
    "Windows 和 macOS 继续真机测试",
    "核心实现、客户配置与制盘工具不公开",
    "结构示意，非产品截图",
    "主要调用云端模型",
    "真实运行界面，夹具数据，项目名为占位",
    "Token 模式",
    "最终以 Provider 账单为准",
    "产品由 Codex 独立构思、设计与开发",
    "DevFlow 只检查 Web 单元测试与前端构建",
    "基于树莓派的居家环境与活动状态监测教学原型",
    "Python 编译、11 项后端与源码合同、Android Gradle test task（当前 `NO-SOURCE`）、lint、debug assembly、敏感信息扫描与精确公开清单已由",
    "MQ-7 数字 GPIO 只表示未标定教学阈值事件",
    "ENABLE_PHYSICAL_OUTPUTS=false",
    "ENABLE_CAMERA=false",
    "CI 不上传构建产物",
    "22 个公开硬件项目",
    "历史原型照片，取自各项目公开仓库",
    "不能用于真实道路信号控制",
    "不是医疗器械，不做诊断、处方或急救",
    "医疗或养老看护、CO/燃气报警、跌倒或生命安全判断、身份认证、消费产品、无人值守控制或生产系统",
    "// LATEST BUILD",
    *LANE_MARKERS,
)
REQUIRED_REPOSITORIES = (
    "yipan-showcase",
    "dsh-stats",
    "dsh-spec",
    "tech-mentor",
    "problem-solution-recorder-oss",
    "ningque",
    "devflow-recorder",
    "memory-monitor",
    "pet-desktop-tauri",
    "esp32-s3-multimodal-smart-pot",
    "adaptive-traffic-signal-system",
    "esp32-s3-health-voice-terminal",
    "hardware-lab",
    "raspberry-pi-home-environment-activity-monitoring-demo",
)
# Repositories whose first README mention must sit inside a given lane.
LANE_REPOSITORIES = {
    "// 01 CARRY": ("yipan-showcase",),
    "// 02 SEE": (
        "dsh-stats",
        "dsh-spec",
        "tech-mentor",
        "problem-solution-recorder-oss",
        "ningque",
        "devflow-recorder",
        "memory-monitor",
        "pet-desktop-tauri",
    ),
    "// 03 TOUCH": (
        "hardware-lab",
        "esp32-s3-multimodal-smart-pot",
        "adaptive-traffic-signal-system",
        "esp32-s3-health-voice-terminal",
    ),
}
# Slogans and self-introductions retired at the user's request; project names and facts replace them.
RETIRED_COPY = (
    "随身的上下文",
    "看得见的 Agent",
    "摸得着的硬件",
    "一个人做产品",
    "跟着人走",
    "看得见，才管得住",
    "把代码烧进板子里",
    "三条线",
    "three lanes",
)
FORBIDDEN_TEXT = (
    "—",
    "–",
    "founder-lab.svg",
    "yipan-feature.svg",
    "// OPEN LAB",
    "// LAB NOTES",
    "// OPEN BUILDS",
    "// MORE EXPERIMENTS",
    "// YI盘 PRODUCT",
    "也持续发布本地优先的桌面工具和有趣的硬件项目",
    "SYSTEM ONLINE",
    "| 当前状态 | 平台验证 | 公开范围 |",
    '<td width="50%"',
    "申请体验",
    "咨询 Yi盘",
    "esp32-baby-monitor",
    "esp32-smart-light-controller",
    "esp32-smart-makeup-cabinet",
    "最新收录：[基于ESP32和ILI9341的8键掌机界面教学原型]",
    "最新收录：[基于Arduino的多传感器数据展示与音频联动教学原型]",
    "Arduino 多传感器教学原型的 CI 还检查公开范围、源码契约、Arduino Uno 默认与实验环境隔离构建，以及 Flutter format/test/analyze/debug APK 构建，且不上传构建产物",
    "公开范围扫描、仓库检查、15 项源码契约、Arduino Uno 默认与实验环境隔离构建，以及 Flutter format/test/analyze/debug APK 构建已由",
    "默认关闭模拟数据与 DFPlayer 音频",
    "HC-05 文本协议没有应用层身份认证、授权、端到端加密、MITM 防护、防重放或可靠送达保证",
    "CMD:STOP",
    "最新收录：[基于ESP32-C3的多传感器健康数据展示手环原型]",
    "公开范围扫描、仓库检查、10 项源码契约、ESP32-C3 默认与实验性振动 opt-in 编译，以及 Flutter format/test/analyze/debug APK 构建已由",
    "默认不编译 GPIO5 实验性振动输出，GPIO5 保持输入",
    "GPS 坐标不向 App 传输或展示，但不代表没有位置隐私风险",
    "BLE 服务 UUID 与广播名不是身份",
    "CI 不上传固件、ELF 或 APK 构建产物",
    "医疗或健康结论、心率/血氧准确性、跌倒检测、紧急告警、安全看护、定位/追踪、消费级可穿戴或生产系统",
)


def validate_screenshot(path: Path) -> list[str]:
    """Keep raster screenshots small and free of embedded metadata."""
    if not path.exists():
        return [f"missing screenshot asset: {path}"]
    data = path.read_bytes()
    problems: list[str] = []
    if len(data) > MAX_SCREENSHOT_BYTES:
        problems.append(f"{path.name} is {len(data)} bytes, over {MAX_SCREENSHOT_BYTES}")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return problems + [f"{path.name} is not a PNG"]
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset:offset + 4])
        chunk = data[offset + 4:offset + 8]
        if chunk in FORBIDDEN_PNG_CHUNKS:
            problems.append(f"{path.name} carries a {chunk.decode()} metadata chunk")
        offset += 12 + length
    return problems


def validate_photo_strip(path: Path) -> list[str]:
    """Keep the featured hardware photo strip small, WebP, and free of EXIF or XMP."""
    if not path.exists():
        return [f"missing photo strip: {path}"]
    data = path.read_bytes()
    problems: list[str] = []
    if len(data) > MAX_PHOTO_BYTES:
        problems.append(f"{path.name} is {len(data)} bytes, over {MAX_PHOTO_BYTES}")
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return problems + [f"{path.name} is not a WebP image"]
    offset = 12
    while offset + 8 <= len(data):
        chunk = data[offset:offset + 4]
        (length,) = struct.unpack("<I", data[offset + 4:offset + 8])
        if chunk in FORBIDDEN_WEBP_CHUNKS:
            problems.append(f"{path.name} carries a {chunk.decode().strip()} metadata chunk")
        offset += 8 + length + (length & 1)
    return problems


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
    for text in RETIRED_COPY:
        if text in readme:
            problems.append(f"retired slogan or self-introduction: {text}")
        for hero in HERO_ASSETS:
            if hero.exists() and text in hero.read_text(encoding="utf-8"):
                problems.append(f"{hero.name} still uses retired copy: {text}")

    if "| 项目 | 当前事实 |" not in readme:
        problems.append("product facts must use the approved two-column mobile-readable table")
    # The Yi盘 card links to the public repository and carries the summary itself,
    # so the paragraph under it keeps only the one-sentence definition.
    if not re.search(
        r'<a href="https://github\.com/rongyishuaige7/yipan-showcase"><picture>\n(?:.*\n){2}'
        r"  <img src=\"\./assets/yipan-flow-light\.svg\?v=12\"[^>]*>\n</picture></a>\n\n"
        r"> 结构示意，非产品截图。\n\n\*\*Yi盘是一套装在 U 盘里的随身 AI 工作台。\*\*\n\n\| 项目 \| 当前事实 \|",
        readme,
    ):
        problems.append("Yi盘 card must link to yipan-showcase and keep the approved note and one-sentence definition")
    # The DSH Usage card replaces the description and tag lines and sits above the screenshot.
    if not re.search(
        r"### \[DSH Usage\]\(https://github\.com/rongyishuaige7/dsh-stats\)\n\n"
        r'<a href="https://github\.com/rongyishuaige7/dsh-stats"><picture>\n(?:.*\n){2}'
        r'  <img src="\./assets/dsh-card-light\.svg\?v=1"[^>]*>\n</picture></a>\n\n'
        r"<picture>\n  <source [^\n]*dsh-timeline-dark\.png",
        readme,
    ):
        problems.append("DSH Usage card must link to dsh-stats and sit between its heading and the screenshot")
    for repeated in ("`USAGE` DeepSeek Harness 插件", "以 `@rongyi7/dsh-stats` 发布在 npm"):
        if repeated in readme:
            problems.append(f"DSH Usage card text is repeated in the README body: {repeated}")
    if readme.count('src="./assets/badge-') != 6:
        problems.append("profile must contain exactly six local brand badges")

    positions = [readme.find(marker) for marker in LANE_MARKERS]
    if -1 not in positions:
        if positions != sorted(positions):
            problems.append("lanes must appear in order: " + " / ".join(LANE_MARKERS))
        bounds = dict(zip(LANE_MARKERS, zip(positions, positions[1:] + [len(readme)])))
        for marker, repositories in LANE_REPOSITORIES.items():
            start, end = bounds[marker]
            for repository in repositories:
                first = readme.find(f"github.com/rongyishuaige7/{repository}")
                if first != -1 and not start < first < end:
                    problems.append(f"{repository} must first appear inside the {marker} lane")
        # The newest spotlight carries long safety limits, so it stays folded
        # inside the TOUCH lane instead of competing with the featured builds.
        touch_start, touch_end = bounds["// 03 TOUCH"]
        latest = readme.find("// LATEST BUILD")
        spotlight = readme.find("raspberry-pi-home-environment-activity-monitoring-demo")
        if not touch_start < latest < spotlight < touch_end:
            problems.append("the newest hardware spotlight must stay folded inside the TOUCH lane")

    count = re.search(r"\*\*(\d+) 个公开硬件项目\*\*", readme)
    english = re.search(r"\*\*Hardware Lab:\*\* (\d+) public hardware prototypes", readme)
    if count is None:
        problems.append("TOUCH lane must state the public hardware project count")
    else:
        expected = count.group(1)
        if english is None or english.group(1) != expected:
            problems.append("English overview must state the same hardware project count")
        for strip in STRIP_ASSETS:
            if not strip.exists() or f">{expected} PROTOTYPES<" not in strip.read_text(encoding="utf-8"):
                problems.append(f"{strip.name} must label the same {expected} hardware prototypes")
        for hero in HERO_ASSETS:
            if not hero.exists() or f">{expected} 个硬件原型" not in hero.read_text(encoding="utf-8"):
                problems.append(f"{hero.name} must list the same {expected} hardware prototypes")

    for screenshot in SCREENSHOTS:
        problems.extend(validate_screenshot(screenshot))
    problems.extend(validate_photo_strip(PHOTO_STRIP))
    for theme in ("dark", "light"):
        if f'media="(prefers-color-scheme: {theme})" srcset="./assets/dsh-timeline-{theme}.png?v=1"' not in readme:
            problems.append(f"DSH screenshot must offer the {theme} capture for the {theme} color scheme")

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
    if verified is not None:
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
