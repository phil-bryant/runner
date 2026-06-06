"""Unit tests for the traceability engine discovery helpers."""
from pathlib import Path

from traceability import discovery


def _clear_root_env(monkeypatch):
    for name in (
        "TRACEABILITY_REQUIREMENTS_ROOTS",
        "TRACEABILITY_TEST_ROOTS",
        "SHELL_BATS_ROOTS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_list_requirements_roots_default_and_override(tmp_path, monkeypatch):
    #R001-T01: default root plus a configured override are resolved.
    _clear_root_env(monkeypatch)
    assert discovery.list_requirements_roots(tmp_path) == [tmp_path / "requirements"]
    monkeypatch.setenv("TRACEABILITY_REQUIREMENTS_ROOTS", "a:b")
    roots = discovery.list_requirements_roots(tmp_path)
    assert (tmp_path / "a") in roots and (tmp_path / "b") in roots


def test_list_requirements_files(tmp_path, monkeypatch):
    #R005-T01: a `*-requirements.md` under a root is discovered.
    _clear_root_env(monkeypatch)
    (tmp_path / "requirements").mkdir()
    doc = tmp_path / "requirements" / "foo-requirements.md"
    doc.write_text("# x\n")
    assert doc in discovery.list_requirements_files(tmp_path)


def test_extract_source_files_from_scope(tmp_path):
    #R010-T01: a backtick-quoted source path in Scope is extracted.
    doc = tmp_path / "d-requirements.md"
    doc.write_text("# t\n\n## Scope\n\nApplies to `src/scripts/foo.sh`.\n\nR001  Statement: x\n")
    assert discovery.extract_source_files_from_requirements_path(doc) == ["src/scripts/foo.sh"]


def test_discover_shell_companion(tmp_path, monkeypatch):
    #R015-T01: a shell source maps to its tests/sh/<stem>.bats companion.
    _clear_root_env(monkeypatch)
    (tmp_path / "tests" / "sh").mkdir(parents=True)
    bats = tmp_path / "tests" / "sh" / "foo.bats"
    bats.write_text('@test "x" {\n  :\n}\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.sh").write_text("#!/bin/sh\n")
    doc = tmp_path / "foo-requirements.md"
    doc.write_text("## Scope\nApplies to `src/foo.sh`.\n")
    default, _ui = discovery.discover_test_files_for_requirements(doc, ["src/foo.sh"], tmp_path)
    assert bats.resolve().as_posix() in default


def test_repo_software_files_excludes_and_includes(tmp_path):
    #R020-T01: a normal source is included while an excluded tree is omitted.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.py").write_text("x = 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.py").write_text("y = 2\n")
    files = discovery.list_repository_software_files(tmp_path)
    assert "src/keep.py" in files
    assert "node_modules/skip.py" not in files


def test_engine_self_coverage_includes_engine():
    #R025-T01: the engine modules and wrapper appear in the software universe.
    repo_root = Path(__file__).resolve().parents[2]
    files = set(discovery.list_repository_software_files(repo_root))
    assert "tests/py/traceability/verification.py" in files
    assert "tests/t04_run_requirements_traceability_tests.sh" in files


def test_function_tag_candidate_files_prunes_excluded_and_nested_repos(tmp_path):
    #R030-T01: analyzable files are listed; excluded dirs and nested repos are pruned.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.py").write_text("def f():\n    return 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "keep.sh").write_text("g() { :; }\n")
    venv = tmp_path / "proj-venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "skip.py").write_text("z = 1\n")
    nested = tmp_path / "subrepo"
    (nested / ".git").mkdir(parents=True)
    (nested / "inner.py").write_text("def h():\n    return 2\n")
    files = discovery.list_function_tag_candidate_files(tmp_path)
    assert "src/keep.py" in files
    assert "tests/keep.sh" in files
    assert not any(f.startswith("proj-venv/") for f in files)
    assert not any(f.startswith("subrepo/") for f in files)
