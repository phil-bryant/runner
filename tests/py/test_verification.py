"""Unit tests for the traceability engine verification logic.

Bare-tag fixture content is assembled at runtime so the engine's own
unconditional tag-text scan does not flag this test file.
"""
from pathlib import Path

from traceability.verification import TraceabilityVerifier

HASH = "#"


def _clear_root_env(monkeypatch):
    for name in ("TRACEABILITY_TEST_ROOTS", "SHELL_BATS_ROOTS"):
        monkeypatch.delenv(name, raising=False)


def _verifier(tmp_path):
    return TraceabilityVerifier(repo_root=tmp_path)


def test_strict_pair_matches_ids(tmp_path):
    #R001-T01: a missing source #R tag fails the strict pair check.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("R001  Statement: a\nR005  Statement: b\n")
    src = tmp_path / "s.sh"
    src.write_text(HASH + "R001: only one tag\n")
    assert _verifier(tmp_path).verify_strict_pair(doc, src) is False
    src.write_text(HASH + "R001: a\n" + HASH + "R005: b\n")
    assert _verifier(tmp_path).verify_strict_pair(doc, src) is True


def test_scoped_comment_required(tmp_path):
    #R005-T01: a requirement without a scoped comment fails.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("R001  Statement: a\n")
    src = tmp_path / "s.sh"
    src.write_text(HASH + "R001\n")  # bare, not scoped
    assert _verifier(tmp_path).verify_scoped_traceability_comments(doc, src) is False
    src.write_text(HASH + "R001: scoped\n")
    assert _verifier(tmp_path).verify_scoped_traceability_comments(doc, src) is True


def test_header_bundle_rejected(tmp_path):
    #R010-T01: a bundled header #R line is rejected by single-pair verification.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("R001  Statement: a\n")
    src = tmp_path / "s.sh"
    bundle = HASH + "R001 " + HASH + "R005 " + HASH + "R010\n"
    src.write_text("#!/bin/sh\n" + bundle + "echo hi\n")
    assert _verifier(tmp_path).verify_single_pair(doc, src, print_banner=False) is False


def test_test_traceability_missing(tmp_path, monkeypatch):
    #R015-T01: a requirement with no tagged test is reported.
    _clear_root_env(monkeypatch)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_requirements_test_traceability(doc, ["src/foo.sh"]) is False


def test_numbered_test_traceability_missing(tmp_path, monkeypatch):
    #R020-T01: a missing numbered test tag fails the 1:1 check.
    _clear_root_env(monkeypatch)
    monkeypatch.delenv("STRICT_TRACEABILITY_NUMBERED_TAGS", raising=False)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    (tmp_path / "tests" / "sh" / "foo.bats").write_text('@test "x" {\n  :\n}\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_traceability(doc, ["src/foo.sh"]) is False


def test_requirements_only_mode_detected(tmp_path):
    #R025-T01: a requirements-only doc is detected.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("# t\n\n## Scope\n\nRequirements-only mode: true\n")
    assert _verifier(tmp_path).is_requirements_only_mode(doc) is True


def test_repository_coverage_flags_uncovered(tmp_path, monkeypatch):
    #R030-T01: an uncovered software file is reported when coverage is enabled.
    monkeypatch.delenv("STRICT_TRACEABILITY_FULL_COVERAGE", raising=False)
    (tmp_path / "requirements").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lonely.py").write_text("x = 1\n")
    assert _verifier(tmp_path).verify_repository_source_requirements_coverage() is False


def test_aggregate_verdict_fails_on_empty(tmp_path):
    #R035-T01: the aggregate verdict fails when no requirements docs exist.
    assert _verifier(tmp_path).verify_all_requirements() is False


def test_source_tag_text_unconditional(tmp_path):
    #R040-T01: a bare source tag fails tag-text strictness with no opt-out.
    src = tmp_path / "s.sh"
    src.write_text(HASH + "R001\n")  # bare source tag
    assert _verifier(tmp_path).verify_source_tag_text_strictness(src) is False
    src.write_text(HASH + "R001: scoped text\n")
    assert _verifier(tmp_path).verify_source_tag_text_strictness(src) is True


def test_numbered_test_tag_text_unconditional(tmp_path, monkeypatch):
    #R045-T01: a bare numbered test tag fails tag-text strictness with no opt-out.
    _clear_root_env(monkeypatch)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    bare = HASH + "R001-T01\n"
    (tmp_path / "tests" / "sh" / "foo.bats").write_text('@test "x" {\n  ' + bare + "}\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_tag_text(doc, ["src/foo.sh"]) is False


def test_requirements_only_blocked_when_source_exists(tmp_path):
    #R050-T01: requirements-only is rejected when first-party source exists in-repo.
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("# t\n\n## Scope\n\nRequirements-only mode: true\n\nApplies to `src/foo.sh`.\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text("#!/bin/sh\n")
    assert _verifier(tmp_path)._handle_requirements_only(doc) is False
    assert _verifier(tmp_path).verify_requirements_file_sources(doc) is False


def test_requirements_only_allowed_without_source(tmp_path):
    #R050-T02: requirements-only is a legitimate skip when no in-repo source maps.
    doc = tmp_path / "ghost-requirements.md"
    doc.write_text("# t\n\n## Scope\n\nRequirements-only mode: true\n\nApplies to `src/ghost.sh`.\n")
    assert _verifier(tmp_path)._handle_requirements_only(doc) is True
    assert _verifier(tmp_path).verify_requirements_file_sources(doc) is True


def test_engine_self_coverage_has_no_exemption():
    #R055-T01: the engine's own sources are in the coverage universe (no exclude knob).
    from traceability.discovery import list_repository_software_files

    repo_root = Path(__file__).resolve().parents[2]
    files = set(list_repository_software_files(repo_root))
    assert "tests/py/traceability/verification.py" in files
    assert "tests/t04_run_requirements_traceability_tests.sh" in files
