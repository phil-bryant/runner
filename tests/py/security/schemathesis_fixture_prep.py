#!/usr/bin/env python3
import json
import os
import re
import ssl
import sys
import urllib.request
from urllib.parse import urlparse


def fetch_json(url: str, write_token: str, write_token_header_name: str):
    #R001: Fetch authenticated JSON fixtures from API endpoints with TLS policy.
    req = urllib.request.Request(url, headers={write_token_header_name: write_token}, method="GET")
    with urllib.request.urlopen(req, timeout=20, context=_tls_context_for_url(url)) as resp:
        return json.load(resp)


def post_json(url: str, write_token: str, payload: dict, write_token_header_name: str):
    #R001: Post authenticated JSON fixtures to seed runtime API state.
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", write_token_header_name: write_token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20, context=_tls_context_for_url(url)) as resp:
        return json.load(resp)


def _tls_context_for_url(url: str):
    #R001: Resolve HTTPS TLS context policy for local and cert-file targets.
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return None
    if (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}:
        return ssl._create_unverified_context()
    cert_file = os.environ.get("SSL_CERT_FILE") or os.environ.get("TELLER_CLASSIFIER_TLS_CERT_FILE")
    if cert_file and os.path.isfile(cert_file):
        return ssl.create_default_context(cafile=cert_file)
    return ssl._create_unverified_context()


def set_path_param_example(paths, path: str, method: str, param_name: str, value):
    #R005: Set OpenAPI path-parameter examples for fixture determinism.
    operation = paths.get(path, {}).get(method, {})
    for param in operation.get("parameters", []):
        if param.get("in") == "path" and param.get("name") == param_name:
            param["example"] = value


def set_path_param_constraints(paths, path: str, method: str, param_name: str, constraints: dict):
    #R005: Set OpenAPI path-parameter schema constraints for fixture safety.
    operation = paths.get(path, {}).get(method, {})
    for param in operation.get("parameters", []):
        if param.get("in") == "path" and param.get("name") == param_name:
            schema_obj = param.get("schema")
            if isinstance(schema_obj, dict):
                schema_obj.update(constraints)


def set_path_param_enum(paths, path: str, method: str, param_name: str, values):
    #R005: Set OpenAPI path-parameter enums for seeded fixture values.
    operation = paths.get(path, {}).get(method, {})
    for param in operation.get("parameters", []):
        if param.get("in") == "path" and param.get("name") == param_name:
            schema_obj = param.get("schema")
            if isinstance(schema_obj, dict):
                schema_obj["enum"] = values
            if values:
                param["example"] = values[0]


def set_json_body_example(paths, path: str, method: str, example):
    #R005: Set requestBody JSON examples for seeded API operations.
    operation = paths.get(path, {}).get(method, {})
    content = operation.get("requestBody", {}).get("content", {})
    app_json = content.get("application/json")
    if isinstance(app_json, dict):
        app_json["example"] = example


def set_json_body_schema(paths, path: str, method: str, schema_obj: dict):
    #R005: Set requestBody JSON schemas for strict fixture contracts.
    operation = paths.get(path, {}).get(method, {})
    content = operation.get("requestBody", {}).get("content", {})
    app_json = content.get("application/json")
    if isinstance(app_json, dict):
        app_json["schema"] = schema_obj


def set_component_string_min_length(schema: dict, component_name: str, field_names: list[str], min_length: int):
    #R010: Tighten schema string component minimum lengths for non-noop requests.
    components = schema.get("components", {})
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        return
    component = schemas.get(component_name)
    if not isinstance(component, dict):
        return
    properties = component.get("properties", {})
    if not isinstance(properties, dict):
        return
    for field_name in field_names:
        prop = properties.get(field_name)
        if not isinstance(prop, dict):
            continue
        if prop.get("type") == "string":
            prop["minLength"] = min_length
            continue
        any_of = prop.get("anyOf")
        if isinstance(any_of, list):
            for variant in any_of:
                if isinstance(variant, dict) and variant.get("type") == "string":
                    variant["minLength"] = min_length


