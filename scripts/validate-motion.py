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
# The narrow Yi盘 card lights the same nodes in the same order, without packets; the
# activity LED still flickers between the nodes it connects.
FLOW_MOBILE = Path("assets/yipan-flow-mobile.svg")
FLOW_MOBILE_STAGES = (
    ("lit-context",),
    ("io-read",),
    ("lit-workspace-in",),
    ("lit-cloud", "think-a", "think-b", "think-c"),
    ("lit-workspace-back",),
    ("io-write",),
    ("lit-output",),
    ("lit-rail", "io-sync"),
)
# The Hardware Lab strip loops its circuit story; the narrow strip tells the same story.
STRIP = Path("assets/hardware-strip-light.svg")
STRIP_MOBILE = Path("assets/hardware-strip-mobile.svg")
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
    # The drive's activity LED flickers with each packet that moves on the drive; the
    # cloud thinks while lit; "+1" rises while the output is lit.
    FLOW: ("8s", (
        ("lit-context",),
        ("packet-retrieve", "io-read"),
        ("lit-workspace-in",),
        ("packet-request",),
        ("lit-cloud", "think-a", "think-b", "think-c"),
        ("packet-result",),
        ("lit-workspace-back",),
        ("packet-generate", "io-write"),
        ("lit-output", "plus-one"),
        ("lit-rail", "packet-rail", "io-sync"),
    )),
    # Sensor pads ripple as their signals leave; the glowing tails ride with the signals;
    # the pin wave runs while the chip is lit.
    STRIP: ("6s", (
        ("pad-a", "pad-b", "pad-c", "sig-in-a", "sig-in-b", "sig-in-c", "comet-in-a", "comet-in-b", "comet-in-c"),
        ("chip-on", "pin-hi"),
        ("sig-out-a", "sig-out-b", "sig-out-c", "comet-out-a", "comet-out-b", "comet-out-c"),
        ("led-a", "led-b", "led-c"),
    )),
}
# The chip's pin-1 dot ticks once a second on the same loop, outside the story.
STRIP_AMBIENT = {"heartbeat"}
# Looping cards play a fixed number of passes, then every animation stops on the base
# frame (the complete static card) instead of moving beside the README text forever.
DSH_MOBILE = Path("assets/dsh-card-mobile.svg")
LOOP_PASSES = {FLOW: "3", FLOW_MOBILE: "3", DSH: "3", DSH_MOBILE: "3"}
# The cards' status dots and buttons (shine, ring, arrow nudge) run on the same 8s cycle
# but sit outside their stories; any other animated class must belong to a stage.
CARD_AMBIENT = {
    FLOW: {"status-pulse", "cta-shine", "cta-ring", "cta-arrow"},
}
# Accumulating classes play one pass that spans all three card passes: class n lands
# during pass n, while the named stage is lit, and stays (the record stack grows to three).
CARD_ACCUMULATE = {
    FLOW: ("lit-output", ("sheet-1", "sheet-2", "sheet-3")),
}
CARD_CYCLE_SECONDS = 8.0
# Badges: primary buttons and FACTS play three 8s passes and end on their resting frame
# (hidden, in place, or swept off a clipped badge); BUILD's cursor and TOUCH's LED are
# status lights that keep blinking.
BADGE_MOTION = {
    Path("assets/badge-studio.svg"): ({"shine", "arrow"}, "8s", "3"),
    Path("assets/badge-feedback.svg"): ({"shine", "arrow"}, "8s", "3"),
    Path("assets/badge-product-facts.svg"): ({"packet"}, "8s", "3"),
    Path("assets/badge-build-log.svg"): ({"cursor"}, "1.1s", "infinite"),
    Path("assets/badge-hardware.svg"): ({"led-lit"}, "6s", "infinite"),
}
# The hero plays once and holds its final frame (WCAG 2.2.2: motion that starts
# on its own must end within 5 seconds). Classes start in this order: the three
# entry cards, then the drive shine, the DSH capture pan, and the photo deck.
HERO_ORDER = ("entry-carry", "entry-see", "entry-touch", "drive-shine", "shot-pan", "deck-1", "deck-2", "deck-3")
ONE_SHOT_BUDGET_SECONDS = 5.0
# Functional DSH stages may overlap at their edges, but their first starts must
# follow this causal order. npm figures and persistent feature captions never move.
DSH_PHASES = (
    ("record-a", "record-b", "record-c"),
    ("packet-a", "packet-b", "packet-c"),
    ("project-a", "project-b", "project-c"),
    ("usage-a", "usage-b", "usage-c"),
    ("lane-a", "lane-b", "lane-c"),
    ("timeline-scan",),
    ("cta-arrow", "cta-underline"),
)
DSH_TRANSIENT = {"packet-a", "packet-b", "packet-c", "timeline-scan"}
DSH_MOBILE_CLASSES = {"packet-a", "lane-a", "lane-b", "lane-c"}
# The scan lights every bar and lane it crosses (transient marks, one class each). The
# downloads odometer has one class per digit place; the figure uses the low places only.
DSH_SCAN_MARK = re.compile(r"mark-(?P<kind>bar|lane)-\d+")
DSH_ODOMETER = re.compile(r"odo-(?P<place>\d+)")
# Base styles are the final frame, so reduced motion shows what the animation
# ends on. The drive shine is the exception: it starts and ends outside the
# clipped drive face, so its final frame is invisible either way.
HERO_OFFSTAGE_END = frozenset({"drive-shine"})
HERO_ANIMATION = re.compile(r"\.(?P<class>[\w-]+)\s*\{\s*animation:\s*(?P<value>[^;]+);")
FINAL_KEYFRAME = re.compile(r"(?:^|[\s}])(?:to|100%)\s*\{(?P<body>[^}]*)\}")
# Keyframes may only move compositor-friendly properties. The one exception is a dash
# offset on a pre-dashed stroke, which draws the strip's signal tails along their traces.
ANIMATED_PROPERTIES = {"transform", "opacity"}
# A keyframe may set the easing of its own segment; that is not an animated property.
KEYFRAME_EASING = "animation-timing-function"
DASH_KEYFRAMES = {
    "hardware-strip-": re.compile(r"comet-(?:in|out)-[abc]"),
}
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


