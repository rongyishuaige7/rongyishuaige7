#!/usr/bin/env python3
"""Validate local profile SVG assets without rendering or network access."""

import base64
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"script", "foreignObject", "iframe", "image", "use"}
FORBIDDEN_VALUE = re.compile(r"(?:javascript:|data:|https?://)", re.IGNORECASE)
FORBIDDEN_STYLE = re.compile(r"(?:@import|javascript:|data:|https?://)", re.IGNORECASE)
EXPECTED_ASSETS = {
    "badge-build-log.svg",
    "badge-feedback.svg",
    "badge-hardware.svg",
    "badge-product-facts.svg",
    "badge-studio.svg",
    "badge-yipan.svg",
    "hardware-strip-dark.svg",
    "hardware-strip-light.svg",
    "dsh-card-dark.svg",
    "dsh-card-light.svg",
    "hero-dark.svg",
    "hero-light.svg",
    "yipan-flow-dark.svg",
    "yipan-flow-light.svg",
}
THEME_PAIRS = (
    ("hero-dark.svg", "hero-light.svg"),
    ("yipan-flow-dark.svg", "yipan-flow-light.svg"),
    ("dsh-card-dark.svg", "dsh-card-light.svg"),
    ("hardware-strip-dark.svg", "hardware-strip-light.svg"),
)
# Pairs rendered by scripts/render-svg.py must match element for element.
GENERATED_PAIRS = {"hero-dark.svg", "yipan-flow-dark.svg", "dsh-card-dark.svg", "hardware-strip-dark.svg"}
GEOMETRY_ATTRIBUTES = (
    "id",
    "class",
    "d",
    "x",
    "y",
    "width",
    "height",
    "cx",
    "cy",
    "r",
    "rx",
    "transform",
    "stroke-dashoffset",
)
# The Yi盘 card follows the homepage featured card: summary, tags, repo button and status
# on the left, the diagram in its own panel on the right. In the diagram the local nodes
# sit inside the dashed U 盘 boundary and the cloud model outside it, linked to the
# workspace in both directions.
FLOW_CARD_TEXT = {
    "card-copy": ("资料、任务记录和产出保存在盘内，", "智能处理主要调用云端模型。"),
    "card-tags": ("U 盘存储", "云端模型"),
    "card-cta": ("查看公开仓库",),
    "card-status": ("受控内测",),
}
FLOW_LOCAL_IDS = {"drive-boundary", "continuity-rail", "flow-context", "step-retrieve", "flow-workspace", "step-generate", "flow-output"}
FLOW_CLOUD_IDS = {"flow-cloud", "link-request", "link-result"}
FLOW_TITLES = ("盘内资料与任务", "Yi盘工作台", "产出与任务记录")
# The DSH Usage card follows the homepage SEE card. Its metrics are stable facts from the
# dsh-stats README; download counts and version numbers would go stale in a static image.
DSH_CARD_TEXT = {
    "card-copy": ("USAGE", "按项目统计 DSH 会话的 Token、", "开发时长、费用和余额。", "未知价格会明确标出，密钥只在本机使用。"),
    "card-tags": ("TypeScript", "DSH Plugin", "Local-first"),
    "card-cta": ("查看仓库",),
    "card-status": ("已发布到 npm · MIT", "@rongyi7/dsh-stats"),
}
DSH_VIEWS = ("项目总览", "开发时间线", "用量趋势", "账户余额")
DSH_PANEL_TEXT = {
    "card-metrics": ("统计视图", "4", "趋势范围", "7/30/90", "导出格式", "CSV/JSON"),
    "card-views": DSH_VIEWS,
}
DSH_VOLATILE = re.compile(r"下载|最新版本|已发布版本|\bv?\d+\.\d+\.\d+\b")
PRIMARY_BADGES = {"badge-yipan.svg", "badge-feedback.svg", "badge-studio.svg"}
MAX_BADGE_BYTES = 20 * 1024
# The hero may embed raster media only as base64 WebP (GitHub's SVG CSP blocks
# external images). Each file stays small and carries no EXIF or XMP chunk.
EMBEDDED_WEBP = re.compile(r"data:image/webp;base64,([A-Za-z0-9+/]+={0,2})")
FORBIDDEN_WEBP_CHUNKS = {b"EXIF", b"XMP "}
MAX_HERO_BYTES = 160 * 1024
HERO_ENTRY_RIGHT_EDGE = 1160


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def drawn_text(root: ET.Element) -> str:
    """Text a viewer sees: <text> elements only, never <title> or <desc>."""
    return "\n".join("".join(element.itertext()) for element in root.iter() if local_name(element.tag) == "text")


