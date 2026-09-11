# Night Light: end-to-end public-release completion plan

Date: 2026-09-10. Status: planned, not implemented or release-cleared.

Revision 2: implementation-ready execution controls added. The companion [execution checklist, decisions and release contract](PUBLIC_RELEASE_EXECUTION_CONTRACT.md) is mandatory alongside this plan. It supplies numbered tasks, requirement coverage, dependency and evidence rules, access gates, and fail-closed release criteria. It does not certify unresolved Windows behavior or unavailable credentials as resolved.

This execution addendum connects the [current audit](../../audit/public-readiness-20260910/REPORT.md) to the existing [specification](spec.md) and [architecture plan](plan.md). It does not replace their requirements, comfort-rate limits, privacy rules, fourteen-night soak, or formative usability gate. Existing checkmarks and historical receipts are not proof for a new candidate.

## Outcome and boundaries

One current Windows app, one supported primary installer, one direct public download. The premium UI is the actual shipped interface. A simpler presentation, if retained, is a mode of the same app and controller—not the retired application or a second download. Existing users get safe replacement and a clear choice before materially different Smart behavior begins.

Completion means a new visitor can download, install, understand, enable, pin, pause, update and uninstall the exact verified release. No account, donation, IP-based location, prototype web server, or developer tooling is required.

Planning does not authorize publication, paid signing enrollment, external tester recruitment, or destructive testing on Hassan's daily-use installation. Perform failure tests in disposable environments. Request only genuinely missing access/authority, not intermediate design reviews. Preserve unrelated dirty work. Do not expand into an updater service, cloud telemetry, new learning collection, clinical claims, or another redesign.

## 0. Establish the source of truth

**Work:** Inventory the existing dirty source, current Spec Kit tasks, installer assets, website ownership and build scripts. Reconcile each original FR/NFR against implementation and current evidence. Refresh stale code indexes during implementation. Use one release ledger with requirement, current status, task, test, candidate identity, evidence and unresolved limitation. Correct stale installed-release documentation rather than treating candidate j receipts as current k proof.

Resolve the branding mismatch explicitly: current constitution names Night Light by HT, while a test demands Night Light. Preserve the approved visible UI name until the public-name policy and tests are reconciled together. Legacy names remain in an isolated compatibility catalog, never as another app option.

**Gate G0:** All seven audit findings and every original requirement have an owner/task and verification method. Baseline records 509 passes, one compatibility-name assertion failure, one skip; skipped coverage is classified. Candidate k is a baseline, not the future release.

## 1. Reliable commands and fresh taskbar behavior

**Files:** `main.py`, `create_shortcuts.py`, `tray_app.py`, `ipc_transport.py`, `wpf_jumplist.cs`, `premium_ui.py`, `premium/desktop.js`; existing command/shortcut tests.

First reproduce fresh-install → pin → first click on supported Windows in an isolated user profile. Do not assume an existing repaired `.lnk` proves new pin behavior.

Preferred contract: ordinary app activation is the moon toggle; explicit `--show` opens controls; explicit `--background` starts without a toggle. The pin-capable primary shortcut must retain toggle semantics when Windows creates a pin. First-ever launch may present neutral onboarding before offering activation. Installer completion opens controls explicitly rather than accidentally toggling. Jump List “Open controls” remains unambiguous. Remove reliance on periodically rewriting Windows-managed pins. If Windows grouping prevents the intended behavior, prove an app-owned launcher/identity solution in this spike before committing architecture; do not ship a taskbar hook or simulated global clicks.

Use request identities for IPC retries: the same delivered request must not toggle twice; two deliberate clicks remain two actions. Verify cold/warm/background startup, open/closed panel, same-instance routing, double-clicks and rapid clicks. Off must cancel stale pending output, preserve a valid recovery route, and remain Off after restart. Opening settings must never toggle.

Save feedback is state-driven: “Saving…” immediately; “Saved” only after durable commit; separately show applying, active, scheduled-neutral, paused, blocked or unconfirmed output. Example: “Saved. Smart starts at 6:45 PM” is successful even when the screen remains neutral. Retry after timeout reconciles the original request; errors preserve editable inputs and explain the next action.

