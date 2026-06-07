# runner

Runner is the shared runbook engine for the eggnest workspace. It holds the canonical ("golden") numbered bash
scripts, parallel test lanes, security tooling, database DDL, and per-repo profile configuration that the
sibling repos (`teller`, `classy`, `matchy`, `mailcart`) and the eggnest workspace root all delegate into.

For the design (dual-root model, layering, data flow) see [`Architecture.md`](Architecture.md).

## Pre-release CI/CD Policy

CI is **implemented but intentionally disabled for automatic runs** until the `v1.0` customer release. A GitHub
Actions workflow exists at `.github/workflows/ci.yml`, but it is **manual-dispatch-only**
(`on: workflow_dispatch`) — it does **not** trigger on `push`, `pull_request`, or `schedule`. Pre-release, the
enforcement mechanism is the local numbered lanes (`tests/tNN_*.sh` + `./11_run_all_self_tests_parallel.sh`),
not GitHub-hosted CI: this is a solo project and red X's on every push are noise rather than signal. The
workflow runs the engine's Linux-portable self-run subset against `runner` itself (requirements traceability
`t04` + shell unit `t05` (shellcheck + Bats over the shared goldens) + Python unit `t06`); the AV (`t01`),
dependency-freshness (`t02`), SAST (`t03`), mutation (`t07`), fuzz (`t08`), DAST (`t09`), and FileVault (`t10`)
lanes stay local. It is kept correct and manually runnable so it can be wired to `push`/`pull_request` as the
project approaches `v1.0`. This matches the workspace-wide policy in
[`teller`'s README](../teller/README.md#pre-release-cicd-policy).

## Why this design holds together

One engine, many repos. Runner keeps a single set of golden `NN_*.sh` lifecycle scripts and shared
`tests/tNN_*.sh` lanes; the sibling repos own no copy of that logic. Each consuming repo ships only thin shims
that delegate through a shared helper — resolve `RUNNER_HOME`, export their own `RUNBOOK_REPO_ROOT`, source the
matching `config/runbook/<repo>.env` profile, and exec the mapped golden. The behavior lives in one place; the
repos just point at it. That shape buys a few things that are genuinely pleasant to live with:

- **Single source of truth, no forked shell.** There is exactly one golden engine. A pointer is a delegation
  contract, not a copy of the logic, so a behavior fix lands once instead of in five repos.
- **Profile-driven customization.** Per-repo differences (prereq mode, venv policy, pip bootstrap, orchestrator
  mode, DAST target, lane selection) are declared in a small `.env`, never by editing the shell. teller runs the
  full Postgres/ZAP stack, matchy stays Python/SAST-only, classy verifies prereqs and builds SQLCipher — same
  goldens, different knobs.
- **Contiguous, selectable lanes.** Shared lanes are numbered contiguously `t00`–`t10`. Each repo opts into the
  subset it needs via `RUN_LANE_ALLOWLIST` in its profile, and `--no-ui` / `--no-mutation` / `--no-av` skip the
  optional lanes on an ad-hoc run. Predictable numbering, no gaps to reason about.
- **Upgrades propagate immediately.** Harden or fix a golden once and every repo that delegates into it picks up
  the change on its next run — no fan-out edits, no version skew, minimal cross-repo drift.
- **Secure by default.** `umask 007` and `set -euo pipefail` in every golden; no `rm` (destructive cleanup moves
  to `~/.Trash`); secrets referenced by 1psa item *name*, never stored in profiles; a hash-pinned `pip` bootstrap
  before installs; and a single-run orchestrator lock scoped per `RUNBOOK_REPO_ROOT`, so a run against one repo
  never blocks a run against another.

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

Pointer-contract assets are centralized in runner and loaded via profile roots:

- `TRACEABILITY_REQUIREMENTS_ROOTS` -> includes `runner/shared/requirements/pointers/<repo>`
- `TRACEABILITY_TEST_ROOTS` / `SHELL_BATS_ROOTS` -> include `runner/shared/tests/sh/pointers/<repo>`

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
per-script logs under the repo's artifacts directory, and emits completion-order PASS/FAIL lines.
`matchy/04_run_all_tests_parallel.sh` is the matchy-facing pointer into the same orchestrator.

## Autodiscovery

The parallel orchestrator is discovery-first: it scans the target repo for executable `tests/tNN_*.sh` lanes,
then applies profile/flag filters (for example `RUN_LANE_ALLOWLIST` and `--no-*` skips) before launching the
selected lanes concurrently. You do not maintain a hardcoded lane list in runner.

## Autodiscovering All Autodiscovering Test Runners

`../run_all_test_runners.sh` is the workspace-level thin pointer that selects the `eggnest-runners` profile and
delegates into `07_run_all_tests_parallel.sh` in runners-discovery mode. In practical terms, it discovers each
repo's executable `NN_run_all_*tests_parallel.sh` entrypoint and runs those repo-level runners in parallel so
you can kick off the full workspace test-runner surface with one command.

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
`requirements/**/*-requirements.md` (plus any roots in `TRACEABILITY_REQUIREMENTS_ROOTS`) to source files and
`#R###`-tagged tests. Shared wrapper requirements and their companion bats tests now live under:

- `shared/requirements/pointers/<repo>/*.md`
- `shared/tests/sh/pointers/<repo>/*.bats`

The `t04` lane runs this mapping so requirements, code, and tests stay in sync without per-repo wrapper copies.

## Testing of Testing

A test runner that nobody tests is just unverified infrastructure. Runner takes the less common step of testing
the thing that runs the tests — we don't only run lanes, we prove the lane engine and its delegation contracts
are sound.

- **The engine runs green against itself (dogfooding).** `11_run_all_self_tests_parallel.sh` sets
  `RUNBOOK_REPO_ROOT` to runner, sources `config/runbook/runner.env`, and execs the golden
  `07_run_all_tests_parallel.sh` over runner's own `tests/tNN_*.sh`. It runs only the lanes that make sense for
  the engine itself — the `RUN_LANE_ALLOWLIST` subset `t01` (AV), `t02` (dependency freshness), `t03` (static
  security / SAST), `t04` (requirements traceability), and `t05` (shell unit) — so the orchestrator we ship to
  every sibling repo has to pass its own gates first.
- **Pointer→golden contract tests.** Each sibling pointer is pinned by a Bats contract under
  `shared/tests/sh/pointers/<repo>/*.bats` that asserts the pointer sets `RUNBOOK_REPO_ROOT`, sources its
  profile, and `exec`s the *correct* mapped golden. Renumbering or re-mapping a pointer can't silently desync
  from its golden — the contract fails the lane loudly instead.
- **Traceability of the test surface.** The `t04` requirements-traceability lane maps `#R###`-tagged tests back
  to requirements (including the shared pointer roots), so a lane or pointer that loses its requirement linkage
  shows up as a traceability failure, not a silent gap.
- **Bats coverage of the goldens and lanes.** The shared shell-unit lane (`t05`, via `SHELL_BATS_ROOTS`) runs
  Bats over the goldens and lane wrappers themselves, alongside the pointer contracts above.

The angle is simple: before the engine gates a sibling repo, it has already gated itself, and every delegation
edge into a golden is held to a contract.

## Traceability of Traceability

The requirements-traceability engine used to be the one blind spot — the tool that demands a requirements doc and
tagged tests for every other file was itself excluded from the scan it runs. That exclusion is gone. The engine
now holds itself to the exact standard it enforces on everything else: it traces *itself*.

- **The engine's own source is a first-class traced surface.** The lane wrapper
  (`tests/t04_run_requirements_traceability_tests.sh`) and the Python engine modules
  (`tests/py/traceability/{cli,discovery,parsing,verification}.py`) each have a companion requirements doc —
  `requirements/tests/t04_run_requirements_traceability_tests-requirements.md` and
  `requirements/tests/py/traceability/{cli,discovery,parsing,verification}-requirements.md` — carry scoped
  `#Rnnn:` requirement tags in the source, and are exercised by tagged tests
  (`tests/py/test_{cli,discovery,parsing,verification}.py` and
  `tests/sh/t04_run_requirements_traceability_tests.bats`) bearing `#Rnnn-Tnn:` test tags. The engine is now
  *included* in coverage rather than carved out of it.
- **Mandatory tag text, unconditional and non-disablable.** Every `#Rnnn` source tag and every `#Rnnn-Tnn` test
  tag must carry its scoped requirement text (`#Rnnn: <text>`); a bare tag fails the lane. This check is
  deliberately *not* gated behind any environment knob — there is no opt-out flag to quietly lower the bar in a
  future change. Text is the point: a tag with no statement is traceability theater, and the engine refuses it.
- **Full-coverage enforcement on by default.** The repository-source coverage check is on, so a software file
  that ships without a requirements doc is a hard failure — and that rule now binds the engine's own modules just
  like any other source. New engine code can't land untraced.
- **The requirements-only loophole is closed.** "Requirements-only mode" is legitimate only for docs with no
  mappable first-party source in the repo (e.g. thin cross-repo pointer docs). If real in-repo source exists, the
  doc fails closed and must be fully traced to source and tests — so no one can hide working code behind a
  requirements-only flag to dodge enforcement.

The meta-point is the whole point: a traceability engine that exempts itself is asking for trust it hasn't
earned. This one earns it by passing its own gate — same scoped tags, same mandatory text, same coverage rule,
no exemptions.

## Constraints

- No Docker (workspace rule).
- No direct `pip install` in consuming repos — use the numbered load-requirements script.
- No `rm` — destructive cleanup moves to `~/.Trash` with timestamps.
- `umask 007`; files `660`, directories `770`, executables/symlinks `550`.
