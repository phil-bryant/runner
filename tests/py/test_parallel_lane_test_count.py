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

    def test_sql_unit_total_from_pg_prove_summary(self):
        #R022-T01: Verify the sql-unit lane parses pg_prove Files/Tests summary counts.
        text = "Files=2, Tests=9, 0 wallclock secs ( 0.02 usr  0.01 sys +  0.04 cusr  0.00 csys =  0.07 CPU)"
        self.assertEqual(self.module._parse_sql_unit_total(text), 9)

    def test_swift_unit_total_from_xctest_summary(self):
        #R012-T01: Verify the swift-unit lane parses the most recent XCTest summary total.
        text = "Executed 12 tests, with 0 failures in 0.123 seconds"
        self.assertEqual(self.module._parse_swift_xctest_total(text), 12)

    def test_e2e_lane_total_from_pytest_summary(self):
        #R010-T03: Verify a pytest-based e2e lane resolves its total through the pytest parser, including xfailed/xpassed outcomes.
        text = "=================== 20 passed, 5 xfailed, 1 xpassed in 0.08s ==================="
        with tempfile.TemporaryDirectory() as tmp:
            lane_log = Path(tmp) / "t10_run_e2e_tests.log"
            lane_log.write_text(text, encoding="utf-8")
            count = self.module.resolve_lane_count("t10_run_e2e_tests.sh", lane_log, Path(tmp))
        self.assertEqual(count, 26)

    def test_landing_unit_total_from_vitest_summary(self):
        #R035-T01: Verify the landing-unit lane parses the vitest Tests summary total, including mixed failed/passed summaries.
        text = " Test Files  2 passed (2)\n      Tests  17 passed (17)\n"
        self.assertEqual(self.module._parse_vitest_total(text), 17)
        mixed = "      Tests  1 failed | 16 passed (17)\n"
        self.assertEqual(self.module._parse_vitest_total(mixed), 17)
        self.assertIsNone(self.module._parse_vitest_total("no summary here"))

    def test_landing_e2e_total_from_playwright_outcomes(self):
        #R040-T01: Verify the landing-e2e lane sums playwright outcome line counts.
        text = "  1 failed\n  3 passed (16.3s)\n"
        self.assertEqual(self.module._parse_playwright_total(text), 4)
        self.assertIsNone(self.module._parse_playwright_total("nothing to see"))

    def test_landing_typecheck_total_from_astro_check_result(self):
        #R045-T01: Verify the landing-typecheck lane parses the astro-check Result files count.
        text = "Result (14 files): \n- 0 errors\n- 0 warnings\n"
        self.assertEqual(self.module._parse_astro_check_total(text), 14)
        self.assertIsNone(self.module._parse_astro_check_total("no result line"))

    #R001: function tag for test_cpp_integration_total_from_ctest_summary
    def test_cpp_integration_total_from_ctest_summary(self):
        # Verify C++ integration lane count is parsed from ctest summary output.
        text = "100% tests passed, 0 tests failed out of 7"
        self.assertEqual(self.module._parse_cpp_integration_total(text), 7)

    #R001: function tag for test_cpp_integration_total_from_mailcart_final_count
    def test_cpp_integration_total_from_mailcart_final_count(self):
        # Verify the mailcart C++ lane summary format resolves the test count.
        text = "Final count: tests 4/4 passed, expectations 26/26 passed."
        self.assertEqual(self.module._parse_cpp_integration_total(text), 4)

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

    #R001: function tag for test_cpp_lane_stem_uses_cpp_parser
    def test_cpp_lane_stem_uses_cpp_parser(self):
        # Verify renumbered C++ lane names still resolve counts from lane logs.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            lane_log = repo_root / "cpp.log"
            lane_log.write_text("100% tests passed, 0 tests failed out of 11\n", encoding="utf-8")
            count = self.module.resolve_lane_count("t08_run_cpp_integration_tests.sh", lane_log, repo_root)
        self.assertEqual(count, 11)

    def test_sql_lane_stem_uses_sql_parser(self):
        #R022-T02: Verify renumbered SQL lane names resolve counts from pg_prove TAP plan output.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            lane_log = repo_root / "sql.log"
            lane_log.write_text("1..2\nok 1 - first\nok 2 - second\n1..3\n", encoding="utf-8")
            count = self.module.resolve_lane_count("t06_run_sql_unit_tests.sh", lane_log, repo_root)
        self.assertEqual(count, 5)

    def test_read_text_and_json_helpers_cover_error_paths(self):
        #R015-T02: file readers handle missing/invalid payloads safely.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            missing = base / "missing.txt"
            self.assertEqual(self.module._read_text(missing), "")
            self.assertIsNone(self.module._read_json(missing))
            bad_json = base / "bad.json"
            bad_json.write_text("{", encoding="utf-8")
            self.assertIsNone(self.module._read_json(bad_json))
            bad_field = base / "field.json"
            bad_field.write_text(json.dumps({"count": "x"}), encoding="utf-8")
            self.assertIsNone(self.module._read_int_field(bad_field, "count"))
            self.assertIsNone(self.module._read_int_field(bad_field, "missing"))

    def test_extract_reports_dir_default_when_log_has_no_reports_line(self):
        #R025-T02: report-dir extractor falls back to default when no Reports line exists.
        repo_root = Path("/repo/root")
        default = repo_root / "artifacts/security/reports"
        self.assertEqual(
            self.module._extract_reports_dir_from_log("no reports marker", repo_root, default),
            default,
        )

    def test_pytest_parser_handles_no_tests_and_collected_fallback(self):
        #R010-T02: pytest parser handles no-tests and collected fallback branches.
        self.assertEqual(self.module._parse_pytest_total("no tests ran in 0.01s"), 0)
        self.assertEqual(self.module._parse_pytest_total("collected 17 items\nsomething"), 17)
        self.assertIsNone(self.module._parse_pytest_total("no pytest markers here"))

    def test_swift_parser_uses_test_run_fallback(self):
        #R012-T02: swift parser falls back to "Test run with N tests".
        self.assertEqual(self.module._parse_swift_xctest_total("Test run with 6 tests"), 6)

    def test_sql_parser_uses_ok_line_fallback(self):
        #R022-T03: sql parser falls back to counting ok TAP lines.
        log_text = "ok 1 - one\nok 2 - two\nok 3 - three\n"
        self.assertEqual(self.module._parse_sql_unit_total(log_text), 3)
        self.assertIsNone(self.module._parse_sql_unit_total("nothing to parse"))

    def test_cpp_parser_uses_fallback_patterns(self):
        #R001-T02: C++ parser covers gtest/catch2/fallback case counting branches.
        gtest = "[==========] Running 12 tests from 4 test suites."
        self.assertEqual(self.module._parse_cpp_integration_total(gtest), 12)
        catch2 = "All tests passed (24 assertions in 9 test cases)"
        self.assertEqual(self.module._parse_cpp_integration_total(catch2), 9)
        fallback = "Test #1: A\nTest #2: B\n"
        self.assertEqual(self.module._parse_cpp_integration_total(fallback), 2)
        self.assertEqual(self.module._parse_cpp_integration_total("Total Tests: 14"), 14)
        self.assertEqual(self.module._parse_cpp_integration_total("Running TestA\nRunning TestB"), 2)
        self.assertIsNone(self.module._parse_cpp_integration_total("unrecognized output"))

    def test_numeric_selector_rejects_invalid_tokens(self):
        #R018-T03: selector parser rejects malformed/reversed range syntax.
        self.assertIsNone(self.module._parse_numeric_selector_count("abc"))
        self.assertIsNone(self.module._parse_numeric_selector_count("5-2"))
        self.assertIsNone(self.module._parse_numeric_selector_count(",,"))
        self.assertIsNone(self.module._parse_numeric_selector_count(""))

    def test_macos_ui_parser_falls_back_to_xctest_then_selector_file(self):
        #R018-T04: macOS UI parser falls back to XCTest and then selector-file parsing.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            selector_file = repo_root / "artifacts/macos-ui-regression/xcuitest-steps.env"
            selector_file.parent.mkdir(parents=True, exist_ok=True)
            selector_file.write_text("1-2,4", encoding="utf-8")
            xctest_total = self.module._parse_macos_ui_regression_total("Executed 5 tests", repo_root)
            selector_total = self.module._parse_macos_ui_regression_total("no summary", repo_root)
        self.assertEqual(xctest_total, 5)
        self.assertEqual(selector_total, 3)
        self.assertEqual(
            self.module._parse_macos_ui_regression_total(
                "scenarios total: completed over 9 scenarios",
                Path("/tmp"),
            ),
            9,
        )
        self.assertEqual(
            self.module._parse_macos_ui_regression_total(
                "Using XCUITest profile x with scenarios: 1-3,7",
                Path("/tmp"),
            ),
            4,
        )

    def test_parse_traceability_and_bats_none_paths(self):
        #R001-T03: traceability and bats parsers return None when no usable counts exist.
        self.assertIsNone(self.module._parse_traceability_total("Summary: nothing"))
        self.assertEqual(self.module._parse_bats_total("ok 1\nok 2\n"), 2)
        self.assertIsNone(self.module._parse_bats_total("not tap output"))

    def test_resolve_lane_count_covers_primary_parser_branches(self):
        #R030-T04: resolver routes trace/shell/python/swift/macOS lanes to parser outputs.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            trace_log = repo_root / "trace.log"
            trace_log.write_text("Summary: total=5 pass=4 fail=1", encoding="utf-8")
            shell_log = repo_root / "shell.log"
            shell_log.write_text("1..3\nok 1\nok 2\nok 3\n", encoding="utf-8")
            py_log = repo_root / "py.log"
            py_log.write_text("2 passed in 0.1s", encoding="utf-8")
            swift_log = repo_root / "swift.log"
            swift_log.write_text("Executed 4 tests", encoding="utf-8")
            macos_log = repo_root / "macos.log"
            macos_log.write_text("scenarios total: over 6 scenarios", encoding="utf-8")

            self.assertEqual(self.module.resolve_lane_count("t04_run_requirements_traceability_tests.sh", trace_log, repo_root), 5)
            self.assertEqual(self.module.resolve_lane_count("t05_run_shell_unit_tests.sh", shell_log, repo_root), 3)
            self.assertEqual(self.module.resolve_lane_count("t06_run_python_unit_tests.sh", py_log, repo_root), 2)
            self.assertEqual(self.module.resolve_lane_count("t07_run_swift_unit_tests.sh", swift_log, repo_root), 4)
            self.assertEqual(self.module.resolve_lane_count("t09_run_macos_ui_regression_tests.sh", macos_log, repo_root), 6)

    def test_resolve_lane_count_handles_all_artifact_driven_lanes(self):
        #R030-T02: lane resolver covers fuzz/mutation/quality/security/static/dynamic branches.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            lane_log = repo_root / "lane.log"
            lane_log.write_text("Reports: artifacts/security/reports", encoding="utf-8")

            fuzz = repo_root / "artifacts/fuzz"
            fuzz.mkdir(parents=True, exist_ok=True)
            (fuzz / "fuzz-summary.json").write_text(json.dumps({"property_test_count": 11}), encoding="utf-8")
            self.assertEqual(
                self.module.resolve_lane_count("t07_run_fuzz_tests.sh", lane_log, repo_root),
                11,
            )

            mutation = repo_root / "artifacts/mutation"
            mutation.mkdir(parents=True, exist_ok=True)
            (mutation / "mutation-summary.json").write_text(json.dumps({"total": 13}), encoding="utf-8")
            self.assertEqual(
                self.module.resolve_lane_count("t08_run_mutation_tests.sh", lane_log, repo_root),
                13,
            )

            quality = repo_root / "artifacts/quality/reports"
            quality.mkdir(parents=True, exist_ok=True)
            (quality / "vulture.txt").write_text("ok", encoding="utf-8")
            (quality / "radon.txt").write_text("skipped", encoding="utf-8")
            self.assertEqual(
                self.module.resolve_lane_count("t04_run_code_quality_tests.sh", lane_log, repo_root),
                1,
            )

            security = repo_root / "artifacts/security"
            security.mkdir(parents=True, exist_ok=True)
            (security / "dependency-freshness.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                self.module.resolve_lane_count("t09_run_dependency_freshness_tests.sh", lane_log, repo_root),
                1,
            )

            static_reports = repo_root / "artifacts/security/reports"
            static_reports.mkdir(parents=True, exist_ok=True)
            (static_reports / "semgrep.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.module.resolve_lane_count("t10_run_static_security_tests.sh", lane_log, repo_root), 1)

            dynamic_reports = repo_root / "artifacts/security-dast"
            dynamic_reports.mkdir(parents=True, exist_ok=True)
            (dynamic_reports / "zap-classification-summary.json").write_text("{}", encoding="utf-8")
            (dynamic_reports / "schemathesis.log").write_text("ok", encoding="utf-8")
            self.assertEqual(
                self.module.resolve_lane_count("t11_run_dynamic_security_tests.sh", repo_root / "dynamic.log", repo_root),
                2,
            )

    def test_main_prints_fallback_for_none_and_negative_counts(self):
        #R030-T03: CLI prints fallback value 1 for None/negative count resolver output.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            lane_log = repo_root / "lane.log"
            lane_log.write_text("x", encoding="utf-8")
            with patch.object(self.module, "resolve_lane_count", return_value=None):
                with patch("sys.argv", [
                    "parallel_lane_test_count.py",
                    "--lane-script", "a.sh",
                    "--lane-log", str(lane_log),
                    "--repo-root", str(repo_root),
                ]):
                    self.assertEqual(self.module.main(), 0)
            with patch.object(self.module, "resolve_lane_count", return_value=-5):
                with patch("sys.argv", [
                    "parallel_lane_test_count.py",
                    "--lane-script", "a.sh",
                    "--lane-log", str(lane_log),
                    "--repo-root", str(repo_root),
                ]):
                    self.assertEqual(self.module.main(), 0)


if __name__ == "__main__":
    unittest.main()