**Gate G1:** New and existing pins perform exactly one intended toggle; setup and settings do not toggle unexpectedly; save/retry/race/Off tests and installed interactions pass. Pending UI acknowledgement p95 ≤200 ms and ordinary local Save p95 ≤1 second on declared reference hardware, per existing plan.

## 2. Complete Smart migration without reviving the old app

**Files:** `smart_migration.py`, `smart_migration_switch.py`, `smart_store.py`, `smart_desktop.py`, `smart_runtime.py`, `premium_ui.py`; migration and restart tests.

Replace the unavailable-switch placeholder only after the complete transaction is tested. Review current versus proposed timing, location, warmth, dimming, pause/manual intent and inferred-behavior changes. Actions: “Use new Smart mode” and “Not now.” The latter stays in the new UI with an honestly labelled compatibility policy, never launches old binaries. No automatic increase in intensity or expansion of tracking consent.

Use a versioned non-executable configuration backup with bounded retention and user-readable deletion controls. Coordinate config locking, commit, active-controller handoff and generation invalidation so only one controller can own output. Failure before commit leaves old intent valid; failure after commit recovers the new persisted intent without double application. Do not replay a stale preview on restart. Define corrupt, unsupported, already-migrated and interrupted states. New installations initialize v2 neutral with skippable setup.

Retire obsolete automatic learning authority for migrated users; describe retained legacy data and provide safe deletion. Compatibility code is not a second install. About/diagnostics expose active policy version so future audits do not infer it from appearance.

**Gate G2:** Fresh/v1/v2/corrupt/interrupted/repeated migration fixtures pass; consent and themes persist; no two controllers write; an authorized installed migration shows v2 in actual persisted state and runtime diagnostics.

## 3. Qualify Smart timing, comfort and VPN independence

Preserve the existing single-controller design: normal gradual schedule and bounded late-start catch-up are different trajectories of one policy, not competing Smart engines. Reuse the specified rate ceilings; do not invent “scientifically optimal” durations or promise imperceptibility. Warmth and dimming remain independent. Slower comfort settings affect transitions without delaying emergency recovery.

Solar timing uses saved, user-confirmed coarse coordinates; personal timing uses civil times and the Windows zone. Never derive either from IP, VPN exit nodes, proxy settings or process TZ. A changed Windows zone is a real OS change, not something a VPN-independence promise can ignore. Saved location is not silently changed by travel. Offline/manual location entry remains possible.

Test Dearborn Heights 48127; DST gap/fold; half-hour and quarter-hour offsets; opposite hemispheres; midnight-crossing intervals; polar conditions; missing solar data; date/clock corrections; offline lookup failure; VPN on/off/exit-country changes; and timezone changes while enabled. Show dated resolved events, location source and meaningful fallback status. Personal mode needs no location.

Exercise late activation, wake, restart, missed events, pause expiry during sleep, compare timeout, schedule edits and Windows Night Light on/off/unknown. Observe accepted backend output, not just desired configuration. Handle other transform owners without a reset loop that fights accessibility software. Diagnose unsupported HDR/display states honestly.

**Gate G3:** Deterministic clock/location/backend matrix passes; hardware transition samples remain within agreed bounds; no instant catch-up jump after sleep; VPN changes alone leave saved schedule inputs unchanged. UI distinguishes scheduled-neutral from failed output. No unqualified all-hardware or health claims.

## 4. Crash-recoverable replacement and complete owned cleanup

**Files:** `installer/upgrade.ps1`, `installer/remove-owned.ps1`, `installer/night-light.nsi`, `build_installer.py`; installation/removal tests.

Model installation as a recoverable transaction: verified staging → durable prepared journal → previous payload reserved → replacement promoted → owned integration updated → committed → old payload cleaned. Record transaction ID, old/new receipts and hashes, validated paths, phase, and recoverable prior shortcut/startup state. Flush/atomically replace the journal before dependent mutation. Recovery trusts verified bytes plus journal phase, not phase text alone. Keep the existing lock/mutex, ownership checks and reparse-path protections.

