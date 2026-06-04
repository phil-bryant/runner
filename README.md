# runner

Runner is the shared runbook engine for the eggnest workspace. It holds the canonical ("golden") numbered bash
scripts, parallel test lanes, security tooling, database DDL, and per-repo profile configuration that the
sibling repos (`teller`, `classy`, `matchy`, `mailcart`) and the eggnest workspace root all delegate into.

For the design (dual-root model, layering, data flow) see [`Architecture.md`](Architecture.md).

## You run it from the sibling repo, not from here

You almost never invoke runner directly. Each consuming repo keeps thin `NN_*.sh` operator pointers and
`tests/tNN_*.sh` test pointers that set `RUNBOOK_REPO_ROOT`, source the repo's profile, and exec the matching
golden in runner. Run the numbered script inside the target repo and it operates on that repo's venv, sources, and tests.

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
./11_run_all_self_tests_parallel.sh   # 5 self lanes against runner, all green
```

The load-requirements step bootstraps a hash-pinned secure `pip` (`26.1.2`) before self-tests run. If `t03` ever
fails with `pip-audit` findings on `pip` itself, reactivate `runner-venv` and rerun `./04_load_requirements.sh`
(or recreate the venv with `./02_create_venv.sh`) before running `./11_run_all_self_tests_parallel.sh` again.

`11_run_all_self_tests_parallel.sh` sets `RUNBOOK_REPO_ROOT` to runner, sources `config/runbook/runner.env`, and execs the
golden `07_run_all_tests_parallel.sh`. The orchestrator discovers runner's own `tests/tNN_*.sh` goldens and runs only the
lanes named in `RUN_LANE_ALLOWLIST` (`t01` AV, `t02` dependency freshness, `t03` static security, `t04` requirements
traceability, `t05` shell unit). The heavier DB/UI/DAST lanes are intentionally not part of the self-run. There are no
`rtNN_*.sh` self-pointers anymore — the engine runs its goldens directly under `RUNBOOK_REPO_ROOT=runner`.

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
./05_deploy_database.sh          # teller pointer -> runner/06_deploy_database.sh
./06_run_all_tests_parallel.sh   # teller pointer -> runner/07_run_all_tests_parallel.sh
```

### matchy — checks

```bash
cd ../matchy
./02_create_venv.sh
activate
./03_load_requirements.sh
./04_run_all_tests_parallel.sh   # parallel CI batch (excludes setup + integration entrypoints)
```

### eggnest — cross-repo engine e2e

```bash
cd ..                            # eggnest workspace root
./01_create_venv.sh
activate
./02_load_requirements.sh
./03_run_e2e_tests.sh            # offline matching cases; --record drives a live AI recording
```

## Parallel orchestration

`07_run_all_tests_parallel.sh` discovers `tests/t*.sh` under the target repo, runs them in parallel, writes
per-script logs under the repo's artifacts directory, and emits completion-order PASS/FAIL lines plus quality
telemetry. `matchy/04_run_all_tests_parallel.sh` is the matchy-facing pointer into the same orchestrator.

## Test-lane catalog (`tests/tNN_*.sh`)

The runner holds only the lanes that are genuinely shared across repos, renumbered contiguous `t00`-`t10`:

| Lane | Focus |
|------|-------|
| `t00` | Code quality |
| `t01` | Antivirus (ClamAV) |
| `t02` | Dependency freshness |
| `t03` | Static security (SAST) |
| `t04` | Requirements traceability |
| `t05` | Shell unit tests (Bats) |
| `t06` | Python unit tests (pytest) |
| `t07` | Mutation tests (mutmut) |
| `t08` | Fuzz / property tests (Hypothesis) |
| `t09` | Dynamic security (DAST) |
| `t10` | FileVault encryption verification |

Repo-specific test lanes are not shared goldens; they live as self-contained lanes inside their owning repo:

- **teller**: DB-deploy verification, SQL/pgTAP unit, Teller API smoke, Teller live canary.
- **classy**: Swift unit, macOS UI regression, macOS crash verification, classification persistence.

Not every repo enables every shared lane; the profile and the repo's `tests/` pointers select which lanes run.
Each consuming repo numbers its own `tests/tNN_*.sh` contiguously (teller/classy `t00`-`t14`, matchy/mailcart `t00`-`t10`).

## Pointers are hand-authored

The thin `NN_*.sh` operator pointers and `tests/tNN_*.sh` test pointers in each consuming repo are hand-authored source,
not generated. Each repo renumbers and selects its own lane subset (e.g. classy's `04_install_classifier_api_tls.sh`,
teller's renumbered `05_deploy_database.sh`), so there is no uniform scheme to generate. When you add or rename a
golden, update the affected repo's pointer by hand: set `RUNBOOK_REPO_ROOT`, source the repo profile, and `exec`
the golden (see [`Architecture.md`](Architecture.md#thin-pointer-pattern) for the template).

## Requirements traceability

`tests/py/traceability/` (`cli.py`, `discovery.py`, `parsing.py`, `verification.py`) maps
`requirements/**/*-requirements.md` to source files and `#R###`-tagged tests. The `t04` lane runs it to
keep requirements, code, and tests in sync.

## Constraints

- No Docker (workspace rule).
- No direct `pip install` in consuming repos — use the numbered load-requirements script.
- No `rm` — destructive cleanup moves to `~/.Trash` with timestamps.
- `umask 007`; files `660`, directories `770`, executables/symlinks `550`.
