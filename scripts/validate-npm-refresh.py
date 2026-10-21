#!/usr/bin/env python3
"""Restrict the bot to generated npm files and the README's marked snapshot."""

from pathlib import Path
import subprocess
import sys

from npm_snapshot import split_snapshot

ALLOWED = {
    "data/npm-stats.json", "assets/dsh-card-dark.svg", "assets/dsh-card-light.svg",
    "assets/dsh-card-still.svg", "assets/dsh-card-mobile.svg", "assets/dsh-card-mobile-still.svg", "README.md",
}


def validate_changes(changed: set[str], base_readme: str, current_readme: str) -> list[str]:
    problems = [f"unexpected refresh output: {path}" for path in sorted(changed - ALLOWED)]
    if "README.md" in changed:
        try:
            before, _, after = split_snapshot(base_readme)
            current_before, _, current_after = split_snapshot(current_readme)
        except ValueError as error:
            problems.append(str(error))
        else:
            if (before, after) != (current_before, current_after):
                problems.append("refresh changed README outside the npm snapshot markers")
    return problems


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def main() -> int:
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(path.decode("utf-8") for path in git(*args).split(b"\0") if path)
    problems = validate_changes(changed, git("show", "HEAD:README.md").decode("utf-8"), Path("README.md").read_text())
    if problems:
        print("npm refresh boundary failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print(f"npm refresh stayed within its generated files ({len(changed)} changed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
