#!/usr/bin/env python3
"""Validate that local SVG motion tells one sequential, compositor-only story."""

from pathlib import Path
import re
import sys


FLOW = Path("assets/yipan-flow-light.svg")
HERO = Path("assets/hero-light.svg")
PAIR = {
    FLOW: Path("assets/yipan-flow-dark.svg"),
    HERO: Path("assets/hero-dark.svg"),
}
FORBIDDEN_ANIMATED_PROPERTIES = re.compile(
    r"(?:^|[;{])\s*(?:width|height|x|y|top|left|right|bottom|filter|stroke-width)\s*:",
    re.MULTILINE,
)
ANIMATION = re.compile(r"\.(?P<class>[\w-]+)\s*\{\s*animation:\s*(?P<keyframe>[\w-]+)")
KEYFRAME = re.compile(r"@keyframes\s+(?P<name>[\w-]+)\s*\{(?P<body>.*?)\n\s*\}", re.DOTALL)
PERCENT = re.compile(r"(?P<points>(?:\d+(?:\.\d+)?%\s*,?\s*)+)\{")


def visible_intervals(body: str) -> list[tuple[float, float]]:
    """Return coarse intervals whose declared opacity is non-zero."""
    declarations: list[tuple[float, float]] = []
    blocks = list(re.finditer(r"(?P<points>(?:\d+(?:\.\d+)?%\s*,?\s*)+)\{(?P<body>[^}]*)\}", body))
    for block in blocks:
        opacity = re.search(r"opacity:\s*([0-9.]+)", block.group("body"))
        if not opacity:
            continue
        value = float(opacity.group(1))
        for point in re.findall(r"\d+(?:\.\d+)?", block.group("points")):
            declarations.append((float(point), value))
    declarations.sort()
    intervals: list[tuple[float, float]] = []
    for (start, value), (end, _) in zip(declarations, declarations[1:]):
        if value > 0:
            intervals.append((start, end))
    return intervals


def main() -> int:
    problems: list[str] = []
    flow = FLOW.read_text(encoding="utf-8")
    hero = HERO.read_text(encoding="utf-8")

    for light, dark in PAIR.items():
        light_text = light.read_text(encoding="utf-8")
        dark_text = dark.read_text(encoding="utf-8")
        light_css = re.search(r"<style>(.*?)</style>", light_text, re.DOTALL)
        dark_css = re.search(r"<style>(.*?)</style>", dark_text, re.DOTALL)
        if not light_css or not dark_css or light_css.group(1) != dark_css.group(1):
            problems.append(f"{light.name} and {dark.name} do not share identical motion CSS")
        if light_css and FORBIDDEN_ANIMATED_PROPERTIES.search(light_css.group(1)):
            problems.append(f"{light.name} animates a property other than transform or opacity")

    required_flow = (
        "packet-context",
        "activity-workspace-in",
        "packet-model-out",
        "activity-model",
        "packet-model-back",
        "activity-workspace-back",
        "packet-output",
        "activity-output",
    )
    flow_animation = dict(ANIMATION.findall(flow))
    flow_keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(flow)}
    previous_end = -1.0
    for class_name in required_flow:
        keyframe = flow_animation.get(class_name)
        if not keyframe or keyframe not in flow_keyframes:
            problems.append(f"missing flow animation for {class_name}")
            continue
        intervals = visible_intervals(flow_keyframes[keyframe])
        if not intervals:
            problems.append(f"{class_name} never becomes visible")
            continue
        start, end = intervals[0]
        if start < previous_end - 3:
            problems.append(f"{class_name} overlaps the previous causal stage too heavily ({start}% < {previous_end}%)")
        previous_end = end

    if "6.8s" not in flow:
        problems.append("flow does not use one 6.8s task cycle")
    if "CLOUD MODELS" in hero or ">AGENT<" in hero or ">CONTEXT<" in hero:
        problems.append("hero still duplicates the cloud-agent workflow semantics")
    for text in ("DESKTOP", "PORTABLE CONTEXT", "ANOTHER COMPUTER"):
        if text not in hero:
            problems.append(f"hero is missing portable-value stage: {text}")

    if problems:
        print("Motion contract validation failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print("Hero portability narrative and the sequential 6.8s task cycle are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
