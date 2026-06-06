#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

repo_root = Path(__file__).resolve().parents[2]
script_path = repo_root / "tests" / "py" / "security" / "schemathesis_fixture_prep.py"
spec = importlib.util.spec_from_file_location("schemathesis_fixture_prep_under_test", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load schemathesis_fixture_prep.py")
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


def test_auth_get_post_with_tls_context():
    #R001-T01: Verify authenticated GET/POST fixture helpers and TLS policy handling for loopback/cert-aware targets.
    get_resp = MagicMock()
    get_resp.__enter__.return_value = get_resp
    get_resp.read.return_value = json.dumps({"ok": "get"}).encode("utf-8")
    post_resp = MagicMock()
    post_resp.__enter__.return_value = post_resp
    post_resp.read.return_value = json.dumps({"ok": "post"}).encode("utf-8")
    with patch.object(MODULE.urllib.request, "urlopen", side_effect=[get_resp, post_resp]):
        got = MODULE.fetch_json("https://127.0.0.1/v1/openapi", "token", "X-Token")
        posted = MODULE.post_json("https://127.0.0.1/v1/seed", "token", {"a": 1}, "X-Token")
    assert got["ok"] == "get"
    assert posted["ok"] == "post"
    assert MODULE._tls_context_for_url("https://127.0.0.1/v1/openapi") is not None


def test_path_body_mutation_helpers():
    #R005-T01: Verify path/body mutation helpers apply expected fixture schema/example updates.
    paths = {
        "/v1/example/{id}": {
            "put": {
                "parameters": [{"in": "path", "name": "id", "schema": {"type": "integer"}}],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
            }
        }
    }
    MODULE.set_path_param_example(paths, "/v1/example/{id}", "put", "id", 9)
    MODULE.set_path_param_constraints(paths, "/v1/example/{id}", "put", "id", {"minimum": 1})
    MODULE.set_path_param_enum(paths, "/v1/example/{id}", "put", "id", [9, 10])
    MODULE.set_json_body_example(paths, "/v1/example/{id}", "put", {"ok": True})
    MODULE.set_json_body_schema(paths, "/v1/example/{id}", "put", {"type": "object", "required": ["ok"]})
    param = paths["/v1/example/{id}"]["put"]["parameters"][0]
    body = paths["/v1/example/{id}"]["put"]["requestBody"]["content"]["application/json"]
    assert param["example"] == 9
    assert param["schema"]["enum"] == [9, 10]
    assert body["example"] == {"ok": True}
    assert body["schema"]["required"] == ["ok"]


def test_tighten_query_params_blocks_noop():
    #R010-T01: Verify tightened query/component constraints prevent schema-valid no-op fixture inputs.
    paths = {
        "/v1/matchy/messages/search": {
            "get": {
                "parameters": [
                    {"in": "query", "name": "subject", "schema": {"type": "string"}},
                    {"in": "query", "name": "start_date", "schema": {"type": "string"}},
                ]
            }
        }
    }
    MODULE.tighten_matchy_search_query_params(paths)
    params = paths["/v1/matchy/messages/search"]["get"]["parameters"]
    subject = next(item for item in params if item["name"] == "subject")
    start_date = next(item for item in params if item["name"] == "start_date")
    assert subject["required"] is True
    assert subject["schema"]["minLength"] == 1
    assert start_date["schema"]["minLength"] == 10


def test_choose_first_matching_seed_discovery():
    #R015-T01: Verify fixture candidate selection and seed discovery logic produce valid operation identifiers.
    value = MODULE.choose_first_matching(["", "bad id", "ABC_123"], r"^[A-Za-z0-9_]+$")
    assert value == "ABC_123"


def test_emit_fixture_and_summary():
    #R020-T01: Verify fixture artifact emission and summary payload fields from main orchestration.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_path = tmp_path / "fixture.json"
        seed_path = tmp_path / "seed.json"
        seed_path.write_text("{}", encoding="utf-8")
        schema = {
            "paths": {
                "/v1/matchy/messages/search": {"get": {"parameters": []}},
                "/v1/transactions": {"get": {"parameters": []}},
                "/v1/categories/{nys_snw_category_id}": {"put": {"parameters": []}, "delete": {"parameters": []}},
                "/v1/transactions/{transaction_id}/classification": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/transactions/classifications": {"post": {"requestBody": {"content": {"application/json": {}}}}},
                "/v1/matchy/matches/{match_id}/confirm": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/matchy/matches/{match_id}/override": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/matchy/matches/{match_id}/no-email": {"put": {"parameters": []}},
                "/v1/matchy/matches/{match_id}/clear": {"put": {"parameters": []}},
                "/v1/matchy/transactions/{transaction_id}/clear": {"put": {"parameters": []}},
                "/v1/matchy/transactions/{transaction_id}/confirm-candidate": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/matchy/transactions/{transaction_id}/override-candidate": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/matchy/transactions/{transaction_id}/override": {
                    "put": {"parameters": [], "requestBody": {"content": {"application/json": {}}}}
                },
                "/v1/matchy/transactions/{transaction_id}/candidates": {"get": {"parameters": []}},
                "/v1/matchy/review": {"get": {"parameters": []}},
            },
            "components": {"schemas": {"CategoryCreateMutation": {"properties": {}}, "CategoryUpdateMutation": {"properties": {}}}},
        }
        fetch_responses = [
            schema,
            {"items": [{"transaction_id": "tx-1"}]},
            {"items": [{"match_id": 2, "transaction_id": "tx-1", "email_message_id": "msg-2"}]},
            {"items": [{"transaction_id": "tx-2"}]},
            [{"email_message_id": "msg-candidate"}],
        ]
        post_responses = [{"nys_snw_category_id": i} for i in range(100, 140)]
        argv = [
            "schemathesis_fixture_prep.py",
            "https://example.com/openapi.json",
            "https://example.com",
            str(out_path),
            "token",
            "X-Token",
            str(seed_path),
            "run-1",
        ]
        import sys

        original_argv = sys.argv
        sys.argv = argv
        try:
            with patch.object(MODULE, "fetch_json", side_effect=fetch_responses):
                with patch.object(MODULE, "post_json", side_effect=post_responses):
                    rc = MODULE.main()
        finally:
            sys.argv = original_argv
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert "paths" in payload


def test_tighten_transactions_query_params_sets_fixtures():
    #R050-T01: Verify transactions query fixture tightening applies date constraints and examples.
    paths = {
        "/v1/transactions": {
            "get": {
                "parameters": [
                    {"in": "query", "name": "start_date", "schema": {"type": "string", "pattern": ".*"}},
                    {"in": "query", "name": "end_date", "schema": {"type": "string"}},
                ]
            }
        }
    }
    MODULE.tighten_transactions_query_params(paths)
    params = paths["/v1/transactions"]["get"]["parameters"]
    start = next(item for item in params if item["name"] == "start_date")
    end = next(item for item in params if item["name"] == "end_date")
    assert start["schema"]["format"] == "date"
    assert start["schema"]["minLength"] == 10
    assert end["examples"]["seed"]["value"] == "2026-04-15"