def check_properties(path: Path, text: str) -> list[str]:
    """Keyframes animate transform/opacity; dash offsets only on named, dashed strokes."""
    problems: list[str] = []
    dash = next((pattern for prefix, pattern in DASH_KEYFRAMES.items() if path.name.startswith(prefix)), None)
    dashed_keyframes: set[str] = set()
    for match in KEYFRAME.finditer(text):
        name, body = match.group("name"), match.group("body")
        allowed = ANIMATED_PROPERTIES | {KEYFRAME_EASING}
        if dash and dash.fullmatch(name):
            allowed.add("stroke-dashoffset")
            dashed_keyframes.add(name)
        extra = set(re.findall(r"([\w-]+)\s*:", body)) - allowed
        if extra:
            problems.append(f"{path.name}: {name} animates {', '.join(sorted(extra))}; only transform/opacity may move")
    if dashed_keyframes:
        animated = {class_name for class_name, keyframe in ANIMATION.findall(text) if keyframe in dashed_keyframes}
        root = ET.fromstring(text)
        parents = {child: parent for parent in root.iter() for child in parent}
        for element in root.iter():
            if not set(element.get("class", "").split()) & animated:
                continue
            node, dashed = element, False
            while node is not None and not dashed:
                dashed = bool(node.get("stroke-dasharray"))
                node = parents.get(node)
            if not dashed:
                problems.append(f"{path.name}: {element.get('class')} moves a dash offset on an undashed stroke")
    return problems


def check_ambient(path: Path, text: str, stages: tuple[tuple[str, ...], ...], ambient: set[str]) -> list[str]:
    story = {name for stage in stages for name in stage}
    return [
        f"{path.name}: {class_name} is animated outside its story"
        for class_name in sorted(set(dict(ANIMATION.findall(text))) - story - ambient)
    ]


def seconds(token: str) -> float:
    return float(token[:-2]) / 1000 if token.endswith("ms") else float(token[:-1])