def tighten_matchy_search_query_params(paths: dict):
    #R010: Tighten search query constraints to avoid schema-valid no-op calls.
    operation = paths.get("/v1/matchy/messages/search", {}).get("get", {})
    parameters = operation.get("parameters", [])
    if not isinstance(parameters, list):
        return
    for param in parameters:
        if not isinstance(param, dict):
            continue
        if param.get("in") != "query":
            continue
        name = param.get("name")
        schema_obj = param.get("schema")
        if not isinstance(schema_obj, dict):
            continue
        if name in {"subject", "sender", "body"}:
            schema_obj["minLength"] = max(int(schema_obj.get("minLength", 0) or 0), 1)
        if name == "subject":
            # FastAPI enforces "at least one structured criterion", which OpenAPI cannot express as
            # "one-of these query params must be present". Require `subject` in the generated
            # Schemathesis fixture to avoid schema-valid empty requests that the API correctly rejects.
            param["required"] = True
        if name in {"start_date", "end_date"}:
            # The API treats empty/"null" date values as no-op criteria and can return 422 when
            # no effective structured filters remain. Keep Schemathesis focused on meaningful
            # structured date inputs so schema-valid requests align with success-path behavior.
            schema_obj["minLength"] = 10
            schema_obj["maxLength"] = 10
            schema_obj["pattern"] = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def tighten_transactions_query_params(paths: dict):
    #R010: Tighten transaction query constraints for semantically valid dates.
    #R050: Tighten transactions query params with fixtures for schemathesis boundary coverage.
    operation = paths.get("/v1/transactions", {}).get("get", {})
    parameters = operation.get("parameters", [])
    if not isinstance(parameters, list):
        return
    for param in parameters:
        if not isinstance(param, dict):
            continue
        if param.get("in") != "query":
            continue
        name = param.get("name")
        if name not in {"start_date", "end_date"}:
            continue
        schema_obj = param.get("schema")
        if not isinstance(schema_obj, dict):
            continue
        # Keep fuzzing focused on semantically valid calendar dates for positive-mode checks.
        schema_obj.pop("pattern", None)
        schema_obj["format"] = "date"
        schema_obj["minLength"] = 10
        schema_obj["maxLength"] = 10
        param["examples"] = {
            "seed": {"value": "2026-04-15"},
        }


def choose_first_matching(values, pattern: str) -> str | None:
    #R015: Select first fixture candidate value matching required pattern.
    matcher = re.compile(pattern)
    for value in values:
        if isinstance(value, str) and value and matcher.fullmatch(value):
            return value
    return None


#R015: Load optional matchy seed payload and normalize supported seed values.
def _load_matchy_seed_values(matchy_seed_path: str) -> dict[str, object]:
    values: dict[str, object] = {
        "match_ids": [],
        "match_override_email": None,
        "active_match_transaction_ids": [],
        "candidate_transaction_id": None,
        "candidate_email_id": None,
    }
    if not matchy_seed_path:
        return values
    try:
        with open(matchy_seed_path, "r", encoding="utf-8") as fh:
            seed_payload = json.load(fh)
    except Exception:
        return values
    if not isinstance(seed_payload, dict):
        return values

    values["match_ids"] = [value for value in seed_payload.get("match_ids", []) if isinstance(value, int)]
    seeded_override_email = seed_payload.get("override_email_message_id")
    if isinstance(seeded_override_email, str) and seeded_override_email:
        values["match_override_email"] = seeded_override_email
    values["active_match_transaction_ids"] = [
        value for value in seed_payload.get("active_match_transaction_ids", []) if isinstance(value, str) and value
    ]
    seeded_candidate_tx = seed_payload.get("candidate_transaction_id")
    if isinstance(seeded_candidate_tx, str) and seeded_candidate_tx:
        values["candidate_transaction_id"] = seeded_candidate_tx
    seeded_candidate_email = seed_payload.get("candidate_email_id")
    if isinstance(seeded_candidate_email, str) and seeded_candidate_email:
        values["candidate_email_id"] = seeded_candidate_email
    return values


