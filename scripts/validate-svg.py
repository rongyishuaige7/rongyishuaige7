#!/usr/bin/env python3
"""Validate local SVG assets without rendering or network access."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"script", "foreignObject", "iframe", "image", "use"}
FORBIDDEN_VALUE = re.compile(r"(?:javascript:|data:|https?://)", re.IGNORECASE)


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


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
    if not root.get("aria-labelledby"):
        problems.append("missing aria-labelledby")

    title = root.find(f"{SVG_NAMESPACE}title")
    description = root.find(f"{SVG_NAMESPACE}desc")
    if title is None or not "".join(title.itertext()).strip():
        problems.append("missing non-empty title")
    if description is None or not "".join(description.itertext()).strip():
        problems.append("missing non-empty description")

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

    return problems


def main() -> int:
    assets = sorted(Path("assets").glob("*.svg"))
    if not assets:
        print("No SVG assets found.", file=sys.stderr)
        return 1

    failed = False
    for asset in assets:
        problems = validate(asset)
        if problems:
            failed = True
            print(f"FAIL {asset}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"OK   {asset}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
