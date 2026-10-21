"""Shared boundaries for the one generated npm paragraph in README.md."""

START = "<!-- npm-snapshot:start -->"
END = "<!-- npm-snapshot:end -->"


def split_snapshot(readme: str) -> tuple[str, str, str]:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one npm snapshot marker pair")
    before, rest = readme.split(START)
    if END not in rest:
        raise ValueError("npm snapshot markers are reversed")
    body, after = rest.split(END)
    return before, body, after


def format_snapshot(stats: dict) -> str:
    return (
        f"\nnpm 每日快照：近 30 天下载 **{stats['downloads_last_month']:,}** · "
        f"最新版 **v{stats['latest']}** · 已发布 **{stats['version_count']}** 个版本。\n"
        f"下载统计截至 **{stats['downloads_end']}** · "
        "[刷新结果](https://github.com/rongyishuaige7/rongyishuaige7/actions/workflows/refresh-npm-card.yml)\n"
    )


def replace_snapshot(readme: str, stats: dict) -> str:
    before, _, after = split_snapshot(readme)
    return before + START + format_snapshot(stats) + END + after
