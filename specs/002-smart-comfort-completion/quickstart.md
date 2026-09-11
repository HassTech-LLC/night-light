# Verification and completion runbook

Status: future execution gates. This file describes tests to run, not tests already passed. Any run record must say Passed, Failed, Blocked, Not run, or Explicitly deferred, with evidence and scope. Deferred work cannot satisfy a required stable-release gate.

## Safe starting conditions

Use canonical app source, preserve dirty work and select an exact candidate snapshot. First inspect `conftest.py` and build isolation, not the user's real config. Automated tests set `NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND=1` and a freshly created temporary `NIGHT_LIGHT_BY_HT_CONFIG_DIR`; never reuse `%APPDATA%/NightLightWidget`. No test invokes real startup, taskbar, registry or display integration without a separate authorized native procedure. Log secret locations, not values.

Existing baseline commands are `rtk uv run --frozen python -m pytest` and the existing side-effect-free `build.py`/`release.py` entry points. Verify their current CLI flags, runtime pin and isolation before execution; do not copy an old release command that excludes premium helpers or new modules. New named tests/scripts below are implementation targets, not callable tools today.

## G0 — Exact baseline and safety

Capture app source revision plus dirty-file inventory, installed version/hash paths, existing schema fixtures, native-helper inventory and current website worktree/deployment identity. Reconcile each old release blocker from RELEASE-HANDOFF.md against current source/evidence rather than assuming it remains open or fixed. Amend the constitution with rationale/migration before runtime implementation. Prove tests cannot touch live config, transform, registry or IPC endpoint.

Required receipt: `audit/smart-comfort/baseline.json`, private sensitive-path redaction and `docs/CURRENT_CAPABILITIES.md`. Stable release requires a clean exact source revision, not merely a recorded dirty snapshot.

## G1 — State, storage and recovery

Test all intent/availability/override combinations; repeated Off; stale generation, callback, request and config revision; duplicate/parallel commands; pending Save followed by Off; duplicate launch; owner crash; command-only display isolation.

Inject validation errors, disk full, permission failure, interrupted atomic write, truncated config, slow/late/missing/out-of-order reply, UI reconnect and owner restart. Save timeout must reconcile, not blindly overwrite. Off must request neutral despite persistence failure, report session-versus-durable status, leave an unclean recovery record and open neutral on next start. A failed neutral backend call cannot say `Normal colors restored`.

Prove explicit comfort preview works while persisted Off, comparison while Off is harmless, and a newer Off cancels every restoration token. Availability block always wins over Apply now/preview. Check native state interpretation against labelled Windows Settings ON/OFF evidence on every supported Windows build; do not adopt a registry marker from one host observation.

## G2 — Smart mathematical and timing invariants

Use injected clocks/fake backend. Check normal multi-hour trajectories, extremes and random valid endpoints for bounded position, velocity, acceleration, unquantized RGB increments, no overshoot, continuous replan and no repeated ease restart. Verify inverse-temperature normalization/round-trip bounds. Test 5/10/20 Hz and jitter/long gaps without changing the intended temporal trajectory.

Catch-up cases: tiny/large delta; enabled before/during/after ramp; moving desired trajectory; impossible deadline; morning after missing the night; 2-second handoff hysteresis; velocity reduction into normal ceilings; explicit Apply now versus automatic catch-up. Target is current schedule, not deepest night endpoint. ETA must match the constrained simulation to within displayed minute resolution for stationary feasible targets; otherwise show a range or omit precision.

Short nights: intersection of forward/reachable-neutral envelopes, independently feasible warmth/dim peaks, bisection convergence, zero feasible peak, no hidden later morning return. Expose achieved peak and any missed anchor truthfully.

Time cases: Dearborn Heights using America/Detroit semantics; UTC; America/New_York DST; Europe/London; Asia/Kolkata half-hour; Asia/Kathmandu quarter-hour; Australia/Lord_Howe half-hour DST; Pacific/Chatham quarter-hour/DST; Pacific/Kiritimati and Pacific/Pago_Pago date-line extremes; southern-hemisphere seasons; polar no-sunset/no-sunrise; non-DST zones. Enumerate all packaged zones for valid dated scheduling across a defined one-year window; explicit edge cases still required. Do not confuse zone coverage with global postal-provider coverage.

Personal timing: midnight crossing, gap shift, first fold occurrence, exactly-once event IDs, equal-times rejection, clock forward/back, travel, manual coordinates update. Solar times require published reference vectors with declared latitude/date/tolerance and algorithm limitations; preserve the actual current approximation's documented tolerance until deliberately improved and verified. A one-minute goal is not a proven property of the present approximate implementation.

Pause accounting: sleep included; display interpolation excludes it; restart with correct clock, clock rollback, no repeated extension, expiry while blocked, resume while Manual, crossing DST. State expected output and intent separately.

## G3 — UI, guide and accessibility

Exercise native installed WebView2 host, not just the browser mock. First-run, skipped setup, resumed setup, legacy migration, no location, failed lookup, no network, missing runtime, no bridge, expired preview, save failure and conflict all have readable terminal states.

Verify every help snippet against the actual command. New users can install, locate/open app, enable, pause, restore normal and find Help without facilitator instruction. Pin tutorial and screenshots match supported Windows builds. Close-versus-Quit is understood; Start with Windows retains Off. Guide works offline and does not require a remote video or image.

Display matrix: light/dark/system, Glass/Frosted/Solid/legacy Ceramic, all independent preset values, custom black/white/extremes, opacity unavailable, forced colors, reduced motion. Test at 100/125/150/200% DPI and separate 200% text enlargement, smallest supported work area and mixed DPI monitors. No horizontal scroll, clipped essential action, hidden keyboard focus or tiny mandatory text.

