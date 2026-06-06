"""Unit tests for the traceability engine discovery helpers."""
from pathlib import Path

from traceability import discovery


#R001: shard-3 function tag
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


import ast


#R065: shard-3 function tag
def _extract_traceability_env_knobs_from_source(source_text: str) -> set[str]:
    knobs: set[str] = set()
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            continue
        owner = node.func.value
        if (
            isinstance(owner, ast.Attribute)
            and owner.attr == "environ"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "os"
        ):
            knobs.add(node.args[0].value)
    return {name for name in knobs if name.startswith("TRACEABILITY_") or name == "SHELL_BATS_ROOTS"}


def test_traceability_weakening_knob_surface_locked():
    #R065-T01: traceability env-knob surface remains scope-root only.
    base = Path(__file__).resolve().parent / "traceability"
    observed: set[str] = set()
    for name in ("discovery.py", "parsing.py", "verification.py"):
        observed.update(_extract_traceability_env_knobs_from_source((base / name).read_text(encoding="utf-8")))
    expected = {
        "TRACEABILITY_REQUIREMENTS_ROOTS",
        "TRACEABILITY_TEST_ROOTS",
        "SHELL_BATS_ROOTS",
    }
    assert observed == expected


def test_parse_root_list_dedup_and_normalize(tmp_path):
    #R100-T01: configured root-list parsing de-duplicates and normalizes roots.
    roots = discovery._parse_root_list("a:a,b\n c", tmp_path)
    assert len(roots) == 3


def test_list_shell_test_roots_override_and_default(tmp_path, monkeypatch):
    #R105-T01: shell-test roots honor overrides and default to tests/sh.
    _clear_root_env(monkeypatch)
    assert discovery.list_shell_test_roots(tmp_path) == [tmp_path / "tests/sh"]
    monkeypatch.setenv("TRACEABILITY_TEST_ROOTS", "alt")
    assert discovery.list_shell_test_roots(tmp_path) == [tmp_path / "alt"]


def test_requirements_root_for_file_resolution(tmp_path, monkeypatch):
    #R110-T01: requirements-root ownership resolves the matching configured root.
    _clear_root_env(monkeypatch)
    root_a = tmp_path / "reqA"
    root_a.mkdir()
    monkeypatch.setenv("TRACEABILITY_REQUIREMENTS_ROOTS", root_a.as_posix())
    doc = root_a / "x-requirements.md"
    doc.write_text("# x\n", encoding="utf-8")
    assert discovery._requirements_root_for_file(doc, tmp_path) == root_a


def test_extract_source_files_from_analogous_tree_by_stem(tmp_path):
    #R115-T01: analogous-tree discovery resolves source files by requirements stem.
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    doc = req_dir / "foo-requirements.md"
    doc.write_text("# x\n", encoding="utf-8")
    src = req_dir / "foo.py"
    src.write_text("x = 1\n", encoding="utf-8")
    discovered = discovery.extract_source_files_from_analogous_tree(doc, tmp_path)
    assert "requirements/foo.py" in discovered
