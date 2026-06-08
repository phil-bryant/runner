"""Unit tests for the traceability engine verification logic.

Bare-tag fixture content is assembled at runtime so the engine's own
unconditional tag-text scan does not flag this test file.
"""
import ast
from pathlib import Path

from traceability.verification import TraceabilityVerifier, tests_inline_from_list as _tests_inline_from_list

HASH = "#"


#R001: shard-3 function tag
def _clear_root_env(monkeypatch):
    for name in ("TRACEABILITY_TEST_ROOTS", "SHELL_BATS_ROOTS"):
        monkeypatch.delenv(name, raising=False)


#R001: shard-3 function tag
def _verifier(tmp_path):
    return TraceabilityVerifier(repo_root=tmp_path)


#R001: shard-3 function tag
def _constant_string_first_arg(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first_arg = call.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    return None


#R001: shard-3 function tag
def _is_env_flag_false_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Attribute) and call.func.attr == "_env_flag_false"


#R001: shard-3 function tag
def _is_os_environ_get_call(call: ast.Call) -> bool:
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "get"):
        return False
    owner = call.func.value
    return (
        isinstance(owner, ast.Attribute)
        and owner.attr == "environ"
        and isinstance(owner.value, ast.Name)
        and owner.value.id == "os"
    )


#R001: shard-3 function tag
def _is_traceability_env_knob(name: str) -> bool:
    return (
        name.startswith("STRICT_TRACEABILITY_")
        or name.startswith("TRACEABILITY_")
        or name == "SHELL_BATS_ROOTS"
    )


