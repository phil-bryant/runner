"""Unit tests for the traceability engine parsing primitives.

Bare tag inputs are assembled at runtime (string concatenation) so the literal
bare-tag patterns do not appear in this file and trip the engine's own
unconditional tag-text scan.
"""
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
