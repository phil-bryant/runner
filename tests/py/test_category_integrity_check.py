#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
script_path = repo_root / "tests" / "py" / "security" / "category_integrity_check.py"
spec = importlib.util.spec_from_file_location("category_integrity_check_under_test", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load category_integrity_check.py")
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


def test_parse_seed_row_count_failure():
    #R001-T01: Verify canonical seed parser fails clearly when the expected SQL block is missing or empty.
    try:
        MODULE.parse_seed_row_count("SELECT 1;")
    except ValueError:
        return
    raise AssertionError("Expected ValueError for missing seed SQL block")


def test_report_artifact_written():
    #R005-T01: Verify base-report and write-report paths emit deterministic artifact structure and status fields.
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.json"
        report = MODULE.build_base(strict_mode=False, seed_row_count=12)
        MODULE.write_report(report_path, report)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["canonical_seed_row_count"] == 12
    assert payload["status"] == "passed"


def test_strict_mode_failure_sets_gate():
    #R010-T01: Verify invariant failures drive strict vs non-strict gate behavior and final status fields.
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "integrity.json"
        seed_path = Path(tmp) / "seed.sql"
        seed_path.write_text("invalid", encoding="utf-8")
        argv = ["category_integrity_check.py", str(report_path), str(seed_path), "true"]
        import sys

        original_argv = sys.argv
        sys.argv = argv
        try:
            rc = MODULE.main()
        finally:
            sys.argv = original_argv
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert rc == 2
    assert payload["status"] == "error"
    assert payload["gate_failed"] is True
