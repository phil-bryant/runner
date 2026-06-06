# Delete Category Contract Check Requirements

## Scope

Applies to `tests/py/security/delete_category_contract_check.py`.

R001  Statement: Normalize authenticated JSON request/response behavior.
Design: Perform authenticated JSON requests and normalize both success and HTTP-error payloads for contract assertions.
Tests:
- R001-T01: Verify request helper returns normalized payloads for success and HTTP error responses.

R005  Statement: Apply HTTPS/TLS context policy for local and cert-aware targets.
Design: Use permissive loopback TLS behavior and optional cert-file context for non-loopback HTTPS requests.
Tests:
- R005-T01: Verify TLS context policy for loopback hosts and explicit cert-file inputs.

R010  Statement: Load OpenAPI schema from URL or local file source.
Design: Resolve and parse schema payloads from HTTP(S) URLs or filesystem paths using shared request/TLS handling.
Tests:
- R010-T01: Verify schema loader supports URL and file inputs with consistent JSON payload parsing.

R015  Statement: Enforce delete-category lifecycle contract and summary output.
Design: Run create/delete/delete-again lifecycle validation for category endpoints and write a deterministic summary artifact.
Tests:
- R015-T01: Verify create/delete lifecycle checks and summary payload fields for contract success/failure paths.
