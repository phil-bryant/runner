# mutmut Darwin Driver Requirements

## Scope

Applies to `src/scripts/mutmut_darwin.py` and `src/scripts/mutmut_darwin_stub.py`.

R001  Statement: Provide a macOS-safe mutmut flow that avoids in-process fork crashes.
Design: Split operation into `prepare` and `execute` phases, generating mutants/stats first and then running mutant test subsets through subprocess `pytest`.
Tests:
- R001-T01: Verify command routing and execute-path behavior for prepared and unprepared mutant states.

R005  Statement: Preserve deterministic mutant execution environment.
Design: Configure `PYTHONPATH`, virtualenv PATH, bytecode suppression, and cache paths while mapping exit codes to kill/survive outcomes and persisting per-mutant metadata updates.
Tests:
- R005-T01: Verify subprocess pytest invocation arguments/environment and per-mutant metadata updates.

R010  Statement: Stub `setproctitle` before mutmut import side effects on Darwin.
Design: Register `setproctitle` stub module via `mutmut_darwin_stub.py` so mutmut startup remains stable on macOS runtimes affected by the fork crash path.
Tests:
- R010-T01: Verify the stub module installs a callable `setproctitle` symbol and can be imported before mutmut bootstrap.

R030  Statement: Resolve mutmut configuration and mutation path predicates across API variants.
Design: Resolve repo root, load mutmut config via legacy/modern interfaces, and evaluate whether each source path is eligible for mutation.
Tests:
- R030-T01: Verify config-loading fallback behavior and mutation-path predicate handling across compatibility shims.
- R030-T02: Verify config loader accepts legacy dict-based configuration payloads.
- R030-T03: Verify config loader raises explicit runtime errors for unsupported modern Config APIs.
- R030-T04: Verify mutation-path predicate defaults to mutate-true when Config import is unavailable.

R035  Statement: Prepare mutation task inputs from stats and per-mutant test selection.
Design: Build execution metadata by loading stats, collecting rerunnable mutant keys, and selecting ordered covering tests for each mutant.
Tests:
- R035-T01: Verify task collection and per-mutant test selection produce deterministic runnable task sets.

R040  Statement: Generate mutants serially without forked multiprocessing.
Design: Replace pool-based generation with serial in-process mutant creation to avoid Darwin fork instability during prepare phase.
Tests:
- R040-T01: Verify serial mutant generation updates mutation stats without requiring multiprocessing pools.
- R040-T02: Verify serial generation emits warnings and raises underlying mutation errors.

R045  Statement: Compose deterministic subprocess environment for mutant execution.
Design: Build stable subprocess env/path variables, purge pycache, and parse worker/env knobs that control subprocess execution behavior.
Tests:
- R045-T01: Verify subprocess env composition (`PYTHONPATH`, venv PATH, bytecode/cache controls) and pycache cleanup behavior.
- R045-T02: Verify tests-dir fallback discovery includes `tests/` and `tests/py/` layouts deterministically.
- R045-T03: Verify pycache purge relocates `__pycache__` directories to trash-safe paths.

R050  Statement: Apply trial/rerun/status policy for mutation verdicts.
Design: Run mutant trials, rerun based on configured policy/escalation, map exit codes to statuses, and persist execution outcomes.
Tests:
- R050-T01: Verify exit-code status mapping and rerun/escalation behavior for executed mutants.
- R050-T02: Verify trial helper records timeout and retry metadata for transient execution outcomes.
- R050-T03: Verify rerun policy helper enforces attempt limits and escalation controls.
- R050-T04: Verify execute path returns non-zero when stats are missing or no runnable tasks remain.
- R050-T05: Verify execute path updates mutant metadata and succeeds for serial/parallel workers.

R055  Statement: Route CLI commands with Darwin-safe stub bootstrap.
Design: Dispatch `prepare` vs `execute` command paths through `main` and guarantee the deterministic `setproctitle` stub is available during startup.
Tests:
- R055-T01: Verify CLI routing behavior and Darwin stub import/install path are both exercised.
