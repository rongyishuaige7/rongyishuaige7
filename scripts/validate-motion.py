#!/usr/bin/env python3
"""Validate that local SVG motion tells sequential, compositor-only stories."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


FLOW = Path("assets/yipan-flow-light.svg")
HERO = Path("assets/hero-light.svg")
# Narrow screens get a stacked hero that plays the same one-shot story.
HERO_MOBILE = Path("assets/hero-mobile.svg")
# The narrow Yi盘 card lights the same nodes in the same order, without packets.
FLOW_MOBILE = Path("assets/yipan-flow-mobile.svg")
FLOW_MOBILE_STAGES = (
    ("lit-context",),
    ("lit-workspace-in",),
    ("lit-cloud",),
    ("lit-workspace-back",),
    ("lit-output",),
    ("lit-rail",),
)
STRIP = Path("assets/hardware-strip-light.svg")
DSH = Path("assets/dsh-card-light.svg")
PAIR = {
    FLOW: Path("assets/yipan-flow-dark.svg"),
    DSH: Path("assets/dsh-card-dark.svg"),
    HERO: Path("assets/hero-dark.svg"),
    STRIP: Path("assets/hardware-strip-dark.svg"),
}
# Each story is a list of stages that share one cycle. Classes inside a stage
# run together (three traces, three LEDs); a stage may not start before the
# previous stage has nearly finished, so the cause always precedes the effect.
STORIES = {
    FLOW: ("8s", (
        ("lit-context",),
        ("packet-retrieve",),
        ("lit-workspace-in",),
        ("packet-request",),
        ("lit-cloud",),
        ("packet-result",),
        ("lit-workspace-back",),
        ("packet-generate",),
        ("lit-output",),
        ("lit-rail", "packet-rail"),
    )),
    STRIP: ("6s", (
        ("sig-in-a", "sig-in-b", "sig-in-c"),
        ("chip-on",),
        ("sig-out-a", "sig-out-b", "sig-out-c"),
        ("led-a", "led-b", "led-c"),
    )),
}
# Looping cards play a fixed number of passes, then every animation stops on the base
# frame (the complete static card) instead of moving beside the README text forever.
LOOP_PASSES = {FLOW: "3", FLOW_MOBILE: "3"}
# The cards' status dots and button shines run on the same 8s cycle but sit outside
# their stories; any other animated class must belong to a stage.
CARD_AMBIENT = {
    FLOW: {"status-pulse", "cta-shine"},
}
# The hero plays once and holds its final frame (WCAG 2.2.2: motion that starts
# on its own must end within 5 seconds). Classes start in this order: the three
# entry cards, then the drive shine, the DSH capture pan, and the photo deck.
HERO_ORDER = ("entry-carry", "entry-see", "entry-touch", "drive-shine", "shot-pan", "deck-1", "deck-2", "deck-3")
HERO_BUDGET_SECONDS = 5.0
# Functional DSH stages may overlap at their edges, but their first starts must
# follow this causal order. npm figures and persistent feature captions never move.
DSH_PHASES = (
    ("record-a", "record-b", "record-c"),
    ("packet-a", "packet-b", "packet-c"),
    ("project-a", "project-b", "project-c"),
    ("usage-a", "usage-b", "usage-c"),
    ("lane-a", "lane-b", "lane-c"),
    ("timeline-scan",),
    ("cta-arrow",),
)
DSH_TRANSIENT = {"packet-a", "packet-b", "packet-c", "timeline-scan"}
DSH_MOBILE_CLASSES = {"packet-a", "lane-a", "lane-b", "lane-c"}
# Base styles are the final frame, so reduced motion shows what the animation
# ends on. The drive shine is the exception: it starts and ends outside the
# clipped drive face, so its final frame is invisible either way.
HERO_OFFSTAGE_END = {"drive-shine"}
HERO_ANIMATION = re.compile(r"\.(?P<class>[\w-]+)\s*\{\s*animation:\s*(?P<value>[^;]+);")
FINAL_KEYFRAME = re.compile(r"(?:^|[\s}])(?:to|100%)\s*\{(?P<body>[^}]*)\}")
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


def seconds(token: str) -> float:
    return float(token[:-2]) / 1000 if token.endswith("ms") else float(token[:-1])


def check_hero(path: Path, text: str) -> list[str]:
    problems: list[str] = []
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    if set(declarations) != set(HERO_ORDER):
        problems.append(
            f"{path.name}: animated classes must be exactly {', '.join(HERO_ORDER)}; found {', '.join(sorted(declarations))}"
        )
    previous_delay = -1.0
    for class_name in HERO_ORDER:
        value = declarations.get(class_name)
        if value is None:
            continue
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", value).split()
        keyframe = tokens[0] if tokens else ""
        if keyframe not in keyframes:
            problems.append(f"{path.name}: {class_name} uses undefined keyframes {keyframe}")
            continue
        times = [seconds(token) for token in tokens if re.fullmatch(r"\d+(?:\.\d+)?m?s", token)]
        if len(times) != 2:
            problems.append(f"{path.name}: {class_name} must declare one duration and one delay")
            continue
        duration, delay = times
        if "infinite" in tokens or any(re.fullmatch(r"\d+(?:\.\d+)?", token) for token in tokens):
            problems.append(f"{path.name}: {class_name} must play exactly once")
        if not {"both", "forwards"} & set(tokens):
            problems.append(f"{path.name}: {class_name} must hold its final frame (fill both or forwards)")
        if delay + duration > HERO_BUDGET_SECONDS:
            problems.append(f"{path.name}: {class_name} ends at {delay + duration:g}s, after {HERO_BUDGET_SECONDS:g}s")
        if delay < previous_delay:
            problems.append(f"{path.name}: {class_name} starts before the previous hero stage")
        previous_delay = delay
        if class_name in HERO_OFFSTAGE_END:
            continue
        final = FINAL_KEYFRAME.search(keyframes[keyframe])
        body = final.group("body") if final else ""
        transform = re.search(r"transform:\s*([^;]+)", body)
        opacity = re.search(r"opacity:\s*([0-9.]+)", body)
        moved = transform is not None and any(float(number) != 0 for number in re.findall(r"-?\d+(?:\.\d+)?", transform.group(1)))
        if final is None or moved or (opacity is not None and float(opacity.group(1)) != 1):
            problems.append(f"{path.name}: {keyframe} must end on the untransformed, fully opaque base frame")
    return problems


def check_passes(path: Path, text: str, passes: str) -> list[str]:
    problems: list[str] = []
    for match in HERO_ANIMATION.finditer(text):
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", match.group("value")).split()
        if "infinite" in tokens or passes not in tokens:
            problems.append(f"{path.name}: {match.group('class')} must play {passes} passes, then stop")
    return problems


def check_dsh(path: Path, text: str, *, mobile: bool = False) -> list[str]:
    problems: list[str] = []
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    expected = {name for phase in DSH_PHASES for name in phase}
    if set(declarations) != expected:
        problems.append(f"{path.name}: DSH motion must cover its functional story and CTA only")
    for class_name, value in declarations.items():
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", value).split()
        name = tokens[0]
        if name not in keyframes:
            problems.append(f"{path.name}: {class_name} needs defined keyframes")
            continue
        if "8s" not in tokens or "infinite" not in tokens:
            problems.append(f"{path.name}: {class_name} must use the shared 8s infinite loop")
        body = keyframes[name]
        properties = set(re.findall(r"([\w-]+)\s*:", body))
        if properties - {"transform", "opacity"}:
            problems.append(f"{path.name}: {name} must animate transform/opacity only")
    root = ET.fromstring(text)
    used = {name for element in root.iter() for name in element.get("class", "").split()} & set(declarations)
    if used != (DSH_MOBILE_CLASSES if mobile else expected):
        problems.append(f"{path.name}: DSH illustration is missing an animated stage")
    for element in root.iter():
        if element.get("id") in {"card-copy", "card-tags", "card-metrics", "npm-as-of", "flow-caption", "view-1", "view-2", "view-3", "view-4"}:
            if any(set(child.get("class", "").split()) & set(declarations) for child in element.iter()):
                problems.append(f"{path.name}: {element.get('id')} must remain still and visible")
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
        if light == HERO:
            problems.extend(check_hero(light, light_text))
            continue
        if light == DSH:
            problems.extend(check_dsh(light, light_text))
            continue
        cycle, stages = STORIES[light]
        problems.extend(check_story(light, light_text, cycle, stages))

    mobile = Path("assets/dsh-card-mobile.svg")
    problems.extend(check_dsh(mobile, mobile.read_text(encoding="utf-8"), mobile=True))
    flow_mobile = FLOW_MOBILE.read_text(encoding="utf-8")
    problems.extend(check_story(FLOW_MOBILE, flow_mobile, "8s", FLOW_MOBILE_STAGES))
    for card, passes in LOOP_PASSES.items():
        problems.extend(check_passes(card, card.read_text(encoding="utf-8"), passes))
    hero_mobile = HERO_MOBILE.read_text(encoding="utf-8")
    hero_mobile_css = re.search(r"<style>(.*?)</style>", hero_mobile, re.DOTALL)
    if hero_mobile_css and FORBIDDEN_ANIMATED_PROPERTIES.search(hero_mobile_css.group(1)):
        problems.append(f"{HERO_MOBILE.name} animates a property other than transform or opacity")
    problems.extend(check_hero(HERO_MOBILE, hero_mobile))
    for card, ambient in CARD_AMBIENT.items():
        card_text = card.read_text(encoding="utf-8")
        if set(re.findall(r"animation:\s*[\w-]+\s+([\d.]+m?s)", card_text)) != {"8s"}:
            problems.append(f"{card.name} does not use one 8s loop like the homepage")
        story_classes = {name for stage in STORIES[card][1] for name in stage}
        for class_name in sorted(set(dict(ANIMATION.findall(card_text))) - story_classes - ambient):
            problems.append(f"{card.name}: {class_name} is animated outside its story")
    for path in (HERO, HERO_MOBILE):
        hero = path.read_text(encoding="utf-8")
        if "CLOUD MODELS" in hero or ">AGENT<" in hero or ">CONTEXT<" in hero:
            problems.append(f"{path.name} still duplicates the cloud-agent workflow semantics")
        for text in (">Yi盘<", ">DSH Usage<", ">Hardware Lab<"):
            if text not in hero:
                problems.append(f"{path.name} is missing a project entry card: {text.strip('<>')}")

    if problems:
        print("Motion contract validation failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print("Hero motion ends within 5s; Yi盘 plays three causal passes; DSH and hardware keep causal loop stories. Static image sources provide reduced-motion fallbacks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