At startup of setup, recover an unfinished transaction before attempting another update. Every repeat operation is idempotent. Failures before commit restore a usable prior app and all integration changes, including newly created links; failures after commit finish scoped cleanup. Disk-full, locked-file, tampered-receipt, killed-process and abrupt-VM-power-off tests cover each boundary. Never test power loss on the user's machine.

Temporary rollback data is necessary during a transaction, but must not be another advertised launchable installation. Prefer a non-launchable verified backup container where feasible. Remove positively owned superseded payloads after success; unfinished cleanup is explicit and retryable, not a silent `.failed-*` executable pile. Never recursively delete all files matching a product name or unknown executables.

Uninstall enumerates only receipt-owned files and positively owned Desktop/Start/pinned/startup/uninstall entries. Preserve unrelated entries, other users' data and preferences by default. Offer a separate explicit “Remove my settings and local history” choice. Restore/stop owned output safely before removal. Support partial uninstall and rerun. Verify reinstall, old renamed shortcut catalog, symlink/junction abuse and two-user separation.

**Gate G4:** Every injected interruption recovers to one coherent installed version or a clear recoverable no-install state; no stale owned launch/startup entries after removal; unknown files are unchanged. Each case has before/after inventory and hashes. “All old traces removed” means owned obsolete launchable artifacts and integration—not source history, required compatibility identifiers, or consent-preserving data backups.

## 5. Finish the premium experience and instructions

Use one continuous app surface with controlled scrolling and a border fitted to the native window; no horizontal scrollbar, nested-card clutter or dependence on the concept page. Glass/Frosted/Solid affect backgrounds, surfaces, controls and depth coherently. Keep readable opaque fallback. Every color property gets visibly filled labelled presets, custom value, selected state and reset, independently persisted for light/dark modes. Theme changes never alter physical filtering.

Keep quick controls short; collapse Appearance/Advanced. Provide inline explanations for Smart versus Manual, warmth, software dimming, compare, temporary overrides, pause and resume. Guide: neutral first run → choose mode → timing/location if needed → reversible appearance preview → save/enable confirmation → optional pin/startup tips. Pinning and startup are never silently enabled. Pin instructions must match the implementation proven in G1. Explain that the taskbar Windows menu is OS-styled; improve labels, icons and grouping without promising a custom glass system menu.

Help is bundled offline and reopenable. Include Windows Night Light conflict, unknown backend, travel/VPN, display limitations, reset, updates and uninstall. Preview must restore on Escape, timeout, close, deactivation/failure paths as specified. Diagnostics are opt-in exports, redact credentials/location/history by default and include version/policy/backend status.

**Gate G5:** Current installed screenshots and interaction recordings, not mockups; light/dark/forced colors/reduced motion; keyboard and screen reader; large text and supported mixed-DPI monitors; narrow/short window; all essential journeys completed without clipped controls. Warm open p95 ≤500 ms, cold usable ≤3 seconds on declared hardware; record whole-process CPU/memory against original budgets.

## 6. Green regression and clean immutable candidate

Fix the branding test by distinguishing visible copy from compatibility literals, not deleting upgrade handling. Identify why the skipped test is skipped; run it in its required environment or explicitly narrow support—never count a required skipped test as passed. Add regressions for G1–G5 before fixes and retain meaningful negative tests.

Reconcile original tasks with this addendum, run all unit/integration/native/installer/security checks, and review the final diff. Assemble a clean release source revision without unrelated/private files. Build once per candidate identity from locked dependencies, with version + source revision + build ID exposed in About, package and release manifest. Helpers must have attributable sources and dependency licenses. Do not rebuild silently under the same version.

**Gate G6:** Zero unexplained failures or release-critical skips; clean-source reproduction; exact source-bound build/installer receipts; no legacy UI in package; all required launch modes and cleanup policies covered. Passing this gate is candidate readiness, not public release.