#R001: Wrap authenticated GET fixtures with tolerant failure handling.
def _safe_fetch_json(url: str, write_token: str, write_token_header_name: str):
    try:
        return fetch_json(url, write_token, write_token_header_name)
    except Exception:
        return None


#R001: Wrap authenticated POST fixtures with tolerant failure handling.
def _safe_post_json(url: str, write_token: str, payload: dict, write_token_header_name: str):
    try:
        return post_json(url, write_token, payload, write_token_header_name)
    except Exception:
        return None


#R015: Seed deterministic category fixtures for contract-driven delete scenarios.
def _create_seed_category(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    dast_run_id: str,
    seed_suffix: str,
):
    created = _safe_post_json(
        f"{base_url}/v1/categories",
        write_token,
        {
            "level_1": "DAST",
            "level_1_name": "DAST Seed",
            "level_2": "Validation",
            "level_2_name": "Validation",
            "level_3": "Schemathesis",
            "level_4": f"Delete Seed {seed_suffix}",
            "categorization": f"Runtime [{dast_run_id}] {seed_suffix}",
            "applicability": f"all-{seed_suffix}",
        },
        write_token_header_name,
    )
    if isinstance(created, dict):
        return created.get("nys_snw_category_id")
    return None


#R015: Seed primary category and fall back to existing categories when needed.
def _resolve_seeded_category_id(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    dast_run_id: str,
):
    created = _safe_post_json(
        f"{base_url}/v1/categories",
        write_token,
        {
            "level_1": "DAST",
            "level_1_name": "DAST Seed",
            "level_2": "Validation",
            "level_2_name": "Validation",
            "level_3": "Schemathesis",
            "level_4": "Seed",
            "categorization": f"Runtime [{dast_run_id}]",
            "applicability": "all",
        },
        write_token_header_name,
    )
    if isinstance(created, dict):
        seeded_id = created.get("nys_snw_category_id")
        if seeded_id is not None:
            return seeded_id

    categories = _safe_fetch_json(f"{base_url}/v1/categories", write_token, write_token_header_name)
    if isinstance(categories, list) and categories:
        return categories[0].get("nys_snw_category_id")
    return None


#R015: Build deterministic category ids for delete-contract fixtures.
def _collect_delete_seed_ids(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    dast_run_id: str,
) -> list[int]:
    delete_seed_ids: list[int] = []
    for idx in range(32):
        seed_id = _create_seed_category(base_url, write_token, write_token_header_name, dast_run_id, str(idx))
        if isinstance(seed_id, int):
            delete_seed_ids.append(seed_id)
    return delete_seed_ids


#R015: Resolve first available transaction id for classification fixture seeding.
def _resolve_transaction_id(base_url: str, write_token: str, write_token_header_name: str) -> str | None:
    tx_payload = _safe_fetch_json(
        f"{base_url}/v1/transactions?limit=1&offset=0",
        write_token,
        write_token_header_name,
    )
    items = tx_payload.get("items", []) if isinstance(tx_payload, dict) else []
    if not items:
        return None
    first_item = items[0]
    if isinstance(first_item, dict):
        tx_id = first_item.get("transaction_id")
        if isinstance(tx_id, str) and tx_id:
            return tx_id
    return None


#R015: Discover match review fixture ids and active-match transaction ids.
def _collect_match_review_seed(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    match_ids: list[int],
    active_match_transaction_ids: list[str],
    match_override_email: str | None,
) -> tuple[list[int], list[str], str | None]:
    if match_ids:
        return match_ids, active_match_transaction_ids, match_override_email
    review_payload = _safe_fetch_json(
        f"{base_url}/v1/matchy/review?limit=25&offset=0",
        write_token,
        write_token_header_name,
    )
    review_items = review_payload.get("items", []) if isinstance(review_payload, dict) else []
    for item in review_items:
        if not isinstance(item, dict):
            continue
        match_id = item.get("match_id")
        if isinstance(match_id, int):
            match_ids.append(match_id)
        tx_value = item.get("transaction_id")
        if isinstance(tx_value, str) and tx_value:
            active_match_transaction_ids.append(tx_value)
        email_value = item.get("email_message_id")
        if match_override_email is None and isinstance(email_value, str) and email_value:
            match_override_email = email_value
    return match_ids, active_match_transaction_ids, match_override_email


