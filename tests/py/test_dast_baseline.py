#!/usr/bin/env python3

import importlib.util
import json
import tempfile
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


if __name__ == "__main__":
    unittest.main()
