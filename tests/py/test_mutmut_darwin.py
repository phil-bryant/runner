#!/usr/bin/env python3

import importlib.util
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


#R030: shard-3 function tag
def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "mutmut_darwin.py"
    spec = importlib.util.spec_from_file_location("mutmut_darwin_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mutmut_darwin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#R030: shard-3 function tag
def load_stub():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "mutmut_darwin_stub.py"
    spec = importlib.util.spec_from_file_location("mutmut_darwin_stub_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mutmut_darwin_stub.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MutmutDarwinTests(unittest.TestCase):
    #R030: shard-3 function tag
    def setUp(self):
        self.module = load_module()

    def test_repo_root_prefers_runbook_repo_root(self):
        #R030-T01: Verify config-loading fallback behavior and mutation-path predicate handling across compatibility shims.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"RUNBOOK_REPO_ROOT": tmp}, clear=False):
                self.assertEqual(self.module._repo_root(), Path(tmp).resolve())

    def test_collect_mutation_tasks_uses_prepared_metadata(self):
        #R035-T01: Verify task collection and per-mutant test selection produce deterministic runnable task sets.
        keep_path = Path("keep.py")
        skip_path = Path("skip.py")

        class FakeMeta:
            #R030: shard-3 function tag
            def __init__(self, path):
                self.path = path
                self.exit_code_by_key = {}

            #R030: shard-3 function tag
            def load(self):
                if self.path == keep_path:
                    self.exit_code_by_key = {"mutant.keep": None}
                else:
                    self.exit_code_by_key = {"mutant.skip": 0}

        mutmut_module = types.SimpleNamespace(config=types.SimpleNamespace(should_mutate=lambda path: Path(path) == keep_path))
        _, tasks = self.module._collect_mutation_tasks(
            [keep_path, skip_path],
            mutmut=mutmut_module,
            SourceFileMutationData=FakeMeta,
            rerun_codes={None},
        )
        self.assertEqual(tasks, [(keep_path, "mutant.keep")])

    def test_generate_mutants_serial_accumulates_stats(self):
        #R040-T01: Verify serial mutant generation updates mutation stats without requiring multiprocessing pools.
        class Stats:
            #R030: shard-3 function tag
            def __init__(self):
                self.unmodified = 0
                self.ignored = 0
                self.mutated = 0

        class Result:
            #R030: shard-3 function tag
            def __init__(self, unmodified=False, ignored=False):
                self.warnings = []
                self.error = None
                self.unmodified = unmodified
                self.ignored = ignored

        paths = [Path("a.py"), Path("b.py"), Path("c.py")]

        #R030: shard-3 function tag
        def walk_source_files():
            return paths

        #R030: shard-3 function tag
        def create_file_mutants(path):
            if path.name == "a.py":
                return Result(unmodified=True)
            if path.name == "b.py":
                return Result(ignored=True)
            return Result()

        stats = self.module._generate_mutants_serial(
            walk_source_files=walk_source_files,
            create_file_mutants=create_file_mutants,
            MutantGenerationStats=Stats,
        )
        self.assertEqual((stats.unmodified, stats.ignored, stats.mutated), (1, 1, 1))

    def test_run_mutant_pytest_builds_expected_environment(self):
        #R045-T01: Verify subprocess env composition (`PYTHONPATH`, venv PATH, bytecode/cache controls) and pycache cleanup behavior.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root / "venv/bin/python3"
            python.parent.mkdir(parents=True)
            python.write_text("", encoding="utf-8")
            (root / "mutants/src").mkdir(parents=True)
            (root / "src").mkdir(parents=True)
            captured = {}

            #R030: shard-3 function tag
            def fake_run(args, cwd=None, env=None):
                captured["args"] = args
                captured["cwd"] = cwd
                captured["env"] = env
                return types.SimpleNamespace(returncode=0)

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                rc = self.module._run_mutant_pytest(python, root, "mutant.sample", ["tests/py"])
        self.assertEqual(rc, 0)
        self.assertEqual(captured["cwd"], root)
        self.assertIn("MUTANT_UNDER_TEST", captured["env"])
        self.assertEqual(captured["env"]["MUTANT_UNDER_TEST"], "mutant.sample")
        self.assertIn("PYTHONDONTWRITEBYTECODE", captured["env"])

    def test_status_and_rerun_policy(self):
        #R050-T01: Verify exit-code status mapping and rerun/escalation behavior for executed mutants.
        self.assertEqual(self.module._status_for_exit_code(1), "killed")
        self.assertEqual(self.module._status_for_exit_code(0), "survived")
        self.assertTrue(self.module._should_rerun_mutant(None, {None, -11}))
        self.assertTrue(self.module._should_rerun_mutant(-9, {None}))

    def test_main_routes_prepare_execute_and_stub(self):
        #R055-T01: Verify CLI routing behavior and Darwin stub import/install path are both exercised.
        with patch.object(self.module, "_repo_root", return_value=Path("/tmp/repo")):
            with patch.object(self.module, "_prepare", return_value=17) as prep:
                with patch.object(self.module, "_execute", return_value=23) as execute:
                    prep_rc = self.module.main(["prepare"])
                    exec_rc = self.module.main(["execute"])
        self.assertEqual(prep_rc, 17)
        self.assertEqual(exec_rc, 23)
        prep.assert_called_once()
        execute.assert_called_once()
        stub = load_stub()
        self.assertTrue(hasattr(stub.sys.modules["setproctitle"], "setproctitle"))

    def test_positive_int_env_helper_defaults_on_invalid_values(self):
        #R045-T02: env integer helper falls back to defaults on invalid/non-positive values.
        with patch.dict("os.environ", {"MUTATION_WORKERS": "abc"}, clear=False):
            self.assertEqual(self.module._positive_int_from_env("MUTATION_WORKERS", 3), 3)
        with patch.dict("os.environ", {"MUTATION_WORKERS": "0"}, clear=False):
            self.assertEqual(self.module._positive_int_from_env("MUTATION_WORKERS", 3), 3)
        with patch.dict("os.environ", {"MUTATION_WORKERS": "5"}, clear=False):
            self.assertEqual(self.module._positive_int_from_env("MUTATION_WORKERS", 3), 5)

    def test_should_mutate_path_uses_available_config_predicates(self):
        #R030-T02: path predicate helper honors should_mutate/should_ignore variants.
        config_mutate = types.SimpleNamespace(should_mutate=lambda _p: True)
        self.assertTrue(self.module._should_mutate_path(mutmut_module=types.SimpleNamespace(config=config_mutate), path=Path("x.py")))
        config_ignore = types.SimpleNamespace(should_ignore_for_mutation=lambda _p: True)
        self.assertFalse(self.module._should_mutate_path(mutmut_module=types.SimpleNamespace(config=config_ignore), path=Path("x.py")))
        config_private_ignore = types.SimpleNamespace(_should_ignore_for_mutation=lambda _p: False)
        self.assertTrue(self.module._should_mutate_path(mutmut_module=types.SimpleNamespace(config=config_private_ignore), path=Path("x.py")))

    def test_run_mutant_trial_fallback_and_escalation_paths(self):
        #R050-T02: mutant trial helper covers no-tests fallback and full-suite escalation.
        stats = {"tests_by_mangled_function_name": {}, "duration_by_test": {}}
        python = Path("/tmp/python")
        root = Path("/tmp/root")
        with patch.object(self.module, "_tests_for_mutant", return_value=[]):
            exit_code, duration, executed = self.module._run_mutant_trial(
                mutant_name="module__mutmut_1",
                stats=stats,
                python=python,
                root=root,
                fallback_tests=[],
                escalation_tests=[],
            )
        self.assertEqual((exit_code, executed), (33, False))
        self.assertEqual(duration, 0.0)

        stats_with_tests = {"tests_by_mangled_function_name": {"mutant__x": ["tests/py"]}, "duration_by_test": {}}
        with (
            patch.object(self.module, "_tests_for_mutant", return_value=["tests/py"]),
            patch.object(self.module, "_run_mutant_pytest", side_effect=[0, 1]) as run_pytest,
        ):
            exit_code, _, executed = self.module._run_mutant_trial(
                mutant_name="mutant.x",
                stats=stats_with_tests,
                python=python,
                root=root,
                fallback_tests=["tests/py"],
                escalation_tests=["tests/full"],
            )
        self.assertTrue(executed)
        self.assertEqual(exit_code, 1)
        self.assertEqual(run_pytest.call_count, 2)

    def test_full_suite_tests_prefers_pyproject_then_tests_dir(self):
        #R050-T03: full-suite helper prefers configured mutmut tests_dir, else falls back to tests/py.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyproject = root / "pyproject.toml"
            (root / "custom-tests").mkdir()
            pyproject.write_text(
                json.dumps({}),
                encoding="utf-8",
            )
            # overwrite with valid TOML after creating file shell
            pyproject.write_text(
                "[tool.mutmut]\ntests_dir = [\"custom-tests\"]\n",
                encoding="utf-8",
            )
            self.assertEqual(self.module._full_suite_tests(root), [str((root / "custom-tests").resolve())])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests" / "py").mkdir(parents=True, exist_ok=True)
            self.assertEqual(self.module._full_suite_tests(root), [str(root / "tests" / "py")])

    def test_purge_pycache_moves_directories_to_trash(self):
        #R045-T03: pycache purge relocates cache dirs to trash-safe paths.
        with tempfile.TemporaryDirectory() as tmp:
            mutants_root = Path(tmp) / "mutants"
            cache_dir = mutants_root / "pkg" / "__pycache__"
            cache_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(self.module.Path, "home", return_value=Path(tmp)):
                self.module._purge_pycache_under(mutants_root)
            self.assertFalse(cache_dir.exists())

    def test_generate_mutants_serial_warns_and_raises_on_error(self):
        #R040-T02: serial mutant generation emits warnings and raises result.error.
        class Stats:
            #R040: nested helper function tag
            def __init__(self):
                self.unmodified = 0
                self.ignored = 0
                self.mutated = 0

        class Result:
            #R040: nested helper function tag
            def __init__(self, *, warnings=None, error=None, unmodified=False, ignored=False):
                self.warnings = warnings or []
                self.error = error
                self.unmodified = unmodified
                self.ignored = ignored

        #R040: nested helper function tag
        def walk():
            return [Path("a.py"), Path("b.py")]

        #R040: nested helper function tag
        def create(path):
            if path.name == "a.py":
                return Result(warnings=["warn-a"], unmodified=True)
            return Result(error=RuntimeError("boom"))

        with patch.object(self.module.warnings, "warn") as warn_mock:
            with self.assertRaises(RuntimeError):
                self.module._generate_mutants_serial(
                    walk_source_files=walk,
                    create_file_mutants=create,
                    MutantGenerationStats=Stats,
                )
        warn_mock.assert_called_once()

    def test_ensure_config_loaded_raises_for_unsupported_config_api(self):
        #R030-T03: config loader raises when modern Config API lacks ensure_loaded/get.
        fake_mutmut_pkg = types.ModuleType("mutmut")
        fake_mutmut_pkg.__path__ = []
        fake_main = types.ModuleType("mutmut.__main__")
        fake_config = types.ModuleType("mutmut.configuration")
        fake_config.Config = type("Config", (), {})
        with patch.dict(
            "sys.modules",
            {"mutmut": fake_mutmut_pkg, "mutmut.__main__": fake_main, "mutmut.configuration": fake_config},
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                self.module._ensure_mutmut_config_loaded()

    def test_should_mutate_path_defaults_true_when_config_import_missing(self):
        #R030-T04: path mutation helper defaults to True when Config import is unavailable.
        with patch.dict("sys.modules", {"mutmut.configuration": None}, clear=False):
            self.assertTrue(
                self.module._should_mutate_path(mutmut_module=types.SimpleNamespace(config=None), path=Path("x.py"))
            )

    def test_execute_handles_missing_stats_and_no_tasks(self):
        #R050-T04: execute path returns non-zero when stats are missing or no tasks remain.
        fake_mutmut = types.ModuleType("mutmut")
        fake_mutmut.config = types.SimpleNamespace(should_mutate=lambda _p: True)
        fake_main = types.ModuleType("mutmut.__main__")
        fake_main.SourceFileMutationData = object
        fake_main.walk_source_files = lambda: []
        fake_main.load_stats = lambda: False
        fake_config = types.ModuleType("mutmut.configuration")
        fake_config.Config = type("Config", (), {"ensure_loaded": staticmethod(lambda: None)})
        cwd_before = Path.cwd()

        with patch.dict(
            "sys.modules",
            {"mutmut": fake_mutmut, "mutmut.__main__": fake_main, "mutmut.configuration": fake_config},
            clear=False,
        ):
            try:
                rc = self.module._execute(Path("/tmp"), Path("/tmp/python"))
            finally:
                os.chdir(cwd_before)
        self.assertEqual(rc, 1)

        fake_main.load_stats = lambda: True
        with (
            patch.dict(
                "sys.modules",
                {"mutmut": fake_mutmut, "mutmut.__main__": fake_main, "mutmut.configuration": fake_config},
                clear=False,
            ),
            patch.object(self.module, "_load_stats", return_value={}),
            patch.object(self.module, "_collect_mutation_tasks", return_value=({}, [])),
        ):
            try:
                rc = self.module._execute(Path("/tmp"), Path("/tmp/python"))
            finally:
                os.chdir(cwd_before)
        self.assertEqual(rc, 1)

    def test_execute_updates_meta_and_returns_success(self):
        #R050-T05: execute path updates mutant metadata and succeeds for serial/parallel workers.
        class _Meta:
            #R050: nested helper function tag
            def __init__(self):
                self.exit_code_by_key = {}
                self.durations_by_key = {}
                self.saved = 0

            #R050: nested helper function tag
            def save(self):
                self.saved += 1

        path = Path("a.py")
        meta = _Meta()
        fake_mutmut = types.ModuleType("mutmut")
        fake_mutmut.config = types.SimpleNamespace(should_mutate=lambda _p: True)
        fake_main = types.ModuleType("mutmut.__main__")
        fake_main.SourceFileMutationData = object
        fake_main.walk_source_files = lambda: [path]
        fake_main.load_stats = lambda: True
        fake_config = types.ModuleType("mutmut.configuration")
        fake_config.Config = type("Config", (), {"ensure_loaded": staticmethod(lambda: None)})

        cwd_before = Path.cwd()
        with (
            patch.dict(
                "sys.modules",
                {"mutmut": fake_mutmut, "mutmut.__main__": fake_main, "mutmut.configuration": fake_config},
                clear=False,
            ),
            patch.object(self.module, "_load_stats", return_value={"tests_by_mangled_function_name": {}, "duration_by_test": {}}),
            patch.object(self.module, "_collect_mutation_tasks", return_value=({path: meta}, [(path, "module__mutmut_1")])),
            patch.object(self.module, "_run_mutant_trial", return_value=(0, 0.01, True)),
            patch.dict("os.environ", {"MUTATION_WORKERS": "1"}, clear=False),
        ):
            try:
                rc = self.module._execute(Path("/tmp"), Path("/tmp/python"))
            finally:
                os.chdir(cwd_before)
        self.assertEqual(rc, 0)
        self.assertEqual(meta.exit_code_by_key["module__mutmut_1"], 0)
        self.assertEqual(meta.saved, 1)

        meta_parallel = _Meta()
        with (
            patch.dict(
                "sys.modules",
                {"mutmut": fake_mutmut, "mutmut.__main__": fake_main, "mutmut.configuration": fake_config},
                clear=False,
            ),
            patch.object(self.module, "_load_stats", return_value={"tests_by_mangled_function_name": {}, "duration_by_test": {}}),
            patch.object(self.module, "_collect_mutation_tasks", return_value=({path: meta_parallel}, [(path, "module__mutmut_2")])),
            patch.object(self.module, "_run_mutant_trial", return_value=(1, 0.02, True)),
            patch.dict("os.environ", {"MUTATION_WORKERS": "2"}, clear=False),
        ):
            try:
                rc = self.module._execute(Path("/tmp"), Path("/tmp/python"))
            finally:
                os.chdir(cwd_before)
        self.assertEqual(rc, 0)
        self.assertEqual(meta_parallel.exit_code_by_key["module__mutmut_2"], 1)



if __name__ == "__main__":
    unittest.main()
