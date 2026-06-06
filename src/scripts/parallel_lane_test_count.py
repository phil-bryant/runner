#!/usr/bin/env python3
"""Resolve per-lane test/check counts for parallel PASS output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_report_dir(path_value: str, repo_root: Path) -> Path:
    candidate = Path(path_value.strip())
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


#R025: Security lanes resolve the report directory from the lane log `Reports:`
# line (falling back to a default) and count discovered tool artifact files.
def _extract_reports_dir_from_log(log_text: str, repo_root: Path, default: Path) -> Path:
    match = re.search(r"Reports:\s*(\S+)", log_text)
    if match is None:
        return default
    return _normalize_report_dir(match.group(1), repo_root)


#R015: Artifact-summary lanes read an integer count field from a summary JSON
# (fuzz `property_test_count`, mutation `total`).
def _read_int_field(path: Path, field: str) -> int | None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if not isinstance(value, int):
        return None
    return value


#R001: Traceability lane count comes from the engine `Summary: total=N` line.
def _parse_traceability_total(log_text: str) -> int | None:
    match = re.search(r"Summary:\s*total=(\d+)\s+pass=\d+\s+fail=\d+", log_text)
    if match is None:
        return None
    return int(match.group(1))


#R005: Shell-unit lane count sums bats TAP plan lines, else counts `ok` results.
def _parse_bats_total(log_text: str) -> int | None:
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


def _parse_numeric_selector_count(selector: str) -> int | None:
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
    return sum(1 for name in names if (base_dir / name).is_file())


#R020: Quality lane counts only the non-skipped text sub-check reports present.
def _count_non_skipped_text_reports(base_dir: Path, names: list[str]) -> int:
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
    lane_stem = Path(lane_script).stem
    log_text = _read_text(lane_log)

    if lane_stem == "t04_run_requirements_traceability_tests":
        return _parse_traceability_total(log_text)

    if lane_stem == "t05_run_shell_unit_tests":
        return _parse_bats_total(log_text)

    if lane_stem == "t06_run_python_unit_tests":
        return _parse_pytest_total(log_text)

    if lane_stem == "t08_run_swift_unit_tests":
        return _parse_swift_xctest_total(log_text)

    if lane_stem.endswith("run_macos_ui_regression_tests"):
        return _parse_macos_ui_regression_total(log_text, repo_root)

    if lane_stem == "t08_run_fuzz_tests":
        return _read_int_field(repo_root / "artifacts/fuzz/fuzz-summary.json", "property_test_count")

    if lane_stem == "t07_run_mutation_tests":
        return _read_int_field(repo_root / "artifacts/mutation/mutation-summary.json", "total")

    if lane_stem == "t00_run_code_quality_tests":
        quality_dir = repo_root / "artifacts/quality/reports"
        quality_checks = _count_non_skipped_text_reports(
            quality_dir,
            ["vulture.txt", "radon.txt", "xenon.txt", "periphery.txt", "lizard.txt"],
        )
        return quality_checks if quality_checks > 0 else None

    if lane_stem == "t02_run_dependency_freshness_tests":
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

    if lane_stem == "t03_run_static_security_tests":
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

    if lane_stem == "t09_run_dynamic_security_tests":
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
