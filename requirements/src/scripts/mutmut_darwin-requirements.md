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

R035  Statement: Prepare mutation task inputs from stats and per-mutant test selection.
Design: Build execution metadata by loading stats, collecting rerunnable mutant keys, and selecting ordered covering tests for each mutant.
Tests:
- R035-T01: Verify task collection and per-mutant test selection produce deterministic runnable task sets.

R040  Statement: Generate mutants serially without forked multiprocessing.
Design: Replace pool-based generation with serial in-process mutant creation to avoid Darwin fork instability during prepare phase.
Tests:
- R040-T01: Verify serial mutant generation updates mutation stats without requiring multiprocessing pools.

R045  Statement: Compose deterministic subprocess environment for mutant execution.
Design: Build stable subprocess env/path variables, purge pycache, and parse worker/env knobs that control subprocess execution behavior.
Tests:
- R045-T01: Verify subprocess env composition (`PYTHONPATH`, venv PATH, bytecode/cache controls) and pycache cleanup behavior.

R050  Statement: Apply trial/rerun/status policy for mutation verdicts.
Design: Run mutant trials, rerun based on configured policy/escalation, map exit codes to statuses, and persist execution outcomes.
Tests:
- R050-T01: Verify exit-code status mapping and rerun/escalation behavior for executed mutants.

R055  Statement: Route CLI commands with Darwin-safe stub bootstrap.
Design: Dispatch `prepare` vs `execute` command paths through `main` and guarantee the deterministic `setproctitle` stub is available during startup.
Tests:
- R055-T01: Verify CLI routing behavior and Darwin stub import/install path are both exercised.
