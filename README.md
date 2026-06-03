# runner

Runner is the shared runbook engine for the eggnest workspace. It holds the canonical ("golden") numbered bash
scripts, parallel test lanes, security tooling, database DDL, and per-repo profile configuration that the
sibling repos (`teller`, `classy`, `matchy`, `mailcart`) and the eggnest workspace root all delegate into.

For the design (dual-root model, layering, data flow) see [`Architecture.md`](Architecture.md).

## You run it from the sibling repo, not from here

You almost never invoke runner directly. Each consuming repo keeps thin `NN_*.sh` (or `rNN_*.sh`) pointers that
set `RUNBOOK_REPO_ROOT`, source the repo's profile, and exec the matching golden in runner. Run the numbered
script inside the target repo and it operates on that repo's venv, sources, and tests.

```bash
cd ../teller
./02_create_venv.sh        # execs runner/02_create_venv.sh against teller
```

Two locations stay distinct:

- `RUNNER_HOME` — the runner tree (golden code + helpers).
- `RUNBOOK_REPO_ROOT` — the repo being operated on (its `<repo>-venv`, `src/`, `config/`, `tests/`).

## Running runner on itself

Runner can also be the target repo. The engine only runs the lanes that make sense for itself — antivirus,
dependency freshness, static security, requirements traceability, and shell unit tests:

```bash
cd runner
./02_create_venv.sh && source runner-venv/bin/activate && ./04_load_requirements.sh && deactivate
./run_self_checks.sh             # 5 self lanes against runner, all green
```

`run_self_checks.sh` sets `RUNBOOK_REPO_ROOT` to runner, sources `config/runbook/runner.env`, and execs the
golden `11_run_all_tests_parallel.sh`. Because the goldens live in `tests/tNN_*.sh`, the profile sets
`TEST_POINTER_PREFIX="r"` so discovery runs the thin `tests/rtNN_*.sh` self-pointers (rt01/rt02/rt03/rt04/rt07)
instead of the shared goldens. The numbered/heavy DB/UI lanes are intentionally not part of the self-run.

## Profiles

[`config/runbook/`](config/runbook/) holds one declarative `.env` per repo. The repo's pointer sources its
profile before exec; profiles set knobs (prereq mode, venv policy, pip bootstrap, orchestrator mode, DAST
target) but never secrets (secrets are referenced by 1psa item name).

| Repo | Profile sourced |
|------|-----------------|
| teller | `config/runbook/teller.env` |
| matchy | `config/runbook/matchy.env` |
| mailcart | `config/runbook/mailcart.env` |
| classy | `config/runbook/classy.env` |
| runner (self-run) | `config/runbook/runner.env` |
| eggnest workspace root | `config/runbook/eggnest.env` |

## Ordered workflows

### teller — full stack

```bash
cd ../teller
./01_install_prerequisites.sh    # Homebrew, ZAP, 1psa, Xcode, Postgres, pgTAP
./02_create_venv.sh
activate
./04_load_requirements.sh        # hash-pinned install (locked golden)
./06_deploy_database.sh          # applies teller/src/sql DDL to the profile target
./11_run_all_tests_parallel.sh   # discovers and runs teller/tests/tNN_*
```

### matchy — checks

```bash
cd ../matchy
./02_create_venv.sh
activate
./03_load_requirements.sh
./05_run_unit_tests.sh
./12_run_all_checks_parallel.sh  # parallel CI batch (excludes setup + integration entrypoints)
```

### eggnest — cross-repo engine e2e

```bash
cd ..                            # eggnest workspace root
./02_create_venv.sh
activate
./03_load_requirements.sh
./05_run_e2e_tests.sh            # offline matching cases; --record drives a live AI recording
```

## Parallel orchestration

`11_run_all_tests_parallel.sh` discovers `tests/t*.sh` under the target repo, runs them in parallel, writes
per-script logs under the repo's artifacts directory, and emits completion-order PASS/FAIL lines plus quality
telemetry. `12_run_all_checks_parallel.sh` is the matchy-facing alias into the same orchestrator.

## Test-lane catalog (`tests/tNN_*.sh`)

| Lane | Focus |
|------|-------|
| `t00` | Code quality |
| `t01` | Antivirus (ClamAV) |
| `t02` | Dependency freshness |
| `t03` | Static security (SAST) |
| `t04` | Requirements traceability |
| `t06` | SQL unit tests (pgTAP) |
| `t07` | Shell unit tests (Bats) |
| `t08` | Python unit tests (pytest) |
| `t09` | Mutation tests (mutmut) |
| `t11` | Fuzz / property tests (Hypothesis) |
| `t12` | Dynamic security (DAST) |
| `t13` | API smoke tests |
| `t17` | Live canary |
| `t18` | FileVault encryption verification |

Not every repo enables every lane; the profile and the repo's `tests/` pointers select which lanes run.

## Regenerating pointers

When a golden script is added or renamed, regenerate the thin pointers across all consuming repos:

```bash
./src/scripts/generate_runbook_pointers.sh
```

## Requirements traceability

`tests/py/traceability/` (`cli.py`, `discovery.py`, `parsing.py`, `verification.py`) maps
`requirements/**/*-requirements.md` to source files and `#R###`-tagged tests. The `00`/`t04` lanes run it to
keep requirements, code, and tests in sync.

## Constraints

- No Docker (workspace rule).
- No direct `pip install` in consuming repos — use the numbered load-requirements script.
- No `rm` — destructive cleanup moves to `~/.Trash` with timestamps.
- `umask 007`; files `660`, directories `770`, executables/symlinks `550`.
