#!/usr/bin/env python3

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


def load_module():
    #R030: Load checker module for direct helper-function assertions.
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "check_postgres_freshness.py"
    spec = importlib.util.spec_from_file_location("check_postgres_freshness", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_postgres_freshness module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CheckPostgresFreshnessTests(unittest.TestCase):
    #R020: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()
        self.repo_root = Path(__file__).resolve().parents[2]
        self.script_path = self.repo_root / "src" / "scripts" / "check_postgres_freshness.py"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.stub_bin = self.tmp_path / "bin"
        self.stub_bin.mkdir(parents=True, exist_ok=True)
        self._write_psql_stub()

    #R020: shard-3 function tag
    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    #R020: shard-3 function tag
    def _write_psql_stub(self) -> None:
        stub_path = self.stub_bin / "psql"
        stub_path.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1\" == \"--version\" ]]; then\n"
            "  echo \"psql (PostgreSQL) ${PSQL_CLIENT_VERSION:-16.2}\"\n"
            "  exit 0\n"
            "fi\n"
            "if [[ \"${PSQL_SERVER_QUERY_EXIT:-0}\" != \"0\" && \" $* \" == *\" -tAc \"* ]]; then\n"
            "  echo \"${PSQL_SERVER_QUERY_ERROR:-server query failed}\" >&2\n"
            "  exit \"${PSQL_SERVER_QUERY_EXIT}\"\n"
            "fi\n"
            "if [[ \"$1\" == \"-tAc\" ]]; then\n"
            "  echo \"${PSQL_SERVER_VERSION_NUM:-160002}\"\n"
            "  exit 0\n"
            "fi\n"
            "if [[ \"$2\" == \"-tAc\" ]]; then\n"
            "  echo \"${PSQL_SERVER_VERSION_NUM:-160002}\"\n"
            "  exit 0\n"
            "fi\n"
            "echo \"unsupported psql invocation\" >&2\n"
            "exit 1\n",
            encoding="utf-8",
        )
        stub_path.chmod(0o755)

    #R020: shard-3 function tag
    def _run_checker(self, snapshot: dict, policy: dict, extra_args: list[str] | None = None) -> tuple[int, dict]:
        snapshot_path = self.tmp_path / "snapshot.json"
        policy_path = self.tmp_path / "policy.json"
        output_json = self.tmp_path / "report.json"
        output_text = self.tmp_path / "report.txt"

        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        cmd = [
            "python3",
            str(self.script_path),
            "--output-json",
            str(output_json),
            "--output-text",
            str(output_text),
            "--check-cves",
            "--fail-on-cve",
            "--cve-snapshot",
            str(snapshot_path),
            "--cve-policy",
            str(policy_path),
        ]
        if extra_args:
            cmd.extend(extra_args)

        env = os.environ.copy()
        env["PATH"] = f"{self.stub_bin}:{env.get('PATH', '')}"
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
        report = json.loads(output_json.read_text(encoding="utf-8"))
        return proc.returncode, report

    def test_fail_on_matching_cve_range(self) -> None:
        #R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.
        #R050-T01: Verify CVE gate fails when installed versions match affected ranges above threshold (`tests/py/test_check_postgres_freshness.py`).
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cves": [
                {
                    "id": "CVE-TEST-0001",
                    "severity": "critical",
                    "affected": [
                        {
                            "component": "client",
                            "ranges": [">=16.0,<16.3"],
                            "fixed_versions": ["16.3"],
                        }
                    ],
                }
            ],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 168,
            "fail_on_stale_snapshot": False,
        }

        code, report = self._run_checker(snapshot=snapshot, policy=policy)
        self.assertEqual(code, 1)
        self.assertTrue(report["summary"]["gate_failed"])
        self.assertEqual(len(report["cve"]["vulnerabilities"]), 1)
        self.assertEqual(report["cve"]["vulnerabilities"][0]["component"], "client")

    def test_parse_semver_normalizes(self) -> None:
        #R030-T01: Verify version parsing/normalization produces expected comparable values for semantic and server-version inputs (`tests/py/test_check_postgres_freshness.py`).
        self.assertEqual(self.module.parse_semver("16.2"), (16, 2, 0))
        self.assertEqual(self.module.parse_server_version_num("160002"), "16.2.0")
        self.assertEqual(self.module.compare_semver("16.2", "15.9"), 1)

    def test_version_in_any_range(self) -> None:
        #R035-T01: Verify version-range evaluation correctly matches and rejects boundary version cases (`tests/py/test_check_postgres_freshness.py`).
        self.assertTrue(self.module.version_in_any_range("16.2.0", [">=16.0,<16.3"]))
        self.assertFalse(self.module.version_in_any_range("16.3.0", [">=16.0,<16.3"]))

    def test_server_version_query(self) -> None:
        #R040-T01: Verify server version query flow populates parsed server version and freshness status fields (`tests/py/test_check_postgres_freshness.py`).
        snapshot = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "cves": []}
        policy = {"severity_threshold": "high", "max_snapshot_age_hours": 168, "fail_on_stale_snapshot": False}
        code, report = self._run_checker(
            snapshot=snapshot,
            policy=policy,
            extra_args=["--check-server-version", "--server-dsn", "postgresql://demo"],
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["server"]["status"], "ok")
        self.assertEqual(report["server"]["version"], "16.2.0")

    def test_cve_snapshot_load_refresh(self) -> None:
        #R045-T01: Verify snapshot refresh/load decision logic recognizes changed payloads and freshness metadata behavior (`tests/py/test_check_postgres_freshness.py`).
        existing = {"generated_at": "2026-01-01T00:00:00Z", "cves": [{"id": "CVE-1"}]}
        refreshed_same = {"generated_at": "2026-01-02T00:00:00Z", "cves": [{"id": "CVE-1"}]}
        refreshed_changed = {"generated_at": "2026-01-02T00:00:00Z", "cves": [{"id": "CVE-2"}]}
        self.assertFalse(self.module.should_write_refreshed_snapshot(existing, refreshed_same))
        self.assertTrue(self.module.should_write_refreshed_snapshot(existing, refreshed_changed))

    def test_pass_when_versions_not_in_affected_ranges(self) -> None:
        #R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cves": [
                {
                    "id": "CVE-TEST-0002",
                    "severity": "high",
                    "affected": [
                        {
                            "component": "client",
                            "ranges": [">=16.3,<16.4"],
                            "fixed_versions": ["16.4"],
                        }
                    ],
                }
            ],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 168,
            "fail_on_stale_snapshot": False,
        }

        code, report = self._run_checker(snapshot=snapshot, policy=policy)
        self.assertEqual(code, 0)
        self.assertFalse(report["summary"]["gate_failed"])
        self.assertEqual(report["cve"]["vulnerabilities"], [])

    def test_stale_snapshot_can_fail_policy(self) -> None:
        #R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.
        old_ts = datetime.now(timezone.utc) - timedelta(days=30)
        snapshot = {
            "generated_at": old_ts.isoformat().replace("+00:00", "Z"),
            "cves": [],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 24,
            "fail_on_stale_snapshot": True,
        }

        code, report = self._run_checker(snapshot=snapshot, policy=policy)
        self.assertEqual(code, 1)
        self.assertTrue(report["cve"]["snapshot_stale"])
        self.assertTrue(report["summary"]["gate_failed"])

    def test_empty_snapshot_reports_inconclusive_assurance(self) -> None:
        #R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cves": [],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 168,
            "fail_on_stale_snapshot": False,
        }

        code, report = self._run_checker(snapshot=snapshot, policy=policy)
        self.assertEqual(code, 0)
        self.assertEqual(report["cve"]["status"], "inconclusive")
        self.assertEqual(report["cve"]["assurance"], "empty-snapshot")
        self.assertFalse(report["summary"]["gate_failed"])

    def test_server_version_num_for_pg16_parses_minor_correctly(self) -> None:
        #R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cves": [
                {
                    "id": "CVE-TEST-SERVER-15",
                    "severity": "critical",
                    "affected": [
                        {
                            "component": "server",
                            "ranges": [">=15.0,<15.16"],
                            "fixed_versions": ["15.16"],
                        }
                    ],
                }
            ],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 168,
            "fail_on_stale_snapshot": False,
        }
        prior_server_num = os.environ.get("PSQL_SERVER_VERSION_NUM")
        os.environ["PSQL_SERVER_VERSION_NUM"] = "150017"
        try:
            code, report = self._run_checker(
                snapshot=snapshot,
                policy=policy,
                extra_args=["--check-server-version", "--server-dsn", "postgresql://example"],
            )
        finally:
            if prior_server_num is None:
                os.environ.pop("PSQL_SERVER_VERSION_NUM", None)
            else:
                os.environ["PSQL_SERVER_VERSION_NUM"] = prior_server_num
        self.assertEqual(code, 0)
        self.assertEqual(report["server"]["version"], "15.17.0")
        self.assertEqual(report["cve"]["vulnerabilities"], [])

    def test_server_warning_includes_attempted_target_details(self) -> None:
        #R020-T01: Verify client/server version parsing and stale-component gating for compliant and non-compliant versions.
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cves": [],
        }
        policy = {
            "severity_threshold": "high",
            "max_snapshot_age_hours": 168,
            "fail_on_stale_snapshot": False,
        }
        prior_query_exit = os.environ.get("PSQL_SERVER_QUERY_EXIT")
        prior_query_error = os.environ.get("PSQL_SERVER_QUERY_ERROR")
        os.environ["PSQL_SERVER_QUERY_EXIT"] = "2"
        os.environ["PSQL_SERVER_QUERY_ERROR"] = "connection refused"
        try:
            _, report = self._run_checker(
                snapshot=snapshot,
                policy=policy,
                extra_args=["--check-server-version", "--server-psql-args=-h dbhost -U teller -d prod"],
            )
        finally:
            if prior_query_exit is None:
                os.environ.pop("PSQL_SERVER_QUERY_EXIT", None)
            else:
                os.environ["PSQL_SERVER_QUERY_EXIT"] = prior_query_exit
            if prior_query_error is None:
                os.environ.pop("PSQL_SERVER_QUERY_ERROR", None)
            else:
                os.environ["PSQL_SERVER_QUERY_ERROR"] = prior_query_error
        joined_warnings = "\n".join(report["summary"]["warnings"])
        self.assertIn("attempted psql args: -h dbhost -U teller -d prod", joined_warnings)
        self.assertEqual(report["server"]["status"], "error")
        self.assertIn("connection refused", report["server"]["error"])

    def test_cve_policy_gate(self) -> None:
        #R055-T01: Verify CVE policy loading and gate-failed flags honor configured stale-snapshot and threshold policy values (`tests/py/test_check_postgres_freshness.py`).
        policy_path = self.tmp_path / "policy-load.json"
        policy_path.write_text(
            json.dumps({"severity_threshold": "critical", "max_snapshot_age_hours": 12, "fail_on_stale_snapshot": True}),
            encoding="utf-8",
        )
        args = type("Args", (), {"cve_policy": str(policy_path)})()
        policy = self.module._load_cve_policy(args)
        result = {"gate_failed": False, "status": "passed", "assurance": "matched"}
        self.module._mark_policy_failed(result)
        self.assertEqual(policy["severity_threshold"], "critical")
        self.assertEqual(policy["max_snapshot_age_hours"], 12)
        self.assertTrue(policy["fail_on_stale_snapshot"])
        self.assertTrue(result["gate_failed"])
        self.assertEqual(result["status"], "failed")

    def test_report_format(self) -> None:
        #R060-T01: Verify formatted report output contains expected summary fields and warning sections (`tests/py/test_check_postgres_freshness.py`).
        report = {
            "client": {"status": "ok", "version": "16.2.0", "minimum_version": "15.0"},
            "server": {"checked": True, "status": "ok", "version": "16.2.0", "minimum_version": "15.0"},
            "cve": {
                "checked": True,
                "severity_threshold": "high",
                "snapshot_cve_count": 1,
                "snapshot_generated_at": "2026-01-01T00:00:00Z",
                "snapshot_age_hours": 1.5,
                "status": "passed",
                "assurance": "matched-against-snapshot",
                "vulnerabilities": [],
            },
            "summary": {"warnings": ["warn"], "stale_components": [], "gate_failed": False},
        }
        text = self.module.format_text_report(report)
        self.assertIn("PostgreSQL freshness report", text)
        self.assertIn("- Warnings:", text)

    def test_cli_artifact_and_exit(self) -> None:
        #R065-T01: Verify CLI run writes artifacts and exits with gate-driven status code (`tests/py/test_check_postgres_freshness.py`).
        snapshot = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "cves": []}
        policy = {"severity_threshold": "high", "max_snapshot_age_hours": 168, "fail_on_stale_snapshot": False}
        code, report = self._run_checker(snapshot=snapshot, policy=policy)
        self.assertEqual(code, 0)
        self.assertIn("summary", report)
        self.assertIn("cve", report)


