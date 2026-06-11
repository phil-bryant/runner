#!/usr/bin/env bash
# Reusable prereq hook: eggnest landing web toolchain (npm dependencies and the
# Playwright Chromium browser for the landing unit/api and browser-smoke lanes).
# Sourced by the generic 01 install golden when PREREQ_EXTRA_HOOK points here.
# Relies on rb_ensure_brew_formula from runbook_common; node/npm itself is
# installed via the profile's BREW_FORMULAS.

ensure_landing_node_modules() {
    #R010: Ensure landing npm dependencies are installed via npm ci when missing.
    local landing_dir="${RUNBOOK_REPO_ROOT}/landing"
    echo "[landing npm] Checking..."
    if ! command -v npm >/dev/null 2>&1; then
        echo "❌ [landing npm] npm is required but not available on PATH"
        exit 1
    fi
    if [ ! -f "${landing_dir}/package.json" ]; then
        echo "❌ [landing npm] No package.json at ${landing_dir}"
        exit 1
    fi
    if [ -d "${landing_dir}/node_modules" ]; then
        echo "✅ [landing npm] node_modules present at ${landing_dir}/node_modules"
        return
    fi
    echo "[landing npm] Installing dependencies with npm ci..."
    (cd "$landing_dir" && npm ci)
    echo "✅ [landing npm] Dependencies installed"
}

ensure_playwright_chromium() {
    #R020: Ensure the Playwright Chromium browser is installed for the smoke lane.
    local landing_dir="${RUNBOOK_REPO_ROOT}/landing"
    echo "[playwright] Checking..."
    if (cd "$landing_dir" && npx --no-install playwright install --dry-run chromium 2>/dev/null | grep -q "is already installed"); then
        echo "✅ [playwright] Chromium browser already installed"
        return
    fi
    echo "[playwright] Installing Chromium browser..."
    (cd "$landing_dir" && npx --no-install playwright install chromium)
    echo "✅ [playwright] Chromium browser installed"
}

#R001: Ensure node/npm, landing npm dependencies, and the Playwright browser.
echo ""
rb_ensure_brew_formula "node" "npm"
ensure_landing_node_modules
ensure_playwright_chromium
