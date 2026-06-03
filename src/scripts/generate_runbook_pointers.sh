#!/usr/bin/env bash
umask 007
set -euo pipefail

# Generates the thin pointer scripts in each repo. Each pointer sets
# RUNBOOK_REPO_ROOT, sources its repo profile, and execs the genericized runner golden.
# Idempotent: rewrites pointer files deterministically. Run from anywhere.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="$(cd "${SCRIPT_DIR}/../.." && pwd)"
EGGNEST_ROOT="$(cd "${RUNNER_HOME}/.." && pwd)"

emit_root_pointer() {
  local repo="$1" profile="$2" pointer="$3" golden_rel="$4"
  local out="${EGGNEST_ROOT}/${repo}/${pointer}"
  cat > "$out" <<EOF
#!/usr/bin/env bash
# Thin runbook pointer: sets RUNBOOK_REPO_ROOT + ${profile} profile, execs the runner golden.
umask 007
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="\$(cd "\${SCRIPT_DIR}/../runner" && pwd)"
export RUNBOOK_REPO_ROOT="\$SCRIPT_DIR"
# shellcheck source=/dev/null
source "\${RUNNER_HOME}/config/runbook/${profile}.env"
exec "\${RUNNER_HOME}/${golden_rel}" "\$@"
EOF
  chmod 770 "$out"
}

emit_eggnest_workspace_pointer() {
  local profile="$1" pointer="$2" golden_rel="$3"
  local out="${EGGNEST_ROOT}/${pointer}"
  cat > "$out" <<EOF
#!/usr/bin/env bash
# Eggnest workspace pointer: RUNBOOK_REPO_ROOT is the eggnest repo root; execs runner golden.
umask 007
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="\$(cd "\${SCRIPT_DIR}/runner" && pwd)"
export RUNBOOK_REPO_ROOT="\$SCRIPT_DIR"
# shellcheck source=/dev/null
source "\${RUNNER_HOME}/config/runbook/${profile}.env"
exec "\${RUNNER_HOME}/${golden_rel}" "\$@"
EOF
  chmod 770 "$out"
}

emit_test_pointer() {
  local repo="$1" profile="$2" pointer="$3" golden_rel="$4"
  local out="${EGGNEST_ROOT}/${repo}/tests/${pointer}"
  cat > "$out" <<EOF
#!/usr/bin/env bash
# Thin test pointer: sets RUNBOOK_REPO_ROOT + ${profile} profile, execs the runner test golden.
umask 007
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="\$(cd "\${SCRIPT_DIR}/../../runner" && pwd)"
RUNBOOK_REPO_ROOT="\$(cd "\${SCRIPT_DIR}/.." && pwd)"
export RUNBOOK_REPO_ROOT
# shellcheck source=/dev/null
source "\${RUNNER_HOME}/config/runbook/${profile}.env"
exec "\${RUNNER_HOME}/tests/${golden_rel}" "\$@"
EOF
  chmod 770 "$out"
}

# --- teller (full pipeline) ---
emit_root_pointer teller teller r01_install_prerequisites.sh 01_install_prerequisites.sh
emit_root_pointer teller teller r02_create_venv.sh 02_create_venv.sh
emit_root_pointer teller teller r03_prepare_supply_chain_integrity.sh 03_prepare_supply_chain_integrity.sh
emit_root_pointer teller teller r04_load_requirements.sh src/scripts/load_requirements_generic.sh
emit_root_pointer teller teller r06_deploy_database.sh 06_deploy_database.sh
emit_root_pointer teller teller r11_run_all_tests_parallel.sh 11_run_all_tests_parallel.sh
emit_root_pointer teller teller r12_report_quality_trends.sh 12_report_quality_trends.sh
emit_root_pointer teller teller r13_validate_quality_target.sh 13_validate_quality_target.sh
emit_root_pointer teller teller r14_prune_quality_telemetry.sh 14_prune_quality_telemetry.sh
emit_root_pointer teller teller r97_backup_database.sh 97_backup_database.sh
emit_root_pointer teller teller r98_destroy_database.sh 98_destroy_database.sh
emit_root_pointer teller teller r99_restore_database.sh 99_restore_database.sh
for t in t00_run_code_quality_tests t01_run_av_test t02_run_dependency_freshness_tests \
  t03_run_static_security_tests t04_run_requirements_traceability_tests \
  t05_deploy_database_verification_test t06_run_sql_unit_tests t07_run_shell_unit_tests \
  t08_run_python_unit_tests t09_run_mutation_tests t11_run_fuzz_tests \
  t12_run_dynamic_security_tests t13_run_teller_api_smoke_tests \
  t17_run_teller_live_canary_test t18_verify_filevault_encryption_test; do
  emit_test_pointer teller teller "${t}.sh" "${t}.sh"
