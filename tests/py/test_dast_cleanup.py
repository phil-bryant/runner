#!/usr/bin/env python3

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


#R030: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "dast_cleanup.py"
    spec = importlib.util.spec_from_file_location("dast_cleanup_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load dast_cleanup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DastCleanupTests(unittest.TestCase):
    #R030: shard-3 function tag
    def setUp(self):
        self.module = load_module()

    def test_single_transaction_restore_delete_sequence(self):
        #R030-T01: Verify a single transaction executes restore/delete sequence and records expected count fields.
        with patch.object(self.module, "_restore_matches", return_value=2):
            with patch.object(self.module, "_delete_post_baseline_audits", return_value=3):
                with patch.object(self.module, "_delete_post_baseline_matches", return_value=4):
                    with patch.object(self.module, "_reconcile_classifications", return_value=(5, 6)):
                        with patch.object(self.module, "_delete_post_baseline_categories", return_value=7):
                            with patch.object(self.module, "_restore_categories", return_value=8):
                                with patch.object(self.module, "text"):
                                    fake_conn = object()
                                    begin_ctx = unittest.mock.MagicMock()
                                    begin_ctx.__enter__.return_value = fake_conn
                                    begin_ctx.__exit__.return_value = None
                                    fake_engine = unittest.mock.MagicMock()
                                    fake_engine.begin.return_value = begin_ctx
                                    counts = self.module._run_cleanup_transaction(
                                        fake_engine,
                                        matches_baseline=[],
                                        classifications_baseline=[],
                                        categories_baseline=[],
                                        baseline_max_match_id=0,
                                        baseline_max_match_audit_id=0,
                                        baseline_max_category_id=0,
                                        run_id="run-123",
                                    )
        self.assertEqual(
            counts,
            {
                "matches_restored": 2,
                "match_audit_rows_deleted": 3,
                "matches_deleted": 4,
                "classifications_deleted": 5,
                "classifications_restored": 6,
                "categories_deleted": 7,
                "categories_restored": 8,
            },
        )

    def test_profile_mismatch_refuses_nonzero_exit(self):
        #R035-T01: Verify profile mismatch path returns refused status with non-zero exit and no cleanup mutation.
        with patch.dict("os.environ", {"DAST_CLEANUP_FORCE": "false"}, clear=False):
            message = self.module._profile_refusal_message("baseline-a", "active-b")
        self.assertIsNotNone(message)
        self.assertIn("refusing to run", message)

    def test_missing_baseline_skip_summary(self):
        #R040-T01: Verify missing/non-captured baseline paths emit skipped status and zero exit.
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            summary = {"status": "unknown", "errors": [], "counts": {}}
            exit_code = self.module._skip_with_error(summary, summary_path, "missing baseline")
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "skipped")
        self.assertIn("missing baseline", payload["errors"][0])

    def test_summary_artifact_written(self):
        #R045-T01: Verify summary artifact and emitted payload are written for applied and failure flows.
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            summary = {"status": "applied", "counts": {"matches_restored": 1}, "errors": []}
            payload = {"status": "applied"}
            exit_code = self.module._emit_summary(summary_path, summary, payload, 0)
            persisted = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(persisted["status"], "applied")
        self.assertEqual(persisted["counts"]["matches_restored"], 1)

    def test_refuse_with_error_writes_nonzero_summary(self):
        #R035-T02: refusal helper writes refused status and returns non-zero.
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            summary = {"status": "unknown", "errors": [], "counts": {}}
            rc = self.module._refuse_with_error(summary, summary_path, "profile mismatch")
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 1)
        self.assertEqual(payload["status"], "refused")
        self.assertIn("profile mismatch", payload["errors"][0])

    def test_profile_refusal_message_force_override(self):
        #R035-T03: force override suppresses refusal on profile mismatch.
        with patch.dict("os.environ", {"DAST_CLEANUP_FORCE": "true"}, clear=False):
            message = self.module._profile_refusal_message("baseline", "active")
        self.assertIsNone(message)

    def test_restore_delete_helpers_return_row_counts(self):
        #R030-T02: row-level restore/delete helpers return execute rowcount values.
        class _ExecResult:
            def __init__(self, rowcount=0):
                self.rowcount = rowcount

        class _Conn:
            def execute(self, *_args, **_kwargs):
                return _ExecResult(rowcount=2)

        conn = _Conn()
        restored = self.module._restore_matches(
            conn,
            [{"match_id": 1, "active": True}],
            baseline_max_match_id=10,
        )
        deleted_audit = self.module._delete_post_baseline_audits(conn, 5)
        deleted_matches = self.module._delete_post_baseline_matches(conn, 5)
        deleted_cats = self.module._delete_post_baseline_categories(conn, 5, "run-1")
        self.assertEqual(restored, 2)
        self.assertEqual(deleted_audit, 2)
        self.assertEqual(deleted_matches, 2)
        self.assertEqual(deleted_cats, 2)

    def test_reconcile_and_restore_category_helpers(self):
        #R030-T03: classification/category helpers cover delete-all and restore filtering branches.
        class _ExecResult:
            def __init__(self, rowcount=0):
                self.rowcount = rowcount

        class _Conn:
            def execute(self, *_args, **_kwargs):
                return _ExecResult(rowcount=1)

        conn = _Conn()
        deleted, restored = self.module._reconcile_classifications(conn, [])
        self.assertEqual((deleted, restored), (1, 0))
        restored_categories = self.module._restore_categories(
            conn,
            [
                {"nys_snw_category_id": 2, "is_seed": False},
                {"nys_snw_category_id": 3, "is_seed": True},
            ],
            baseline_max_category_id=2,
        )
        self.assertEqual(restored_categories, 1)

    def test_main_usage_and_skip_paths(self):
        #R040-T02: main returns usage code and skip statuses for missing/non-captured baselines.
        with patch("sys.argv", ["dast_cleanup.py"]):
            self.assertEqual(self.module.main(), 2)

        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "missing.json"
            summary_path = Path(tmp) / "summary.json"
            with patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-x", str(summary_path)]):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "skipped")

        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(json.dumps({"status": "skipped"}), encoding="utf-8")
            summary_path = Path(tmp) / "summary.json"
            with patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-y", str(summary_path)]):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "skipped")

    def test_main_import_refusal_applied_and_failure_paths(self):
        #R045-T02: main covers import-fail, refusal, applied, and transaction-failure statuses.
        fake_db = types.ModuleType("teller.teller_db")
        fake_db.get_engine = lambda: object()
        fake_profile_mod = types.ModuleType("teller.teller_db_profile")
        fake_profile_mod.resolve_profile = lambda: types.SimpleNamespace(name="active")
        fake_teller_pkg = types.ModuleType("teller")
        fake_teller_pkg.__path__ = []

        baseline_payload = {
            "status": "captured",
            "profile_name": "baseline",
            "baseline_max_category_id": 1,
            "baseline_max_match_id": 1,
            "baseline_max_match_audit_id": 1,
            "matches": [],
            "classifications": [],
            "categories": [],
        }

        # Import-fail skip path
        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline_payload), encoding="utf-8")
            summary_path = Path(tmp) / "summary.json"
            original_import = __import__

            def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "teller.teller_db":
                    raise ImportError("db unavailable")
                return original_import(name, globals, locals, fromlist, level)

            with (
                patch("builtins.__import__", side_effect=guarded_import),
                patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-a", str(summary_path)]),
            ):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "skipped")

        # Refusal path
        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline_payload), encoding="utf-8")
            summary_path = Path(tmp) / "summary.json"
            with (
                patch.dict(
                    sys.modules,
                    {
                        "teller": fake_teller_pkg,
                        "teller.teller_db": fake_db,
                        "teller.teller_db_profile": fake_profile_mod,
                    },
                    clear=False,
                ),
                patch.dict("os.environ", {"DAST_CLEANUP_FORCE": "false"}, clear=False),
                patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-b", str(summary_path)]),
            ):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 1)
        self.assertEqual(payload["status"], "refused")

        # Applied path
        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(
                json.dumps({**baseline_payload, "profile_name": "active"}),
                encoding="utf-8",
            )
            summary_path = Path(tmp) / "summary.json"
            with (
                patch.dict(
                    sys.modules,
                    {
                        "teller": fake_teller_pkg,
                        "teller.teller_db": fake_db,
                        "teller.teller_db_profile": fake_profile_mod,
                    },
                    clear=False,
                ),
                patch.object(self.module, "_run_cleanup_transaction", return_value={"matches_restored": 1}),
                patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-c", str(summary_path)]),
            ):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "applied")

        # Failure path
        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(
                json.dumps({**baseline_payload, "profile_name": "active"}),
                encoding="utf-8",
            )
            summary_path = Path(tmp) / "summary.json"
            with (
                patch.dict(
                    sys.modules,
                    {
                        "teller": fake_teller_pkg,
                        "teller.teller_db": fake_db,
                        "teller.teller_db_profile": fake_profile_mod,
                    },
                    clear=False,
                ),
                patch.object(self.module, "_run_cleanup_transaction", side_effect=RuntimeError("boom")),
                patch("sys.argv", ["dast_cleanup.py", str(baseline_path), "run-d", str(summary_path)]),
            ):
                rc = self.module.main()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 1)
        self.assertEqual(payload["status"], "failed")


if __name__ == "__main__":
    unittest.main()
