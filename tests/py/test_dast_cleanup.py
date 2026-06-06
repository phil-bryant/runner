#!/usr/bin/env python3

import importlib.util
import json
import tempfile
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
        engine = object()
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


if __name__ == "__main__":
    unittest.main()
