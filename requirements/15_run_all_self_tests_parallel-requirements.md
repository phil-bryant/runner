# 15 run all self tests parallel Requirements

## Scope

Requirements-only mode: true

Applies to `15_run_all_self_tests_parallel.sh`. This is a runner self-run pointer entrypoint owned by the runner engine and exercised by runner itself, delegating execution to the shared golden parallel orchestrator where behavioral source/test traceability is enforced. Runner records it here as a self-run inventory entry so the numbered-script coverage and scope-alignment checks remain satisfied without duplicating downstream enforcement.