#R001: shard-3 function tag
def _extract_traceability_env_knobs_from_source(source_text: str) -> set[str]:
    knobs: set[str] = set()
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        env_name = _constant_string_first_arg(node)
        if env_name is None:
            continue
        if _is_env_flag_false_call(node):
            knobs.add(env_name)
            continue
        if _is_os_environ_get_call(node):
            knobs.add(env_name)
    return {name for name in knobs if _is_traceability_env_knob(name)}


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
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    (tmp_path / "tests" / "sh" / "foo.bats").write_text('@test "x" {\n  :\n}\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_traceability(doc, ["src/foo.sh"]) is False


def test_numbered_tag_anchoring_passes_when_inside_block(tmp_path, monkeypatch):
    #R070-T01: a numbered tag anchored inside a real test block passes the gate.
    _clear_root_env(monkeypatch)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    inside = HASH + "R001-T01: inside the test block\n"
    (tmp_path / "tests" / "sh" / "foo.bats").write_text('@test "x" {\n  ' + inside + "}\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_tag_anchoring(doc, ["src/foo.sh"]) is True


def test_numbered_tag_anchoring_fails_outside_block(tmp_path, monkeypatch):
    #R070-T02: a numbered tag placed outside any test block fails the gate.
    _clear_root_env(monkeypatch)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    outside = HASH + "R001-T01: outside any test block\n"
    (tmp_path / "tests" / "sh" / "foo.bats").write_text(outside + '@test "x" {\n  :\n}\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_tag_anchoring(doc, ["src/foo.sh"]) is False


def test_numbered_tag_anchoring_fails_closed_for_unparseable_language(tmp_path, monkeypatch):
    #R070-T03: a test file whose language has no parseable test-block convention fails closed.
    _clear_root_env(monkeypatch)
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("R001  Statement: a\nTests:\n- R001-T01: does a thing\n")
    (tmp_path / "tests" / "sql").mkdir(parents=True)
    tag = HASH + "R001-T01: tag in an unparseable sql test file\n"
    (tmp_path / "tests" / "sql" / "foo.sql").write_text("select 1;  " + tag)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sql").write_text(HASH + "R001: a\n")
    assert _verifier(tmp_path).verify_numbered_test_tag_anchoring(doc, ["src/foo.sql"]) is False


def test_requirements_only_mode_detected(tmp_path):
    #R025-T01: a requirements-only doc is detected.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("# t\n\n## Scope\n\nRequirements-only mode: true\n")
    assert _verifier(tmp_path).is_requirements_only_mode(doc) is True


def test_repository_coverage_flags_uncovered(tmp_path):
    #R030-T01: an uncovered software file is reported when coverage is enabled.
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


def test_function_tag_gate_enforced_unconditionally(tmp_path):
    #R060-T01: the gate always enforces and fails on an untagged function.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("def untagged():\n    return 1\n")
    assert _verifier(tmp_path).verify_function_tag_coverage() is False


def test_function_tag_gate_ignores_legacy_weakening_knobs(tmp_path, monkeypatch):
    #R060-T02: legacy opt-out and baseline env knobs no longer weaken enforcement.
    monkeypatch.setenv("STRICT_TRACEABILITY_FUNCTION_TAGS", "false")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("def untagged():\n    return 1\n")
    baseline = tmp_path / "config" / "traceability" / "function-tag-baseline.txt"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("src/m.py:1: untagged\n")
    monkeypatch.setenv("TRACEABILITY_FUNCTION_TAG_BASELINE", baseline.as_posix())
    assert _verifier(tmp_path).verify_function_tag_coverage() is False


def test_traceability_weakening_knob_surface_locked():
    #R065-T01: traceability env surface is locked to scope knobs only.
    base = Path(__file__).resolve().parent / "traceability"
    module_paths = [
        base / "discovery.py",
        base / "parsing.py",
        base / "verification.py",
    ]
    observed: set[str] = set()
    for module_path in module_paths:
        observed.update(_extract_traceability_env_knobs_from_source(module_path.read_text(encoding="utf-8")))
    expected = {
        "TRACEABILITY_REQUIREMENTS_ROOTS",
        "TRACEABILITY_TEST_ROOTS",
        "SHELL_BATS_ROOTS",
    }
    if observed == expected:
        return
    added = sorted(observed - expected)
    removed = sorted(expected - observed)
    details: list[str] = []
    if added:
        details.append(f"Added knobs: {', '.join(added)}")
    if removed:
        details.append(f"Removed/renamed knobs: {', '.join(removed)}")
    details_text = "\n".join(details) if details else "No diff details available."
    raise AssertionError(
        "Traceability env-knob surface changed.\n"
        "Only scope knobs are allowed; strictness knobs are intentionally abolished.\n"
        "If intentional, update both contract files deliberately:\n"
        "- requirements/tests/py/traceability/verification-requirements.md (R065)\n"
        "- tests/py/test_verification.py expected allowlist\n"
        f"{details_text}\n"
        f"Expected: {sorted(expected)}\n"
        f"Observed: {sorted(observed)}"
    )


def test_verify_single_pair_with_tests_pipeline(tmp_path):
    #R100-T01: single-pair verification combines strict/source/test checks.
    req = tmp_path / "x-requirements.md"
    req.write_text("R001  Statement: a\nTests:\n- R001-T01: x\n", encoding="utf-8")
    src = tmp_path / "x.sh"
    src.write_text(HASH + "R001: scoped\n", encoding="utf-8")
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    (tmp_path / "tests" / "sh" / "x.bats").write_text(
        '@test "x" {\n  ' + HASH + "R001-T01: scoped\n}\n",
        encoding="utf-8",
    )
    assert _verifier(tmp_path).verify_single_pair_with_tests(req, src) is True


def test_verify_requirements_file_sources_resolves_and_checks(tmp_path):
    #R105-T01: per-doc source resolution fails when mapped sources are missing.
    req = tmp_path / "x-requirements.md"
    req.write_text("## Scope\n`x.sh`\nR001  Statement: a\nTests:\n- R001-T01: x\n", encoding="utf-8")
    assert _verifier(tmp_path).verify_requirements_file_sources(req) is False


def test_verify_numbered_script_requirements_coverage_skips_deprecated(tmp_path):
    #R110-T01: numbered coverage fails for missing docs and skips deprecated paths.
    (tmp_path / "12_x.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "deprecated").mkdir()
    (tmp_path / "deprecated" / "13_old.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    assert _verifier(tmp_path).verify_numbered_script_requirements_coverage() is False


def test_verify_numbered_requirement_scope_alignment_mismatch(tmp_path):
    #R115-T01: numbered requirement scope alignment fails on mismatched NN sources.
    (tmp_path / "requirements").mkdir()
    req = tmp_path / "requirements" / "12_x-requirements.md"
    req.write_text("## Scope\n`13_x.sh`\nR001  Statement: a\n", encoding="utf-8")
    assert _verifier(tmp_path).verify_numbered_requirement_scope_alignment() is False


def test_verify_numbered_script_test_coverage_requires_companion(tmp_path):
    #R120-T01: numbered script coverage requires companion bats files.
    (tmp_path / "12_x.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    assert _verifier(tmp_path).verify_numbered_script_test_coverage() is False


def test_collect_shared_runner_covered_sources_byte_identical(tmp_path):
    #R125-T01: shared-runner credit is granted only for byte-identical files.
    repo = tmp_path / "repo"
    runner = tmp_path / "runner"
    repo.mkdir()
    runner.mkdir()
    (runner / "requirements").mkdir()
    (runner / "requirements" / "x-requirements.md").write_text(
        "## Scope\n`x.sh`\nR001  Statement: a\n", encoding="utf-8"
    )
    (runner / "x.sh").write_text("echo ok\n", encoding="utf-8")
    (repo / "x.sh").write_text("echo ok\n", encoding="utf-8")
    verifier = TraceabilityVerifier(repo_root=repo)
    assert verifier._files_identical(repo / "x.sh", runner / "x.sh") is True


def test_collect_ids_and_numbered_ids_from_list(tmp_path):
    #R130-T01: test-id collectors aggregate ids and misplaced diagnostics.
    test_file = tmp_path / "x.bats"
    test_file.write_text(
        HASH + 'R100: plain\n@test "x" {\n  ' + HASH + "R100-T01: scoped\n}\n",
        encoding="utf-8",
    )
    v = _verifier(tmp_path)
    ids = v.collect_ids_from_test_list([test_file.as_posix()])
    numbered, misplaced = v.collect_numbered_test_ids_from_list([test_file.as_posix()])
    assert "R100" in ids and "R100-T01" in numbered and not misplaced


def test_locked_source_detection_and_exception(tmp_path):
    #R135-T01: lock markers are detected and policy requirements are validated.
    src = tmp_path / "x.sh"
    src.write_text("## <AI_MODEL_INSTRUCTION>\n## DO_NOT_MODIFY_THIS_FILE\n", encoding="utf-8")
    req = tmp_path / "x-requirements.md"
    req.write_text("R001  Statement: locked traceability policy\n", encoding="utf-8")
    v = _verifier(tmp_path)
    assert v.is_locked_source_file(src) is True
    assert v.verify_locked_exception(req, src) is True


def test_run_dispatches_argv_and_maps_exit(tmp_path):
    #R140-T01: CLI dispatch and exit mapping cover help/all/single-pair modes.
    v = _verifier(tmp_path)
    v.verify_all_requirements = lambda: True  # type: ignore[assignment]
    v.verify_single_pair_with_tests = lambda _r, _s: True  # type: ignore[assignment]
    assert v.run(["-h"]) == 0
    assert v.run([]) == 0
    assert v.run(["a", "b"]) == 0


def test_path_and_inline_helpers(tmp_path):
    #R145-T01: path and inline helper behavior stays stable.
    v = _verifier(tmp_path)
    rel = v._to_repo_path("x.sh")
    assert rel == tmp_path / "x.sh"
    assert _tests_inline_from_list([]) == "(none discovered)"
