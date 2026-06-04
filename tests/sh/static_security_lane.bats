#!/usr/bin/env bats
# Static unit tests for src/scripts/security/run_static_security_lane.sh security baseline behavior.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  STATIC_LANE="${REPO_ROOT}/src/scripts/security/run_static_security_lane.sh"
}

@test "static security lane script remains shell-parseable" {
  #R120-T01
  run bash -n "$STATIC_LANE"
  [ "$status" -eq 0 ]
}

@test "static security lane defines secure pip baseline defaults" {
  #R120-T02
  run python3 - <<'PY' "$STATIC_LANE"
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

expected = {
    "PIP_AUDIT_MIN_SECURE_PIP_VERSION": "26.1",
    "BOOTSTRAP_PIP_VERSION": "26.1.2",
}
for key, value in expected.items():
    pattern = rf'{key}="\$\{{{key}:-{re.escape(value)}\}}"'
    if re.search(pattern, text) is None:
        raise SystemExit(f"missing secure default for {key}")

sha_line = (
    'BOOTSTRAP_PIP_SHA256="${BOOTSTRAP_PIP_SHA256:-'
    "382ff9f685ee3bc25864f820aa50505825f10f5458ffff07e30a6d96e5715cab}"
    '"'
)
if sha_line not in text:
    raise SystemExit("missing BOOTSTRAP_PIP_SHA256 secure default")
PY
  [ "$status" -eq 0 ]
}

@test "static security lane enforces secure pip baseline before pip-audit" {
  #R120-T03
  run python3 - <<'PY' "$STATIC_LANE"
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

required_snippets = [
    'if ! pip_version_gte "$BOOTSTRAP_PIP_VERSION" "$PIP_AUDIT_MIN_SECURE_PIP_VERSION"; then',
    'pip==${BOOTSTRAP_PIP_VERSION} --hash=sha256:${BOOTSTRAP_PIP_SHA256}',
    '"$target_python" -m pip install --upgrade --require-hashes --only-binary=:all: -r "$bootstrap_requirements_file"',
]
for snippet in required_snippets:
    if snippet not in text:
        raise SystemExit(f"missing secure enforcement snippet: {snippet}")

invoke_index = text.find("configure_pip_audit_python\nenforce_pip_audit_secure_baseline")
pip_audit_index = text.find('pip-audit --format json --output "${REPORT_DIR}/pip-audit.json"')
if invoke_index == -1:
    raise SystemExit("missing secure-baseline invocation after configure_pip_audit_python")
if pip_audit_index == -1:
    raise SystemExit("missing pip-audit execution command")
if invoke_index > pip_audit_index:
    raise SystemExit("secure-baseline enforcement occurs after pip-audit")
PY
  [ "$status" -eq 0 ]
}
