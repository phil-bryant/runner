from __future__ import annotations

import os
from pathlib import Path

from .parsing import extract_source_files_from_requirements


ALLOWED_SOURCE_EXTS = {".sh", ".py", ".swift", ".sql", ".c", ".cc", ".cpp", ".cxx", ".m", ".mm", ".h", ".hpp", ".ts", ".astro", ".mjs"}
ALLOWED_SOURCE_NAMES = {"Makefile", ".gitignore"}

# The traceability engine itself lives under tests/, which is otherwise excluded
# from repository-source coverage. The tool must keep its own house in order, so
# these sources are force-included in the coverage universe: an undocumented
# engine module is then flagged just like any other untraced source file.
TRACEABILITY_ENGINE_DIR = "tests/py/traceability"
TRACEABILITY_ENGINE_WRAPPER = "tests/t04_run_requirements_traceability_tests.sh"


#R025: Self-coverage — force-include the traceability engine's own sources so the
# tool keeps its own house in order even though the rest of tests/ is excluded.
def list_traceability_engine_files(repo_root: Path) -> list[str]:
    files: set[str] = set()
    engine_dir = repo_root / TRACEABILITY_ENGINE_DIR
    if engine_dir.is_dir():
        for path in engine_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            if "__pycache__" in path.parts:
                continue
            if path.is_file():
                files.add(path.relative_to(repo_root).as_posix())
        wrapper = repo_root / TRACEABILITY_ENGINE_WRAPPER
        if wrapper.is_file():
            files.add(wrapper.relative_to(repo_root).as_posix())
    return sorted(files)


#R100: shard-3 function tag
def _parse_root_list(raw_value: str, repo_root: Path) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    normalized = raw_value.replace("\n", ":").replace(",", ":")
    for entry in normalized.split(":"):
        token = entry.strip()
        if not token:
            continue
        path = Path(token)
        if not path.is_absolute():
            path = repo_root / token
        key = path.resolve(strict=False).as_posix()
        if key in seen:
            continue
        seen.add(key)
        roots.append(path)
    return roots


#R100: shard-3 function tag
def _restrict_roots_to_repo(roots: list[Path], repo_root: Path) -> list[Path]:
    """Keep only roots that resolve within the active repository root.

    This prevents environment-level root overrides from leaking files across
    sibling repositories during unit tests or nested workspace runs.
    """
    repo_resolved = repo_root.resolve(strict=False)
    kept: list[Path] = []
    for root in roots:
        resolved = root.resolve(strict=False)
        try:
            resolved.relative_to(repo_resolved)
        except ValueError:
            continue
        kept.append(resolved)
    return kept


#R001: Resolve requirements roots, defaulting to repo_root/requirements and
# honoring a TRACEABILITY_REQUIREMENTS_ROOTS override (colon/comma/newline list).
#R065: shard-3 function tag
def list_requirements_roots(repo_root: Path) -> list[Path]:
    configured = os.environ.get("TRACEABILITY_REQUIREMENTS_ROOTS", "").strip()
    if configured:
        roots = _restrict_roots_to_repo(_parse_root_list(configured, repo_root), repo_root)
        if roots:
            return roots
    return [repo_root / "requirements"]


#R105: shard-3 function tag
#R065: shard-3 function tag
def list_shell_test_roots(repo_root: Path) -> list[Path]:
    configured = (
        os.environ.get("TRACEABILITY_TEST_ROOTS", "").strip()
        or os.environ.get("SHELL_BATS_ROOTS", "").strip()
    )
    if configured:
        roots = _restrict_roots_to_repo(_parse_root_list(configured, repo_root), repo_root)
        if roots:
            return roots
    return [repo_root / "tests/sh"]


#R110: shard-3 function tag
def _requirements_root_for_file(requirements_file: Path, repo_root: Path) -> Path | None:
    for root in list_requirements_roots(repo_root):
        try:
            requirements_file.relative_to(root)
            return root
        except ValueError:
            continue
    return None


#R005: Enumerate requirements docs by globbing `*-requirements.md` under roots.
def list_requirements_files(repo_root: Path) -> list[Path]:
    files: set[Path] = set()
    for root in list_requirements_roots(repo_root):
        if not root.is_dir():
            continue
        files.update({path for path in root.rglob("*-requirements.md") if path.is_file()})
    return sorted(files)