Keyboard-only operation and Narrator/NVDA: proper names/roles/values; all preset selections announced; sliders work without dragging; timed Compare alternative; Escape cancels; Save/error announcement once; ticking ETA not repeatedly announced. Automated contrast checks cover token combinations; rendered transparency/native chrome needs real review. No WCAG/native blanket certification from automated checks alone.

## G4 — Physical Windows behavior and performance

Use a declared test account/VM and suitable physical hardware with consent. Keep an independent recovery route available and record neutral cleanup. VM API acceptance is not physical-display proof.

Minimum supported matrix: Windows 11 x64 declared builds; SDR LCD; representative OLED; one and multiple monitors with mixed DPI. Include HDR, RDP/virtual monitors, GPU variations, Magnifier/color filters and other warmth software as conditional rows, never implicitly supported. If hardware is unavailable, mark Blocked or explicitly exclude that configuration from release claims and ensure safe unsupported behavior.

Repeat at least 20 suspend/resume cycles, 10 monitor disconnect/reconnect/topology changes, 10 Explorer restarts, 10 owner/UI-helper fault/restart cases and 10 Windows Night Light transitions per representative supported configuration where meaningful. Test login/logout, locked session, hotkey unavailable, high contrast, battery/AC and low-resource conditions. These counts are engineering stress targets, not statistical reliability guarantees.

Readback mismatch/conflict must stop overwrite loops. Verify actual visible output/restoration, but do not label visual inspection as a spectral measurement. Missing backend and failed native helper must remain usable for Off/Help/diagnostics.

Measure plan.md budgets with hardware/build/workload and whole process-tree accounting. Record 30 cold/warm launches and 100 control/Save actions for latency distributions, ten-minute steady/fade CPU windows and settled memory after repeated open/close/override cycles. If budgets fail, optimize or explicitly narrow support before promotion.

## G5 — Preference/comfort and actual soak

Run the formative 12–20 participant comparison specified in plan.md with consent, reversible settings, counterbalanced order and unchanged-screen control. No advice to change medication or abandon care. Record notices separately from annoyance, readability, confusion and override behavior. Report negative/inconclusive results, denominator and missing data. No participant means Blocked, not a fabricated usability pass.

Fourteen actual nightly sessions on the release candidate: log build/policy ID, actual date, schedule, backend availability, start/ready/morning state, overrides, crashes and recovery. At least one continuous multi-night run; document gaps, system clock changes and missed observation. Simulated fourteen-night tests supplement but cannot replace wall-clock soak. Behavior-affecting changes restart affected evidence; unrelated documentation changes require a recorded impact assessment, not silent reuse of old proof.

Optical instrumentation and sleep outcomes remain Explicitly deferred. They are not universal utility-release blockers, but no measured-light or health-effect claim can pass without appropriate evidence.

## G6 — Signed distribution and website

Run the distribution contract against final signed bytes: artifact-derived manifest/SBOM/provenance, actual PE inventory, timestamp/publisher verification, private-source retention, dependency/redistribution review and secrets scan. Test installer cancellation, missing WebView2, offline preparation, low disk, interruptions, rerun, upgrade from supported old versions, stable pins and per-user coexistence. Uninstall must not remove shared WebView2 or unrelated files/settings.

From staging site, verify no-JS/keyboard/mobile CTA and help, redirects/MIME/attachment/length/range/cache, invalid-version 404 behavior and complete download hash. Install that downloaded file in a clean Windows environment; confirm About, executable path/hash, native design/controls and rollback. Never substitute a local build file for the visitor-downloaded artifact.

Staging uploads, new storage/DNS/signing access and public promotion need real execution authority. A required external gate remains Blocked when unavailable; the plan itself can still be complete.

## G7 — Approved public release and handoff

Before promotion: all required G0–G6 rows passed or supported scope explicitly narrowed without evading critical behavior; no critical/high unresolved issue; lower-severity defects documented with disposition. Owner approves public publication. Download assets first, verify, then promote manifest/site/alias. Failures keep the previous stable release live.

After deployment: anonymous real-page download, full hash/signature/version verification, clean install, native interaction, pin/open, pause/Off and upgrade/removal receipt. Record app source revision, artifact hash and site deploy revision together. Verify stable pointer rollback and explicit affected-user guidance. Handoff includes install URL, version, requirements, guide, limitations, release notes and rollback path.

## Traceability

| Requirements | Gate | Planned test/evidence locations |
|---|---|---|
| FR-001–004 | G1 | test_smart_state.py, test_smart_save.py, test_display_status.py, test_ipc.py |
| FR-005–008 | G2 | test_smart_schedule.py, test_smart_transition.py, test_smart_mode.py |
| FR-009–010 | G3 | test_onboarding.py, test_help_contract.py, premium/verify-ui.cjs, native guide receipts |
| FR-011–013 | G3/G4 | test_theme_contract.py, premium/verify-ui.cjs, native accessibility screenshots/receipts |
| FR-014–016 | G1/G2/G4 | test_smart_timezones.py, test_smart_migration.py, test_windows_nightlight.py, lifecycle receipts |
| FR-017–020 | G6/G7 | test_installer_contract.py, test_release_readiness.py, site release verifier, downloaded install receipt |
| NFR-001/004/006 | G0/G1/G6 | isolation, privacy and requirement ledger |
| NFR-002 | G4 | process-tree benchmark receipt |
| NFR-003 | G3/G6 | offline/network and deletion tests |
| NFR-005 | G4/G5/G7 | supported matrix and separate evidence ledgers |

Per-case receipt fields: ID, requirement, exact build/policy/config-schema, environment, steps, expected, observed, status, timestamp, evidence paths/hash, reviewer and cleanup outcome. Keep personally identifying participant data separate and access-limited. No blank successful-looking placeholders.
