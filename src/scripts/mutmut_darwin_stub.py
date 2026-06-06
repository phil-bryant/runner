#R001: Support Darwin-safe mutmut orchestration by providing a stable import path.
#R005: Keep stub behavior deterministic for subprocess-based mutation runs.
#R010: Stub setproctitle before mutmut import side effects on Darwin.
#R030: Resolve mutmut bootstrap compatibility through an import-safe shim module.
#R035: Keep prepare/execute startup deterministic by avoiding runtime branching here.
#R040: Enforce serial-safe startup by preventing crashy setproctitle imports.
#R045: Preserve deterministic subprocess bootstrap behavior on Darwin hosts.
#R050: Support stable trial/rerun policy execution by guaranteeing safe imports.
"""Stub setproctitle before mutmut imports it (macOS fork crash, mutmut #446)."""
import sys


class _SetproctitleStub:
    def setproctitle(self, *_args, **_kwargs):
        #R055: Provide deterministic Darwin-safe setproctitle stub implementation.
        pass


sys.modules["setproctitle"] = _SetproctitleStub()