#R010: Extract a doc's declared source files from its Scope section (backtick paths).
def extract_source_files_from_requirements_path(requirements_file: Path) -> list[str]:
    return extract_source_files_from_requirements(requirements_file.read_text(encoding="utf-8"))


#R115: shard-3 function tag
def extract_source_files_from_analogous_tree(requirements_file: Path, repo_root: Path) -> list[str]:
    req_root = _requirements_root_for_file(requirements_file, repo_root)
    rel_path = requirements_file.relative_to(req_root) if req_root else Path(requirements_file.name)
    req_base = rel_path.name
    source_stem = req_base.removesuffix("-requirements.md")
    if source_stem == req_base:
        return []
    search_root = repo_root / rel_path.parent
    if not search_root.exists():
        search_root = repo_root

    matches: set[str] = set()
    for root, _dirs, files in os.walk(search_root):
        for name in files:
            path = Path(root) / name
            if path.suffix and path.stem == source_stem and path.suffix.lstrip(".") in {e.lstrip(".") for e in ALLOWED_SOURCE_EXTS}:
                matches.add(path.relative_to(repo_root).as_posix())
            if name == source_stem and name in ALLOWED_SOURCE_NAMES:
                matches.add(path.relative_to(repo_root).as_posix())
    return sorted(matches)


#R015: Discover companion test files for a doc/source set by convention
# (shell `<stem>.bats`, python `tests/py/test_<stem>.py`, swift lanes, etc.).
def discover_test_files_for_requirements(
    requirements_file: Path, source_files: list[str], repo_root: Path
) -> tuple[list[str], list[str]]:
    seen_default: set[Path] = set()
    seen_ui: set[Path] = set()
    default_results: list[Path] = []
    ui_results: list[Path] = []

    #R015: shard-3 function tag
    def add_path(path: str, lane: str) -> None:
        candidate = (repo_root / path) if not Path(path).is_absolute() else Path(path)
        if not candidate.is_file():
            return
        normalized = candidate.resolve()
        if lane == "ui":
            if normalized not in seen_ui:
                seen_ui.add(normalized)
                ui_results.append(normalized)
            return
        if normalized not in seen_default:
            seen_default.add(normalized)
            default_results.append(normalized)

    #R015: shard-3 function tag
    def collect_swift_lane(root_dir: str, lane: str, stem: str = "") -> None:
        root_path = repo_root / root_dir
        if not root_path.is_dir():
            return
        for path in root_path.rglob("*.swift"):
            if stem and stem not in path.name:
                continue
            add_path(path.relative_to(repo_root).as_posix(), lane)

    #R015: shard-3 function tag
    def add_shell_test(stem: str) -> None:
        if not stem:
            return
        for root in list_shell_test_roots(repo_root):
            add_path((root / f"{stem}.bats").as_posix(), "default")

    requirements_stem = requirements_file.name.removesuffix("-requirements.md")
    add_shell_test(requirements_stem)

    for source_file in source_files:
        source_path = Path(source_file)
        if source_path.is_absolute():
            try:
                source_path = source_path.resolve().relative_to(repo_root.resolve())
            except ValueError:
                pass
        source_norm = source_path.as_posix()
        base = source_path.name
        stem = source_path.stem
        ext = source_path.suffix.lower()
        if ext == ".sh":
            add_shell_test(stem)
        if base == "Makefile":
            add_shell_test("Makefile")
        if ext == ".py":
            if source_norm.startswith("src/teller/"):
                add_path(f"tests/py/test_{stem}.py", "default")
            elif source_norm.startswith("tests/py/traceability/"):
                add_path(f"tests/py/test_{stem}.py", "default")
                if stem == "parsing":
                    add_path("tests/py/properties/test_traceability_properties.py", "default")
            elif source_norm.startswith(tuple(f"{n:02d}_" for n in range(100))):
                add_shell_test(stem)
            else:
                add_path(f"tests/py/test_{stem}.py", "default")
        if ext == ".sql":
            add_shell_test(stem)
            add_path(f"tests/sql/{stem}.sql", "default")
            add_path(f"tests/sql/test_{stem}.sql", "default")
        if ext == ".swift" and source_norm.startswith("src/macos-ui/Sources/"):
            collect_swift_lane("src/macos-ui/Tests", "default", stem=stem)
            collect_swift_lane("src/macos-ui/UITests", "ui", stem=stem)

    if requirements_file.as_posix().startswith((repo_root / "requirements/macos-ui/").as_posix()):
        collect_swift_lane("src/macos-ui/UITests", "ui")

    if requirements_file.name == "t11_run_macos_ui_regression_tests-requirements.md":
        collect_swift_lane("src/macos-ui/UITests", "ui")

    return sorted(path.as_posix() for path in default_results), sorted(path.as_posix() for path in ui_results)


