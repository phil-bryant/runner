from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Iterable


REQ_ID_PATTERN = re.compile(r"^R\d{3}(?:-\d{3})*")
REQ_LINE_PATTERN = re.compile(r"^(R\d{3}(?:-\d{3})*)\s+Statement:")
SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*)")
SCOPED_SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*):\s*[A-Za-z0-9_]")
NUMBERED_TEST_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*-T\d{2})")
NUMBERED_BULLET_PATTERN = re.compile(r"^-\s+(R\d{3}(?:-\d{3})*)-T(\d{2})\s*:")
BACKTICK_TOKEN_PATTERN = re.compile(r"`([^`]+)`")

UI_HINT_PATTERN = re.compile(r"ui[\s-]*test|xcuitest|xctest[\s-]*ui|ui[\s-]*mode", flags=re.IGNORECASE)

ALLOWED_SCOPE_FILE_EXTS = {
    "sh",
    "py",
    "swift",
    "sql",
    "c",
    "cc",
    "cpp",
    "cxx",
    "m",
    "mm",
    "h",
    "hpp",
}
ALLOWED_SCOPE_FILENAMES = {"Makefile", ".gitignore"}

_BATS_START_RE = re.compile(
    r"^\s*(?:@test\b.*\{\s*$|bats_test_function\b.*\{\s*$|[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{\s*$)"
)
_PYTHON_START_RE = re.compile(r"^\s*def\s+test[_A-Za-z0-9]*\s*\(")
_SWIFT_START_RE = re.compile(r"^\s*func\s+test[_A-Za-z0-9]*\s*\(")


#R001: Extract requirement IDs from requirements docs (lines beginning `Rxxx`).
def extract_requirement_ids(text: str) -> list[str]:
    ids = set()
    for line in text.splitlines():
        match = REQ_ID_PATTERN.match(line)
        if match:
            ids.add(match.group(0))
    return sorted(ids)


#R005: Extract source #R tag IDs (scoped or bare) from a source file's text.
def extract_source_ids(text: str) -> list[str]:
    ids = {match.group(1) for match in SOURCE_TAG_PATTERN.finditer(text)}
    return sorted(ids)


#R010: Extract only scoped source IDs (the `#Rxxx: <text>` form, ignoring bare tags).
def extract_scoped_source_ids(text: str) -> list[str]:
    ids = {match.group(1) for match in SCOPED_SOURCE_TAG_PATTERN.finditer(text)}
    return sorted(ids)


def detect_header_bundle_tags(text: str, max_lines: int = 40) -> str | None:
    for idx, raw_line in enumerate(text.splitlines()[:max_lines], start=1):
        total = len(SOURCE_TAG_PATTERN.findall(raw_line))
        scoped = len(re.findall(r"#R\d{3}(?:-\d{3})*:", raw_line))
        if total >= 3 and scoped == 0:
            return f"{idx}:{raw_line}"
    return None


def extract_source_files_from_requirements(text: str) -> list[str]:
    files: set[str] = set()
    in_scope = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped == "## Scope":
            in_scope = True
            continue
        if stripped.startswith("## ") and in_scope:
            in_scope = False
        if REQ_ID_PATTERN.match(stripped) and in_scope:
            in_scope = False
        if not in_scope:
            continue
        for match in BACKTICK_TOKEN_PATTERN.finditer(line):
            token = match.group(1)
            if token.startswith("./"):
                token = token[2:]
            path = Path(token)
            ext = path.suffix.lower().lstrip(".")
            if ext in ALLOWED_SCOPE_FILE_EXTS or token in ALLOWED_SCOPE_FILENAMES:
                files.add(token)
    return sorted(files)


def extract_ui_required_ids(text: str) -> list[str]:
    ids = set()
    for line in text.splitlines():
        lowered = line.lower()
        if not re.match(r"^r\d{3}(?:-\d{3})*\s+statement:", lowered):
            continue
        rid = line.split(None, 1)[0].upper()
        if UI_HINT_PATTERN.search(lowered):
            ids.add(rid)
    return sorted(ids)