#R015: Build candidate transaction probe list from seeded, active, and recent rows.
def _build_tx_candidates_to_probe(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    transaction_id: str | None,
    active_match_transaction_ids: list[str],
) -> list[str]:
    tx_candidates_to_probe = [transaction_id] if transaction_id else []
    for tx_id in active_match_transaction_ids:
        if tx_id not in tx_candidates_to_probe:
            tx_candidates_to_probe.append(tx_id)

    tx_payload = _safe_fetch_json(
        f"{base_url}/v1/transactions?limit=40&offset=0",
        write_token,
        write_token_header_name,
    )
    items = tx_payload.get("items", []) if isinstance(tx_payload, dict) else []
    for item in items:
        tx_id = item.get("transaction_id") if isinstance(item, dict) else None
        if isinstance(tx_id, str) and tx_id and tx_id not in tx_candidates_to_probe:
            tx_candidates_to_probe.append(tx_id)
    return tx_candidates_to_probe


#R015: Resolve candidate transaction/email fixture pair from candidate endpoints.
def _resolve_candidate_fixture(
    base_url: str,
    write_token: str,
    write_token_header_name: str,
    tx_candidates_to_probe: list[str],
    active_match_transaction_ids: list[str],
    candidate_transaction_id: str | None,
    candidate_email_id: str | None,
) -> tuple[str | None, str | None]:
    if candidate_transaction_id and candidate_email_id:
        return candidate_transaction_id, candidate_email_id
    for tx_id in tx_candidates_to_probe:
        if tx_id in active_match_transaction_ids:
            continue
        candidates = _safe_fetch_json(
            f"{base_url}/v1/matchy/transactions/{tx_id}/candidates",
            write_token,
            write_token_header_name,
        )
        if not isinstance(candidates, list) or not candidates:
            continue
        emails = [candidate.get("email_message_id") for candidate in candidates if isinstance(candidate, dict)]
        selected_email = choose_first_matching(emails, r"^[A-Za-z0-9_\-=]+$")
        if selected_email is None:
            continue
        return tx_id, selected_email
    return candidate_transaction_id, candidate_email_id


#R005: Apply shared matchy transaction path constraints for fixture operations.
def _apply_matchy_transaction_constraints(paths: dict):
    for path_name in (
        "/v1/matchy/transactions/{transaction_id}/confirm-candidate",
        "/v1/matchy/transactions/{transaction_id}/override-candidate",
        "/v1/matchy/transactions/{transaction_id}/override",
        "/v1/matchy/transactions/{transaction_id}/clear",
    ):
        set_path_param_constraints(
            paths,
            path_name,
            "put",
            "transaction_id",
            {"minLength": 1, "maxLength": 120, "pattern": r"^[A-Za-z0-9_.:-]+$"},
        )


#R005: Apply category/classification fixture examples from seeded identifiers.
def _apply_category_classification_fixtures(
    paths: dict,
    category_id,
    delete_seed_ids: list[int],
    transaction_id: str | None,
):
    if category_id is not None:
        set_path_param_example(paths, "/v1/categories/{nys_snw_category_id}", "put", "nys_snw_category_id", category_id)
    if delete_seed_ids:
        set_path_param_enum(paths, "/v1/categories/{nys_snw_category_id}", "delete", "nys_snw_category_id", delete_seed_ids)
    elif category_id is not None:
        set_path_param_example(paths, "/v1/categories/{nys_snw_category_id}", "delete", "nys_snw_category_id", category_id)
    if transaction_id is not None:
        set_path_param_example(
            paths,
            "/v1/transactions/{transaction_id}/classification",
            "put",
            "transaction_id",
            transaction_id,
        )
    if transaction_id is not None and category_id is not None:
        set_json_body_example(
            paths,
            "/v1/transactions/{transaction_id}/classification",
            "put",
            {"nys_snw_category_id": category_id},
        )
        set_json_body_example(
            paths,
            "/v1/transactions/classifications",
            "post",
            {"updates": [{"transaction_id": transaction_id, "nys_snw_category_id": category_id}]},
        )