class PostgresFreshnessHelperTests(unittest.TestCase):
    #R020: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()

    def test_semver_helpers_cover_invalid_and_legacy_paths(self) -> None:
        #R030-T02: semver helpers cover invalid, legacy, and minimum-threshold branches.
        self.assertIsNone(self.module.parse_semver("abc"))
        self.assertIsNone(self.module.compare_semver("bad", "1.0"))
        self.assertEqual(self.module.parse_server_version_num("90603"), "9.6.3")
        self.assertIsNone(self.module.parse_server_version_num("not-a-number"))
        self.assertIsNone(self.module.meets_minimum("16.2", None))
        self.assertEqual(self.module.compare_semver("1.0", "1.0"), 0)

    def test_severity_and_component_helpers(self) -> None:
        #R030-T03: severity/component helpers normalize unknown values and scopes.
        self.assertEqual(self.module.normalize_severity("MODERATE"), "moderate")
        self.assertEqual(self.module.normalize_severity("weird"), "unknown")
        self.assertTrue(self.module.severity_meets_threshold("critical", "high"))
        self.assertFalse(self.module.severity_meets_threshold("low", "high"))
        self.assertEqual(self.module.component_to_scope("Contrib module"), "server")
        self.assertEqual(self.module.component_to_scope("random text"), "both")
        self.assertEqual(self.module.score_to_severity(None), "unknown")
        self.assertEqual(self.module.score_to_severity(9.1), "critical")
        self.assertEqual(self.module.score_to_severity(7.1), "high")
        self.assertEqual(self.module.score_to_severity(4.1), "medium")
        self.assertEqual(self.module.score_to_severity(1.0), "low")

    def test_range_and_datetime_helpers(self) -> None:
        #R035-T02: range and datetime helpers cover invalid-constraint and empty-input branches.
        self.assertFalse(self.module.satisfies_constraint("16.2.0", "bogus"))
        self.assertFalse(self.module.satisfies_range("16.2.0", ""))
        self.assertFalse(self.module.version_in_any_range(None, [">=16.0,<16.3"]))
        self.assertIsNone(self.module.parse_iso_datetime("not-iso"))
        self.assertEqual(self.module.extract_major("16.2.1"), "16")
        self.assertIsNone(self.module.extract_major("x"))
        self.assertEqual(self.module.strip_html("<b>hello</b> &amp; world"), "hello & world")

    def test_validate_major_and_fetch_json_shapes(self) -> None:
        #R045-T02: major validation and JSON-file loader handle invalid values and shapes.
        with self.assertRaises(ValueError):
            self.module.validate_postgresql_major("00")
        self.assertEqual(self.module.validate_postgresql_major("15"), "15")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.json"
            p.write_text("[]", encoding="utf-8")
            self.assertIsNone(self.module.read_json_file(str(p)))
            p.write_text(json.dumps({"ok": 1}), encoding="utf-8")
            self.assertEqual(self.module.read_json_file(str(p)), {"ok": 1})

    def test_snapshot_freshness_policy_paths(self) -> None:
        #R045-T03: snapshot freshness policy marks stale/invalid timestamps as expected.
        args = type("Args", (), {"fail_on_cve": True})()
        result = {
            "warnings": [],
            "snapshot_stale": None,
            "status": "evaluating",
            "assurance": "unknown",
            "fail_on_stale_snapshot": True,
            "max_snapshot_age_hours": 1,
            "gate_failed": False,
        }
        self.module._apply_snapshot_freshness(result, None, args)
        self.assertTrue(result["snapshot_stale"])
        self.assertTrue(result["gate_failed"])

    def test_findings_and_summary_merge_helpers(self) -> None:
        #R050-T02: finding collection/merge helpers handle invalid specs and stale-policy summary merge.
        findings = self.module._findings_for_spec(
            cve_id="CVE-X",
            severity="high",
            title="title",
            spec={"component": "both", "ranges": [">=16.0,<16.3"], "fixed_versions": ["16.3"]},
            client_version="16.2.0",
            server_version="16.2.0",
        )
        self.assertEqual(len(findings), 2)
        self.assertEqual(self.module._findings_for_spec(
            cve_id="CVE-Y",
            severity="high",
            title=None,
            spec="invalid",
            client_version="16.2.0",
            server_version="16.2.0",
        ), [])
        cve_result = {
            "warnings": ["warn-a"],
            "vulnerabilities": [],
            "snapshot_stale": True,
            "checked": True,
            "gate_failed": True,
        }
        warnings = []
        stale = []
        self.module._merge_cve_summary(cve_result=cve_result, warnings=warnings, stale_components=stale)
        self.assertIn("warn-a", warnings)
        self.assertIn("cve_snapshot_stale", stale)
        self.assertIn("cve_policy_unmet", stale)

    def test_server_command_and_init_payload_helpers(self) -> None:
        #R040-T02: server-command and initial payload helpers honor DSN/args/check flags.
        args = type(
            "Args",
            (),
            {
                "server_psql_args": "-h db -U user",
                "server_dsn": "postgresql://x",
                "check_server_version": True,
                "min_client_version": "16.0",
                "min_server_version": "15.0",
                "fail_on_stale": True,
                "check_cves": True,
                "fail_on_cve": False,
                "cve_snapshot": "",
                "cve_policy": "",
            },
        )()
        cmd = self.module._build_server_version_command(args)
        self.assertIn("-h", cmd)
        self.assertIn("db", cmd)
        client_info = self.module._initial_client_info(args, psql_path=None)
        server_info = self.module._initial_server_info(args, psql_path=None)
        self.assertEqual(client_info["status"], "missing")
        self.assertEqual(server_info["status"], "unknown")
        policy = self.module._policy_from_args(args)
        self.assertTrue(policy["check_server_version"])

    def test_fetch_security_page_branches(self) -> None:
        #R045-T04: security-page fetch covers missing requests, network errors, and host validation.
        with patch.object(self.module, "requests", None):
            with self.assertRaises(RuntimeError):
                self.module.fetch_postgresql_security_page("16")

        class _ReqErr:
            class RequestException(RuntimeError):
                pass

            @staticmethod
            #R045: nested helper function tag
            def get(*_args, **_kwargs):
                raise _ReqErr.RequestException("network down")

        with patch.object(self.module, "requests", _ReqErr):
            with self.assertRaises(RuntimeError):
                self.module.fetch_postgresql_security_page("16")

        class _RespBadHost:
            url = "http://evil.example.com/page"
            text = "<html></html>"
            encoding = "utf-8"

            @staticmethod
            #R045: nested helper function tag
            def raise_for_status():
                return None

        class _ReqBadHost:
            RequestException = RuntimeError

            @staticmethod
            #R045: nested helper function tag
            def get(*_args, **_kwargs):
                return _RespBadHost()

        with patch.object(self.module, "requests", _ReqBadHost):
            with self.assertRaises(RuntimeError):
                self.module.fetch_postgresql_security_page("16")

    def test_fetch_cve_snapshot_parses_security_rows(self) -> None:
        #R045-T05: CVE snapshot parser extracts CVE rows from postgresql.org table markup.
        html_payload = (
            "<table><tr>"
            "<td><a>CVE-2026-1111</a></td>"
            "<td>affected</td>"
            "<td>16.3</td>"
            "<td>8.1 client</td>"
            "<td>description more details</td>"
            "</tr></table>"
        )
        with patch.object(self.module, "fetch_postgresql_security_page", return_value=html_payload):
            snapshot = self.module.fetch_postgresql_cve_snapshot({"16"})
        self.assertEqual(snapshot["source"], "postgresql.org/support/security/<major>/")
        self.assertEqual(len(snapshot["cves"]), 1)
        self.assertEqual(snapshot["cves"][0]["id"], "CVE-2026-1111")

    def test_check_client_server_version_branches(self) -> None:
        #R040-T03: client/server check helpers cover missing, error, stale, and success branches.
        args = type(
            "Args",
            (),
            {
                "fail_on_stale": True,
                "min_client_version": "16.0",
                "check_server_version": True,
                "min_server_version": "16.0",
                "server_psql_args": "",
                "server_dsn": "",
            },
        )()
        warnings = []
        stale = []
        client_info = self.module._initial_client_info(args, psql_path=None)
        self.module._check_client_version(
            args=args,
            psql_path=None,
            client_info=client_info,
            warnings=warnings,
            stale_components=stale,
        )
        self.assertIn("client_missing", stale)

        with patch.object(self.module, "run_command", return_value=(1, "bad")):
            client_info = self.module._initial_client_info(args, psql_path="/usr/bin/psql")
            warnings = []
            stale = []
            self.module._check_client_version(
                args=args,
                psql_path="/usr/bin/psql",
                client_info=client_info,
                warnings=warnings,
                stale_components=stale,
            )
        self.assertEqual(client_info["status"], "error")
        self.assertIn("client_unknown", stale)

        with patch.object(self.module, "run_command", return_value=(0, "psql (PostgreSQL) 15.1")):
            client_info = self.module._initial_client_info(args, psql_path="/usr/bin/psql")
            warnings = []
            stale = []
            self.module._check_client_version(
                args=args,
                psql_path="/usr/bin/psql",
                client_info=client_info,
                warnings=warnings,
                stale_components=stale,
            )
        self.assertEqual(client_info["status"], "stale")
        self.assertIn("client_outdated", stale)

        with patch.object(self.module, "run_command", return_value=(0, "160002")):
            server_info = self.module._initial_server_info(args, psql_path="/usr/bin/psql")
            warnings = []
            stale = []
            self.module._check_server_version(
                args=args,
                psql_path="/usr/bin/psql",
                server_info=server_info,
                warnings=warnings,
                stale_components=stale,
            )
        self.assertEqual(server_info["status"], "ok")

    def test_evaluate_cves_no_snapshot_and_invalid_entries(self) -> None:
        #R050-T03: CVE evaluation handles missing snapshots and invalid cve entry shapes.
        args = type(
            "Args",
            (),
            {
                "check_cves": True,
                "fail_on_cve": True,
                "cve_policy": "",
                "cve_snapshot": "",
                "refresh_cve_snapshot": False,
            },
        )()
        with patch.object(self.module, "_refresh_or_load_snapshot", return_value=None):
            result = self.module.evaluate_cves(args=args, client_version="16.2.0", server_version="16.2.0")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["gate_failed"])

        snapshot = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "cves": "not-a-list"}
        with patch.object(self.module, "_refresh_or_load_snapshot", return_value=snapshot):
            result = self.module.evaluate_cves(args=args, client_version="16.2.0", server_version="16.2.0")
        self.assertEqual(result["status"], "inconclusive")

    def test_run_command_timeout_and_target_description(self) -> None:
        #R040-T04: command runner timeout handling and server target descriptions.
        timeout = subprocess.TimeoutExpired(cmd=["x"], timeout=1)
        with patch.object(self.module.subprocess, "run", side_effect=timeout):
            rc, output = self.module.run_command(["x"], timeout_seconds=1)
        self.assertEqual(rc, 124)
        self.assertIn("timed out", output)

        args = type("Args", (), {"server_psql_args": "", "server_dsn": "postgresql://x"})()
        self.assertEqual(self.module.describe_server_target(args), "server dsn")

if __name__ == "__main__":
    unittest.main()
