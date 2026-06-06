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


def test_extract_numbered_test_ids_requires_treesitter_for_bats(tmp_path, monkeypatch):
    #R045-T01: parser-backed bats extraction hard-fails when tree-sitter is unavailable.
    fixture = tmp_path / "x.bats"
    fixture.write_text('@test "x" {\n  ' + HASH + "R904-T01: inside test block\n}\n")
    monkeypatch.setattr(parsing, "_TS_GET_PARSER", False)
    monkeypatch.setattr(parsing, "_TS_PARSER_CACHE", {})
    with pytest.raises(RuntimeError, match="tree_sitter_language_pack"):
        parsing.extract_numbered_test_ids(fixture)


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


def test_find_untagged_functions_reports_only_untagged(tmp_path):
    #R040-T01: an untagged function is reported; ones tagged above or inside are not.
    fixture = tmp_path / "m.py"
    body = (
        HASH + "R001: tagged on the leading comment\n"
        "def alpha():\n    return 1\n"
        "def beta():\n    " + HASH + "R002: tagged inside the body\n    return 2\n"
        "def gamma():\n    return 3\n"
    )
    fixture.write_text(body)
    names = [n for n, _ in parsing.find_untagged_functions(fixture)]
    assert "gamma" in names
    assert "alpha" not in names and "beta" not in names


def test_find_untagged_functions_includes_private_nested_dunder(tmp_path):
    #R040-T02: private, nested, and dunder functions are enumerated (not exempt).
    fixture = tmp_path / "m.py"
    body = (
        "class C:\n"
        "    def __init__(self):\n        pass\n"
        "    def _helper(self):\n"
        "        def inner():\n            return 1\n"
        "        return inner\n"
    )
    fixture.write_text(body)
    names = [n for n, _ in parsing.find_untagged_functions(fixture)]
    assert "__init__" in names and "_helper" in names and "inner" in names


def test_find_untagged_functions_unparseable_and_unsupported(tmp_path):
    #R040-T03: a syntax-error Python file and an unsupported suffix yield no findings.
    bad = tmp_path / "b.py"
    bad.write_text("def broken(:\n    pass\n")
    sql = tmp_path / "s.sql"
    sql.write_text("select 1;\n")
    assert parsing.find_untagged_functions(bad) == []
    assert parsing.find_untagged_functions(sql) == []


def test_find_untagged_functions_treesitter_languages(tmp_path):
    #R040-T04: bash and swift functions are enumerated and untagged ones flagged.
    pytest.importorskip("tree_sitter_language_pack")
    sh = tmp_path / "x.sh"
    sh.write_text("foo() {\n  echo hi\n}\n" + HASH + "R003: tag above bar\nbar() {\n  echo bye\n}\n")
    sw = tmp_path / "x.swift"
    sw.write_text('class X {\n  func a() {\n    let s = "}"\n  }\n}\n')
    sh_names = [n for n, _ in parsing.find_untagged_functions(sh)]
    sw_names = [n for n, _ in parsing.find_untagged_functions(sw)]
    assert "foo" in sh_names and "bar" not in sh_names
    assert "a" in sw_names


def test_find_unanchored_numbered_test_tags_python(tmp_path):
    #R050-T01: a tag inside a real def test_* block is anchored; a module-level tag is reported.
    fixture = tmp_path / "x.py"
    body = (
        "def test_a():\n"
        "    x = 1  " + HASH + "R901-T01: inside a real test block\n"
        "GLOBAL = 1  " + HASH + "R902-T01: outside any test function\n"
    )
    fixture.write_text(body)
    reported = [tag for _line, tag, _reason in parsing.find_unanchored_numbered_test_tags(fixture)]
    assert "R902-T01" in reported
    assert "R901-T01" not in reported


def test_find_unanchored_numbered_test_tags_bats(tmp_path):
    #R050-T02: a tag inside a bats @test block is anchored; one outside is reported.
    pytest.importorskip("tree_sitter_language_pack")
    fixture = tmp_path / "x.bats"
    body = (
        HASH + "R901-T01: outside any block\n"
        '@test "t" {\n'
        "  " + HASH + "R902-T01: inside the block\n"
        "}\n"
    )
    fixture.write_text(body)
    reported = [tag for _line, tag, _reason in parsing.find_unanchored_numbered_test_tags(fixture)]
    assert "R901-T01" in reported
    assert "R902-T01" not in reported


def test_find_unanchored_numbered_test_tags_unparseable_fails_closed(tmp_path):
    #R050-T03: an unparseable test-language file with a tag fails closed; no tags yields no findings.
    tagged = tmp_path / "s.sql"
    tagged.write_text("select 1;  " + HASH + "R901-T01: tag in an unparseable sql test file\n")
    reported = [tag for _line, tag, _reason in parsing.find_unanchored_numbered_test_tags(tagged)]
    assert "R901-T01" in reported
    empty = tmp_path / "e.sql"
    empty.write_text("select 1;\n")
    assert parsing.find_unanchored_numbered_test_tags(empty) == []


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
