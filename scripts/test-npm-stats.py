#!/usr/bin/env python3
"""Regression checks for npm's inclusive 30-day download window; no network access."""

from contextlib import redirect_stderr
from datetime import date, timedelta
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = load_script("fetch-npm-stats")
validate = load_script("validate-svg")


class DownloadWindowTests(unittest.TestCase):
    def response(self, start: str, end: str) -> list[dict]:
        return [
            {"package": fetch.PACKAGE, "downloads": 100, "start": start, "end": end},
            {"name": fetch.PACKAGE, "dist-tags": {"latest": "0.4.3"}, "versions": {"0.4.3": {}}},
        ]

    def test_accepts_thirty_inclusive_days_across_month_and_leap_day(self):
        for start, end in (("2026-09-19", "2026-10-18"), ("2024-02-01", "2024-03-01")):
            with self.subTest(start=start), patch.object(fetch, "fetch_json", side_effect=self.response(start, end)):
                stats = fetch.collect()
                self.assertEqual(stats["downloads_last_month"], 100)
                self.assertEqual(stats["downloads_start"], start)

    def test_rejects_bad_windows_before_writing(self):
        tomorrow = date.today() + timedelta(days=1)
        windows = (
            ("2026-10-18", "2026-10-19"),  # two days
            ("2026-09-18", "2026-10-18"),  # 31 days
            ("2026-10-18", "2026-10-18"),  # one day
            ("2026-10-19", "2026-10-18"),  # reversed
            ("2026-02-30", "2026-03-29"),  # impossible calendar date
            ((tomorrow - timedelta(days=29)).isoformat(), tomorrow.isoformat()),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "npm-stats.json"
            output.write_text("existing snapshot\n")
            for start, end in windows:
                with self.subTest(start=start, end=end), patch.object(fetch, "OUTPUT", output), \
                     patch.object(fetch, "fetch_json", side_effect=self.response(start, end)), \
                     redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    fetch.main()
                self.assertNotEqual(error.exception.code, 0)
                self.assertEqual(output.read_text(), "existing snapshot\n")

    def test_checked_in_data_rejects_short_long_and_impossible_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "npm-stats.json"
            for start, end in (("2026-10-18", "2026-10-19"), ("2026-09-18", "2026-10-18"),
                               ("2026-02-30", "2026-03-29")):
                stats = {"package": fetch.PACKAGE, "downloads_last_month": 100,
                         "downloads_start": start, "downloads_end": end, "latest": "0.4.3", "version_count": 1}
                path.write_text(json.dumps(stats))
                with self.subTest(start=start), patch.object(validate, "NPM_STATS", path):
                    self.assertTrue(validate.load_npm_stats()[1])


if __name__ == "__main__":
    unittest.main()