def check_once(path: Path, text: str, order: tuple[str, ...], offstage_end: frozenset[str] = frozenset()) -> list[str]:
    """One-shot motion: each class plays once in order, ends within the budget and holds its final frame."""
    problems: list[str] = []
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    if set(declarations) != set(order):
        problems.append(
            f"{path.name}: animated classes must be exactly {', '.join(order)}; found {', '.join(sorted(declarations))}"
        )
    previous_delay = -1.0
    for class_name in order:
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
        if delay + duration > ONE_SHOT_BUDGET_SECONDS:
            problems.append(f"{path.name}: {class_name} ends at {delay + duration:g}s, after {ONE_SHOT_BUDGET_SECONDS:g}s")
        if delay < previous_delay:
            problems.append(f"{path.name}: {class_name} starts before the previous stage")
        previous_delay = delay
        if class_name in offstage_end:
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
    """Every animation plays `passes` cycles, or once across all of them, then stops."""
    problems: list[str] = []
    for match in HERO_ANIMATION.finditer(text):
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", match.group("value")).split()
        durations = [seconds(token) for token in tokens if re.fullmatch(r"\d+(?:\.\d+)?m?s", token)]
        spans_all = "1" in tokens and durations[:1] == [int(passes) * CARD_CYCLE_SECONDS]
        if "infinite" in tokens or not (passes in tokens or spans_all):
            problems.append(f"{path.name}: {match.group('class')} must play {passes} passes, then stop")
    return problems