done

# --- classy ---
# classy pointers are hand-curated with a renumbered NN_ scheme (e.g. 03_load_requirements,
# 07_run_classification_macos_ui, 08_run_all_tests_parallel) and tests/tNN_*.sh; not generated here.

# --- matchy ---
# matchy pointers are hand-curated (setup 01/02/03 + 04_run_all_checks_parallel orchestrator +
# tests/tNN_*.sh on the shared runner/tests goldens); not generated here.

# --- mailcart (Swift app + Outlook Graph; numbered NN_ pointers, no r prefix) ---
emit_root_pointer mailcart mailcart 00_verify_requirements_traceability.sh 00_verify_requirements_traceability.sh
emit_root_pointer mailcart mailcart 01_install_prerequisites.sh 01_install_prerequisites.sh
emit_root_pointer mailcart mailcart 02_create_venv.sh 02_create_venv.sh
emit_root_pointer mailcart mailcart 03_load_requirements.sh src/scripts/load_requirements_generic.sh
emit_root_pointer mailcart mailcart 04_run_dependency_freshness_checks.sh 04_run_dependency_freshness_checks.sh
emit_root_pointer mailcart mailcart 05_install_matchy_api_tls.sh 05_install_matchy_api_tls.sh
emit_root_pointer mailcart mailcart 11_run_all_tests_parallel.sh 11_run_all_tests_parallel.sh
for t in t00_run_code_quality_tests t01_run_av_test t02_run_dependency_freshness_tests \
  t03_run_static_security_tests t04_run_requirements_traceability_tests \
  t07_run_shell_unit_tests t08_run_python_unit_tests \
  t18_verify_filevault_encryption_test; do
  emit_test_pointer mailcart mailcart "${t}.sh" "${t}.sh"
done

# --- eggnest workspace (cross-repo engine-level matching e2e; pointers at repo root) ---
emit_eggnest_workspace_pointer eggnest r02_create_venv.sh 02_create_venv.sh
emit_eggnest_workspace_pointer eggnest r03_load_requirements.sh src/scripts/load_requirements_generic.sh
emit_eggnest_workspace_pointer eggnest r05_run_e2e_tests.sh 05_run_e2e_tests.sh

# --- runner (self-run: the engine runs its own applicable lanes against itself via rtNN_ pointers) ---
emit_runner_self_orchestrator() {
  local out="${RUNNER_HOME}/run_self_checks.sh"
  cat > "$out" <<'EOF'
#!/usr/bin/env bash
# Runner self-run pointer: runs runner's own applicable lanes (tests/rtNN_) against runner itself.
umask 007
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RUNBOOK_REPO_ROOT="$SCRIPT_DIR"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/config/runbook/runner.env"
exec "${SCRIPT_DIR}/11_run_all_tests_parallel.sh" "$@"
EOF
  chmod 770 "$out"
}

emit_runner_self_test_pointer() {
  local golden="$1"
  local out="${RUNNER_HOME}/tests/r${golden}"
  cat > "$out" <<EOF
#!/usr/bin/env bash
# Runner self test pointer: runs the ${golden%.sh} golden lane against runner itself.
umask 007
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="\$(cd "\${SCRIPT_DIR}/.." && pwd)"
export RUNBOOK_REPO_ROOT="\$RUNNER_HOME"
# shellcheck source=/dev/null
source "\${RUNNER_HOME}/config/runbook/runner.env"
exec "\${RUNNER_HOME}/tests/${golden}" "\$@"
EOF
  chmod 770 "$out"
}

emit_runner_self_orchestrator
for t in t01_run_av_test t02_run_dependency_freshness_tests t03_run_static_security_tests \
  t04_run_requirements_traceability_tests t07_run_shell_unit_tests; do
  emit_runner_self_test_pointer "${t}.sh"
done

echo "✅ Generated runbook pointers under: ${EGGNEST_ROOT}/{teller,classy,matchy,mailcart,runner} and eggnest workspace root"