#R005: Apply match-id fixture examples for match-level endpoints.
def _apply_match_id_fixtures(paths: dict, match_ids: list[int], match_override_email: str | None):
    if not match_ids:
        return
    for path_name in (
        "/v1/matchy/matches/{match_id}/confirm",
        "/v1/matchy/matches/{match_id}/no-email",
        "/v1/matchy/matches/{match_id}/clear",
        "/v1/matchy/matches/{match_id}/override",
    ):
        set_path_param_enum(paths, path_name, "put", "match_id", match_ids)
    set_json_body_schema(paths, "/v1/matchy/matches/{match_id}/confirm", "put", {"type": "null"})
    set_json_body_example(paths, "/v1/matchy/matches/{match_id}/confirm", "put", None)
    set_json_body_example(
        paths,
        "/v1/matchy/matches/{match_id}/override",
        "put",
        {"email_message_id": match_override_email or "msg_seeded_override_1", "note": "Schemathesis seeded override"},
    )


#R005: Apply candidate transaction/email fixtures for matchy candidate endpoints.
def _apply_candidate_fixtures(
    paths: dict,
    active_match_transaction_ids: list[str],
    candidate_transaction_id: str | None,
    candidate_email_id: str | None,
):
    if active_match_transaction_ids:
        set_path_param_enum(
            paths,
            "/v1/matchy/transactions/{transaction_id}/clear",
            "put",
            "transaction_id",
            active_match_transaction_ids,
        )
    if candidate_transaction_id is None or not candidate_email_id:
        return

    for path_name in (
        "/v1/matchy/transactions/{transaction_id}/confirm-candidate",
        "/v1/matchy/transactions/{transaction_id}/override-candidate",
        "/v1/matchy/transactions/{transaction_id}/override",
    ):
        set_path_param_enum(paths, path_name, "put", "transaction_id", [candidate_transaction_id])
        set_path_param_example(paths, path_name, "put", "transaction_id", candidate_transaction_id)

    candidate_body_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["email_message_id"],
        "properties": {
            "email_message_id": {"type": "string", "enum": [candidate_email_id]},
            "note": {"type": "string", "maxLength": 800, "pattern": r"^[\x20-\x7E]*$"},
        },
    }
    set_json_body_schema(
        paths,
        "/v1/matchy/transactions/{transaction_id}/confirm-candidate",
        "put",
        candidate_body_schema,
    )
    set_json_body_schema(
        paths,
        "/v1/matchy/transactions/{transaction_id}/override-candidate",
        "put",
        candidate_body_schema,
    )
    candidate_body = {"email_message_id": candidate_email_id, "note": "Schemathesis seeded candidate"}
    set_json_body_example(
        paths,
        "/v1/matchy/transactions/{transaction_id}/confirm-candidate",
        "put",
        candidate_body,
    )
    set_json_body_example(
        paths,
        "/v1/matchy/transactions/{transaction_id}/override-candidate",
        "put",
        candidate_body,
    )
    set_json_body_example(
        paths,
        "/v1/matchy/transactions/{transaction_id}/override",
        "put",
        {"email_message_id": candidate_email_id, "note": "Schemathesis seeded override"},
    )


#R020: Persist prepared fixture schema and print seed summary payload.
def _write_fixture_and_summary(
    out_path: str,
    schema: dict,
    category_id,
    transaction_id: str | None,
    delete_seed_ids: list[int],
    match_ids: list[int],
    active_match_transaction_ids: list[str],
    candidate_transaction_id: str | None,
    candidate_email_id: str | None,
    match_override_email: str | None,
) -> None:
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(schema, fh)
        fh.write("\n")
    print(
        json.dumps(
            {
                "fixture": out_path,
                "seeded_category_id": category_id,
                "seeded_transaction_id": transaction_id,
                "delete_seed_ids": delete_seed_ids,
                "match_ids": match_ids,
                "active_match_transaction_ids": active_match_transaction_ids,
                "candidate_transaction_id": candidate_transaction_id,
                "candidate_email_id": candidate_email_id,
                "match_override_email": match_override_email,
            }
        )
    )