#R015: Parse numbered `- Rxxx-Tnn:` test bullets under `Tests:`, scoped to the
# requirement they belong to.
def extract_numbered_requirement_test_ids(text: str) -> list[str]:
    current_requirement_id: str | None = None
    in_tests = False
    ids: set[str] = set()
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        req_match = REQ_LINE_PATTERN.match(stripped)
        if req_match:
            current_requirement_id = req_match.group(1)
            in_tests = False
            continue
        if stripped == "Tests:":
            in_tests = True
            continue
        if in_tests and stripped.startswith("- "):
            match = NUMBERED_BULLET_PATTERN.match(stripped)
            if match and current_requirement_id and match.group(1) == current_requirement_id:
                ids.add(f"{match.group(1)}-T{match.group(2)}")
            continue
        if in_tests and stripped and not stripped.startswith("- "):
            in_tests = False
    return sorted(ids)


#R020: Validate numbered test bullets are well-formed and matched to their owning
# requirement (flag unnumbered/mismatched bullets under `Tests:`).
def verify_requirements_numbered_test_bullets(text: str, requirements_file: str) -> list[str]:
    current_requirement_id: str | None = None
    in_tests = False
    seen_numbers: dict[str, list[int]] = {}
    issues: list[str] = []
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        req_match = REQ_LINE_PATTERN.match(stripped)
        if req_match:
            current_requirement_id = req_match.group(1)
            in_tests = False
            seen_numbers.setdefault(current_requirement_id, [])
            continue
        if stripped == "Tests:":
            in_tests = True
            continue
        if in_tests and stripped.startswith("- "):
            match = NUMBERED_BULLET_PATTERN.match(stripped)
            if not match:
                expected = ""
                if current_requirement_id:
                    next_number = len(seen_numbers.get(current_requirement_id, [])) + 1
                    expected = f" (expected prefix: {current_requirement_id}-T{next_number:02d})"
                issues.append(
                    f"{requirements_file}:{idx}: unnumbered/invalid test bullet under Tests:{expected}"
                )
                continue
            bullet_requirement_id = match.group(1)
            bullet_test_number = int(match.group(2))
            if current_requirement_id and bullet_requirement_id != current_requirement_id:
                issues.append(
                    f"{requirements_file}:{idx}: test bullet {bullet_requirement_id}-T{bullet_test_number:02d} does not match requirement {current_requirement_id}"
                )
                continue
            if current_requirement_id:
                seen_numbers[current_requirement_id].append(bullet_test_number)
            continue
        if in_tests and stripped and not stripped.startswith("- "):
            in_tests = False
    return issues


_TS_GET_PARSER = None  # None = not yet attempted, False = unavailable, else callable
_TS_PARSER_CACHE: dict[str, object] = {}


def _treesitter_required() -> bool:
    return os.environ.get("STRICT_TRACEABILITY_TREESITTER", "false").lower() == "true"


def _treesitter_parser(language_name: str):
    """Return a cached tree-sitter parser for ``language_name`` or ``None``.

    Imports are lazy and failures degrade gracefully to the brace-counting
    fallbacks. When ``STRICT_TRACEABILITY_TREESITTER=true`` an unavailable
    parser is a hard error so CI cannot silently ship the weaker detector.
    """
    global _TS_GET_PARSER
    if _TS_GET_PARSER is None:
        try:
            from tree_sitter_language_pack import get_parser

            _TS_GET_PARSER = get_parser
        except Exception:
            _TS_GET_PARSER = False
    if _TS_GET_PARSER is False:
        if _treesitter_required():
            raise RuntimeError(
                "STRICT_TRACEABILITY_TREESITTER=true but tree_sitter_language_pack "
                "could not be imported; install tree-sitter-language-pack."
            )
        return None
    if language_name not in _TS_PARSER_CACHE:
        try:
            _TS_PARSER_CACHE[language_name] = _TS_GET_PARSER(language_name)
        except Exception:
            if _treesitter_required():
                raise
            _TS_PARSER_CACHE[language_name] = None
    return _TS_PARSER_CACHE[language_name]


# The tree-sitter binding shipped by tree-sitter-language-pack exposes node
# accessors as methods (`kind()`, `start_position()`, `child(i)`), whereas the
# upstream python-tree-sitter exposes them as properties (`type`, `start_point`,
# `children`). These adapters normalize both so the detector is binding-agnostic.
_MISSING = object()


def _ts_value(value):
    return value() if callable(value) else value


