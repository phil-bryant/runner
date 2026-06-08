#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: Path, default):
    #R001: Load scanner report JSON artifacts from the configured report directory.
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def count_pip_audit(payload) -> int:
    #R005: Normalize pip-audit payload variants into vulnerability counts.
    if isinstance(payload, list):
        return sum(len(item.get("vulns", [])) for item in payload if isinstance(item, dict))
    if isinstance(payload, dict) and isinstance(payload.get("dependencies"), list):
        return sum(len(dep.get("vulns", [])) for dep in payload["dependencies"] if isinstance(dep, dict))
    if isinstance(payload, dict):
        vulns = payload.get("vulns", [])
        return len(vulns) if isinstance(vulns, list) else 0
    return 0


#R010: Parse and validate SAST summary CLI arguments.
def _parse_args(argv: list[str]) -> tuple[Path, bool, str]:
    if len(argv) != 4:
        raise SystemExit(
            "usage: sast_summary_gate.py <report_dir> <fail_gate_bool> <policy_mode: medium|high>"
        )
    report_dir = Path(argv[1])
    fail_gate = argv[2].lower() == "true"
    policy_mode = argv[3].strip().lower()
    return report_dir, fail_gate, policy_mode


#R010: Load all scanner payloads from the configured report directory.
def _load_payloads(report_dir: Path) -> dict[str, object]:
    return {
        "semgrep": load_json(report_dir / "semgrep.json", {}),
        "bandit": load_json(report_dir / "bandit.json", {}),
        "pip_audit": load_json(report_dir / "pip-audit.json", []),
        "detect_secrets": load_json(report_dir / "detect-secrets.json", {}),
        "swiftlint": load_json(report_dir / "swiftlint.json", []),
        "shellcheck": load_json(report_dir / "shellcheck.json", []),
        "gitleaks": load_json(report_dir / "gitleaks.json", []),
        "ruff": load_json(report_dir / "ruff.json", []),
    }


#R010: Normalize scanner payload structures into list/dict shapes for counting.
def _normalize_payloads(payloads: dict[str, object]) -> dict[str, object]:
    semgrep_payload = payloads["semgrep"]
    bandit_payload = payloads["bandit"]
    detect_secrets_payload = payloads["detect_secrets"]
    return {
        "semgrep_results": semgrep_payload.get("results", []) if isinstance(semgrep_payload, dict) else [],
        "bandit_results": bandit_payload.get("results", []) if isinstance(bandit_payload, dict) else [],
        "secret_results": detect_secrets_payload.get("results", {}) if isinstance(detect_secrets_payload, dict) else {},
        "swiftlint_results": payloads["swiftlint"] if isinstance(payloads["swiftlint"], list) else [],
        "shellcheck_results": payloads["shellcheck"] if isinstance(payloads["shellcheck"], list) else [],
        "ruff_results": payloads["ruff"] if isinstance(payloads["ruff"], list) else [],
    }


#R010: Count gitleaks findings across list and wrapped-report payload variants.
def _count_gitleaks(payload) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        return len(payload.get("findings", []))
    return 0


#R010: Compute all scanner severity totals needed for policy gate decisions.
def _build_totals(payloads: dict[str, object], normalized: dict[str, object]) -> dict[str, int]:
    semgrep_results = normalized["semgrep_results"]
    bandit_results = normalized["bandit_results"]
    secret_results = normalized["secret_results"]
    swiftlint_results = normalized["swiftlint_results"]
    shellcheck_results = normalized["shellcheck_results"]
    ruff_results = normalized["ruff_results"]

    semgrep_high = sum(1 for item in semgrep_results if item.get("extra", {}).get("severity") == "ERROR")
    semgrep_medium = sum(
        1
        for item in semgrep_results
        if str(item.get("extra", {}).get("severity", "")).upper() in {"WARNING", "ERROR", "CRITICAL"}
    )
    bandit_high = sum(1 for item in bandit_results if item.get("issue_severity") == "HIGH")
    bandit_medium = sum(
        1 for item in bandit_results if str(item.get("issue_severity", "")).upper() in {"MEDIUM", "HIGH"}
    )
    secret_findings = sum(len(values) for values in secret_results.values() if isinstance(values, list))
    swiftlint_high = sum(1 for item in swiftlint_results if str(item.get("severity", "")).lower() == "error")
    swiftlint_medium = sum(
        1 for item in swiftlint_results if str(item.get("severity", "")).lower() in {"warning", "error"}
    )
    shellcheck_high = sum(1 for item in shellcheck_results if str(item.get("level", "")).lower() == "error")
    shellcheck_medium = sum(
        1 for item in shellcheck_results if str(item.get("level", "")).lower() in {"warning", "error"}
    )
    ruff_total = len(ruff_results)
    gitleaks_findings = _count_gitleaks(payloads["gitleaks"])
    dep_vulns = count_pip_audit(payloads["pip_audit"])

    high_total = semgrep_high + bandit_high + secret_findings + swiftlint_high + shellcheck_high + gitleaks_findings + ruff_total
    medium_total = (
        semgrep_medium
        + bandit_medium
        + dep_vulns
        + secret_findings
        + swiftlint_medium
        + shellcheck_medium
        + gitleaks_findings
        + ruff_total
    )
    return {
        "semgrep_high": semgrep_high,
        "semgrep_medium": semgrep_medium,
        "bandit_high": bandit_high,
        "bandit_medium": bandit_medium,
        "dep_vulns": dep_vulns,
        "secret_findings": secret_findings,
        "swiftlint_high": swiftlint_high,
        "swiftlint_medium": swiftlint_medium,
        "shellcheck_high": shellcheck_high,
        "shellcheck_medium": shellcheck_medium,
        "gitleaks_findings": gitleaks_findings,
        "ruff_total": ruff_total,
        "high_total": high_total,
        "medium_total": medium_total,
    }