def check_card(
    root: ET.Element,
    label: str,
    copy: dict[str, tuple[str, ...]],
    panel_id: str,
    panel_parts: dict[str, tuple[str, ...]],
) -> list[str]:
    """A homepage-style card: copy groups outside the panel, panel parts inside it, each with its drawn text."""
    problems: list[str] = []
    by_id = {element.get("id"): element for element in root.iter() if element.get("id")}
    for part_id, part_text in {**copy, **panel_parts}.items():
        part = by_id.get(part_id)
        if part is None:
            problems.append(f"{label} card is missing element: {part_id}")
            continue
        for required_text in part_text:
            if required_text not in drawn_text(part):
                problems.append(f"{label} card {part_id} is missing text: {required_text}")
    panel = by_id.get(panel_id)
    if panel is None:
        problems.append(f"{label} card is missing element: {panel_id}")
    else:
        panel_ids = {element.get("id") for element in panel.iter() if element.get("id")}
        if not set(panel_parts) <= panel_ids:
            problems.append(f"{label} card panel {panel_id} must hold " + ", ".join(sorted(panel_parts)))
        if panel_ids & set(copy):
            problems.append(f"{label} card copy must stay outside the panel {panel_id}")
    return problems


def validate_motion_css(style_text: str) -> list[str]:
    """Require every animation declaration to be opt-in for normal motion."""
    problems: list[str] = []
    depth = 0
    motion_guard_depth: int | None = None

    for line_number, line in enumerate(style_text.splitlines(), start=1):
        opens = line.count("{")
        closes = line.count("}")
        if "@media" in line and "prefers-reduced-motion: no-preference" in line:
            motion_guard_depth = depth + opens
        if "animation:" in line and motion_guard_depth is None:
            problems.append(f"animation declaration outside no-preference guard at style line {line_number}")
        depth += opens - closes
        if motion_guard_depth is not None and depth < motion_guard_depth:
            motion_guard_depth = None

    return problems


def validate_embedded_webp(href: str) -> list[str]:
    match = EMBEDDED_WEBP.fullmatch(href)
    if match is None:
        return ["embedded image must be a base64 WebP data URI"]
    try:
        data = base64.b64decode(match.group(1), validate=True)
    except ValueError:
        return ["embedded image is not valid base64"]
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return ["embedded image is not a WebP file"]
    problems: list[str] = []
    offset = 12
    while offset + 8 <= len(data):
        chunk = data[offset:offset + 4]
        (length,) = struct.unpack("<I", data[offset + 4:offset + 8])
        if chunk in FORBIDDEN_WEBP_CHUNKS:
            problems.append(f"embedded image carries a {chunk.decode().strip()} metadata chunk")
        offset += 8 + length + (length & 1)
    return problems