#R020: Enumerate repository software files for coverage, applying directory and
# path exclusions (vendored/generated/test trees, etc.).
def list_repository_software_files(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    excluded_dirs = {
        ".git",
        ".cursor",
        "requirements",
        "tests",
        "Tests",
        "bin",
        "backups",
        "artifacts",
        ".gocache",
        ".gomodcache",
        ".build",
        "__pycache__",
        ".venv",
        "venv",
        "site-packages",
        ".mypy_cache",
        ".tox",
        "node_modules",
        ".gradle",
        "Pods",
        ".swiftpm",
        "teller-venv",
        ".derivedData-ui-tests",
        "dist",
        ".astro",
        ".wrangler",
        "test-results",
        "playwright-report",
    }
    excluded_dir_prefixes = (".derivedData",)
    excluded_relative_paths = {"storage/schema.sql"}
    excluded_relative_prefixes = ("storage/sql/", "archive/", "deprecated/", "src/macos-ui/", "src/sql/postgres/", "src/teller/")

    files: set[str] = set()
    for root, dirs, filenames in os.walk(repo_root):
        root_path = Path(root)
        kept_dirs: list[str] = []
        for directory in dirs:
            if directory in excluded_dirs:
                continue
            if any(directory.startswith(prefix) for prefix in excluded_dir_prefixes):
                continue
            # Prune nested repositories so umbrella workspaces only cover their own files.
            if (root_path / directory / ".git").exists():
                continue
            kept_dirs.append(directory)
        dirs[:] = kept_dirs
        for filename in filenames:
            path = root_path / filename
            rel = path.relative_to(repo_root).as_posix()
            if path.suffix.lower() in ALLOWED_SOURCE_EXTS:
                if rel in excluded_relative_paths:
                    continue
                if any(rel.startswith(prefix) for prefix in excluded_relative_prefixes):
                    continue
                # TypeScript declaration files are generated/type-only surfaces.
                if rel.endswith(".d.ts"):
                    continue
                files.add(rel)
    # Self-coverage: pull the traceability engine's own sources back into the
    # universe even though the rest of tests/ is excluded. The engine grants
    # itself no exemption — every engine source must be covered like any other.
    for engine_rel in list_traceability_engine_files(repo_root):
        files.add(engine_rel)
    return sorted(files)


FUNCTION_TAG_CANDIDATE_EXTS = {
    ".py",
    ".sh",
    ".bats",
    ".swift",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".m",
    ".mm",
}

_FUNCTION_TAG_EXCLUDED_DIRS = {
    ".git",
    ".cursor",
    "artifacts",
    "backups",
    "node_modules",
    "Pods",
    ".build",
    ".swiftpm",
    "site-packages",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".gradle",
    "__pycache__",
    "vendor",
    "third_party",
}


#R030: shard-3 function tag
def _is_function_tag_excluded_dir(name: str) -> bool:
    return (
        name in _FUNCTION_TAG_EXCLUDED_DIRS
        or name.endswith("-venv")
        or name.startswith(".derivedData")
        or name.endswith(".egg-info")
    )


#R030: Enumerate analyzable source+test files for the per-function tag-coverage
# gate. Unlike the coverage universe this includes test trees and applies no
# macos-ui/teller scope exclusions, but prunes vendored/build/venv dirs and any
# nested git repository (so an umbrella workspace does not sweep its subrepos).
def list_function_tag_candidate_files(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    files: set[str] = set()
    for root, dirs, filenames in os.walk(repo_root):
        root_path = Path(root)
        kept = []
        for d in dirs:
            if _is_function_tag_excluded_dir(d):
                continue
            # Prune any nested git repository (e.g. an umbrella workspace's
            # subrepos) so the gate covers only this repo's own functions.
            if (root_path / d / ".git").exists():
                continue
            kept.append(d)
        dirs[:] = kept
        for filename in filenames:
            path = root_path / filename
            if path.suffix.lower() in FUNCTION_TAG_CANDIDATE_EXTS:
                files.add(path.relative_to(repo_root).as_posix())
    return sorted(files)
