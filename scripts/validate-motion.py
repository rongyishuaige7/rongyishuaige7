#!/usr/bin/env python3
"""Validate that local SVG motion tells sequential, compositor-only stories."""

from pathlib import Path
import re
import sys


FLOW = Path("assets/yipan-flow-light.svg")
HERO = Path("assets/hero-light.svg")
STRIP = Path("assets/hardware-strip-light.svg")
PAIR = {
    FLOW: Path("assets/yipan-flow-dark.svg"),
    HERO: Path("assets/hero-dark.svg"),
    STRIP: Path("assets/hardware-strip-dark.svg"),
}
# Each story is a list of stages that share one cycle. Classes inside a stage
# run together (three traces, three LEDs); a stage may not start before the
# previous stage has nearly finished, so the cause always precedes the effect.
STORIES = {
    FLOW: ("8.4s", (
        ("packet-context",),
        ("activity-workspace-in",),
        ("packet-model-out",),
        ("activity-model",),
        ("packet-model-back",),
        ("activity-workspace-back",),
        ("packet-output",),
        ("activity-output",),
        ("packet-continuity",),
        ("activity-context-return",),
    )),
    HERO: ("7.2s", (
        ("core-pulse",),
        ("packet-see",),
        ("activity-see",),
        ("packet-touch",),
        ("pulse-a", "pulse-b", "pulse-c"),
        ("lit-a", "lit-b", "lit-c"),
    )),
    STRIP: ("6s", (
        ("sig-in-a", "sig-in-b", "sig-in-c"),
        ("chip-on",),
        ("sig-out-a", "sig-out-b", "sig-out-c"),
        ("led-a", "led-b", "led-c"),
    )),
}
FORBIDDEN_ANIMATED_PROPERTIES = re.compile(
    r"(?:^|[;{])\s*(?:width|height|x|y|top|left|right|bottom|filter|stroke-width)\s*:",
    re.MULTILINE,
)
ANIMATION = re.compile(r"\.(?P<class>[\w-]+)\s*\{\s*animation:\s*(?P<keyframe>[\w-]+)")
KEYFRAME = re.compile(r"@keyframes\s+(?P<name>[\w-]+)\s*\{(?P<body>.*?)\n\s*\}", re.DOTALL)


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


def check_story(path: Path, text: str, cycle: str, stages: tuple[tuple[str, ...], ...]) -> list[str]:
    problems: list[str] = []
    animation = dict(ANIMATION.findall(text))
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    for class_name, keyframe in animation.items():
        if keyframe not in keyframes:
            problems.append(f"{path.name}: {class_name} uses undefined keyframes {keyframe}")

    previous_end = -1.0
    for stage in stages:
        starts: list[float] = []
        ends: list[float] = []
        for class_name in stage:
            keyframe = animation.get(class_name)
            if not keyframe or keyframe not in keyframes:
                problems.append(f"{path.name}: missing animation for {class_name}")
                continue
            if not re.search(
                rf"\.{re.escape(class_name)}\s*\{{\s*animation:\s*[^;]*\b{re.escape(cycle)}\b",
                text,
            ):
                problems.append(f"{path.name}: {class_name} does not use the shared {cycle} cycle")
            intervals = visible_intervals(keyframes[keyframe])
            if not intervals:
                problems.append(f"{path.name}: {class_name} never becomes visible")
                continue
            starts.append(intervals[0][0])
            ends.append(intervals[0][1])
        if not starts:
            continue
        start = min(starts)
        if start < previous_end - 3:
            problems.append(
                f"{path.name}: {' / '.join(stage)} overlaps the previous causal stage too heavily "
                f"({start}% < {previous_end}%)"
            )
        previous_end = max(ends)
    return problems


def main() -> int:
    problems: list[str] = []

    for light, dark in PAIR.items():
        light_text = light.read_text(encoding="utf-8")
        dark_text = dark.read_text(encoding="utf-8")
        light_css = re.search(r"<style>(.*?)</style>", light_text, re.DOTALL)
        dark_css = re.search(r"<style>(.*?)</style>", dark_text, re.DOTALL)
        if not light_css or not dark_css or light_css.group(1) != dark_css.group(1):
            problems.append(f"{light.name} and {dark.name} do not share identical motion CSS")
        if light_css and FORBIDDEN_ANIMATED_PROPERTIES.search(light_css.group(1)):
            problems.append(f"{light.name} animates a property other than transform or opacity")
        cycle, stages = STORIES[light]
        problems.extend(check_story(light, light_text, cycle, stages))

    flow = FLOW.read_text(encoding="utf-8")
    hero = HERO.read_text(encoding="utf-8")
    if "8.4s" not in flow or "6.8s" in flow:
        problems.append("flow does not use one 8.4s continuity cycle")
    if "CLOUD MODELS" in hero or ">AGENT<" in hero or ">CONTEXT<" in hero:
        problems.append("hero still duplicates the cloud-agent workflow semantics")
    for text in ("随身", "看得见", "摸得着", "PORTABLE CONTEXT"):
        if text not in hero:
            problems.append(f"hero is missing a studio lane: {text}")

    if problems:
        print("Motion contract validation failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print("Hero studio map, hardware strip, and the 8.4s continuity loop each tell one sequential story.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
