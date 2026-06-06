#!/usr/bin/env python3

import importlib.util
import json
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


#R001: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "check_binary_integrity.py"
    spec = importlib.util.spec_from_file_location("check_binary_integrity", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load check_binary_integrity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#R001: shard-3 function tag
def make_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR)


class CheckBinaryIntegrityTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self) -> None:
        self.module = load_module()

    def test_make_report_detects_missing_and_version_stale(self) -> None:
        #R001-T01: Evaluate a policy with present and missing commands and verify report includes executable path, version, and hash fields (`tests/py/test_check_binary_integrity.py`).
        #R005-T01: Verify report generation counts missing required and stale-version statuses correctly (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "fake-tool"
            make_executable(
                fake_bin,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    echo "fake-tool version 1.0.0"
                    """
                ),
            )
            policy_path = tmp_path / "policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "id": "missing-required",
                                "command": "definitely-not-on-path-xyz",
                                "required": True,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": "1.0.0",
                                "allowed_sha256": [],
                            },
                            {
                                "id": "stale-tool",
                                "command": str(fake_bin),
                                "required": True,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": "2.0.0",
                                "allowed_sha256": [],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = self.module.make_report(policy_path)
        self.assertEqual(report["summary"]["missing_required"], 1)
        self.assertEqual(report["summary"]["version_stale"], 1)
        statuses = {entry["id"]: entry["status"] for entry in report["binaries"]}
        self.assertEqual(statuses["missing-required"], "missing")
        self.assertEqual(statuses["stale-tool"], "version_stale")

    def test_main_fails_on_hash_mismatch_when_enabled(self) -> None:
        #R010-T01: Verify `main()` returns failing exit status only when the corresponding strict gate is enabled and its condition is present (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "fake-hash-tool"
            make_executable(
                fake_bin,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    echo "fake-hash-tool 3.2.1"
                    """
                ),
            )
            policy_path = tmp_path / "policy.json"
            out_json = tmp_path / "report.json"
            out_text = tmp_path / "report.txt"
            policy_path.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "id": "hash-tool",
                                "command": str(fake_bin),
                                "required": True,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": "1.0.0",
                                "allowed_sha256": ["0" * 64],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            argv = sys.argv
            try:
                sys.argv = [
                    "check_binary_integrity.py",
                    "--policy",
                    str(policy_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-hash",
                ]
                rc = self.module.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["hash_mismatch"], 1)

    def test_make_report_marks_hash_allowlist_match_ok(self) -> None:
        #R015-T01: Verify a digest in `allowed_sha256` produces an `ok` hash status and no hash mismatch count (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "fake-hash-ok-tool"
            make_executable(
                fake_bin,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    echo "fake-hash-ok-tool 1.2.3"
                    """
                ),
            )
            expected_digest = self.module.sha256_file(str(fake_bin))
            policy_path = tmp_path / "policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "id": "hash-ok-tool",
                                "command": str(fake_bin),
                                "required": True,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": None,
                                "allowed_sha256": [expected_digest.upper()],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = self.module.make_report(policy_path)
        self.assertEqual(report["summary"]["hash_mismatch"], 0)
        entry = report["binaries"][0]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["hash_status"], "ok")

    def test_main_passes_without_failure_flags(self) -> None:
        #R010-T01: Verify `main()` returns failing exit status only when the corresponding strict gate is enabled and its condition is present (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "optional-tool"
            make_executable(
                fake_bin,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    echo "optional-tool 1.0.0"
                    """
                ),
            )
            policy_path = tmp_path / "policy.json"
            out_json = tmp_path / "report.json"
            out_text = tmp_path / "report.txt"
            policy_path.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "id": "optional-tool",
                                "command": str(fake_bin),
                                "required": False,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": None,
                                "allowed_sha256": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            argv = sys.argv
            try:
                sys.argv = [
                    "check_binary_integrity.py",
                    "--policy",
                    str(policy_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                ]
                rc = self.module.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 0)
            self.assertTrue(out_text.exists())

    def test_normalize_hex_digest_canonicalizes(self) -> None:
        #R030-T01: Verify `_normalize_hex_digest` canonicalizes case and whitespace for comparison-safe matching (`tests/py/test_check_binary_integrity.py`).
        self.assertEqual(self.module._normalize_hex_digest("  AaBbCc  "), "aabbcc")

    def test_load_policy_validates_entries(self) -> None:
        #R035-T01: Verify `load_policy` rejects malformed manifest entries and accepts typed valid entries (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            policy_path.write_text(json.dumps({"binaries": [{"id": "x", "command": "", "version_args": []}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.module.load_policy(policy_path)

    def test_version_probe_compare(self) -> None:
        #R040-T01: Verify probe parse/compare flow classifies older/newer/equal version relationships correctly (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "probe-tool"
            make_executable(
                fake_bin,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    echo "probe-tool v2.4.0"
                    """
                ),
            )
            raw, error = self.module.run_version_probe(str(fake_bin), ("--version",))
            parsed = self.module.parse_version(raw, r"(\d+\.\d+\.\d+)")
        self.assertIsNone(error)
        self.assertEqual(parsed, "2.4.0")
        self.assertEqual(self.module.compare_versions(parsed, "2.3.9"), 1)
        self.assertEqual(self.module.compare_versions(parsed, "2.4.0"), 0)
        self.assertEqual(self.module.compare_versions(parsed, "2.5.0"), -1)

    def test_sha256_file_matches_known_digest(self) -> None:
        #R045-T01: Verify `sha256_file` returns the known digest for a deterministic file payload (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = tmp_path / "payload.bin"
            payload.write_bytes(b"eggnest-binary-integrity")
            digest = self.module.sha256_file(str(payload))
        self.assertEqual(digest, "8b35c3e0ffe8cd1db3b4ab172194090c3399cd7370da5bb87e2cc51ce5d320b8")

    def test_cli_gate_fails_on_policy_violation(self) -> None:
        #R050-T01: Verify CLI gate mode returns non-zero and writes report artifacts when policy violations are present (`tests/py/test_check_binary_integrity.py`).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            policy_path = tmp_path / "policy.json"
            out_json = tmp_path / "report.json"
            out_text = tmp_path / "report.txt"
            policy_path.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "id": "required-missing",
                                "command": "no-such-binary",
                                "required": True,
                                "version_args": ["--version"],
                                "version_pattern": "(\\d+\\.\\d+\\.\\d+)",
                                "min_version": "1.0.0",
                                "allowed_sha256": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            argv = sys.argv
            try:
                sys.argv = [
                    "check_binary_integrity.py",
                    "--policy",
                    str(policy_path),
                    "--output-json",
                    str(out_json),
                    "--output-text",
                    str(out_text),
                    "--fail-on-missing-required",
                ]
                rc = self.module.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 1)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_text.exists())


if __name__ == "__main__":
    unittest.main()
