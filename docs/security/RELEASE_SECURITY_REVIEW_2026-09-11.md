# Night Light Release Security Review — 2026-09-11

## Executive summary

No reportable critical, high, or medium vulnerability was found by the available local release-security gate. The synchronized `release/0.2.0-source-sync` source passed full-history secret scanning, dependency advisory auditing, production Python static analysis, targeted frontend/WebView2 review, and the complete automated test suite.

This is not a completed Codex Security Deep Scan. That managed scan could not start because the parent task exposes an unrestricted filesystem instead of the read-only managed filesystem profile required by its worker. This limitation must remain visible in release claims.

## Scope

- Python application, smart scheduling, display control, IPC, build and release code
- Vanilla JavaScript/CSS/HTML premium interface
- WebView2 native host bridge
- NSIS installer, upgrade and owned-removal scripts
- Dependency lock and bundled third-party notices
- Git history and prospective release commits

Generated environments and historical audit sandboxes were excluded from first-party static analysis. Their packages were assessed through the project dependency audit and recorded third-party provenance instead.

## Evidence

| Control | Result |
| --- | --- |
| `gitleaks git --no-banner --redact --exit-code 1 .` | Passed; 15 commits and approximately 1.80 MB scanned, no leaks found |
| `pip-audit . --strict --progress-spinner off` | Passed; no known vulnerabilities found |
| Bandit 1.9.4 over tracked, non-test Python files with medium/high severity and medium/high confidence thresholds | Passed; 5,986 lines scanned, no issues identified |
| Frontend dangerous-sink search | No `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, script-bearing URL, or browser credential storage path found |
| `python -m pytest -q` under the frozen `uv` environment | Passed at 100% |
| `git diff --check` | Passed |

## Validated controls

- `build_premium.py` downloads a version-pinned WebView2 SDK package from a fixed HTTPS NuGet host and rejects bytes that do not match the pinned SHA-256.
- `premium_host.cs` maps a fixed virtual host with CORS denied; blocks unexpected navigation, new windows, permissions and downloads; accepts web messages only from its fixed local origin; and caps message length.
- `premium_ui.py` validates action names, allowed fields, protocol version, session identity and request identity before dispatch. Save requests are replay-bound to their original payload.
- Browser local storage in `docs/design/appearance.js` contains appearance preferences only. It does not store credentials, tokens, personal location, or authentication state.
- Loopback IPC authentication and private configuration behavior remain covered by the automated release tests.

## Scanner triage

Initial recursive Bandit output included third-party virtual environments and historical audit runtimes. Those are not first-party source and were removed from the production-code scan scope. Two test-only `exec` calls compile locally parsed functions for isolated regression tests; they do not process external input. The fixed NuGet download was reviewed and annotated with its immediate SHA-256 enforcement.

## Findings

No reportable critical, high, or medium first-party finding was identified by this local gate.

## Remaining release limitations

- Codex Security Deep Scan: not run; managed filesystem permission was unavailable.
- Code signing: the installer remains unsigned Early Access unless a trusted signing certificate is added later.
- A clean-machine physical Windows install and uninstall pass provides stronger hardware/runtime evidence than repository automation alone.
- This review is point-in-time evidence for the reviewed source. Any later code or dependency change requires the relevant gates to be rerun.