def _ts_attr(obj, *names):
    for name in names:
        attr = getattr(obj, name, _MISSING)
        if attr is not _MISSING:
            return _ts_value(attr)
    return None


def _point_row(point) -> int:
    if point is None:
        return 0
    row = getattr(point, "row", None)
    if row is not None:
        return row
    try:
        return point[0]
    except Exception:
        return 0


def _ts_kind(node) -> str | None:
    return _ts_attr(node, "type", "kind")


def _ts_children(node) -> list:
    children = getattr(node, "children", _MISSING)
    if children is not _MISSING and not callable(children):
        return list(children)
    count = _ts_attr(node, "child_count")
    if count is None:
        return list(children()) if callable(children) else []
    return [node.child(i) for i in range(count)]


def _ts_node_name(node, source_bytes: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    text = getattr(name_node, "text", _MISSING)
    if text is not _MISSING:
        text = _ts_value(text)
        if isinstance(text, (bytes, bytearray)):
            return bytes(text).decode("utf-8", "replace")
        if text is not None:
            return str(text)
    start = _ts_attr(name_node, "start_byte")
    end = _ts_attr(name_node, "end_byte")
    if start is not None and end is not None:
        return source_bytes[start:end].decode("utf-8", "replace")
    return None


def _ts_parse(parser, source_text: str):
    try:
        return parser.parse(source_text.encode("utf-8"))
    except TypeError:
        return parser.parse(source_text)


def _treesitter_block_ranges(
    language_name: str, source_text: str, node_kinds: set[str], name_prefix: str | None = None
) -> list[tuple[int, int]] | None:
    parser = _treesitter_parser(language_name)
    if parser is None:
        return None
    try:
        tree = _ts_parse(parser, source_text)
    except Exception:
        if _treesitter_required():
            raise
        return None
    source_bytes = source_text.encode("utf-8")
    ranges: list[tuple[int, int]] = []
    stack = [_ts_attr(tree, "root_node")]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if _ts_kind(node) in node_kinds:
            if name_prefix is None or (
                (name := _ts_node_name(node, source_bytes)) is not None and name.startswith(name_prefix)
            ):
                ranges.append((_point_row(_ts_attr(node, "start_point", "start_position")) + 1,
                               _point_row(_ts_attr(node, "end_point", "end_position")) + 1))
        stack.extend(_ts_children(node))
    return ranges


def _brace_ranges(lines: list[str], start_re: re.Pattern[str]) -> list[tuple[int, int]]:
    """Fallback block detector: brace-balanced ranges started by ``start_re``.

    Reproduces the legacy heuristic for use when tree-sitter is unavailable.
    """
    ranges: list[tuple[int, int]] = []
    in_block = False
    depth = 0
    start = 0
    for idx, line in enumerate(lines, start=1):
        if not in_block and start_re.search(line):
            in_block = True
            depth = 0
            start = idx
        if in_block:
            depth += line.count("{")
            depth -= line.count("}")
            if depth <= 0:
                ranges.append((start, idx))
                in_block = False
                depth = 0
    if in_block:
        ranges.append((start, len(lines)))
    return ranges


def _python_indentation_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Fallback block detector for unparseable Python (SyntaxError)."""
    ranges: list[tuple[int, int]] = []
    in_block = False
    block_indent = 0
    start = 0
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" \t"))
        if not in_block:
            if _PYTHON_START_RE.search(line):
                in_block = True
                block_indent = indent
                start = idx
            continue
        if stripped and indent <= block_indent and not _PYTHON_START_RE.search(line):
            ranges.append((start, idx - 1))
            in_block = False
            if _PYTHON_START_RE.search(line):
                in_block = True
                block_indent = indent
                start = idx
    if in_block:
        ranges.append((start, len(lines)))
    return ranges


def _python_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _python_indentation_ranges(lines)
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            end = getattr(node, "end_lineno", None) or node.lineno
            ranges.append((node.lineno, end))
    return ranges


_BATS_TEST_DECL_RE = re.compile(r"^(\s*)(?:@test\b.*|bats_test_function\b.*)\{\s*$")


def _bats_to_bash(text: str) -> str:
    """Rewrite bats ``@test "..." {`` headers into valid bash function decls.

    The rewrite is line-preserving (same number of lines, replacement stays on
    the original line) so tree-sitter node rows map 1:1 back to source lines.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        match = _BATS_TEST_DECL_RE.match(line)
        if match:
            out_lines.append(f"{match.group(1)}function _bats_test_shim() {{")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _bats_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    ranges = _treesitter_block_ranges("bash", _bats_to_bash(text), {"function_definition"})
    if ranges is not None:
        return ranges
    return _brace_ranges(lines, _BATS_START_RE)


def _swift_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    ranges = _treesitter_block_ranges("swift", text, {"function_declaration"}, name_prefix="test")
    if ranges is not None:
        return ranges
    return _brace_ranges(lines, _SWIFT_START_RE)


def _test_block_line_ranges(suffix: str, text: str, lines: list[str]) -> list[tuple[int, int]] | None:
    """Inclusive (start_line, end_line) ranges of test bodies for ``suffix``.

    Returns ``None`` for languages with no defined test-block convention, which
    signals "collect tags anywhere, enforce no placement" to the caller.
    """
    if suffix == ".py":
        return _python_test_block_ranges(text, lines)
    if suffix == ".bats":
        return _bats_test_block_ranges(text, lines)
    if suffix == ".swift":
        return _swift_test_block_ranges(text, lines)
    return None


def _numbered_tags_by_line(lines: list[str]) -> list[tuple[int, str]]:
    tags: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        for match in NUMBERED_TEST_TAG_PATTERN.finditer(line):
            tags.append((idx, match.group(1)))
    return tags


def _line_in_ranges(ranges: list[tuple[int, int]], line_number: int) -> bool:
    return any(start <= line_number <= end for start, end in ranges)


#R025: Extract numbered `#Rxxx-Tnn` tags from a test file and enforce that they
# live inside executable test blocks (reporting misplaced tags). Test-block
# boundaries come from a parser (Python `ast`; bats/swift via tree-sitter) so
# braces/dedents inside strings, comments, and heredocs no longer mislead the
# detector; languages with no block convention collect tags without placement.
def extract_numbered_test_ids(test_file: Path) -> tuple[list[str], list[str]]:
    if not test_file.exists():
        return [], []

    text = test_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    tags = _numbered_tags_by_line(lines)
    ranges = _test_block_line_ranges(test_file.suffix.lower(), text, lines)

    ids: set[str] = set()
    misplaced: list[str] = []
    if ranges is None:
        for _line_number, tag in tags:
            ids.add(tag)
        return sorted(ids), misplaced

    for line_number, tag in tags:
        if _line_in_ranges(ranges, line_number):
            ids.add(tag)
        else:
            misplaced.append(f"{test_file}:{line_number}: #{tag}")
    return sorted(ids), misplaced


_ANY_SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*)(-T\d{2})?")
_SCOPED_SUFFIX_PATTERN = re.compile(r":\s*\S")


#R030: Locate bare source #R tags that omit scoped requirement text (strictness).
def find_unscoped_source_tags(text: str) -> list[str]:
    """Locate source #Rxxx tags that carry no scoped requirement text.

    A compliant source tag is the scoped form ``#Rxxx: <text>``; a bare ``#Rxxx``
    with nothing meaningful after it is reported as ``<line>:<tag>``. Numbered
    test tags (``#Rxxx-Tnn``) are intentionally ignored here; see
    :func:`find_unscoped_numbered_test_tags`.
    """
    issues: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for match in _ANY_SOURCE_TAG_PATTERN.finditer(line):
            if match.group(2):
                continue
            if not _SCOPED_SUFFIX_PATTERN.match(line[match.end():]):
                issues.append(f"{idx}:{match.group(0)}")
    return issues


#R035: Locate numbered #Rxxx-Tnn test tags that omit scoped text (strictness).
def find_unscoped_numbered_test_tags(text: str) -> list[str]:
    """Locate numbered ``#Rxxx-Tnn`` test tags that carry no scoped text.

    A compliant numbered tag is ``#Rxxx-Tnn: <text>``; a bare ``#Rxxx-Tnn`` is
    reported as ``<line>:#<tag>``.
    """
    issues: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for match in NUMBERED_TEST_TAG_PATTERN.finditer(line):
            if not _SCOPED_SUFFIX_PATTERN.match(line[match.end():]):
                issues.append(f"{idx}:#{match.group(1)}")
    return issues


def format_bulleted(items: Iterable[str], prefix: str = "  - ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items)
