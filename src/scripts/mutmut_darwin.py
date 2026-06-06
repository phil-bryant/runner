#!/usr/bin/env python3
#R001: Provide macOS-safe mutmut prepare/execute flow without in-process forks.
#R005: Run mutant tests via subprocess pytest with deterministic environment setup.
#R010: Integrate with pre-import setproctitle stub to avoid Darwin mutmut crash path.
"""macOS mutmut: prepare stats/mutants, then run mutations via subprocess pytest (no os.fork)."""
import argparse
import json
import os
import subprocess
import sys
import time
import tomllib
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Install the setproctitle stub before mutmut is imported anywhere (Darwin fork+setproctitle crash, mutmut #446).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import mutmut_darwin_stub  # noqa: F401
except ModuleNotFoundError:
    pass


def _purge_pycache_under(mutants_root: Path) -> None:
    #R045: Clear stale mutant pycache trees before subprocess execution.
    stamp = datetime.now().strftime("%Y-%m-%d-%H.%M.%S")
    for cache_dir in mutants_root.rglob("__pycache__"):
        if not cache_dir.is_dir():
            continue
        trash = Path.home() / ".Trash" / f"mutants_pycache_{stamp}_{cache_dir.parent.name}"
        trash.parent.mkdir(parents=True, exist_ok=True)
        if trash.exists():
            trash = Path.home() / ".Trash" / f"mutants_pycache_{stamp}_{cache_dir.parent.name}_{os.getpid()}"
        os.rename(cache_dir, trash)


def _repo_root() -> Path:
    #R030: Resolve target repository root for mutmut task orchestration.
    # Operate on the target repo (RUNBOOK_REPO_ROOT), not the runner directory that hosts this golden.
    env_root = os.environ.get("RUNBOOK_REPO_ROOT")
    root = Path(env_root).resolve() if env_root else Path(__file__).resolve().parent.parent
    return root


def _generate_mutants_serial(*, walk_source_files, create_file_mutants, MutantGenerationStats):
    #R040: Generate mutants serially without fork-based pools on Darwin.
    # Serial, in-process equivalent of mutmut.create_mutants() with no multiprocessing.Pool.
    # See _prepare for why the fork-based pool is avoided on macOS.
    stats = MutantGenerationStats()
    for path in walk_source_files():
        result = create_file_mutants(path)
        for warning in result.warnings:
            warnings.warn(warning)
        if result.error:
            raise result.error
        if result.unmodified:
            stats.unmodified += 1
        elif result.ignored:
            stats.ignored += 1
        else:
            stats.mutated += 1
    return stats


def _ensure_mutmut_config_loaded() -> None:
    #R030: Load mutmut configuration via legacy or modern APIs.
    try:
        from mutmut.__main__ import ensure_config_loaded as legacy_ensure_config_loaded
    except (ImportError, AttributeError):
        legacy_ensure_config_loaded = None

    if callable(legacy_ensure_config_loaded):
        legacy_ensure_config_loaded()
        return

    try:
        from mutmut.configuration import Config
    except ImportError as exc:
        raise RuntimeError(
            "Unable to load mutmut configuration: missing legacy ensure_config_loaded and Config API."
        ) from exc

    ensure_loaded = getattr(Config, "ensure_loaded", None)
    if callable(ensure_loaded):
        ensure_loaded()
        return

    get_config = getattr(Config, "get", None)
    if callable(get_config):
        get_config()
        return

    raise RuntimeError("Unable to load mutmut configuration: unsupported Config API.")


def _should_mutate_path(*, mutmut_module, path: Path) -> bool:
    #R030: Apply mutmut path mutation predicates across config variants.
    config = getattr(mutmut_module, "config", None)
    if config is None:
        try:
            from mutmut.configuration import Config
        except ImportError:
            return True
        config = Config.get()

    should_ignore = getattr(config, "should_ignore_for_mutation", None)
    if callable(should_ignore):
        return not bool(should_ignore(path))

    should_mutate = getattr(config, "should_mutate", None)
    if callable(should_mutate):
        return bool(should_mutate(path))

    private_should_ignore = getattr(config, "_should_ignore_for_mutation", None)
    if callable(private_should_ignore):
        return not bool(private_should_ignore(path))

    return True


def _prepare(root: Path, max_children: int) -> int:
    #R035: Prepare mutant stats and coverage-selected test metadata.
    os.chdir(root)
    os.environ["MUTANT_UNDER_TEST"] = "mutant_generation"
    from mutmut.__main__ import (
        CatchOutput,
        MutantGenerationStats,
        PytestRunner,
        collect_or_load_stats,
        copy_also_copy_files,
        copy_src_dir,
        create_file_mutants,
        makedirs,
        run_forced_fail_test,
        setup_source_paths,
        store_lines_covered_by_tests,
        tests_for_mutant_names,
        walk_source_files,
    )
    from pathlib import Path as PPath

    _ensure_mutmut_config_loaded()
    makedirs(PPath("mutants"), exist_ok=True)
    path_before_pool = sys.path.copy()
    with CatchOutput(spinner_title="Generating mutants"):
        copy_src_dir()
        copy_also_copy_files()
        _purge_pycache_under(PPath("mutants"))
        # Build per-test coverage so each mutant runs only its covering tests (keeps verdicts precise
        # and avoids loading unrelated plugins/fixtures during mutant execution).
        setup_source_paths()
        store_lines_covered_by_tests()
        # Generate mutants serially in-process. mutmut's create_mutants() spins up a
        # multiprocessing.Pool under its module-forced set_start_method('fork'); on macOS
        # that no-exec fork inherits the parent's fork-hostile native state (sqlalchemy,
        # ctypes/libonepsa, requests loaded by store_lines_covered_by_tests) and SIGSEGVs.
        # This loop replicates create_mutants() exactly, minus the Pool, so prepare never
        # forks. t07 always prepares with --max-children 1, so no parallelism is lost.
        stats = _generate_mutants_serial(
            walk_source_files=walk_source_files,
            create_file_mutants=create_file_mutants,
            MutantGenerationStats=MutantGenerationStats,
        )
        sys.path[:] = path_before_pool
        _purge_pycache_under(PPath("mutants"))
        setup_source_paths()
    print(
        f"    done ({stats.mutated} files mutated, {stats.ignored} ignored, {stats.unmodified} unmodified)"
    )
    runner = PytestRunner()
    runner.prepare_main_test_run()
    collect_or_load_stats(runner)
    os.environ["MUTANT_UNDER_TEST"] = ""
    with CatchOutput(spinner_title="Running clean tests") as output_catcher:
        tests = tests_for_mutant_names(())
        clean_exit = runner.run_tests(mutant_name=None, tests=tests)
        if clean_exit != 0:
            output_catcher.dump_output()
            print("Failed to run clean test")
            return 1
    print("    done")
    run_forced_fail_test(runner)
    return 0


def _load_stats(root: Path) -> dict:
    #R035: Load prepared mutmut stats required for execute mode.
    stats_path = root / "mutants" / "mutmut-stats.json"
    return json.loads(stats_path.read_text(encoding="utf-8"))


def _positive_int_from_env(name: str, default: int) -> int:
    #R045: Parse positive integer env knobs for subprocess worker settings.
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _tests_for_mutant(stats: dict, mutant_name: str) -> list[str]:
    #R035: Select ordered covering tests for a specific mutant.
    from mutmut.__main__ import mangled_name_from_mutant_name

    key = mangled_name_from_mutant_name(mutant_name)
    tests = stats.get("tests_by_mangled_function_name", {}).get(key, [])
    durations = stats.get("duration_by_test", {})
    return sorted(tests, key=lambda name: durations.get(name, 0.0))


def _full_suite_tests(root: Path) -> list[str]:
    #R050: Resolve fallback full-suite rerun test targets.
    # Coverage-selected tests can miss mutations on def/signature lines (e.g. default-argument values).
    # Escalating to mutmut's configured tests_dir keeps reruns bounded to mutation-relevant tests.
    pyproject = root / "pyproject.toml"
    configured: list[str] = []
    if pyproject.is_file():
        try:
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            tests_dir = payload.get("tool", {}).get("mutmut", {}).get("tests_dir", [])
            if isinstance(tests_dir, str):
                tests_dir = [tests_dir]
            if isinstance(tests_dir, list):
                for candidate in tests_dir:
                    if not isinstance(candidate, str):
                        continue
                    test_path = (root / candidate).resolve()
                    if test_path.exists():
                        configured.append(str(test_path))
        except (OSError, tomllib.TOMLDecodeError):
            configured = []
    if configured:
        return configured
    py_dir = root / "tests" / "py"
    return [str(py_dir)] if py_dir.is_dir() else []


def _run_mutant_pytest(python: Path, root: Path, mutant_name: str, tests: list[str]) -> int:
    #R045: Compose deterministic subprocess pytest environment per mutant.
    # Derive the venv from the resolved interpreter (venv/bin/python3) so the driver is repo-agnostic.
    venv = python.parent.parent
    env = os.environ.copy()
    env["MUTANT_UNDER_TEST"] = mutant_name
    mutants_src = root / "mutants" / "src"
    repo_src = root / "src"
    if mutants_src.is_dir():
        pythonpath_parts = [mutants_src]
        if repo_src.is_dir():
            pythonpath_parts.append(repo_src)
        pythonpath_parts.append(root)
    else:
        pythonpath_parts = [root / "mutants"]
        if repo_src.is_dir():
            pythonpath_parts.append(repo_src)
        pythonpath_parts.append(root)
    env["PYTHONPATH"] = os.pathsep.join(str(item) for item in pythonpath_parts)
    env["MUTATION_IMPORT_PREPEND"] = os.pathsep.join(str(item) for item in pythonpath_parts)
    env["VIRTUAL_ENV"] = str(venv)
    env["PATH"] = f"{venv / 'bin'}:{env.get('PATH', '')}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("HYPOTHESIS_STORAGE_DIRECTORY", str(root / "artifacts/cache/hypothesis"))
    pytest_runner = (
        "import os\n"
        "import sys\n"
        "import pytest\n"
        "prepend = os.environ.get('MUTATION_IMPORT_PREPEND', '')\n"
        "parts = [path for path in prepend.split(os.pathsep) if path]\n"
        "for path in reversed(parts):\n"
        "    if path in sys.path:\n"
        "        sys.path.remove(path)\n"
        "    sys.path.insert(0, path)\n"
        "raise SystemExit(pytest.main(sys.argv[1:]))\n"
    )
    pytest_args = [
        str(python),
        "-c",
        pytest_runner,
        "-x",
        "-q",
        "-p",
        "no:hypothesis",
        "-p",
        "no:randomly",
        "-p",
        "no:random-order",
        "--rootdir",
        str(root),
        "--tb=no",
    ] + tests
    proc = subprocess.run(pytest_args, cwd=root, env=env)
    return int(proc.returncode)


def _should_rerun_mutant(prior: int | None, rerun_codes: set[int | None]) -> bool:
    #R050: Determine mutant rerun eligibility from prior exit policy.
    return prior in rerun_codes or prior == 33 or (isinstance(prior, int) and prior < 0)


def _status_for_exit_code(exit_code: int) -> str:
    #R050: Map mutant subprocess exit codes to mutmut verdict labels.
    if exit_code in (1, 3):
        return "killed"
    if exit_code == 0:
        return "survived"
    return str(exit_code)


def _run_mutant_trial(
    *,
    mutant_name: str,
    stats: dict,
    python: Path,
    root: Path,
    fallback_tests: list[str],
    escalation_tests: list[str],
) -> tuple[int, float, bool]:
    #R050: Execute mutant trial with fallback and escalation rerun policy.
    tests = _tests_for_mutant(stats, mutant_name)
    if not tests:
        if fallback_tests:
            tests = fallback_tests
        else:
            return 33, 0.0, False
    start = time.monotonic()
    exit_code = _run_mutant_pytest(python, root, mutant_name, tests)
    if exit_code == 0 and escalation_tests and tests != escalation_tests:
        exit_code = _run_mutant_pytest(python, root, mutant_name, escalation_tests)
    duration = time.monotonic() - start
    return exit_code, duration, True


def _collect_mutation_tasks(
    source_paths: list,
    *,
    mutmut,
    SourceFileMutationData,
    rerun_codes: set[int | None],
) -> tuple[dict, list[tuple[Path, str]]]:
    #R035: Collect executable mutation tasks from prepared mutant metadata.
    metas_by_path: dict = {}
    tasks: list[tuple[Path, str]] = []
    for path in source_paths:
        if not _should_mutate_path(mutmut_module=mutmut, path=path):
            continue
        meta = SourceFileMutationData(path=path)
        meta.load()
        metas_by_path[path] = meta
        if not meta.exit_code_by_key:
            continue
        for mutant_name, prior in list(meta.exit_code_by_key.items()):
            if _should_rerun_mutant(prior, rerun_codes):
                tasks.append((path, mutant_name))
    return metas_by_path, tasks


def _execute(root: Path, python: Path) -> int:
    #R050: Orchestrate mutant task execution and persist updated verdict metadata.
    os.chdir(root)
    import mutmut
    from mutmut.__main__ import SourceFileMutationData, load_stats, walk_source_files

    _ensure_mutmut_config_loaded()
    if not load_stats():
        print("mutmut-stats.json missing; run prepare first.")
        return 1
    stats = _load_stats(root)
    rerun_codes = {None, -11, -9}
    fallback_tests = _full_suite_tests(root) if os.environ.get("MUTATION_FALLBACK_TESTS", "true").lower() == "true" else []
    use_full_suite_escalation = os.environ.get("MUTATION_FULL_SUITE_ESCALATION", "true").lower() == "true"
    escalation_tests = fallback_tests if use_full_suite_escalation else []
    mutation_workers = _positive_int_from_env("MUTATION_WORKERS", 1)
    source_paths = list(walk_source_files())
    metas_by_path, tasks = _collect_mutation_tasks(
        source_paths,
        mutmut=mutmut,
        SourceFileMutationData=SourceFileMutationData,
        rerun_codes=rerun_codes,
    )
    if not tasks:
        print("No mutants executed (empty meta or all already verdicted).")
        return 1

    def run_task(task: tuple[Path, str]) -> tuple[Path, str, int, float, bool]:
        #R050: Run a single mutant task trial and return persisted verdict tuple.
        path, mutant_name = task
        exit_code, duration, executed = _run_mutant_trial(
            mutant_name=mutant_name,
            stats=stats,
            python=python,
            root=root,
            fallback_tests=fallback_tests,
            escalation_tests=escalation_tests,
        )
        return path, mutant_name, exit_code, duration, executed

    tried = 0
    if mutation_workers > 1:
        max_workers = min(mutation_workers, max(1, len(tasks)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(run_task, task) for task in tasks]
            for future in as_completed(futures):
                path, mutant_name, exit_code, duration, executed = future.result()
                meta = metas_by_path[path]
                meta.exit_code_by_key[mutant_name] = exit_code
                meta.durations_by_key[mutant_name] = duration
                meta.save()
                print(f"  {mutant_name}: {_status_for_exit_code(exit_code)} (exit {exit_code})")
                if executed:
                    tried += 1
    else:
        for task in tasks:
            path, mutant_name, exit_code, duration, executed = run_task(task)
            meta = metas_by_path[path]
            meta.exit_code_by_key[mutant_name] = exit_code
            meta.durations_by_key[mutant_name] = duration
            meta.save()
            print(f"  {mutant_name}: {_status_for_exit_code(exit_code)} (exit {exit_code})")
            if executed:
                tried += 1
    if tried == 0:
        print("No mutants executed (empty meta or all already verdicted).")
        return 1
    print(f"Executed {tried} mutant(s) via subprocess pytest.")
    return 0


def main(argv: list[str] | None = None) -> int:
    #R055: Route CLI command to prepare/execute with Darwin-safe startup path.
    # New files/dirs from this process: no group/other access (aligns with umask 007 policy).
    os.umask(0o007)
    parser = argparse.ArgumentParser(description="macOS-safe mutmut driver")
    parser.add_argument("command", choices=["prepare", "execute"])
    parser.add_argument("--max-children", type=int, default=1)
    args = parser.parse_args(argv)
    root = _repo_root()
    default_python = os.environ.get("MUTATION_PYTHON") or os.environ.get("TELLER_PYTHON") or str(root / "teller-venv/bin/python3")
    python = Path(default_python)
    if not python.is_absolute():
        python = (root / python).resolve()
    else:
        python = python.expanduser()
    if args.command == "prepare":
        return _prepare(root, args.max_children)
    return _execute(root, python)


if __name__ == "__main__":
    raise SystemExit(main())