def check_accumulate(path: Path, text: str, stage: str, classes: tuple[str, ...], passes: int) -> list[str]:
    problems: list[str] = []
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    lit = visible_intervals(keyframes.get(dict(ANIMATION.findall(text)).get(stage, ""), ""))
    if not lit:
        return [f"{path.name}: {stage} must light before anything accumulates on it"]
    for number, class_name in enumerate(classes):
        value = declarations.get(class_name)
        if value is None:
            problems.append(f"{path.name}: missing animation for {class_name}")
            continue
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", value).split()
        if f"{passes * CARD_CYCLE_SECONDS:g}s" not in tokens or "1" not in tokens:
            problems.append(f"{path.name}: {class_name} must play once across all {passes} passes")
        body = keyframes.get(tokens[0], "")
        final = FINAL_KEYFRAME.search(body)
        final_body = final.group("body") if final else ""
        opacity = re.search(r"opacity:\s*([0-9.]+)", final_body)
        transform = re.search(r"transform:\s*([^;]+)", final_body)
        if final is None or opacity is None or float(opacity.group(1)) != 1 or (
            transform is not None and any(float(n) != 0 for n in re.findall(r"-?\d+(?:\.\d+)?", transform.group(1)))
        ):
            problems.append(f"{path.name}: {class_name} must stay in place once it lands")
        intervals = visible_intervals(body)
        if not intervals:
            problems.append(f"{path.name}: {class_name} never becomes visible")
            continue
        landing = intervals[0][0] * passes
        if int(landing // 100) != number or not lit[0][0] <= landing % 100 <= lit[-1][1]:
            problems.append(f"{path.name}: {class_name} must land in pass {number + 1} while {stage} is lit")
    return problems


def keyframe_for(declarations: dict[str, str], class_name: str) -> str:
    return re.sub(r"cubic-bezier\([^)]*\)", "", declarations[class_name]).split()[0]


def check_scan_marks(path: Path, root: ET.Element, keyframes: dict[str, str], declarations: dict[str, str], marks: set[str]) -> list[str]:
    """Each mark lights while the scan is visible, and bars and lanes light left to right."""
    problems: list[str] = []
    scan = visible_intervals(keyframes.get(keyframe_for(declarations, "timeline-scan"), "")) if "timeline-scan" in declarations else []
    if not scan:
        return [f"{path.name}: scan marks need a visible timeline scan"]
    lit: dict[str, list[tuple[float, float, str]]] = {"bar": [], "lane": []}
    for element in root.iter():
        for class_name in set(element.get("class", "").split()) & marks:
            intervals = visible_intervals(keyframes.get(keyframe_for(declarations, class_name), ""))
            if not intervals or not scan[0][0] <= intervals[0][0] <= scan[-1][1]:
                problems.append(f"{path.name}: {class_name} must light while the scan crosses the timeline")
                continue
            lit[DSH_SCAN_MARK.fullmatch(class_name).group("kind")].append((float(element.get("x", "0")), intervals[0][0], class_name))
    for kind, entries in lit.items():
        starts = [start for _, start, _ in sorted(entries)]
        if starts != sorted(starts):
            problems.append(f"{path.name}: scan {kind} marks must light left to right")
    return problems


def check_odometer(path: Path, root: ET.Element, keyframes: dict[str, str], declarations: dict[str, str], odometer: set[str]) -> list[str]:
    """Odometer columns sit in the downloads figure and land on the digit they start on."""
    problems: list[str] = []
    downloads = next((element for element in root.iter() if element.get("id") == "npm-downloads"), None)
    inside = set(downloads.iter()) if downloads is not None else set()
    for element in root.iter():
        for class_name in set(element.get("class", "").split()) & odometer:
            if element not in inside:
                problems.append(f"{path.name}: {class_name} may only roll the downloads figure")
                continue
            rows = [(float(row.get("y", "0")), (row.text or "").strip()) for row in element]
            shifts = [abs(float(value)) for value in re.findall(r"translateY\((-?[\d.]+)px\)", keyframes.get(keyframe_for(declarations, class_name), ""))]
            landing = rows[0][0] + max(shifts, default=0) if rows else None
            if not shifts or (landing, rows[0][1]) not in rows:
                problems.append(f"{path.name}: {class_name} must land on the digit it shows at rest")
    return problems


def check_badge(path: Path, text: str, classes: set[str], duration: str, count: str) -> list[str]:
    problems = check_properties(path, text)
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    if set(declarations) != classes:
        problems.append(f"{path.name}: animated classes must be exactly {', '.join(sorted(classes))}")
    root = ET.fromstring(text)
    parents = {child: parent for parent in root.iter() for child in parent}
    for class_name, value in declarations.items():
        tokens = re.sub(r"(?:cubic-bezier|steps)\([^)]*\)", "", value).split()
        if duration not in tokens or count not in tokens:
            problems.append(f"{path.name}: {class_name} must play {count} x {duration}")
        if count == "infinite" or tokens[0] not in keyframes:
            continue
        final = FINAL_KEYFRAME.search(keyframes[tokens[0]])
        final_body = final.group("body") if final else ""
        opacity = re.search(r"opacity:\s*([0-9.]+)", final_body)
        transform = re.search(r"transform:\s*([^;]+)", final_body)
        hidden = opacity is not None and float(opacity.group(1)) == 0
        in_place = transform is None or not any(float(n) != 0 for n in re.findall(r"-?\d+(?:\.\d+)?", transform.group(1)))
        clipped = False
        for element in root.iter():
            if class_name in element.get("class", "").split():
                node = parents.get(element)
                while node is not None and not clipped:
                    clipped = bool(node.get("clip-path"))
                    node = parents.get(node)
        if final is None or not (hidden or in_place or clipped):
            problems.append(f"{path.name}: {class_name} must end hidden, in place or off its clipped badge")
    return problems


def check_dsh(path: Path, text: str, *, mobile: bool = False) -> list[str]:
    problems: list[str] = []
    keyframes = {match.group("name"): match.group("body") for match in KEYFRAME.finditer(text)}
    declarations = {match.group("class"): match.group("value") for match in HERO_ANIMATION.finditer(text)}
    expected = {name for phase in DSH_PHASES for name in phase}
    marks = {name for name in declarations if DSH_SCAN_MARK.fullmatch(name)}
    odometer = {name for name in declarations if DSH_ODOMETER.fullmatch(name)}
    if set(declarations) - marks - odometer != expected or not marks or not odometer:
        problems.append(f"{path.name}: DSH motion must cover its functional story, scan marks, odometer and CTA only")
    for class_name, value in declarations.items():
        tokens = re.sub(r"cubic-bezier\([^)]*\)", "", value).split()
        name = tokens[0]
        if name not in keyframes:
            problems.append(f"{path.name}: {class_name} needs defined keyframes")
            continue
        if "8s" not in tokens:
            problems.append(f"{path.name}: {class_name} must use the shared 8s cycle")
        body = keyframes[name]
        # Passes join seamlessly and the card stops on its base frame: transient
        # packets and the scan end hidden, everything else ends complete and in place.
        final = FINAL_KEYFRAME.search(body)
        final_body = final.group("body") if final else ""
        opacity = re.search(r"opacity:\s*([0-9.]+)", final_body)
        transform = re.search(r"transform:\s*([^;]+)", final_body)
        if class_name in DSH_TRANSIENT | marks:
            if final is None or opacity is None or float(opacity.group(1)) != 0:
                problems.append(f"{path.name}: {name} must end hidden")
        elif final is None or (opacity is not None and float(opacity.group(1)) != 1) or (
            transform is not None and any(float(number) != 0 for number in re.findall(r"-?\d+(?:\.\d+)?", transform.group(1)))
        ):
            problems.append(f"{path.name}: {name} must end on the complete base frame")
        properties = set(re.findall(r"([\w-]+)\s*:", body))
        if properties - ANIMATED_PROPERTIES - {KEYFRAME_EASING}:
            problems.append(f"{path.name}: {name} must animate transform/opacity only")
    root = ET.fromstring(text)
    used = {name for element in root.iter() for name in element.get("class", "").split()} & set(declarations)
    places = sorted(int(DSH_ODOMETER.fullmatch(name).group("place")) for name in used & odometer)
    if used - odometer != (DSH_MOBILE_CLASSES if mobile else expected | marks) or places != list(range(len(places))) or not places:
        problems.append(f"{path.name}: DSH illustration is missing an animated stage")
    problems.extend(check_odometer(path, root, keyframes, declarations, odometer))
    if not mobile:
        problems.extend(check_scan_marks(path, root, keyframes, declarations, marks))
    for element in root.iter():
        if element.get("id") in {"card-copy", "card-tags", "card-metrics", "npm-as-of", "flow-caption", "view-1", "view-2", "view-3", "view-4"}:
            # Only the downloads odometer may move among the metrics.
            if any(set(child.get("class", "").split()) & (set(declarations) - odometer) for child in element.iter()):
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
        problems.extend(check_properties(light, light_text))
        if light == HERO:
            problems.extend(check_once(light, light_text, HERO_ORDER, HERO_OFFSTAGE_END))
            continue
        if light == DSH:
            problems.extend(check_dsh(light, light_text))
            continue
        cycle, stages = STORIES[light]
        problems.extend(check_story(light, light_text, cycle, stages))

    problems.extend(check_dsh(DSH_MOBILE, DSH_MOBILE.read_text(encoding="utf-8"), mobile=True))
    flow_mobile = FLOW_MOBILE.read_text(encoding="utf-8")
    problems.extend(check_story(FLOW_MOBILE, flow_mobile, "8s", FLOW_MOBILE_STAGES))
    for card, passes in LOOP_PASSES.items():
        problems.extend(check_passes(card, card.read_text(encoding="utf-8"), passes))
    for narrow in (HERO_MOBILE, FLOW_MOBILE, DSH_MOBILE, STRIP_MOBILE):
        problems.extend(check_properties(narrow, narrow.read_text(encoding="utf-8")))
    problems.extend(check_once(HERO_MOBILE, HERO_MOBILE.read_text(encoding="utf-8"), HERO_ORDER, HERO_OFFSTAGE_END))
    strip_mobile = STRIP_MOBILE.read_text(encoding="utf-8")
    problems.extend(check_story(STRIP_MOBILE, strip_mobile, *STORIES[STRIP]))
    for strip in (STRIP, STRIP_MOBILE):
        problems.extend(check_ambient(strip, strip.read_text(encoding="utf-8"), STORIES[STRIP][1], STRIP_AMBIENT))
    strip_css = re.search(r"<style>(.*?)</style>", STRIP.read_text(encoding="utf-8"), re.DOTALL)
    for timing in re.findall(r"\.[\w-]+\s*\{\s*animation:[^;]+;", strip_css.group(1) if strip_css else ""):
        if timing not in strip_mobile:
            problems.append(f"{STRIP_MOBILE.name} must keep the desktop strip timing: {timing}")
    # The narrow Yi盘 card shares the desktop CSS, so the desktop loop, ambient and accumulating rules apply.
    for card, rules in ((FLOW, FLOW), (FLOW_MOBILE, FLOW)):
        card_text = card.read_text(encoding="utf-8")
        stage, accumulate = CARD_ACCUMULATE[rules]
        problems.extend(check_accumulate(card, card_text, stage, accumulate, int(LOOP_PASSES[card])))
        loops = dict(re.findall(r"\.([\w-]+)\s*\{\s*animation:\s*[\w-]+\s+([\d.]+m?s)", card_text))
        if {duration for class_name, duration in loops.items() if class_name not in accumulate} != {"8s"}:
            problems.append(f"{card.name} does not use one 8s loop like the homepage")
        problems.extend(check_ambient(card, card_text, STORIES[rules][1], CARD_AMBIENT[rules] | set(accumulate)))
    for badge, (classes, duration, count) in BADGE_MOTION.items():
        problems.extend(check_badge(badge, badge.read_text(encoding="utf-8"), classes, duration, count))
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
    print("Hero motion ends within 5s; Yi盘 and DSH play three causal passes, the Yi盘 record stack grows once per pass; the DSH scan lights its marks and the downloads odometer lands on the real figure; hardware keeps its causal loop story with tails on dashed traces only; badges rest between passes or blink as status lights. Static image sources provide reduced-motion fallbacks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