## 7. Publisher signing and complete website download

Identify existing publisher signing access early, without purchasing or exposing keys. If unavailable, signing is a real external blocker; do not substitute “ignore Windows warnings.” Sign app-owned executables first, build ownership receipts against those signed bytes, package them, sign the final installer, then generate final hashes/size/provenance. Check trust chain and timestamp on clean Windows; valid signing does not guarantee absence of SmartScreen prompts. Verify signed artifact identity rather than promising byte-identical signing timestamps.

Locate the actual owning website repo/deploy pipeline before edits. Add a primary “Download for Windows” CTA at the hero and relevant lower section, backed by one versioned immutable installer asset and a controlled latest-release manifest. Include version, size, Windows/architecture requirements, WebView2 prerequisite, instructions, privacy, release notes, publisher and checksum. No GitHub/source ZIP detour, account, donation gate, or automatic page-load download. Public downloads must not depend on a private repository credential or expiring local URL.

Stage installer, website and manifest together. Verify HTTPS, file headers/name, complete download/hash/signature, missing-runtime flow, private-browser access and no stale cache/version mismatch. Updating the manifest happens only after the referenced asset is available and verified. Old releases need not remain public download choices; keep controlled recovery provenance privately.

**Gate G7:** Staging browser → downloaded installer → clean installed app → About/running path all identify the same signed candidate. Deployed page claims match measured support. Buying/enrolling signing or publishing requires the appropriate explicit authority/access.

## 8. Real-world qualification, promotion and rollback

Run the original formative usability comparison with 12–20 consenting adults and the specified unassisted-task target, without health-efficacy claims. Recruit only with authority and consent; no hidden activity collection. Record noticeability, annoyance, comprehension and recovery separately. Keep the original requirement for **fourteen actual nightly soak sessions** on the release candidate; simulated clock tests are additional evidence, not nights. Material controller/backend/installer fixes require a new candidate and rerunning affected gates; do not silently carry old proof forward.

In supported Windows environments test clean install, existing-user upgrade, first pin, toggle, Save/Enable, migration, Smart overnight, wake, offline operation, rollback and uninstall. Hardware rows include the declared GPU/display combinations and exclusions. Unavailable hardware or users remain blocked/not-run, not inferred passes.

Prepare a promotion receipt with exact revision, candidate hash/signature, matrix results, known noncritical limitations, operator, and rollback instructions. With publication approval, promote assets then manifest/page. Independently download from the live website in a clean browser context; verify final bytes and installed identity; complete the critical first-user flow. Only then label it public-release verified.

Rollback: stop advertising a defective asset, restore the last verified supported manifest/site if one exists, or withdraw the download when none exists. Never resurrect the retired UI as the fallback. Installed config downgrades require explicit compatibility proof; prefer a versioned forward fix when downgrade cannot preserve data. Document a user-visible advisory when appropriate.

For post-release observation, collect only consented reports and agreed operational checks. No background monitoring automation is created by this plan. A later authorized monitor should alert on actionable download/installation failures, not unchanged state.

**Gate G8:** All P1/critical defects closed; original requirements and evidence accounted for; usability/soak passed; signed exact candidate approved; live download-to-installed proof complete; recovery/withdrawal procedure tested.

## Execution order and handoff

G0 → G1/G2 → G3 → G4 → G5 → G6 → G7 → G8. Investigate signing access and staging hosting during G0 so external lead time is visible early; prepare website content without publishing while reliability work proceeds. These are workstream dependencies, not authorization to spawn agents.

Each gate produces a short receipt: candidate/revision, environment, command or manual procedure, expected/actual result, evidence path, PASS/FAIL/BLOCKED/NOT RUN, and defect links. No readiness percentage substitutes for the gates. Keep the old audit immutable and append closure evidence.

The product is done only when the actual public journey and installed runtime pass—not when the code is written, a local installer exists, or the UI looks finished. Fourteen real nights and external signing/testing access make an instant full-release promise inappropriate.
