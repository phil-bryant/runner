#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
script_path = repo_root / "tests" / "py" / "security" / "sast_summary_gate.py"
spec = importlib.util.spec_from_file_location("sast_summary_gate_under_test", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load sast_summary_gate.py")
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


def test_load_json_reads_artifact():
    #R001-T01: Verify scanner artifact loader handles required report files and returns parsed JSON payloads.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "payload.json"
        path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        payload = MODULE.load_json(path)
    assert payload["ok"] is True


def test_count_pip_audit_payload_variants():
    #R005-T01: Verify pip-audit counter normalizes multiple payload shapes into expected totals.
    as_list = [{"vulns": [1, 2]}, {"vulns": [3]}]
    as_dependencies = {"dependencies": [{"vulns": [1]}, {"vulns": [2, 3]}]}
    as_dict = {"vulns": [1, 2, 3, 4]}
    assert MODULE.count_pip_audit(as_list) == 3
    assert MODULE.count_pip_audit(as_dependencies) == 3
    assert MODULE.count_pip_audit(as_dict) == 4


def test_main_aggregates_and_applies_gate():
    #R010-T01: Verify summary aggregation and policy-mode gate exit behavior for clean and failing finding sets.
    with tempfile.TemporaryDirectory() as tmp:
        report_dir = Path(tmp)
        (report_dir / "semgrep.json").write_text(json.dumps({"results": []}), encoding="utf-8")
        (report_dir / "bandit.json").write_text(json.dumps({"results": []}), encoding="utf-8")
        (report_dir / "pip-audit.json").write_text(json.dumps({"vulns": []}), encoding="utf-8")
        (report_dir / "detect-secrets.json").write_text(json.dumps({"results": {}}), encoding="utf-8")
        (report_dir / "swiftlint.json").write_text(json.dumps([]), encoding="utf-8")
        (report_dir / "shellcheck.json").write_text(json.dumps([]), encoding="utf-8")
        (report_dir / "gitleaks.json").write_text(json.dumps([]), encoding="utf-8")
        argv = ["sast_summary_gate.py", str(report_dir), "true", "medium"]
        import sys

        original_argv = sys.argv
        sys.argv = argv
        try:
            rc = MODULE.main()
        finally:
            sys.argv = original_argv
        summary = json.loads((report_dir / "sast-summary.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert summary["gate_failed"] is False
    assert summary["medium_or_higher_total"] == 0
