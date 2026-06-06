#!/usr/bin/env python3
"""Resolve per-lane test/check counts for parallel PASS output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _read_text(path: Path) -> str:
    #R001: Read lane logs for traceability summary count extraction.
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> object | None:
    #R015: Read lane summary JSON artifacts for integer count fields.
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_report_dir(path_value: str, repo_root: Path) -> Path:
    #R025: Normalize relative/absolute security report directory paths.
    candidate = Path(path_value.strip())
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


#R025: Security lanes resolve the report directory from the lane log `Reports:`
# line (falling back to a default) and count discovered tool artifact files.
def _extract_reports_dir_from_log(log_text: str, repo_root: Path, default: Path) -> Path:
    #R025: Extract security report directory from lane log Reports line.
    match = re.search(r"Reports:\s*(\S+)", log_text)
    if match is None:
        return default
    return _normalize_report_dir(match.group(1), repo_root)


#R015: Artifact-summary lanes read an integer count field from a summary JSON
# (fuzz `property_test_count`, mutation `total`).
def _read_int_field(path: Path, field: str) -> int | None:
    #R015: Read integer count fields from lane summary JSON payloads.
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if not isinstance(value, int):
        return None
    return value


#R001: Traceability lane count comes from the engine `Summary: total=N` line.
def _parse_traceability_total(log_text: str) -> int | None:
    #R001: Parse traceability Summary total count from lane logs.
    match = re.search(r"Summary:\s*total=(\d+)\s+pass=\d+\s+fail=\d+", log_text)
    if match is None:
        return None
    return int(match.group(1))


#R005: Shell-unit lane count sums bats TAP plan lines, else counts `ok` results.
def _parse_bats_total(log_text: str) -> int | None:
    #R005: Parse shell-unit totals from bats TAP plan or ok lines.
    plan_counts = [int(value) for value in re.findall(r"(?m)^\s*1\.\.(\d+)\s*$", log_text)]
    if plan_counts:
        return sum(plan_counts)
    ok_count = len(re.findall(r"(?m)^\s*ok(?:\s+\d+)?\b", log_text))
    if ok_count > 0:
        return ok_count
    return None


#R010: Python-unit lane count parses the pytest summary (0 for "no tests ran",
# else summed outcome counts, with a `collected N items` fallback).
def _parse_pytest_total(log_text: str) -> int | None:
    #R010: Parse python-unit totals from pytest summary or collected fallback.
    if re.search(r"(?m)no tests ran", log_text):
        return 0

    summary_lines = [
        line.strip()
        for line in log_text.splitlines()
        if " in " in line and any(
            token in line
            for token in ("passed", "failed", "error", "errors", "skipped", "xfailed", "xpassed")
        )
    ]
    if summary_lines:
        counts = [int(value) for value in re.findall(r"(\d+)\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed)", summary_lines[-1])]
        if counts:
            return sum(counts)

    collected_match = re.search(r"(?m)^collected\s+(\d+)\s+items?\b", log_text)
    if collected_match:
        return int(collected_match.group(1))
    return None


#R012: Swift-unit lane count prefers XCTest `Executed N tests` summaries when
# present (to avoid trailing `Test run with 0 tests` metadata), with
# `Test run with N tests` as fallback.
def _parse_swift_xctest_total(log_text: str) -> int | None:
    #R012: Parse swift-unit totals from XCTest executed/test-run summaries.
    executed_totals = [
        int(match.group(1))
        for match in re.finditer(r"\bExecuted\s+(\d+)\s+tests?\b", log_text, flags=re.IGNORECASE)
    ]
    if executed_totals:
        return max(executed_totals)

    run_totals = [
        int(match.group(1))
        for match in re.finditer(r"\bTest run with\s+(\d+)\s+tests?\b", log_text, flags=re.IGNORECASE)
    ]
    if not run_totals:
        return None
    return max(run_totals)


#R022: SQL-unit lane count prefers pg_prove `Tests=N` summaries, then TAP plans.
def _parse_sql_unit_total(log_text: str) -> int | None:
    #R022: Parse SQL-unit totals from pg_prove summary or TAP output.
    summary_totals = [
        int(match.group(1))
        for match in re.finditer(r"(?im)\bTests\s*=\s*(\d+)\b", log_text)
    ]
    if summary_totals:
        return max(summary_totals)

    plan_totals = [
        int(value) for value in re.findall(r"(?m)^\s*1\.\.(\d+)\s*$", log_text)
    ]
    if plan_totals:
        return sum(plan_totals)

    ok_totals = len(re.findall(r"(?m)^\s*ok\s+\d+\b", log_text))
    if ok_totals > 0:
        return ok_totals
    return None


#R001: function tag for _parse_cpp_integration_total
def _parse_cpp_integration_total(log_text: str) -> int | None:
    # Parse C++ integration totals from common ctest/gtest/catch2 summaries.
    mailcart_final_count = re.search(
        r"(?im)\bFinal count:\s*tests\s+(\d+)/\d+\s+passed\b",
        log_text,
    )
    if mailcart_final_count is not None:
        return int(mailcart_final_count.group(1))

    ctest_summary = re.search(
        r"(?im)\btests passed,\s+\d+\s+tests failed out of\s+(\d+)\b",
        log_text,
    )
    if ctest_summary is not None:
        return int(ctest_summary.group(1))

    total_tests = re.search(r"(?im)\bTotal Tests:\s*(\d+)\b", log_text)
    if total_tests is not None:
        return int(total_tests.group(1))

    gtest_totals = [
        int(match.group(1))
        for match in re.finditer(
            r"(?im)^\s*\[=+\]\s*Running\s+(\d+)\s+tests?\s+from\s+\d+\s+test suites?\.",
            log_text,
        )
    ]
    if gtest_totals:
        return max(gtest_totals)

    catch2_totals = [
        int(match.group(1))
        for match in re.finditer(
            r"(?im)\bAll tests passed\s+\(\d+\s+assertions?\s+in\s+(\d+)\s+test cases?\)",
            log_text,
        )
    ]
    if catch2_totals:
        return max(catch2_totals)

    discovered_cases = len(re.findall(r"(?im)^\s*(?:\d+/\d+\s+)?Test\s+#\d+:", log_text))
    if discovered_cases > 0:
        return discovered_cases

    mailcart_named_tests = len(re.findall(r"(?im)^\s*Running\s+Test[^\s]+\s*$", log_text))
    if mailcart_named_tests > 0:
        return mailcart_named_tests

    return None


def _parse_numeric_selector_count(selector: str) -> int | None:
    #R018: Parse numeric selector syntax into unique scenario counts.
    selector = selector.strip()
    if not selector:
        return None

    selected_steps: set[int] = set()
    for raw_token in selector.split(","):
        token = raw_token.strip()
        if not token:
            continue
        if re.fullmatch(r"\d+", token):
            selected_steps.add(int(token))
            continue
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
        if range_match is None:
            return None
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        if start > end:
            return None
        selected_steps.update(range(start, end + 1))
    if not selected_steps:
        return None
    return len(selected_steps)


#R018: macOS UI regression lane count prefers explicit scenario summary output,
# then selected-step selector hints, then XCTest `Executed N tests` summaries.
def _parse_macos_ui_regression_total(log_text: str, repo_root: Path) -> int | None:
    #R018: Parse macOS UI scenario totals from summary, selector, or XCTest fallback.
    summary_match = re.search(r"(?im)scenarios\s+total:\s*.*?\bover\s+(\d+)\s+scenarios?\b", log_text)
    if summary_match is not None:
        return int(summary_match.group(1))

    selector_match = re.search(r"(?im)^\s*.*Using XCUITest profile .* with scenarios:\s*([0-9,\-\s]+)\s*$", log_text)
    if selector_match is not None:
        selector_count = _parse_numeric_selector_count(selector_match.group(1))
        if selector_count is not None:
            return selector_count

    swift_xctest_total = _parse_swift_xctest_total(log_text)
    if swift_xctest_total is not None:
        return swift_xctest_total

    steps_selector = _read_text(repo_root / "artifacts/macos-ui-regression/xcuitest-steps.env")
    return _parse_numeric_selector_count(steps_selector)


def _count_existing(base_dir: Path, names: list[str]) -> int:
    #R025: Count existing report artifact files for security lanes.
    return sum(1 for name in names if (base_dir / name).is_file())


#R020: Quality lane counts only the non-skipped text sub-check reports present.
def _count_non_skipped_text_reports(base_dir: Path, names: list[str]) -> int:
    #R020: Count non-skipped quality report artifacts for lane totals.
    total = 0
    for name in names:
        path = base_dir / name
        if not path.is_file():
            continue
        if _read_text(path).strip() == "skipped":
            continue
        total += 1
    return total


def resolve_lane_count(lane_script: str, lane_log: Path, repo_root: Path) -> int | None:
    #R001: Resolve traceability lane total from Summary output.
    #R005: Resolve shell-unit totals from bats TAP plans/results.
    #R010: Resolve python-unit totals from pytest summary output.
    #R022: Resolve sql-unit totals from pg_prove/TAP summary output.
    #R012: Resolve swift-unit totals from XCTest summary output.
    #R015: Resolve artifact-summary lane totals from JSON fields.
    #R018: Resolve macOS UI totals from scenario summaries/selectors.
    #R020: Resolve quality lane totals from non-skipped sub-check reports.
    #R025: Resolve security lane totals from discovered report artifacts.
    #R030: Support unknown-lane fallback handling via shared resolver contract.
    lane_stem = Path(lane_script).stem
    log_text = _read_text(lane_log)

    if lane_stem.endswith("run_requirements_traceability_tests"):
        return _parse_traceability_total(log_text)

    if lane_stem.endswith("run_shell_unit_tests"):
        return _parse_bats_total(log_text)

    if lane_stem.endswith("run_python_unit_tests"):
        return _parse_pytest_total(log_text)

    if lane_stem.endswith("run_sql_unit_tests"):
        return _parse_sql_unit_total(log_text)

    if lane_stem.endswith("run_swift_unit_tests"):
        return _parse_swift_xctest_total(log_text)

    if lane_stem.endswith("run_macos_ui_regression_tests"):
        return _parse_macos_ui_regression_total(log_text, repo_root)

    if lane_stem.endswith("run_cpp_integration_tests"):
        return _parse_cpp_integration_total(log_text)

    if lane_stem.endswith("run_fuzz_tests"):
        return _read_int_field(repo_root / "artifacts/fuzz/fuzz-summary.json", "property_test_count")

    if lane_stem.endswith("run_mutation_tests"):
        return _read_int_field(repo_root / "artifacts/mutation/mutation-summary.json", "total")

    if lane_stem.endswith("run_code_quality_tests"):
        quality_dir = repo_root / "artifacts/quality/reports"
        quality_checks = _count_non_skipped_text_reports(
            quality_dir,
            ["vulture.txt", "radon.txt", "xenon.txt", "periphery.txt", "lizard.txt"],
        )
        return quality_checks if quality_checks > 0 else None

    if lane_stem.endswith("run_dependency_freshness_tests"):
        security_dir = repo_root / "artifacts/security"
        dependency_checks = _count_existing(
            security_dir,
            [
                "dependency-freshness.json",
                "security-toolchain-dependency-freshness.json",
                "binary-integrity.json",
                "teller-api-version-freshness.json",
                "postgres-freshness.json",
            ],
        )
        return dependency_checks if dependency_checks > 0 else None

    if lane_stem.endswith("run_static_security_tests"):
        static_default_dir = repo_root / "artifacts/security/reports"
        static_report_dir = _extract_reports_dir_from_log(log_text, repo_root, static_default_dir)
        static_checks = _count_existing(
            static_report_dir,
            [
                "semgrep.json",
                "bandit.json",
                "pip-audit.json",
                "detect-secrets.json",
                "ruff.json",
                "gitleaks.json",
                "shellcheck.json",
                "swiftlint.json",
            ],
        )
        return static_checks if static_checks > 0 else None

    if lane_stem.endswith("run_dynamic_security_tests"):
        dynamic_default_dir = repo_root / "artifacts/security-dast"
        dynamic_report_dir = _extract_reports_dir_from_log(log_text, repo_root, dynamic_default_dir)
        dynamic_checks = 0
        if (dynamic_report_dir / "zap-classification-summary.json").is_file():
            dynamic_checks += 1
        if (dynamic_report_dir / "schemathesis-junit.xml").is_file() or (dynamic_report_dir / "schemathesis.log").is_file():
            dynamic_checks += 1
        if (dynamic_report_dir / "category-integrity.json").is_file():
            dynamic_checks += 1
        return dynamic_checks if dynamic_checks > 0 else None

    return None


def main() -> int:
    #R030: Print resolved lane count or safe single-test fallback for unknown lanes.
    parser = argparse.ArgumentParser(description="Resolve per-lane test/check count for PASS output.")
    parser.add_argument("--lane-script", required=True, help="Lane script basename (for example t05_run_shell_unit_tests.sh).")
    parser.add_argument("--lane-log", required=True, help="Path to lane log file.")
    parser.add_argument("--repo-root", required=True, help="Repository root path.")
    parser.add_argument("--report-dir", required=False, help="Unused compatibility input from orchestrator.")
    args = parser.parse_args()

    lane_log = Path(args.lane_log)
    repo_root = Path(args.repo_root).resolve()
    count = resolve_lane_count(args.lane_script, lane_log, repo_root)

    #R030: CLI prints a single-test fallback when a lane is unknown or yields no
    # usable (None/negative) count, otherwise prints the resolved count.
    if count is None:
        print("1")
        return 0
    if count < 0:
        print("1")
        return 0
    print(str(count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
