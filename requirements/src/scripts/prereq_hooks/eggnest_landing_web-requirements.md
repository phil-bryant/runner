# Eggnest Landing Web Prereq Hook Requirements

## Scope

Applies to `src/scripts/prereq_hooks/eggnest_landing_web.sh`.

R001  Statement: Ensure the eggnest landing web toolchain (node/npm, npm dependencies, Playwright Chromium).
Design: When sourced by the generic install golden, ensure node/npm via the shared Homebrew helper, then install landing npm dependencies and the Playwright Chromium browser.
Tests:
- R001-T01: Source the hook with stubbed brew/npm helpers and verify it ensures node, npm dependencies, and the Playwright browser.

R010  Statement: Ensure landing npm dependencies are installed via `npm ci` when missing.
Design: `ensure_landing_node_modules` fails when npm or `landing/package.json` is missing, short-circuits when `landing/node_modules` exists, and otherwise runs `npm ci` inside the landing directory.
Tests:
- R010-T01: With node_modules present, verify `ensure_landing_node_modules` reports presence without installing.

R020  Statement: Ensure the Playwright Chromium browser is installed for the browser-smoke lane.
Design: `ensure_playwright_chromium` short-circuits when the browser is already installed and otherwise runs `npx --no-install playwright install chromium` inside the landing directory.
Tests:
- R020-T01: With an already-installed dry-run stub, verify `ensure_playwright_chromium` reports installed without reinstalling.