#R010: Resolve policy metadata and gate counter from requested policy mode.
def _resolve_policy(policy_mode: str, totals: dict[str, int]) -> tuple[str, int]:
    if policy_mode == "high":
        return "high-critical", totals["high_total"]
    return "financial-app-medium-or-higher-blocking", totals["medium_total"]


#R010: Build the persisted SAST summary payload from normalized counts.
def _build_summary(
    normalized: dict[str, object],
    totals: dict[str, int],
    gate_policy: str,
    gate_failed: bool,
) -> dict[str, object]:
    semgrep_results = normalized["semgrep_results"]
    bandit_results = normalized["bandit_results"]
    shellcheck_results = normalized["shellcheck_results"]
    swiftlint_results = normalized["swiftlint_results"]
    return {
        "semgrep_total": len(semgrep_results),
        "semgrep_high_critical": totals["semgrep_high"],
        "semgrep_medium_or_higher": totals["semgrep_medium"],
        "bandit_total": len(bandit_results),
        "bandit_high_critical": totals["bandit_high"],
        "bandit_medium_or_higher": totals["bandit_medium"],
        "pip_audit_vulnerabilities": totals["dep_vulns"],
        "detect_secrets_findings": totals["secret_findings"],
        "ruff_total": totals["ruff_total"],
        "ruff_high_critical": totals["ruff_total"],
        "ruff_medium_or_higher": totals["ruff_total"],
        "shellcheck_total": len(shellcheck_results),
        "shellcheck_high_critical": totals["shellcheck_high"],
        "shellcheck_medium_or_higher": totals["shellcheck_medium"],
        "gitleaks_findings": totals["gitleaks_findings"],
        "swiftlint_total": len(swiftlint_results),
        "swiftlint_high_critical": totals["swiftlint_high"],
        "swiftlint_medium_or_higher": totals["swiftlint_medium"],
        "high_critical_total": totals["high_total"],
        "medium_or_higher_total": totals["medium_total"],
        "gate_policy": gate_policy,
        "gate_failed": gate_failed,
    }


#R010: Persist summary JSON and emit operator-facing status output.
def _write_and_print_summary(report_dir: Path, summary: dict[str, object]) -> None:
    summary_path = report_dir / "sast-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Static Application Security Testing (SAST) summary")
    print(json.dumps(summary, indent=2))


def main() -> int:
    #R010: Aggregate severities, write summary JSON, and enforce policy-mode gate.
    report_dir, fail_gate, policy_mode = _parse_args(sys.argv)
    payloads = _load_payloads(report_dir)
    normalized = _normalize_payloads(payloads)
    totals = _build_totals(payloads, normalized)
    gate_policy, gate_total = _resolve_policy(policy_mode, totals)
    gate_failed = fail_gate and gate_total > 0
    summary = _build_summary(normalized, totals, gate_policy, gate_failed)
    _write_and_print_summary(report_dir, summary)
    if gate_failed:
        if policy_mode == "high":
            print("❌ Static Application Security Testing (SAST) gate failed: High/Critical findings detected.")
        else:
            print("❌ Static Application Security Testing (SAST) gate failed: Medium-or-higher findings detected.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
