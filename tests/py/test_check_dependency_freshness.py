#!/usr/bin/env python3

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


#R001: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "check_dependency_freshness.py"
    spec = importlib.util.spec_from_file_location("check_dependency_freshness", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_dependency_freshness module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CheckDependencyFreshnessTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()

    def test_parse_requirements_and_classify_update(self) -> None:
        #R001-T01: Verify requirements parsing and update classification behavior for pinned and non-pinned dependencies.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            req_path.write_text(
                "requests==2.30.0\n"
                "urllib3>=2.1.0\n"
                "# comment\n"
                "numpy==1.26.4\n",
                encoding="utf-8",
            )
            specs = self.module.parse_requirements(req_path)
        self.assertTrue(specs["requests"].is_exact_pin)
        self.assertEqual(specs["requests"].pinned_version, "2.30.0")
        self.assertFalse(specs["urllib3"].is_exact_pin)
        self.assertEqual(self.module.classify_update("1.0.0", "2.0.0"), "major")
        self.assertEqual(self.module.classify_update("1.2.0", "1.3.0"), "minor")
        self.assertEqual(self.module.classify_update("1.2.3", "1.2.4"), "patch")

    def test_make_report_and_format_text(self) -> None:
        #R005-T01: Run the script with mocked outdated package rows and verify both report formats contain expected summary/package fields.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            original = self.module.run_outdated_list
            self.module.run_outdated_list = lambda: [
                {"name": "requests", "version": "2.30.0", "latest_version": "2.31.0"},
                {"name": "idna", "version": "3.6", "latest_version": "3.7"},
            ]
            try:
                report = self.module.make_report(req_path)
            finally:
                self.module.run_outdated_list = original
        self.assertEqual(report["summary"]["total_outdated"], 2)
        self.assertEqual(report["summary"]["direct_requirements_outdated"], 1)
        text = self.module.format_report_text(report)
        self.assertIn("Dependency freshness report", text)
        self.assertIn("requests", text)
        self.assertIn("transitive", text)

    def test_make_report_orders_constrained_before_actionable(self) -> None:
        #R015-T01: Verify report package ordering places constrained entries before actionable entries, even when update severity would otherwise put actionable entries first.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            req_path.write_text("alpha==1.0.0\nzeta==1.0.0\n", encoding="utf-8")
            original_outdated = self.module.run_outdated_list
            original_constraints = self.module._collect_reverse_dependency_constraints
            original_actionability = self.module._evaluate_actionability
            self.module.run_outdated_list = lambda: [
                {"name": "zeta", "version": "1.0.0", "latest_version": "2.0.0"},
                {"name": "alpha", "version": "1.0.0", "latest_version": "1.0.1"},
            ]
            self.module._collect_reverse_dependency_constraints = lambda: {}
            self.module._evaluate_actionability = (
                lambda latest_version, _required_by: ("constrained", False)
                if latest_version == "1.0.1"
                else ("actionable", True)
            )
            try:
                report = self.module.make_report(req_path)
            finally:
                self.module.run_outdated_list = original_outdated
                self.module._collect_reverse_dependency_constraints = original_constraints
                self.module._evaluate_actionability = original_actionability
        self.assertEqual(
            [item["name"] for item in report["packages"]],
            ["alpha", "zeta"],
        )
        self.assertEqual(
            [item["outdated_actionability"] for item in report["packages"]],
            ["constrained", "actionable"],
        )

    def test_main_fails_for_configured_gates(self) -> None:
        #R010-T01: Verify each gate independently returns a failing exit status only when its configured condition is present.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            out_json = Path(tmp) / "report.json"
            out_text = Path(tmp) / "report.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            argv = sys.argv
            try:
                sys.argv = [
                    "check_dependency_freshness.py",
                    "--requirements",
                    str(req_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-any-actionable-outdated",
                    "--fail-on-major",
                    "--fail-on-direct-outdated",
                ]
                original = self.module.make_report
                self.module.make_report = lambda *_args: {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "requirements_file": str(req_path),
                    "summary": {
                        "total_outdated": 1,
                        "major_updates": 1,
                        "minor_updates": 0,
                        "patch_updates": 0,
                        "unknown_updates": 0,
                        "direct_requirements_outdated": 1,
                        "actionable_outdated": 1,
                        "constrained_outdated": 0,
                        "unknown_actionability_outdated": 0,
                    },
                    "packages": [
                        {
                            "name": "requests",
                            "current_version": "2.30.0",
                            "latest_version": "3.0.0",
                            "update_type": "major",
                            "in_requirements_txt": True,
                            "is_exact_pin_in_requirements": True,
                        }
                    ],
                }
                rc = self.module.main()
            finally:
                self.module.make_report = original
                sys.argv = argv
            self.assertEqual(rc, 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["major_updates"], 1)

    def test_main_fails_on_any_actionable_outdated_with_only_transitive_drift(self) -> None:
        #R010-T01: Verify each gate independently returns a failing exit status only when its configured condition is present.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            out_json = Path(tmp) / "report.json"
            out_text = Path(tmp) / "report.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            argv = sys.argv
            try:
                sys.argv = [
                    "check_dependency_freshness.py",
                    "--requirements",
                    str(req_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-any-actionable-outdated",
                ]
                original = self.module.make_report
                self.module.make_report = lambda *_args: {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "requirements_file": str(req_path),
                    "summary": {
                        "total_outdated": 1,
                        "major_updates": 0,
                        "minor_updates": 1,
                        "patch_updates": 0,
                        "unknown_updates": 0,
                        "direct_requirements_outdated": 0,
                        "actionable_outdated": 1,
                        "constrained_outdated": 0,
                        "unknown_actionability_outdated": 0,
                    },
                    "packages": [
                        {
                            "name": "idna",
                            "current_version": "3.6",
                            "latest_version": "3.7",
                            "update_type": "minor",
                            "in_requirements_txt": False,
                            "is_exact_pin_in_requirements": False,
                            "outdated_actionability": "actionable",
                        }
                    ],
                }
                rc = self.module.main()
            finally:
                self.module.make_report = original
                sys.argv = argv
            self.assertEqual(rc, 1)

    def test_main_ignores_constrained_only_outdated_for_actionable_gate(self) -> None:
        #R010-T01: Verify each gate independently returns a failing exit status only when its configured condition is present.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            out_json = Path(tmp) / "report.json"
            out_text = Path(tmp) / "report.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            argv = sys.argv
            try:
                sys.argv = [
                    "check_dependency_freshness.py",
                    "--requirements",
                    str(req_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-any-actionable-outdated",
                ]
                original = self.module.make_report
                self.module.make_report = lambda *_args: {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "requirements_file": str(req_path),
                    "summary": {
                        "total_outdated": 1,
                        "major_updates": 0,
                        "minor_updates": 1,
                        "patch_updates": 0,
                        "unknown_updates": 0,
                        "direct_requirements_outdated": 0,
                        "actionable_outdated": 0,
                        "constrained_outdated": 1,
                        "unknown_actionability_outdated": 0,
                    },
                    "packages": [
                        {
                            "name": "mando",
                            "current_version": "0.7.1",
                            "latest_version": "0.8.2",
                            "update_type": "minor",
                            "in_requirements_txt": False,
                            "is_exact_pin_in_requirements": False,
                            "outdated_actionability": "constrained",
                        }
                    ],
                }
                rc = self.module.main()
            finally:
                self.module.make_report = original
                sys.argv = argv
            self.assertEqual(rc, 0)

    def test_main_fails_when_venv_cruft_gate_enabled(self) -> None:
        #R010-T01: Verify each gate independently returns a failing exit status only when its configured condition is present.
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            out_json = Path(tmp) / "report.json"
            out_text = Path(tmp) / "report.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            argv = sys.argv
            try:
                sys.argv = [
                    "check_dependency_freshness.py",
                    "--requirements",
                    str(req_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-venv-cruft",
                ]
                original = self.module.make_report
                self.module.make_report = lambda *_args: {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "requirements_file": str(req_path),
                    "summary": {
                        "total_outdated": 0,
                        "major_updates": 0,
                        "minor_updates": 0,
                        "patch_updates": 0,
                        "unknown_updates": 0,
                        "direct_requirements_outdated": 0,
                        "actionable_outdated": 0,
                        "constrained_outdated": 0,
                        "unknown_actionability_outdated": 0,
                    },
                    "packages": [],
                    "venv_cruft_packages": ["semgrep"],
                    "venv_cruft_status": "ok",
                }
                rc = self.module.main()
            finally:
                self.module.make_report = original
                sys.argv = argv
            self.assertEqual(rc, 1)

    def test_parse_requirements_normalizes_names(self) -> None:
        #R030-T01: Verify requirement parsing normalizes package names and captures pinned metadata from mixed requirement lines (`tests/py/test_check_dependency_freshness.py`).
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            req_path.write_text("Requests_Name==1.2.3\nurllib3==2.2.1\n", encoding="utf-8")
            parsed = self.module.parse_requirements(req_path)
        self.assertIn("requests-name", parsed)
        self.assertEqual(parsed["requests-name"].pinned_version, "1.2.3")
        self.assertIn("urllib3", parsed)

    def test_outdated_list_parsing(self) -> None:
        #R035-T01: Verify outdated list parsing returns normalized package rows from pip JSON output (`tests/py/test_check_dependency_freshness.py`).
        class FakeResult:
            returncode = 0
            stdout = json.dumps([{"name": "requests", "version": "2.0.0", "latest_version": "2.1.0"}])
            stderr = ""

        original_run = self.module.subprocess.run
        self.module.subprocess.run = lambda *args, **kwargs: FakeResult()
        try:
            rows = self.module.run_outdated_list()
        finally:
            self.module.subprocess.run = original_run
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "requests")

    def test_classify_update_gate(self) -> None:
        #R040-T01: Verify update classification and actionability evaluation distinguish actionable and constrained outcomes (`tests/py/test_check_dependency_freshness.py`).
        self.assertEqual(self.module.classify_update("1.0.0", "2.0.0"), "major")
        original_collect = self.module._collect_requested_packages
        self.module._collect_requested_packages = lambda: ({"requests", "setuptools"}, "ok")
        try:
            cruft, status = self.module._detect_venv_cruft({"requests": self.module.RequirementSpec("requests", "2.0.0", True)})
        finally:
            self.module._collect_requested_packages = original_collect
        self.assertEqual(status, "ok")
        self.assertEqual(cruft, [])

    def test_report_cli_exit(self) -> None:
        #R045-T01: Verify report rendering and CLI gate exits reflect summary outcomes and configured failure flags (`tests/py/test_check_dependency_freshness.py`).
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "requirements.txt"
            out_json = Path(tmp) / "report.json"
            out_text = Path(tmp) / "report.txt"
            req_path.write_text("requests==2.30.0\n", encoding="utf-8")
            argv = sys.argv
            original = self.module.make_report
            try:
                sys.argv = [
                    "check_dependency_freshness.py",
                    "--requirements",
                    str(req_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-direct-outdated",
                ]
                self.module.make_report = lambda *_args: {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "requirements_file": str(req_path),
                    "summary": {
                        "total_outdated": 1,
                        "major_updates": 0,
                        "minor_updates": 1,
                        "patch_updates": 0,
                        "unknown_updates": 0,
                        "direct_requirements_outdated": 1,
                        "actionable_outdated": 0,
                        "constrained_outdated": 1,
                        "unknown_actionability_outdated": 0,
                    },
                    "packages": [],
                    "venv_cruft_packages": [],
                    "venv_cruft_status": "ok",
                }
                rc = self.module.main()
            finally:
                self.module.make_report = original
                sys.argv = argv
            self.assertEqual(rc, 1)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_text.exists())


if __name__ == "__main__":
    unittest.main()
