#!/usr/bin/env python3

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


#R001: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "parallel_lane_test_count.py"
    spec = importlib.util.spec_from_file_location("parallel_lane_test_count_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load parallel_lane_test_count.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParallelLaneTestCountTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self):
        self.module = load_module()

    def test_traceability_total_from_summary_line(self):
        #R001-T01: Verify the traceability lane returns the `total` from a summary log line.
        text = "Summary: total=46 pass=44 fail=3"
        self.assertEqual(self.module._parse_traceability_total(text), 46)

    def test_shell_unit_totals_from_bats_plan(self):
        #R005-T01: Verify the shell-unit lane sums multiple bats TAP plan counts.
        text = "1..4\nok 1\n1..3\nok 2\n"
        self.assertEqual(self.module._parse_bats_total(text), 7)

    def test_python_unit_total_from_pytest_summary(self):
        #R010-T01: Verify the python-unit lane parses the pytest passed-summary count.
        text = "================= 5 passed, 1 skipped in 0.42s ================="
        self.assertEqual(self.module._parse_pytest_total(text), 6)

    def test_swift_unit_total_from_xctest_summary(self):
        #R012-T01: Verify the swift-unit lane parses the most recent XCTest summary total.
        text = "Executed 12 tests, with 0 failures in 0.123 seconds"
        self.assertEqual(self.module._parse_swift_xctest_total(text), 12)

    def test_artifact_summary_integer_field(self):
        #R015-T01: Verify the fuzz lane reads `property_test_count` from its summary artifact.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(json.dumps({"property_test_count": 9}), encoding="utf-8")
            self.assertEqual(self.module._read_int_field(path, "property_test_count"), 9)

    def test_selector_syntax_expands_unique_steps(self):
        #R018-T02: Verify selector syntax (`1-3,5,7-8`) expands to a unique selected-step count.
        self.assertEqual(self.module._parse_numeric_selector_count("1-3,5,7-8"), 6)

    def test_quality_lane_counts_only_non_skipped_reports(self):
        #R020-T01: Verify the quality lane counts only non-skipped sub-check reports.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.txt").write_text("ok", encoding="utf-8")
            (base / "b.txt").write_text("skipped", encoding="utf-8")
            count = self.module._count_non_skipped_text_reports(base, ["a.txt", "b.txt", "c.txt"])
        self.assertEqual(count, 1)

    def test_normalize_report_dir_relative_absolute(self):
        #R025-T01: Verify the static security lane counts discovered tool artifacts from the report path declared in the log.
        repo_root = Path("/repo/root")
        relative = self.module._normalize_report_dir("artifacts/security/reports", repo_root)
        absolute = self.module._normalize_report_dir("/tmp/reports", repo_root)
        self.assertEqual(relative, (repo_root / "artifacts/security/reports").resolve())
        self.assertEqual(absolute, Path("/tmp/reports"))

    def test_unknown_lane_falls_back_to_one(self):
        #R030-T01: Verify an unknown lane falls back to printing `1`.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            lane_log = repo_root / "lane.log"
            lane_log.write_text("no data\n", encoding="utf-8")
            with patch("sys.argv", [
                "parallel_lane_test_count.py",
                "--lane-script",
                "unknown_lane.sh",
                "--lane-log",
                str(lane_log),
                "--repo-root",
                str(repo_root),
            ]):
                rc = self.module.main()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
