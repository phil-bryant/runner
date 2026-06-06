"""Unit tests for the traceability engine parsing primitives.

Bare tag inputs are assembled at runtime (string concatenation) so the literal
bare-tag patterns do not appear in this file and trip the engine's own
unconditional tag-text scan.
"""
import pytest

from traceability import parsing

HASH = "#"


def test_extract_requirement_ids():
    #R001-T01: requirement IDs are parsed from `Rxxx Statement:` lines.
    text = "R001  Statement: foo\nR005  Statement: bar\n"
    assert parsing.extract_requirement_ids(text) == ["R001", "R005"]


def test_extract_source_ids():
    #R005-T01: scoped and bare source tags both yield their IDs.
    text = HASH + "R001: x\n" + HASH + "R005\n"
    assert parsing.extract_source_ids(text) == ["R001", "R005"]


def test_extract_scoped_source_ids():
    #R010-T01: only scoped `#Rxxx: <text>` tags are returned.
    text = HASH + "R001: x\n" + HASH + "R005\n"
    assert parsing.extract_scoped_source_ids(text) == ["R001"]


def test_extract_numbered_requirement_test_ids():
    #R015-T01: numbered bullets are bound to their requirement block.
    text = "R001  Statement: s\nTests:\n- R001-T01: does a thing\n"
    assert parsing.extract_numbered_requirement_test_ids(text) == ["R001-T01"]


def test_verify_requirements_numbered_test_bullets_flags_unnumbered():
    #R020-T01: an unnumbered bullet under `Tests:` is reported.
    text = "R001  Statement: s\nTests:\n- a plain bullet\n"
    issues = parsing.verify_requirements_numbered_test_bullets(text, "doc.md")
    assert issues and "unnumbered" in issues[0]


def test_extract_numbered_test_ids_placement(tmp_path):
    #R025-T01: tags inside @test blocks are collected; outside tags are flagged.
    fixture = tmp_path / "x.bats"
    body = (
        HASH + "R001-T01: outside the block\n"
        '@test "t" {\n'
        "  " + HASH + "R005-T01: inside the block\n"
        "}\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert "R005-T01" in ids
    assert any("R001-T01" in m for m in misplaced)


def test_extract_numbered_test_ids_python_class_method(tmp_path):
    #R025-T02: ast collects tags in class test methods and flags module-level tags.
    fixture = tmp_path / "x.py"
    body = (
        "class TestThing:\n"
        "    def test_a(self):\n"
        "        x = 1  " + HASH + "R901-T01: inside a class test method\n"
        "GLOBAL = 1  " + HASH + "R902-T01: outside any test function\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert "R901-T01" in ids
    assert any("R902-T01" in m for m in misplaced)


def test_extract_numbered_test_ids_python_multiline_string(tmp_path):
    #R025-T03: a dedented brace inside a multi-line string does not end the block.
    fixture = tmp_path / "x.py"
    body = (
        "def test_doc():\n"
        '    s = """\n'
        "dedented } brace and unindented text\n"
        '"""\n'
        "    assert s  " + HASH + "R903-T01: still inside despite the string body\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert "R903-T01" in ids
    assert not misplaced


def test_extract_numbered_test_ids_python_syntax_error_fallback(tmp_path):
    #R025-T04: an unparseable Python file falls back without raising.
    fixture = tmp_path / "x.py"
    body = (
        "def test_ok(:\n"
        "    pass\n"
        + HASH + "R904-T01: tag in a syntactically broken file\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert isinstance(ids, list) and isinstance(misplaced, list)
    assert "R904-T01" in ids or any("R904-T01" in m for m in misplaced)


def test_extract_numbered_test_ids_bats_brace_in_string(tmp_path):
    #R025-T05: a stray brace inside a bats string does not close the block early.
    pytest.importorskip("tree_sitter_language_pack")
    fixture = tmp_path / "x.bats"
    body = (
        '@test "t" {\n'
        '  echo "a closing brace } inside a string"\n'
        "  " + HASH + "R905-T01: inside despite the stray brace\n"
        "}\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert "R905-T01" in ids
    assert not misplaced


def test_extract_numbered_test_ids_swift_closure_braces(tmp_path):
    #R025-T06: swift closure/string braces do not end a test function early.
    pytest.importorskip("tree_sitter_language_pack")
    fixture = tmp_path / "x.swift"
    body = (
        "class X {\n"
        "  func testFoo() {\n"
        '    let s = "}"\n'
        "    run { thing() }\n"
        "    " + HASH + "R906-T01: inside despite nested/closure braces\n"
        "  }\n"
        "}\n"
    )
    fixture.write_text(body)
    ids, misplaced = parsing.extract_numbered_test_ids(fixture)
    assert "R906-T01" in ids
    assert not misplaced


def test_find_unscoped_source_tags():
    #R030-T01: a bare source tag is reported while a scoped one is not.
    text = HASH + "R001\n" + HASH + "R005: scoped ok\n"
    issues = parsing.find_unscoped_source_tags(text)
    assert any("R001" in i for i in issues)
    assert not any("R005" in i for i in issues)


def test_find_unscoped_numbered_test_tags():
    #R035-T01: a bare numbered tag is reported while a scoped one is not.
    text = HASH + "R001-T01\n" + HASH + "R005-T01: scoped ok\n"
    issues = parsing.find_unscoped_numbered_test_tags(text)
    assert any("R001-T01" in i for i in issues)
    assert not any("R005-T01" in i for i in issues)
