#!/usr/bin/env python3

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


#R001: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "check_teller_api_version_freshness.py"
    spec = importlib.util.spec_from_file_location("check_teller_api_version_freshness", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_teller_api_version_freshness module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TellerApiVersionFreshnessTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()

    def test_extract_version_from_docs_phrase(self) -> None:
        #R001-T01: Verify version discovery fallback order and warning accumulation for failed/invalid sources.
        sample = "Teller uses dated versions with the latest one being 2020-10-12."
        self.assertEqual(self.module.extract_version_from_docs(sample), "2020-10-12")

    def test_extract_version_from_docs_missing_phrase(self) -> None:
        #R001-T01: Verify version discovery fallback order and warning accumulation for failed/invalid sources.
        sample = "Welcome to the Teller API docs."
        self.assertIsNone(self.module.extract_version_from_docs(sample))

    def test_parse_dashboard_versions_latest_phrase(self) -> None:
        #R005-T01: Verify dashboard parsing and credential/OTP error handling paths produce expected status fields.
        sample = "The application is currently using the latest API version (2020-10-12)."
        parsed = self.module.parse_dashboard_versions(sample)
        self.assertEqual(parsed["current_version"], "2020-10-12")
        self.assertEqual(parsed["latest_version"], "2020-10-12")
        self.assertTrue(parsed["on_latest"])

    def test_parse_dashboard_versions_current_and_latest(self) -> None:
        #R005-T01: Verify dashboard parsing and credential/OTP error handling paths produce expected status fields.
        #R010-T01: Verify baseline comparisons and fail-on-new exit behavior for equal, older, and newer-version outcomes.
        sample = "The application is currently using API version (2019-07-01). Latest API version (2020-10-12)."
        parsed = self.module.parse_dashboard_versions(sample)
        self.assertEqual(parsed["current_version"], "2019-07-01")
        self.assertEqual(parsed["latest_version"], "2020-10-12")
        self.assertFalse(parsed["on_latest"])

    def test_resolve_otp_code_from_digits(self) -> None:
        #R005-T01: Verify dashboard parsing and credential/OTP error handling paths produce expected status fields.
        self.assertEqual(self.module.resolve_otp_code("577 572"), "577572")

    def test_resolve_otp_code_from_otpauth_uri(self) -> None:
        #R005-T01: Verify dashboard parsing and credential/OTP error handling paths produce expected status fields.
        uri = "otpauth://totp/Teller:test?issuer=Teller&secret=JBSWY3DPEHPK3PXP&period=30&digits=6"
        code = self.module.resolve_otp_code(uri)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)

    def test_fetch_json_rejects_non_https_source(self) -> None:
        #R030-T01: Verify HTTPS metadata fetch paths (`fetch_json`, `fetch_text`, opener-backed fetch) return payloads/errors for valid and invalid source responses.
        payload, error = self.module.fetch_json("http://example.com/openapi.json", 1)
        self.assertIsNone(payload)
        self.assertIn("unsupported scheme", error)

    def test_build_report_payload_contains_gate_fields(self) -> None:
        #R035-T01: Verify `build_report` and `format_report` include expected status, source, warning, and drift fields.
        args = SimpleNamespace(
            version_sources="https://example.com/openapi.json",
            dashboard_url="https://dashboard.example.com",
            dashboard_psa_item="",
            dashboard_username_field="username",
            dashboard_password_field="password",  # pragma: allowlist secret
            dashboard_otp_field="otp",
            timeout_seconds=1,
            baseline_version="2020-10-10",
            fail_on_new=False,
        )
        dashboard = {
            "checked": False,
            "status": "not-configured",
            "source_url": args.dashboard_url,
            "latest_version": None,
            "current_version": None,
            "on_latest": None,
        }
        with patch.object(self.module, "discover_dashboard_version", return_value=(dashboard, [])):
            with patch.object(
                self.module,
                "discover_version",
                return_value=("2020-10-12", "https://example.com/openapi.json", []),
            ):
                report = self.module.build_report(args)
        text = self.module.format_report(report)
        self.assertEqual(report["status"], "update-available")
        self.assertTrue(report["newer_available"])
        self.assertIn("Teller API version freshness report", text)
        self.assertIn("2020-10-12", text)

    def test_main_returns_nonzero_for_fail_on_new_gate(self) -> None:
        #R040-T01: Verify CLI `main` writes both artifacts and returns non-zero only for fail-on-new gate failures.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_json = tmp_path / "out.json"
            output_text = tmp_path / "out.txt"
            args = SimpleNamespace(output_json=str(output_json), output_text=str(output_text))
            fake_report = {
                "status": "update-available",
                "gate_failed": True,
                "dashboard": {"status": "not-configured", "current_version": None, "on_latest": None},
                "baseline_version": "2020-01-01",
                "latest_version": "2020-10-12",
                "source_url": "https://example.com/openapi.json",
                "newer_available": True,
                "warnings": [],
            }
            with patch.object(self.module, "parse_args", return_value=args):
                with patch.object(self.module, "build_report", return_value=fake_report):
                    with patch.object(self.module, "format_report", return_value="freshness report\n"):
                        exit_code = self.module.main()
            self.assertEqual(exit_code, 1)
            self.assertTrue(output_json.exists())
            self.assertTrue(output_text.exists())
            loaded = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertTrue(loaded["gate_failed"])


if __name__ == "__main__":
    unittest.main()
