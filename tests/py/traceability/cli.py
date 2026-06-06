#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from .verification import TraceabilityVerifier


def main(argv: list[str] | None = None) -> int:
    #R001: Resolve CLI arguments, defaulting to sys.argv[1:] when none are passed.
    args = list(sys.argv[1:] if argv is None else argv)
    #R005: Treat the current working directory as the repository root under test.
    repo_root = Path.cwd()
    verifier = TraceabilityVerifier(repo_root=repo_root)
    return verifier.run(args)


if __name__ == "__main__":
    #R010: Propagate the verifier's return code as the process exit status.
    raise SystemExit(main())
