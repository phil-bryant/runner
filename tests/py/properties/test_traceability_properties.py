"""Property-based tests for traceability parsing primitives."""

from __future__ import annotations

import sys
from pathlib import Path

from hypothesis import given, strategies as st

sys.path.append((Path(__file__).resolve().parents[1]).as_posix())
from traceability import parsing  # noqa: E402


def _rid(value: int) -> str:
    #R025: Build canonical requirement-id text for property-test fixture generation.
    return f"R{value:03d}"


@given(st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=10))
def test_extract_source_ids_deduplicates_and_sorts(ids: list[int]) -> None:
    #R025-T07: property check for deduplication/sorting of extracted source ids.
    tags = [_rid(value) for value in ids]
    lines = [f"#{tag}: scoped source tag" for tag in tags]
    lines.extend(f"#{tag}" for tag in tags)
    parsed = parsing.extract_source_ids("\n".join(lines))
    assert parsed == sorted(set(tags))


@given(
    st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=8),
    st.lists(st.integers(min_value=1, max_value=999), min_size=0, max_size=8),
)
def test_extract_scoped_source_ids_ignores_bare_tags(scoped_ids: list[int], bare_ids: list[int]) -> None:
    #R030-T02: property check that scoped extraction ignores bare `#Rxxx` tags.
    scoped_tags = [_rid(value) for value in scoped_ids]
    bare_tags = [_rid(value) for value in bare_ids]
    lines = [f"#{tag}: scoped text" for tag in scoped_tags]
    lines.extend(f"#{tag}" for tag in bare_tags)
    parsed = parsing.extract_scoped_source_ids("\n".join(lines))
    assert parsed == sorted(set(scoped_tags))


@given(st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=8))
def test_find_unscoped_source_tags_reports_each_bare_tag(bare_ids: list[int]) -> None:
    #R040-T05: property check that every bare source tag produces a strictness issue.
    bare_tags = [_rid(value) for value in bare_ids]
    lines = [f"#{tag}" for tag in bare_tags]
    issues = parsing.find_unscoped_source_tags("\n".join(lines))
    issue_ids = sorted(item.split(":", 1)[1] for item in issues)
    assert issue_ids == sorted(f"#{tag}" for tag in bare_tags)


@given(
    st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=6),
    st.lists(st.integers(min_value=1, max_value=999), min_size=1, max_size=6),
)
def test_numbered_tags_by_line_preserves_line_numbers(
    left_ids: list[int], right_ids: list[int]
) -> None:
    #R145-T02: property check that numbered tag extraction preserves line-number ordering.
    left = [f"#R{value:03d}-T01: left" for value in left_ids]
    right = [f"#R{value:03d}-T02: right" for value in right_ids]
    lines = left + ["echo separator"] + right
    tags = parsing._numbered_tags_by_line(lines)
    expected = [(index + 1, line[1:].split(":", 1)[0]) for index, line in enumerate(lines) if line.startswith("#R")]
    assert tags == expected
