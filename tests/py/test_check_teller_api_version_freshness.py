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


class TellerApiVersionFreshnessHelperTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()

    def test_version_compare_and_source_resolution_helpers(self) -> None:
        #R010-T02: version compare/source resolution helpers cover fallback and unknown paths.
        self.assertIsNone(self.module.parse_semver("abc"))
        self.assertIsNone(self.module.compare_versions("abc", "1.0"))
        self.assertEqual(self.module.compare_versions("1.2.0", "1.1.9"), 1)
        self.assertEqual(
            self.module._resolve_version_sources(""),
            list(self.module.DEFAULT_VERSION_URLS),
        )
        self.assertEqual(self.module._resolve_version_sources("https://a, https://b"), ["https://a", "https://b"])

    def test_otp_helpers_cover_digits_and_invalid_otpauth(self) -> None:
        #R005-T02: OTP helpers cover digit extraction and invalid otpauth payloads.
        self.assertEqual(self.module._otp_from_digits("abc12-34-56"), "123456")
        self.assertEqual(self.module._otp_from_digits("abc"), "")
        self.assertEqual(self.module._totp_from_otpauth("otpauth://totp/x?issuer=y"), "")
        self.assertEqual(self.module.resolve_otp_code(""), "")

    def test_dashboard_latest_logic_and_error_payload(self) -> None:
        #R005-T03: dashboard latest-version logic and standardized error payloads.
        self.assertTrue(self.module._is_dashboard_on_latest("currently using the latest API version", "2020-10-12", None))
        self.assertFalse(self.module._is_dashboard_on_latest("", "2019-01-01", "2020-10-12"))
        result, warnings = self.module._dashboard_error_result({"checked": False, "status": "x"}, [], "oops")
        self.assertTrue(result["checked"])
        self.assertEqual(result["status"], "error")
        self.assertIn("oops", warnings)

    def test_compute_newer_available_branches(self) -> None:
        #R010-T03: drift computation handles dashboard-latest, missing baseline, and unknown latest cases.
        status, newer = self.module._compute_newer_available(None, "2020-10-12", {"checked": False, "on_latest": None})
        self.assertEqual((status, newer), ("unknown", None))
        status, newer = self.module._compute_newer_available("2020-10-12", None, {"checked": False, "on_latest": None})
        self.assertEqual((status, newer), ("ok", None))
        status, newer = self.module._compute_newer_available("2020-10-12", "2019-10-12", {"checked": False, "on_latest": None})
        self.assertEqual((status, newer), ("update-available", True))
        status, newer = self.module._compute_newer_available("2020-10-12", "2019-10-12", {"checked": True, "on_latest": True})
        self.assertEqual((status, newer), ("ok", False))

    def test_discover_dashboard_version_configuration_and_credential_failures(self) -> None:
        #R005-T04: dashboard discovery handles missing PSA config, missing binary, and missing credentials.
        result, warnings = self.module.discover_dashboard_version(
            dashboard_url="https://dashboard.example.com",
            psa_item="",
            username_field="username",
            password_field="pwd_field",  # pragma: allowlist secret
            otp_field="otp",
            timeout_seconds=1,
        )
        self.assertEqual(result["status"], "not-configured")
        self.assertEqual(warnings, [])

        with patch.object(self.module.shutil, "which", return_value=None):
            result, warnings = self.module.discover_dashboard_version(
                dashboard_url="https://dashboard.example.com",
                psa_item="ITEM",
                username_field="username",
                password_field="pwd_field",  # pragma: allowlist secret
                otp_field="otp",
                timeout_seconds=1,
            )
        self.assertEqual(result["status"], "not-configured")
        self.assertTrue(any("1psa not found" in warning for warning in warnings))

        with (
            patch.object(self.module.shutil, "which", return_value="/usr/bin/1psa"),
            patch.object(self.module, "_load_dashboard_credentials", return_value=("", "", "")),
        ):
            result, warnings = self.module.discover_dashboard_version(
                dashboard_url="https://dashboard.example.com",
                psa_item="ITEM",
                username_field="username",
                password_field="pwd_field",  # pragma: allowlist secret
                otp_field="otp",
                timeout_seconds=1,
            )
        self.assertEqual(result["status"], "not-configured")
        self.assertTrue(any("Could not read Teller dashboard credentials" in warning for warning in warnings))

    def test_fetch_helpers_cover_requests_missing_and_error_paths(self) -> None:
        #R030-T02: fetch helpers cover missing requests, network errors, invalid JSON, and opener URL errors.
        with patch.object(self.module, "requests", None):
            payload, error = self.module.fetch_json("https://example.com/data.json", 1)
            self.assertIsNone(payload)
            self.assertIn("requests is required", error)

        class _Req:
            class RequestException(RuntimeError):
                pass

            @staticmethod
            #R030: nested helper function tag
            def get(*_args, **_kwargs):
                raise _Req.RequestException("boom")

        with patch.object(self.module, "requests", _Req):
            payload, error = self.module.fetch_text("https://example.com/docs", 1)
            self.assertIsNone(payload)
            self.assertIn("boom", error)

        class _Resp:
            text = "[]"

            @staticmethod
            #R030: nested helper function tag
            def raise_for_status():
                return None

        class _ReqJson:
            class RequestException(RuntimeError):
                pass

            @staticmethod
            #R030: nested helper function tag
            def get(*_args, **_kwargs):
                return _Resp()

        with patch.object(self.module, "requests", _ReqJson):
            payload, error = self.module.fetch_json("https://example.com/data.json", 1)
            self.assertIsNone(payload)
            self.assertIn("not an object", error)

        module = self.module

        class _Opener:
            #R030: nested helper function tag
            def open(self, *_args, **_kwargs):
                raise module.URLError("bad url")

        payload, error = self.module.fetch_text_with_opener("https://example.com", 1, _Opener())
        self.assertIsNone(payload)
        self.assertIn("bad url", error)

    def test_fetch_json_invalid_json_and_fetch_text_scheme_guard(self) -> None:
        #R030-T03: fetch helpers reject non-JSON payloads and non-HTTPS text sources.
        class _Resp:
            text = "{not-json"

            @staticmethod
            #R030: nested helper function tag
            def raise_for_status():
                return None

        class _Req:
            class RequestException(RuntimeError):
                pass

            @staticmethod
            #R030: nested helper function tag
            def get(*_args, **_kwargs):
                return _Resp()

        with patch.object(self.module, "requests", _Req):
            payload, error = self.module.fetch_json("https://example.com/a.json", 1)
        self.assertIsNone(payload)
        self.assertIn("invalid JSON", error)
        payload, error = self.module.fetch_text("http://example.com/docs", 1)
        self.assertIsNone(payload)
        self.assertIn("unsupported scheme", error)

    def test_submit_helpers_cover_success_and_failure(self) -> None:
        #R005-T05: login/MFA submit helpers handle opener failures and successful responses.
        parsed = self.module.urlsplit("https://dashboard.example.com/settings")

        class _SuccessOpener:
            class _Resp:
                #R005: nested helper function tag
                def __enter__(self):
                    return self

                #R005: nested helper function tag
                def __exit__(self, _exc_type, _exc, _tb):
                    return False

                @staticmethod
                #R005: nested helper function tag
                def read():
                    return b"ok"

            #R005: nested helper function tag
            def open(self, *_args, **_kwargs):
                return self._Resp()

        response, error = self.module._submit_dashboard_login(
            _SuccessOpener(),
            parsed,
            "user",
            "pass",
            "123456",
            "csrf",
            1,
        )
        self.assertEqual(response, "ok")
        self.assertEqual(error, "")

        class _FailOpener:
            #R005: nested helper function tag
            def open(self, *_args, **_kwargs):
                raise RuntimeError("nope")

        response, error = self.module._submit_dashboard_login(
            _FailOpener(),
            parsed,
            "user",
            "pass",
            "",
            "csrf",
            1,
        )
        self.assertIsNone(response)
        self.assertIn("nope", error)
        self.assertIn("nope", self.module._submit_dashboard_mfa(_FailOpener(), parsed, "123456", "csrf", 1))
        self.assertEqual(self.module._submit_dashboard_mfa(_SuccessOpener(), parsed, "123456", "csrf", 1), "")

    def test_discover_version_iterates_sources_and_warnings(self) -> None:
        #R001-T02: source discovery iterates docs/json endpoints and accumulates warnings.
        with (
            patch.object(self.module, "fetch_text", return_value=(None, "timeout")),
            patch.object(self.module, "fetch_json", return_value=({"info": {}}, "")),
        ):
            version, source, warnings = self.module.discover_version(
                ["https://x/docs/api", "https://x/openapi.json"],
                1,
            )
        self.assertIsNone(version)
        self.assertIsNone(source)
        self.assertTrue(any("timeout" in warning for warning in warnings))
        self.assertTrue(any("missing info.version" in warning for warning in warnings))

    def test_dashboard_authenticated_flow_helpers(self) -> None:
        #R005-T06: authenticated dashboard flow covers login-page, csrf, mfa, and parse-result branches.
        base_result = {
            "checked": False,
            "status": "not-configured",
            "source_url": "https://dashboard.example.com",
            "latest_version": None,
            "current_version": None,
            "on_latest": None,
        }
        with patch.object(self.module, "fetch_text_with_opener", return_value=(None, "load fail")):
            result, warnings = self.module._discover_dashboard_version_authenticated(
                dashboard_url="https://dashboard.example.com",
                timeout_seconds=1,
                username="u",
                password="p",
                otp="",
                result=dict(base_result),
                warnings=[],
            )
        self.assertEqual(result["status"], "not-configured")
        self.assertTrue(any("Failed to load Teller dashboard login page" in warning for warning in warnings))

        with (
            patch.object(self.module, "fetch_text_with_opener", return_value=("<html></html>", "")),
        ):
            result, warnings = self.module._discover_dashboard_version_authenticated(
                dashboard_url="https://dashboard.example.com",
                timeout_seconds=1,
                username="u",
                password="p",
                otp="",
                result=dict(base_result),
                warnings=[],
            )
        self.assertTrue(any("_csrf_token" in warning for warning in warnings))

        with (
            patch.object(self.module, "fetch_text_with_opener", return_value=('<input name="_csrf_token" value="x" />', "")),
            patch.object(self.module, "_submit_dashboard_login", return_value=("action=\"/session/mfa\"", "")),
        ):
            result, warnings = self.module._discover_dashboard_version_authenticated(
                dashboard_url="https://dashboard.example.com",
                timeout_seconds=1,
                username="u",
                password="p",
                otp="",
                result=dict(base_result),
                warnings=[],
            )
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("requires MFA" in warning for warning in warnings))

    def test_dashboard_mfa_and_apply_parsed_version_branches(self) -> None:
        #R005-T07: MFA helper and parsed-version applier cover csrf/mfa-fail and parse-miss branches.
        self.assertEqual(
            self.module._maybe_complete_dashboard_mfa(
                login_response="plain response",
                otp="",
                opener=object(),
                parsed_url=self.module.urlsplit("https://dashboard.example.com"),
                timeout_seconds=1,
            ),
            "",
        )
        self.assertIn(
            "_csrf_token",
            self.module._maybe_complete_dashboard_mfa(
                login_response='action="/session/mfa"',
                otp="123456",
                opener=object(),
                parsed_url=self.module.urlsplit("https://dashboard.example.com"),
                timeout_seconds=1,
            ),
        )
        with patch.object(self.module, "_submit_dashboard_mfa", return_value="mfa broken"):
            self.assertIn(
                "Failed to submit",
                self.module._maybe_complete_dashboard_mfa(
                    login_response='action="/session/mfa" name="_csrf_token" value="x"',
                    otp="123456",
                    opener=object(),
                    parsed_url=self.module.urlsplit("https://dashboard.example.com"),
                    timeout_seconds=1,
                ),
            )

        result, warnings = self.module._apply_parsed_dashboard_versions(
            {"checked": False, "status": "x", "latest_version": None, "current_version": None, "on_latest": None},
            [],
            {"latest_version": None, "current_version": None, "on_latest": None},
        )
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("could not parse API version text" in warning for warning in warnings))

    def test_read_1psa_field_password_and_fallback_paths(self) -> None:
        #R005-T08: 1psa reader covers password fast-path, fallback field read, and command failure.
        class _Result:
            #R005: nested helper function tag
            def __init__(self, code, out):
                self.returncode = code
                self.stdout = out

        with patch.object(self.module.subprocess, "run", return_value=_Result(0, "secret\n")):
            self.assertEqual(self.module.read_1psa_field("ITEM", "password"), "secret")

        with patch.object(self.module.subprocess, "run", side_effect=[_Result(1, ""), _Result(0, "user\n")]):
            self.assertEqual(self.module.read_1psa_field("ITEM", "password"), "user")

        with patch.object(self.module.subprocess, "run", return_value=_Result(1, "")):
            self.assertEqual(self.module.read_1psa_field("ITEM", "username"), "")

if __name__ == "__main__":
    unittest.main()
