# Check Binary Integrity Requirements

## Scope

Applies to `src/scripts/check_binary_integrity.py`.

R001  Statement: Collect binary executable path/version/hash metadata from policy-defined command entries.
Design: Load policy JSON entries, resolve executable paths, run version probes, parse versions via regex, and compute SHA256 file digests.
Tests:
- R001-T01: Evaluate a policy with present and missing commands and verify report includes executable path, version, and hash fields (`tests/py/test_check_binary_integrity.py`).

R005  Statement: Emit machine-readable and human-readable binary integrity reports.
Design: Write JSON and text outputs with summary counters plus per-binary status rows.
Tests:
- R005-T01: Verify report generation counts missing required and stale-version statuses correctly (`tests/py/test_check_binary_integrity.py`).

R010  Statement: Enforce optional strict gates for missing required binaries, version policy failures, and hash mismatches.
Design: Return non-zero when `--fail-on-missing-required` detects missing required commands, when `--fail-on-version` detects stale/unknown constrained versions, or when `--fail-on-hash` detects checksum mismatches.
Tests:
- R010-T01: Verify `main()` returns failing exit status only when the corresponding strict gate is enabled and its condition is present (`tests/py/test_check_binary_integrity.py`).

R015  Statement: Maintain SHA256 allowlists for pinned binaries with a documented refresh workflow.
Design: Pin high-sensitivity local binaries in `config/security/binary-integrity-policy.json` (currently `1psa`, `cosign`, and `gitleaks`) and treat `--fail-on-hash` mismatches as blocking in strict lanes. For intentionally upgraded binaries, refresh digest pins by rerunning the integrity checker, copying observed digests into `allowed_sha256`, and rerunning t02 before merging. Homebrew-managed binaries may churn digests on upgrade, so pin selectively and only update hashes for deliberate upgrades.
Tests:
- R015-T01: Verify a digest in `allowed_sha256` produces an `ok` hash status and no hash mismatch count (`tests/py/test_check_binary_integrity.py`).

R030  Statement: Normalize hex digests into a canonical comparable representation.
Design: Strip surrounding whitespace and normalize digest case before allowlist/hash comparisons.
Tests:
- R030-T01: Verify `_normalize_hex_digest` canonicalizes case and whitespace for comparison-safe matching (`tests/py/test_check_binary_integrity.py`).

R035  Statement: Parse and validate binary policy manifest entries.
Design: Parse manifest JSON into typed policy objects, reject malformed entries, and require minimally valid command metadata.
Tests:
- R035-T01: Verify `load_policy` rejects malformed manifest entries and accepts typed valid entries (`tests/py/test_check_binary_integrity.py`).

R040  Statement: Resolve binaries, probe versions, and compare against minimum constraints.
Design: Resolve configured executables, run version probes, parse versions from probe output, and compare semantic ordering against policy minimums.
Tests:
- R040-T01: Verify probe parse/compare flow classifies older/newer/equal version relationships correctly (`tests/py/test_check_binary_integrity.py`).

R045  Statement: Compute file SHA256 digests for binary integrity verification.
Design: Stream file bytes and compute SHA256 digests for policy allowlist/hash enforcement decisions.
Tests:
- R045-T01: Verify `sha256_file` returns the known digest for a deterministic file payload (`tests/py/test_check_binary_integrity.py`).

R050  Statement: Summarize and render reports while enforcing CLI gate exits.
Design: Build summary/report artifacts, render text output, and return non-zero when configured gate flags detect violations.
Tests:
- R050-T01: Verify CLI gate mode returns non-zero and writes report artifacts when policy violations are present (`tests/py/test_check_binary_integrity.py`).
