---
name: fix-traceability-tag-mismatches
overview: Update requirements docs so the numbered test tags match newly added Bats tests, then re-run traceability checks to confirm the lane is green.
todos:
  - id: update-r025-tags
    content: Add R025-T02 and R025-T03 bullets to run_unit_test_lanes requirements doc
    status: completed
  - id: update-r041-r042-tags
    content: Add R041-T02 and R042-T02 bullets to runbook_common requirements doc
    status: completed
  - id: verify-traceability
    content: Run requirements traceability lane and confirm failures drop to zero
    status: completed
isProject: false
---

# Fix Traceability Tag Mismatches

## Findings
- The failure is caused by missing requirement test tags in two requirement docs while tests already reference them.
- Missing tags reported by traceability:
  - `R025-T02`, `R025-T03` in [requirements/src/scripts/run_unit_test_lanes-requirements.md](requirements/src/scripts/run_unit_test_lanes-requirements.md)
  - `R041-T02`, `R042-T02` in [requirements/src/scripts/runbook_common-requirements.md](requirements/src/scripts/runbook_common-requirements.md)

## Implementation Plan
- Update [requirements/src/scripts/run_unit_test_lanes-requirements.md](requirements/src/scripts/run_unit_test_lanes-requirements.md):
  - Under `R025`, add test bullets for `R025-T02` and `R025-T03` that match the existing Bats cases in [tests/sh/run_unit_test_lanes.bats](tests/sh/run_unit_test_lanes.bats) covering dotenv `ITEM.password` fallback for primary and admin SQL roles.
- Update [requirements/src/scripts/runbook_common-requirements.md](requirements/src/scripts/runbook_common-requirements.md):
  - Under `R041`, add `R041-T02` for dotenv fallback recovery when `1psa` fails.
  - Under `R042`, add `R042-T02` for precedence of `ITEM.password` over bare `ITEM` in dotenv fallback lookup.
- Keep existing requirement IDs/statements unchanged; only extend test bullet lists to restore 1:1 tag mapping.

## Validation Plan
- Re-run `tests/t04_run_requirements_traceability_tests.sh` and confirm no numbered-tag mismatch failures remain.
- Optionally run focused Bats files [tests/sh/run_unit_test_lanes.bats](tests/sh/run_unit_test_lanes.bats) and [tests/sh/runbook_common.bats](tests/sh/runbook_common.bats) to ensure traceability tags still align with active tests.