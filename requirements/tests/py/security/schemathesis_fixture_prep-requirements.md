# Schemathesis Fixture Prep Requirements

## Scope

Applies to `tests/py/security/schemathesis_fixture_prep.py`.

R001  Statement: Fetch/post authenticated JSON fixtures with TLS policy handling.
Design: Use authenticated GET/POST helpers with HTTPS TLS context policy to read and seed runtime API fixture data.
Tests:
- R001-T01: Verify authenticated GET/POST fixture helpers and TLS policy handling for loopback/cert-aware targets.

R005  Statement: Set path/body examples and schema constraints in prepared OpenAPI fixtures.
Design: Apply parameter examples/enums/constraints and JSON requestBody examples/schemas needed for deterministic Schemathesis execution.
Tests:
- R005-T01: Verify path/body mutation helpers apply expected fixture schema/example updates.

R010  Statement: Tighten query/body constraints to prevent schema-valid no-op requests.
Design: Tighten component/query constraints (including matchy and transactions query params) so generated requests stay semantically meaningful.
Tests:
- R010-T01: Verify tightened query/component constraints prevent schema-valid no-op fixture inputs.

R015  Statement: Seed and discover runtime fixture identifiers for contract-focused operations.
Design: Create/discover candidate fixture IDs and select valid runtime identifiers for downstream mutation endpoints.
Tests:
- R015-T01: Verify fixture candidate selection and seed discovery logic produce valid operation identifiers.

R020  Statement: Emit prepared OpenAPI fixture artifact and seed summary.
Design: Write the prepared schema fixture file and print deterministic seed summary metadata for downstream lanes.
Tests:
- R020-T01: Verify fixture artifact emission and summary payload fields from main orchestration.
