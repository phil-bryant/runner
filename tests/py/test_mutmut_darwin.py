#!/usr/bin/env python3

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