def validate(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        return [f"invalid XML: {error}"]

    if root.tag != f"{SVG_NAMESPACE}svg":
        problems.append("root element is not an SVG in the SVG namespace")
    if not root.get("viewBox"):
        problems.append("missing viewBox")
    if root.get("role") != "img":
        problems.append('missing role="img"')
    labelled_by = root.get("aria-labelledby", "").split()
    if not labelled_by:
        problems.append("missing aria-labelledby")

    title = root.find(f"{SVG_NAMESPACE}title")
    description = root.find(f"{SVG_NAMESPACE}desc")
    if title is None or not "".join(title.itertext()).strip():
        problems.append("missing non-empty title")
    if description is None or not "".join(description.itertext()).strip():
        problems.append("missing non-empty description")

    element_ids = {element.get("id") for element in root.iter() if element.get("id")}
    for reference in labelled_by:
        if reference not in element_ids:
            problems.append(f"aria-labelledby references missing id {reference}")

    style_text = "\n".join(
        "".join(element.itertext())
        for element in root.iter()
        if local_name(element.tag) == "style"
    )
    if FORBIDDEN_STYLE.search(style_text):
        problems.append("style contains an external or executable reference")
    if "animation:" in style_text and "prefers-reduced-motion" not in style_text:
        problems.append("animated SVG does not honor prefers-reduced-motion")
    problems.extend(validate_motion_css(style_text))

    is_hero = path.name.startswith("hero-")
    embedded_images = 0
    for element in root.iter():
        tag = local_name(element.tag)
        hero_image = is_hero and tag == "image"
        if tag in FORBIDDEN_TAGS and not hero_image:
            problems.append(f"forbidden element <{tag}>")
        if hero_image:
            embedded_images += 1
            hrefs = [value for attribute, value in element.attrib.items() if local_name(attribute) == "href"]
            if len(hrefs) != 1:
                problems.append("hero image must carry exactly one href")
            for href in hrefs:
                problems.extend(validate_embedded_webp(href))
        for attribute, value in element.attrib.items():
            attribute_name = local_name(attribute).lower()
            if attribute_name.startswith("on"):
                problems.append(f"forbidden event attribute {attribute_name}")
            if hero_image and attribute_name == "href":
                continue
            if attribute_name not in {"xmlns"} and FORBIDDEN_VALUE.search(value):
                problems.append(f"forbidden external or executable value in {attribute_name}")

    if is_hero:
        hero_ids = (
            "edge", "grid", "gridFade", "gridMask", "panelClip",
            "entry-carry", "entry-see", "entry-touch", "drive", "dsh-shot", "photo-deck",
        )
        for design_id in hero_ids:
            if design_id not in element_ids:
                problems.append(f"hero is missing required frame, grid, or entry card: {design_id}")
        top_level_rects = [element for element in root if local_name(element.tag) == "rect"]
        if len(top_level_rects) < 3:
            problems.append("hero must keep an outer shell, inset panel, and inner edge")
        if embedded_images != 4:
            problems.append(f"hero must embed one DSH capture and three hardware photos, found {embedded_images}")
        entry_touch = next((element for element in root.iter() if element.get("id") == "entry-touch"), None)
        card = entry_touch.find(f"{SVG_NAMESPACE}rect") if entry_touch is not None else None
        if card is not None and float(card.get("x", "0")) + float(card.get("width", "0")) > HERO_ENTRY_RIGHT_EDGE:
            problems.append("hero entry cards must preserve comfortable right-edge clearance")
        # Captions say what each visual is, as the homepage does.
        visible_text = drawn_text(root)
        for caption in ("功能示意", "运行截图 · 夹具数据", "历史原型照片"):
            if caption not in visible_text:
                problems.append(f"hero entry card is missing its caption: {caption}")
        if path.stat().st_size > MAX_HERO_BYTES:
            problems.append(f"hero SVG is {path.stat().st_size} bytes, over {MAX_HERO_BYTES}")

    if path.name.startswith("hardware-strip-"):
        for design_id in ("edge", "dots", "panelClip", "traces-in", "traces-out", "strip-chip"):
            if design_id not in element_ids:
                problems.append(f"hardware strip is missing required element: {design_id}")
        top_level_rects = [element for element in root if local_name(element.tag) == "rect"]
        if len(top_level_rects) < 3:
            problems.append("hardware strip must keep an outer shell, inset panel, and inner edge")

    if path.name.startswith("yipan-flow-"):
        visible_text = drawn_text(root)
        required_flow_text = (
            "U 盘内",
            *FLOW_TITLES,
            "Inbox 确认后写入长期知识",
            "受管 Agent 处理当前任务",
            "留在盘内，随盘带走",
            "检索 / 继续",
            "生成 / 记录",
            "记录·沉淀",
            "按需请求",
            "返回结果",
            "云端模型",
            "按需推理",
        )
        for required_text in required_flow_text:
            if required_text not in visible_text:
                problems.append(f"Yi盘 diagram is missing required text: {required_text}")
        for required_id in sorted(({"drive", "cloud-branch"} | FLOW_LOCAL_IDS | FLOW_CLOUD_IDS) - element_ids):
            problems.append(f"Yi盘 diagram is missing structural element: {required_id}")
        by_id = {element.get("id"): element for element in root.iter() if element.get("id")}
        problems.extend(check_card(root, "Yi盘", FLOW_CARD_TEXT, "flow-figure", {"drive": (), "cloud-branch": ()}))
        drive = by_id.get("drive")
        cloud_branch = by_id.get("cloud-branch")
        if drive is not None:
            drive_ids = {element.get("id") for element in drive.iter() if element.get("id")}
            if not FLOW_LOCAL_IDS <= drive_ids:
                problems.append("Yi盘 local nodes, steps, and the record rail must sit inside the drive boundary group")
            if drive_ids & FLOW_CLOUD_IDS:
                problems.append("Yi盘 cloud model must stay outside the drive boundary")
        if cloud_branch is not None:
            branch_ids = {element.get("id") for element in cloud_branch.iter() if element.get("id")}
            if branch_ids != FLOW_CLOUD_IDS | {"cloud-branch"}:
                problems.append("Yi盘 cloud branch must hold only the cloud model and its request/result links")
        boundary = by_id.get("drive-boundary")
        cloud = by_id.get("flow-cloud")
        cloud_rect = cloud.find(f"{SVG_NAMESPACE}rect") if cloud is not None else None
        if boundary is not None and (local_name(boundary.tag) != "rect" or not boundary.get("stroke-dasharray")):
            problems.append("Yi盘 drive boundary must be a dashed rectangle")
        elif boundary is not None and cloud_rect is not None and (
            float(cloud_rect.get("x", "0")) <= float(boundary.get("x", "0")) + float(boundary.get("width", "0"))
        ):
            problems.append("Yi盘 cloud model must be drawn outside the drive boundary")
        title_sizes = {
            element.get("font-size")
            for element in root.iter()
            if local_name(element.tag) == "text" and "".join(element.itertext()).strip() in FLOW_TITLES
        }
        if len(title_sizes) != 1:
            problems.append("Yi盘 node titles must share one heading size")

    if path.name.startswith("dsh-card-"):
        problems.extend(check_card(root, "DSH Usage", DSH_CARD_TEXT, "dsh-panel", DSH_PANEL_TEXT))
        by_id = {element.get("id"): element for element in root.iter() if element.get("id")}
        views = by_id.get("card-views")
        if views is not None:
            labels = drawn_text(views)
            positions = [labels.find(label) for label in DSH_VIEWS]
            if positions != sorted(positions):
                problems.append("DSH Usage view tabs must read " + " / ".join(DSH_VIEWS))
            view_ids = {element.get("id") for element in views.iter() if element.get("id")}
            for index, label in enumerate(DSH_VIEWS, start=1):
                view = by_id.get(f"view-{index}")
                if view is None or f"view-{index}" not in view_ids or f"view-{index}" not in view.get("class", "").split():
                    problems.append(f"DSH Usage card is missing animated view group view-{index}")
                    continue
                if [other for other in DSH_VIEWS if other in drawn_text(view)] != [label]:
                    problems.append(f"DSH Usage view-{index} must highlight {label} and no other view")
        # Reduced motion keeps the base styles: the first view shows, the others stay hidden.
        base_css = style_text.split("@media", 1)[0]
        hidden = {
            selector.strip()
            for rule in re.findall(r"([^{}]+)\{\s*opacity:\s*0;\s*\}", base_css)
            for selector in rule.split(",")
        }
        if ".view-1" in hidden or not {".view-2", ".view-3", ".view-4"} <= hidden:
            problems.append("DSH Usage card must show only the first view without motion")
        description_text = "".join(description.itertext()) if description is not None else ""
        for source in (drawn_text(root), description_text):
            stale = DSH_VOLATILE.search(source)
            if stale:
                problems.append(f"DSH Usage card must not carry figures that go stale: {stale.group(0)}")

    if path.name in PRIMARY_BADGES:
        badge_rects = [element for element in root if local_name(element.tag) == "rect"]
        if len(badge_rects) < 2:
            problems.append("primary badge must keep a visible edge and inset highlight")
        else:
            surface = badge_rects[0]
            if surface.get("fill") == surface.get("stroke"):
                problems.append("primary badge border must contrast with its fill")
            if float(surface.get("stroke-width", "0")) < 1.5:
                problems.append("primary badge border is too weak")
            if badge_rects[1].get("stroke-opacity") is None:
                problems.append("primary badge is missing its restrained inset highlight")

    return problems


def main() -> int:
    assets = sorted(Path("assets").glob("*.svg"))
    if not assets:
        print("No SVG assets found.", file=sys.stderr)
        return 1

    failed = False
    asset_names = {asset.name for asset in assets}
    missing = sorted(EXPECTED_ASSETS - asset_names)
    unexpected = sorted(asset_names - EXPECTED_ASSETS)
    if missing:
        failed = True
        print("FAIL assets")
        print("  - missing required assets: " + ", ".join(missing))
    if unexpected:
        failed = True
        print("FAIL assets")
        print("  - unexpected SVG assets: " + ", ".join(unexpected))

    badge_bytes = sum(asset.stat().st_size for asset in assets if asset.name.startswith("badge-"))
    if badge_bytes > MAX_BADGE_BYTES:
        failed = True
        print("FAIL assets")
        print(f"  - badge SVG size {badge_bytes} exceeds {MAX_BADGE_BYTES} bytes")
    else:
        print(f"OK   badge SVG size: {badge_bytes} bytes")

    for asset in assets:
        problems = validate(asset)
        if problems:
            failed = True
            print(f"FAIL {asset}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"OK   {asset}")

    for dark_name, light_name in THEME_PAIRS:
        dark_path = Path("assets", dark_name)
        light_path = Path("assets", light_name)
        if not dark_path.exists() or not light_path.exists():
            continue
        dark_root = ET.parse(dark_path).getroot()
        light_root = ET.parse(light_path).getroot()
        for attribute in ("width", "height", "viewBox"):
            if dark_root.get(attribute) != light_root.get(attribute):
                failed = True
                print(f"FAIL {dark_name} / {light_name}")
                print(f"  - mismatched {attribute}")
        if dark_name in GENERATED_PAIRS:
            dark_shape = [
                (local_name(element.tag), tuple(element.get(attribute) for attribute in GEOMETRY_ATTRIBUTES))
                for element in dark_root.iter()
            ]
            light_shape = [
                (local_name(element.tag), tuple(element.get(attribute) for attribute in GEOMETRY_ATTRIBUTES))
                for element in light_root.iter()
            ]
            if dark_shape != light_shape:
                failed = True
                print(f"FAIL {dark_name} / {light_name}")
                print("  - generated pair geometry differs; edit scripts/render-svg.py, not the SVG")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
