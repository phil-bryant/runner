import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


#R001: shard-3 function tag
def _load_mutmut_darwin_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "src" / "scripts" / "mutmut_darwin.py"
    spec = importlib.util.spec_from_file_location("mutmut_darwin_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mutmut_darwin.py test module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MutmutDarwinCompatTests(unittest.TestCase):
    #R001: shard-3 function tag
    def setUp(self):
        self.module = _load_mutmut_darwin_module()

    #R001: shard-3 function tag
    def _patch_mutmut_modules(self, *, main_module, configuration_module, package_module):
        return patch.dict(
            sys.modules,
            {
                "mutmut": package_module,
                "mutmut.__main__": main_module,
                "mutmut.configuration": configuration_module,
            },
            clear=False,
        )

    #R005: shard-3 function tag
    def test_ensure_config_loaded_uses_legacy_api_when_present(self):
        calls = {"legacy": 0, "modern": 0}

        main_module = types.ModuleType("mutmut.__main__")

        #R005: shard-3 function tag
        def ensure_config_loaded():
            calls["legacy"] += 1

        main_module.ensure_config_loaded = ensure_config_loaded

        configuration_module = types.ModuleType("mutmut.configuration")

        class Config:
            @staticmethod
            #R005: shard-3 function tag
            def ensure_loaded():
                calls["modern"] += 1

        configuration_module.Config = Config
        package_module = types.ModuleType("mutmut")
        package_module.__path__ = []  # Mark as package for submodule imports.

        with self._patch_mutmut_modules(
            main_module=main_module,
            configuration_module=configuration_module,
            package_module=package_module,
        ):
            self.module._ensure_mutmut_config_loaded()

        self.assertEqual(calls["legacy"], 1)
        self.assertEqual(calls["modern"], 0)

    #R005: shard-3 function tag
    def test_ensure_config_loaded_falls_back_to_modern_api(self):
        calls = {"modern": 0}

        main_module = types.ModuleType("mutmut.__main__")
        configuration_module = types.ModuleType("mutmut.configuration")

        class Config:
            @staticmethod
            #R005: shard-3 function tag
            def ensure_loaded():
                calls["modern"] += 1

        configuration_module.Config = Config
        package_module = types.ModuleType("mutmut")
        package_module.__path__ = []

        with self._patch_mutmut_modules(
            main_module=main_module,
            configuration_module=configuration_module,
            package_module=package_module,
        ):
            self.module._ensure_mutmut_config_loaded()

        self.assertEqual(calls["modern"], 1)

    #R001: shard-3 function tag
    def test_collect_mutation_tasks_supports_legacy_config_predicate(self):
        keep_path = Path("keep.py")
        skip_path = Path("skip.py")

        class LegacyConfig:
            @staticmethod
            #R001: shard-3 function tag
            def should_ignore_for_mutation(path):
                return Path(path).name == "skip.py"

        class FakeMeta:
            #R001: shard-3 function tag
            def __init__(self, path):
                self.path = path
                self.exit_code_by_key = {}

            #R001: shard-3 function tag
            def load(self):
                if self.path == keep_path:
                    self.exit_code_by_key = {"mutant.keep": None}
                else:
                    self.exit_code_by_key = {"mutant.skip": None}

        mutmut_module = types.SimpleNamespace(config=LegacyConfig())
        metas_by_path, tasks = self.module._collect_mutation_tasks(
            [keep_path, skip_path],
            mutmut=mutmut_module,
            SourceFileMutationData=FakeMeta,
            rerun_codes={None},
        )

        self.assertIn(keep_path, metas_by_path)
        self.assertNotIn(skip_path, metas_by_path)
        self.assertEqual(tasks, [(keep_path, "mutant.keep")])

    #R001: shard-3 function tag
    def test_collect_mutation_tasks_supports_modern_config_predicate(self):
        keep_path = Path("keep.py")
        skip_path = Path("skip.py")

        class ModernConfig:
            @staticmethod
            #R001: shard-3 function tag
            def should_mutate(path):
                return Path(path).name != "skip.py"

        class FakeMeta:
            #R001: shard-3 function tag
            def __init__(self, path):
                self.path = path
                self.exit_code_by_key = {}

            #R001: shard-3 function tag
            def load(self):
                if self.path == keep_path:
                    self.exit_code_by_key = {"mutant.keep": None}
                else:
                    self.exit_code_by_key = {"mutant.skip": None}

        mutmut_module = types.SimpleNamespace(config=ModernConfig())
        metas_by_path, tasks = self.module._collect_mutation_tasks(
            [keep_path, skip_path],
            mutmut=mutmut_module,
            SourceFileMutationData=FakeMeta,
            rerun_codes={None},
        )

        self.assertIn(keep_path, metas_by_path)
        self.assertNotIn(skip_path, metas_by_path)
        self.assertEqual(tasks, [(keep_path, "mutant.keep")])


if __name__ == "__main__":
    unittest.main()
