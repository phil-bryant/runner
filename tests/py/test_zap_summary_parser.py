#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
script_path = repo_root / "tests" / "py" / "security" / "zap_summary_parser.py"
spec = importlib.util.spec_from_file_location("zap_summary_parser_under_test", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load zap_summary_parser.py")
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


def test_extract_count_returns_value_or_default():
    #R001-T01: Verify count extraction returns parsed values and defaults to zero.
    html = '<tr class="risk-3"><td><div>7</div></td></tr>'
    assert MODULE.extract_count(html, "3") == 7
    assert MODULE.extract_count(html, "2") == 0


def test_main_parses_report_and_summarizes():
    #R005-T01: Verify CLI summary parsing writes expected counts and total output.
    html = """
    <tr class="risk-3"><td><div>1</div></td></tr>
    <tr class="risk-2"><td><div>2</div></td></tr>
    <tr class="risk-1"><td><div>3</div></td></tr>
    <tr class="risk-0"><td><div>4</div></td></tr>
    """
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "zap.html"
        out_path = Path(tmp) / "summary.json"
        html_path.write_text(html, encoding="utf-8")
        import sys

        original_argv = sys.argv
        sys.argv = ["zap_summary_parser.py", html_path.as_posix(), out_path.as_posix()]
        try:
            rc = MODULE.main()
        finally:
            sys.argv = original_argv
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload == {"high": 1, "medium": 2, "low": 3, "informational": 4, "total": 10}
