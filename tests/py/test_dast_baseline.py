#!/usr/bin/env python3

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


#R030: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "dast_baseline.py"
    spec = importlib.util.spec_from_file_location("dast_baseline_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load dast_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DastBaselineTests(unittest.TestCase):
    #R030: shard-3 function tag
    def setUp(self):
        self.module = load_module()

    def test_serialize_row_iso(self):
        #R030-T01: Verify datetime/row serialization helpers produce stable JSON-safe baseline row payloads.
        value = datetime(2026, 1, 2, 3, 4, 5)
        row = (123, value)
        payload = self.module._serialize_row(row, ["id", "created_at"])
        self.assertEqual(payload["id"], 123)
        self.assertTrue(str(payload["created_at"]).startswith("2026-01-02T03:04:05"))

    def test_degrade_to_skipped_summary(self):
        #R035-T01: Verify `main` writes captured/skip artifacts and emits expected summary status fields.
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "baseline.json"
            argv = ["dast_baseline.py", str(output_path)]

            original_import = __import__

            #R030: shard-3 function tag
            def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "teller.teller_db":
                    raise ImportError("forced import failure")
                return original_import(name, globals, locals, fromlist, level)

            with patch("builtins.__import__", side_effect=guarded_import):
                with patch("sys.argv", argv):
                    exit_code = self.module.main()
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "skipped")
        self.assertIn("db_import_failed", payload["reason"])

    def test_main_usage_returns_2(self):
        #R035-T02: invalid CLI argument count returns usage exit code.
        with patch("sys.argv", ["dast_baseline.py"]):
            self.assertEqual(self.module.main(), 2)

    def test_main_captured_payload_path(self):
        #R035-T03: happy path captures baseline maxima and row snapshots.
        class _Result:
            def __init__(self, *, scalar=None, rows=None):
                self._scalar = scalar
                self._rows = rows or []

            def scalar_one(self):
                return self._scalar

            def fetchall(self):
                return self._rows

        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def exec_driver_sql(self, sql):
                if "MAX(nys_snw_category_id)" in sql:
                    return _Result(scalar=20)
                if "MAX(match_id)" in sql and "match_audit_id" not in sql:
                    return _Result(scalar=30)
                if "MAX(match_audit_id)" in sql:
                    return _Result(scalar=40)
                if "FROM teller.nys_snw_category" in sql:
                    return _Result(
                        rows=[
                            (1, "a", "A", "b", "B", "c", "d", "cat", "apply", False),
                        ]
                    )
                if "FROM teller.transaction_email_match" in sql:
                    return _Result(
                        rows=[
                            (2, "txn", "msg", "pending", "0.55", "manual", None, None, True, None),
                        ]
                    )
                if "FROM teller.transaction_nys_snw_category" in sql:
                    return _Result(rows=[("txn", 1, "rule")])
                return _Result()

        class _Engine:
            def connect(self):
                return _Conn()

        fake_db = types.ModuleType("teller.teller_db")
        fake_db.get_engine = lambda: _Engine()
        fake_profile_mod = types.ModuleType("teller.teller_db_profile")
        fake_profile_mod.resolve_profile = lambda: types.SimpleNamespace(name="local", host="localhost", dbname="prod")
        fake_teller_pkg = types.ModuleType("teller")
        fake_teller_pkg.__path__ = []

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "baseline.json"
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
                patch("sys.argv", ["dast_baseline.py", str(output_path)]),
            ):
                exit_code = self.module.main()
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "captured")
        self.assertEqual(payload["baseline_max_category_id"], 20)
        self.assertEqual(payload["baseline_max_match_id"], 30)
        self.assertEqual(payload["baseline_max_match_audit_id"], 40)
        self.assertEqual(len(payload["categories"]), 1)
        self.assertEqual(len(payload["matches"]), 1)
        self.assertEqual(len(payload["classifications"]), 1)


if __name__ == "__main__":
    unittest.main()