def main() -> int:
    #R001: Orchestrate authenticated fixture fetch/post flows with TLS policy handling.
    #R005: Apply path/body schema/example mutations for seeded fixture operations.
    #R010: Enforce tightened query/component constraints to block schema-valid no-ops.
    #R015: Seed and discover runtime fixture identifiers for downstream operations.
    #R020: Emit prepared OpenAPI fixture and seed-summary payload artifact.
    if len(sys.argv) != 8:
        raise SystemExit(
            "usage: schemathesis_fixture_prep.py <openapi_url> <base_url> <out_path> <write_token> <write_token_header_name> <matchy_seed_path> <dast_run_id>"
        )
    openapi_url, base_url, out_path, write_token, write_token_header_name, matchy_seed_path, dast_run_id = sys.argv[1:8]
    schema = fetch_json(openapi_url, write_token, write_token_header_name)

    seed_values = _load_matchy_seed_values(matchy_seed_path)
    match_ids = list(seed_values["match_ids"])
    match_override_email = seed_values["match_override_email"]
    active_match_transaction_ids = list(seed_values["active_match_transaction_ids"])
    candidate_transaction_id = seed_values["candidate_transaction_id"]
    candidate_email_id = seed_values["candidate_email_id"]
    if candidate_email_id and choose_first_matching([candidate_email_id], r"^[A-Za-z0-9_\-=]+$") is None:
        candidate_email_id = None

    category_text_fields = [
        "level_1",
        "level_1_name",
        "level_2",
        "level_2_name",
        "level_3",
        "level_4",
        "categorization",
        "applicability",
    ]
    set_component_string_min_length(schema, "CategoryCreateMutation", category_text_fields, 1)
    set_component_string_min_length(schema, "CategoryUpdateMutation", category_text_fields, 1)

    category_id = _resolve_seeded_category_id(base_url, write_token, write_token_header_name, dast_run_id)
    delete_seed_ids = _collect_delete_seed_ids(base_url, write_token, write_token_header_name, dast_run_id)
    transaction_id = _resolve_transaction_id(base_url, write_token, write_token_header_name)
    match_ids, active_match_transaction_ids, match_override_email = _collect_match_review_seed(
        base_url,
        write_token,
        write_token_header_name,
        match_ids,
        active_match_transaction_ids,
        match_override_email,
    )
    tx_candidates_to_probe = _build_tx_candidates_to_probe(
        base_url,
        write_token,
        write_token_header_name,
        transaction_id,
        active_match_transaction_ids,
    )
    candidate_transaction_id, candidate_email_id = _resolve_candidate_fixture(
        base_url,
        write_token,
        write_token_header_name,
        tx_candidates_to_probe,
        active_match_transaction_ids,
        candidate_transaction_id,
        candidate_email_id,
    )
    active_match_transaction_ids = list(dict.fromkeys(active_match_transaction_ids))

    paths = schema.get("paths", {})
    if isinstance(paths, dict):
        tighten_matchy_search_query_params(paths)
        tighten_transactions_query_params(paths)
        _apply_matchy_transaction_constraints(paths)
        _apply_category_classification_fixtures(paths, category_id, delete_seed_ids, transaction_id)
        _apply_match_id_fixtures(paths, match_ids, match_override_email)
        _apply_candidate_fixtures(
            paths,
            active_match_transaction_ids,
            candidate_transaction_id,
            candidate_email_id,
        )

    _write_fixture_and_summary(
        out_path,
        schema,
        category_id,
        transaction_id,
        delete_seed_ids,
        match_ids,
        active_match_transaction_ids,
        candidate_transaction_id,
        candidate_email_id,
        match_override_email,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
