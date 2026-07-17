#!/usr/bin/env python3
"""Validate local profile SVG assets without rendering or network access."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"script", "foreignObject", "iframe", "image", "use"}
FORBIDDEN_VALUE = re.compile(r"(?:javascript:|data:|https?://)", re.IGNORECASE)
FORBIDDEN_STYLE = re.compile(r"(?:@import|javascript:|data:|https?://)", re.IGNORECASE)
EXPECTED_ASSETS = {
    "badge-build-log.svg",
    "badge-feedback.svg",
    "badge-product-facts.svg",
    "badge-yipan.svg",
    "hero-dark.svg",
    "hero-light.svg",
    "yipan-flow-dark.svg",
    "yipan-flow-light.svg",
}
THEME_PAIRS = (
    ("hero-dark.svg", "hero-light.svg"),
    ("yipan-flow-dark.svg", "yipan-flow-light.svg"),
)
MAX_BADGE_BYTES = 20 * 1024


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


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

    for element in root.iter():
        tag = local_name(element.tag)
        if tag in FORBIDDEN_TAGS:
            problems.append(f"forbidden element <{tag}>")
        for attribute, value in element.attrib.items():
            attribute_name = local_name(attribute).lower()
            if attribute_name.startswith("on"):
                problems.append(f"forbidden event attribute {attribute_name}")
            if attribute_name not in {"xmlns"} and FORBIDDEN_VALUE.search(value):
                problems.append(f"forbidden external or executable value in {attribute_name}")

    if path.name.startswith("hero-"):
        for design_id in ("edge", "grid", "gridFade", "gridMask", "panelClip", "portable-sequence"):
            if design_id not in element_ids:
                problems.append(f"hero is missing required frame or grid definition: {design_id}")
        top_level_rects = [element for element in root if local_name(element.tag) == "rect"]
        if len(top_level_rects) < 3:
            problems.append("hero must keep an outer shell, inset panel, and inner edge")
        portable_sequence = next((element for element in root.iter() if element.get("id") == "portable-sequence"), None)
        if portable_sequence is None or portable_sequence.get("transform") != "translate(-42 0)":
            problems.append("hero portable sequence must preserve comfortable right-edge clearance")
        drive_name = next((element for element in root.iter() if "drive-name" in element.get("class", "").split()), None)
        drive_label = next((element for element in root.iter() if "drive-label" in element.get("class", "").split()), None)
        if drive_name is None or drive_label is None:
            problems.append("hero portable card must separate the Yi盘 name from its supporting label")
        elif (
            drive_name.get("x") != drive_label.get("x")
            or drive_name.get("text-anchor") != "middle"
            or drive_label.get("text-anchor") != "middle"
            or float(drive_name.get("y", "0")) >= float(drive_label.get("y", "0"))
        ):
            problems.append("hero portable card must center Yi盘 above PORTABLE CONTEXT")

    if path.name.startswith("yipan-flow-"):
        visible_text = "".join(root.itertext())
        required_flow_text = (
            "YI盘 / CONTINUITY LOOP",
            "DATA ON DRIVE / CLOUD ON DEMAND",
            "盘内资料与任务",
            "检索资料，处理当前任务",
            "需要智能处理时按需调用",
            "产出与任务记录留在盘内",
            "数据随盘走",
            "记录 / 沉淀",
        )
        for required_text in required_flow_text:
            if required_text not in visible_text:
                problems.append(f"Yi盘 continuity diagram is missing required text: {required_text}")
        output_heading = next(
            (element for element in root.iter() if "".join(element.itertext()).strip() == "产出与任务记录留在盘内"),
            None,
        )
        if output_heading is None or output_heading.get("font-size") != "24":
            problems.append("Yi盘 output heading must match the 24px peer-card heading scale")
        required_flow_ids = {
            "main-loop",
            "context-to-workspace",
            "workspace-to-output",
            "continuity-loop",
            "cloud-branch",
            "workspace-to-model",
            "model-to-workspace",
            "packet-continuity",
            "activity-context-return",
        }
        for required_id in sorted(required_flow_ids - element_ids):
            problems.append(f"Yi盘 continuity diagram is missing structural element: {required_id}")

        main_loop = next((element for element in root.iter() if element.get("id") == "main-loop"), None)
        cloud_branch = next((element for element in root.iter() if element.get("id") == "cloud-branch"), None)
        if main_loop is not None:
            main_ids = {element.get("id") for element in main_loop.iter() if element.get("id")}
            if not {"context-to-workspace", "workspace-to-output", "continuity-loop"}.issubset(main_ids):
                problems.append("Yi盘 main loop must connect context, workspace, output, and continuity return")
        if cloud_branch is not None:
            branch_ids = {element.get("id") for element in cloud_branch.iter() if element.get("id")}
            if branch_ids != {"cloud-branch", "workspace-to-model", "model-to-workspace"}:
                problems.append("Yi盘 cloud models must remain a separate bidirectional branch")
        continuity_path = next((element for element in root.iter() if element.get("id") == "continuity-loop"), None)
        if continuity_path is not None and (
            local_name(continuity_path.tag) != "path" or not continuity_path.get("marker-end")
        ):
            problems.append("Yi盘 continuity return must remain a visible directional path")
        elif continuity_path is not None and (
            continuity_path.get("d") != "M422 268H199C189 268 181 260 181 250V194"
            or continuity_path.get("stroke-dashoffset") != "-12"
        ):
            problems.append(
                "Yi盘 continuity return must run horizontally to the arrow axis, then turn vertically upward"
            )

    if path.name in {"badge-yipan.svg", "badge-feedback.svg"}:
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
        if dark_name == "yipan-flow-dark.svg":
            dark_by_id = {element.get("id"): element for element in dark_root.iter() if element.get("id")}
            light_by_id = {element.get("id"): element for element in light_root.iter() if element.get("id")}
            geometry_attributes = (
                "class",
                "d",
                "x",
                "y",
                "width",
                "height",
                "cx",
                "cy",
                "r",
                "stroke-dashoffset",
            )
            structural_ids = (
                "main-loop",
                "context-to-workspace",
                "workspace-to-output",
                "continuity-loop",
                "cloud-branch",
                "workspace-to-model",
                "model-to-workspace",
                "packet-continuity",
                "activity-context-return",
            )
            for element_id in structural_ids:
                dark_element = dark_by_id.get(element_id)
                light_element = light_by_id.get(element_id)
                if dark_element is None or light_element is None:
                    continue
                dark_geometry = tuple(dark_element.get(attribute) for attribute in geometry_attributes)
                light_geometry = tuple(light_element.get(attribute) for attribute in geometry_attributes)
                if local_name(dark_element.tag) != local_name(light_element.tag) or dark_geometry != light_geometry:
                    failed = True
                    print(f"FAIL {dark_name} / {light_name}")
                    print(f"  - mismatched continuity geometry for {element_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
