#!/usr/bin/env python3

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


#R001: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "check_teller_api_drift.py"
    spec = importlib.util.spec_from_file_location("check_teller_api_drift", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_teller_api_drift module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResolveCredentialsTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.teller_dir = Path(self.temp_dir.name)
        self.module.HOME_TELLER_DIR = self.teller_dir

    #R001: shard-3 function tag
    def _write_token(self, filename: str, token: str) -> None:
        payload = {"current": token}
        (self.teller_dir / filename).write_text(json.dumps(payload), encoding="utf-8")

    def test_suffix_only_token_is_resolved(self) -> None:
        #R001-T01: Verify default discovery, institution filtering, and run-all-token candidate expansion behavior.
        self._write_token("auth_token_chase.json", "token-chase")

        creds = self.module.resolve_credentials()
        self.assertEqual(creds["token"], "token-chase")
        self.assertEqual(creds["token_source"], "chase")
        self.assertEqual(creds["warnings"], [])

    def test_ambiguous_tokens_require_institution_id(self) -> None:
        #R005-T01: Verify live and fallback decision logic emits expected check lists and warning states.
        self._write_token("auth_token_chase.json", "token-chase")
        self._write_token("auth_token_fabt.json", "token-fabt")

        creds = self.module.resolve_credentials()
        self.assertEqual(creds["token"], "")
        self.assertEqual(creds["token_source"], "")
        self.assertEqual(len(creds["warnings"]), 1)
        self.assertIn("--institution-id", creds["warnings"][0])

    def test_institution_id_selects_matching_suffix(self) -> None:
        #R001-T01: Verify institution-id suffix filtering selects the matching local token candidate.
        self._write_token("auth_token_chase.json", "token-chase")
        self._write_token("auth_token_fabt.json", "token-fabt")

        creds = self.module.resolve_credentials(institution_id="fabt")
        self.assertEqual(creds["token"], "token-fabt")
        self.assertEqual(creds["token_source"], "fabt")
        self.assertEqual(creds["warnings"], [])

    def test_run_all_tokens_returns_all_candidates(self) -> None:
        #R001-T01: Verify default discovery, institution filtering, and run-all-token candidate expansion behavior.
        self._write_token("auth_token_chase.json", "token-chase")
        self._write_token("auth_token_fabt.json", "token-fabt")

        creds = self.module.resolve_credentials(run_all_tokens=True)
        candidates = creds["token_candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0][0], "chase")
        self.assertEqual(candidates[1][0], "fabt")
        self.assertEqual(creds["warnings"], [])

    def test_run_all_tokens_respects_institution_filter(self) -> None:
        #R001-T01: Verify default discovery, institution filtering, and run-all-token candidate expansion behavior.
        #R005-T01: Verify live and fallback decision logic emits expected check lists and warning states.
        self._write_token("auth_token_chase.json", "token-chase")
        self._write_token("auth_token_fabt.json", "token-fabt")

        creds = self.module.resolve_credentials(run_all_tokens=True, institution_id="fabt")
        candidates = creds["token_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], "fabt")

    def test_build_text_report_includes_mode_status_and_checks(self) -> None:
        #R010-T01: Verify report persistence and process exit behavior for passing, warning, and failing scenarios.
        report = {
            "mode": "fallback",
            "status": "warn",
            "warnings": ["token missing"],
            "checks": [{"name": "doc:accounts.md", "status": "pass", "detail": "ok"}],
        }
        text = self.module.build_text_report(report)
        self.assertIn("Mode: fallback", text)
        self.assertIn("Status: warn", text)
        self.assertIn("token missing", text)
        self.assertIn("[pass] doc:accounts.md", text)

    def test_resolve_credentials_selects_token(self) -> None:
        #R030-T01: Verify credential resolution selects the expected local token candidate and metadata when multiple token sources exist (`tests/py/test_check_teller_api_drift.py`).
        self._write_token("auth_token_chase.json", "token-chase")
        self._write_token("auth_token_fabt.json", "token-fabt")
        creds = self.module.resolve_credentials(institution_id="chase")
        self.assertEqual(creds["token"], "token-chase")
        self.assertEqual(creds["token_source"], "chase")

    def test_live_canary_detects_drift(self) -> None:
        #R035-T01: Verify live canary checks mark drift failures when endpoint checks return non-200 responses (`tests/py/test_check_teller_api_drift.py`).
        cert_path = self.teller_dir / "certificate.pem"
        key_path = self.teller_dir / "private_key.pem"
        cert_path.write_text("cert", encoding="utf-8")
        key_path.write_text("key", encoding="utf-8")

        class FakeRequestException(Exception):
            pass

        class FakeResponse:
            status_code = 500
            text = "drift"

        fake_requests = type(
            "FakeRequests",
            (),
            {
                "RequestException": FakeRequestException,
                "get": staticmethod(lambda *_args, **_kwargs: FakeResponse()),
            },
        )

        with patch.dict(sys.modules, {"requests": fake_requests}):
            with patch.dict(
                os.environ,
                {
                    "TELLER_CERT_PATH": str(cert_path),
                    "TELLER_KEY_PATH": str(key_path),
                    "TELLER_ACCESS_TOKEN": "token-live",
                },
                clear=False,
            ):
                result = self.module.run_live_canary(timeout_seconds=1)
        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(check["status"] == "fail" for check in result["checks"]))


class MainExitPolicyTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.report_dir = Path(self.temp_dir.name)

    def test_require_live_fails_when_fallback_mode_is_used(self) -> None:
        #R015-T01: Verify `--require-live` returns non-zero when run falls back.
        args = [
            "check_teller_api_drift.py",
            "--output-json",
            str(self.report_dir / "out.json"),
            "--output-text",
            str(self.report_dir / "out.txt"),
            "--require-live",
        ]
        with patch.object(self.module, "run_live_canary", return_value={"mode": "fallback", "status": "warn", "checks": [], "warnings": ["no creds"]}), patch.object(
            self.module,
            "run_fallback_checks",
            return_value={"status": "pass", "checks": [], "warnings": []},
        ), patch.object(os, "umask", return_value=0):
            with patch("sys.argv", args):
                exit_code = self.module.main()
        self.assertEqual(exit_code, 1)

    def test_fail_on_warn_promotes_warning_to_failure(self) -> None:
        #R015-T02: Verify `--fail-on-warn` returns non-zero when report status is warn.
        args = [
            "check_teller_api_drift.py",
            "--output-json",
            str(self.report_dir / "warn.json"),
            "--output-text",
            str(self.report_dir / "warn.txt"),
            "--fail-on-warn",
        ]
        with patch.object(self.module, "run_live_canary", return_value={"mode": "live", "status": "warn", "checks": [], "warnings": ["token missing"]}), patch.object(
            os, "umask", return_value=0
        ):
            with patch("sys.argv", args):
                exit_code = self.module.main()
        self.assertEqual(exit_code, 1)

    def test_report_and_cli_gate(self) -> None:
        #R045-T01: Verify CLI report generation and gate exits return expected status for warning/failure scenarios (`tests/py/test_check_teller_api_drift.py`).
        args = [
            "check_teller_api_drift.py",
            "--output-json",
            str(self.report_dir / "fail.json"),
            "--output-text",
            str(self.report_dir / "fail.txt"),
        ]
        with patch.object(
            self.module,
            "run_live_canary",
            return_value={"mode": "live", "status": "fail", "checks": [{"name": "institutions", "status": "fail"}], "warnings": []},
        ), patch.object(os, "umask", return_value=0):
            with patch("sys.argv", args):
                exit_code = self.module.main()
        self.assertEqual(exit_code, 1)
        self.assertTrue((self.report_dir / "fail.json").exists())
        self.assertTrue((self.report_dir / "fail.txt").exists())


class FallbackSourcePathTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo_root = Path(self.temp_dir.name)
        self.original_cwd = Path.cwd()
        os.chdir(self.repo_root)
        self.addCleanup(lambda: os.chdir(self.original_cwd))

    #R001: shard-3 function tag
    def _write_fallback_docs(self) -> None:
        docs_dir = self.repo_root / "docs" / "teller-api-reference"
        docs_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            "teller-api-reference-institutions.md",
            "teller-api-reference-accounts.md",
            "teller-api-reference-identity.md",
        ):
            (docs_dir / filename).write_text("# ok\n", encoding="utf-8")

    #R001: shard-3 function tag
    def _write_static_source_files(self) -> None:
        markers = "INSTITUTIONS='/institutions'\nACCOUNTS='/accounts'\nIDENTITY='/identity'\n"
        swift_dir = self.repo_root / "src" / "macos-ui" / "Sources" / "TransactionClassifier"
        swift_dir.mkdir(parents=True, exist_ok=True)
        (swift_dir / "TellerSetupService.swift").write_text(markers, encoding="utf-8")
        (swift_dir / "ConnectAPIClient.swift").write_text(markers, encoding="utf-8")
        (self.repo_root / "06_run_classification_macos_ui.sh").write_text(markers, encoding="utf-8")
        (self.repo_root / "07_fetch_teller_api_data.py").write_text(markers, encoding="utf-8")

    #R001: shard-3 function tag
    def test_fallback_checks_pass_when_static_source_files_present_with_markers(self) -> None:
        self._write_fallback_docs()
        self._write_static_source_files()
        report = self.module.run_fallback_checks()
        self.assertEqual(report["status"], "pass")
        source_checks = [check for check in report["checks"] if check["name"].startswith("source:")]
        self.assertEqual(len(source_checks), 4)
        self.assertTrue(all(check["status"] == "pass" for check in source_checks))

    #R001: shard-3 function tag
    def test_fallback_checks_fail_when_static_source_file_missing(self) -> None:
        self._write_fallback_docs()
        report = self.module.run_fallback_checks()
        self.assertEqual(report["status"], "fail")
        source_checks = [check for check in report["checks"] if check["name"].startswith("source:")]
        self.assertEqual(len(source_checks), 4)
        self.assertTrue(any(check["status"] == "fail" for check in source_checks))

    def test_fallback_when_live_unavailable(self) -> None:
        #R040-T01: Verify fallback mode returns expected warning/failure status when live execution prerequisites are unavailable (`tests/py/test_check_teller_api_drift.py`).
        report = self.module._fallback_live_result("requests missing")
        self.assertEqual(report["mode"], "fallback")
        self.assertEqual(report["status"], "warn")
        self.assertIn("requests missing", report["warnings"])


if __name__ == "__main__":
    unittest.main()
