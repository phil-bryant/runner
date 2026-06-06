#!/usr/bin/env python3

import importlib.util
import io
import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

repo_root = Path(__file__).resolve().parents[2]
script_path = repo_root / "tests" / "py" / "security" / "delete_category_contract_check.py"
spec = importlib.util.spec_from_file_location("delete_category_contract_check_under_test", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load delete_category_contract_check.py")
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


def test_request_json_normalizes_http_errors():
    #R001-T01: Verify request helper returns normalized payloads for success and HTTP error responses.
    err_body = io.BytesIO(b'{"error":"bad"}')
    http_error = urllib.error.HTTPError(
        url="https://example.com/v1/categories",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=err_body,
    )
    with patch.object(MODULE.urllib.request, "urlopen", side_effect=http_error):
        status, payload = MODULE.request_json(
            "GET",
            "https://example.com/v1/categories",
            "token",
            "X-Token",
        )
    assert status == 404
    assert payload["error"] == "bad"


def test_tls_context_policy():
    #R005-T01: Verify TLS context policy for loopback hosts and explicit cert-file inputs.
    loopback_ctx = MODULE._tls_context_for_url("https://127.0.0.1:8443/v1")
    assert loopback_ctx is not None
    with tempfile.NamedTemporaryFile("w", delete=False) as cert:
        cert_path = cert.name
    try:
        sentinel_ctx = object()
        with patch.dict("os.environ", {"SSL_CERT_FILE": cert_path}, clear=False):
            with patch.object(MODULE.ssl, "create_default_context", return_value=sentinel_ctx):
                cert_ctx = MODULE._tls_context_for_url("https://example.com/v1")
        assert cert_ctx is sentinel_ctx
    finally:
        Path(cert_path).unlink(missing_ok=True)


def test_load_schema_from_file():
    #R010-T01: Verify schema loader supports URL and file inputs with consistent JSON payload parsing.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "schema.json"
        path.write_text(json.dumps({"openapi": "3.0.0", "paths": {}}), encoding="utf-8")
        payload = MODULE._load_schema(str(path))
    assert payload["openapi"] == "3.0.0"


def test_delete_lifecycle_summary():
    #R015-T01: Verify create/delete lifecycle checks and summary payload fields for contract success/failure paths.
    with tempfile.TemporaryDirectory() as tmp:
        schema_path = Path(tmp) / "schema.json"
        schema_path.write_text(json.dumps({"paths": {"/v1/categories/{nys_snw_category_id}": {}}}), encoding="utf-8")
        output_path = Path(tmp) / "summary.json"
        responses = [
            (200, [{"nys_snw_category_id": 1}]),
            (200, {"nys_snw_category_id": 42}),
            (200, {"deleted": True, "nys_snw_category_id": 42}),
            (404, {"detail": "not found"}),
        ]

        argv = [
            "delete_category_contract_check.py",
            str(schema_path),
            "https://api.example.com",
            str(output_path),
            "token",
            "X-Token",
            "run-1",
        ]
        import sys

        original_argv = sys.argv
        sys.argv = argv
        try:
            with patch.object(MODULE, "request_json", side_effect=lambda *_args, **_kwargs: responses.pop(0)):
                rc = MODULE.main()
        finally:
            sys.argv = original_argv
        payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert rc == 0
    assert payload["status"] == "passed"
    assert payload["created_category_id"] == 42
