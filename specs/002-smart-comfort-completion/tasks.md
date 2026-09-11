# Implementation tasks: Smart Comfort and Direct Download

Status: implementation in progress. Checked tasks have evidence; unchecked tasks may have partial work but are not complete. Tests are required by spec.md NFR-006 and should fail for the intended missing behavior before implementation. New paths below are proposed files, not claims they exist.

App paths are relative to the canonical Night Light repo. `SITE/` denotes the verified Night Light website worktree, reconciled with the latest source/deployment before any edit; its current location is recorded in contracts/distribution.md. Shared files have one integrator. `[P]` indicates parallel work only after the phase prerequisites are met and within the explicitly described batch.

## Phase A — Setup and baseline

- [ ] T001 Capture source/install/schema/dirty-work baseline and reconcile historical blockers in audit/smart-comfort/baseline.json and docs/CURRENT_CAPABILITIES.md.
- [X] T002 Adopt documented policy amendment/migration exception in .specify/memory/constitution.md and record the project decision; preserve immutable safety/privacy rules.
- [ ] T003 Resolve current website source/deployed revision and release prerequisites in docs/SMART_COMFORT_RELEASE_READINESS.md using SITE/src/pages/night-light.astro as the existing page.

Exit: exact scope/source known, unrelated edits preserved, no historical proof passed off as new evidence.

## Phase B — Shared foundations

- [ ] T004 Prove display/config/registry/taskbar isolation and injected failure support in conftest.py and test_smart_isolation.py.
- [X] T005 Implement typed versioned intent/snapshot/availability models and validators in smart_state.py and test_smart_state.py. Evidence: 34 pure state/model tests; typed output serialization used by the engine. Full bridge schema/routing remains T007/T016.
- [X] T006 [P] Define injected civil/UTC/active-time/elapsed-duration adapters in smart_time.py and test_smart_clocks.py.
- [ ] T007 Freeze/version native bridge request and snapshot schemas in premium_ui.py and test_bridge_contract.py; keep credentials out of payloads.
- [ ] T008 Implement atomic session-recovery record and crash-safe config primitives in config_manager.py and test_smart_recovery.py.
- [X] T009 [P] Build redacted legacy schema fixtures in tests/fixtures/smart_config/ and expected migration cases in test_smart_migration.py. Evidence: synthetic legacy-learning, legacy-off and legacy-out-of-range JSON fixtures; preview/keep/switch, preservation, explicit replacement, collection, pause/hold, backup/retry and fresh-install cases. Full migration UI and compatible binary rollback remain T045/T056/T067.

Exit: fake backend/clock/state contracts usable. Parallel batch: T006/T009 after T004, separately from the sequential T005/T007/T008 chain; avoid concurrent edits to shared fixture infrastructure.

## Phase C — US1: Truthful control and recovery (P1, first vertical slice)

- [ ] T010 [P] [US1] Add precedence, stale generation, new-Off-during-Save and owner isolation tests in test_smart_commands.py.
- [ ] T011 [P] [US1] Add disk/reply/idempotency/timeout/reconnect fault tests in test_smart_save.py.
- [X] T012 [US1] Implement intent reducer and generation invalidation in smart_state.py, including preview-from-Off exception and safety precedence. Evidence: test_smart_state.py covers newer Off, owner identity, expired/retried previews, overrides, and fault latching; native routing remains T016.
- [X] T013 [US1] Separate requested/accepted/readback output and availability in nightlight_engine.py and display_status.py. Evidence: fake Magnification API conflict/readback tests, typed full-matrix observations, fault-specific status and native Retry command. Actual hardware qualification remains T048.
- [ ] T014 [US1] Implement stage-persist-commit Save, revision reconciliation and Off storage exception in config_manager.py and premium_ui.py.
- [ ] T015 [US1] Integrate durable session recovery and neutral-on-unclean-start in main.py, tray_app.py and nightlight_engine.py.
- [ ] T016 [US1] Route UI/tray/taskbar/IPC through the one-owner intent path in main.py, tray_app.py, premium_ui.py and wpf_jumplist.cs.
- [ ] T017 [US1] Implement semantic status and Save feedback in premium/desktop.js and premium/settings.html with native-correlated revisions.
- [ ] T018 [US1] Record isolated manual-save/Off/restart vertical-slice proof in audit/smart-comfort/us1-control.json.

Independent check: G1 passes for manual control even before new scheduling/UI polish. Parallel: T010/T011; implementation is sequential through shared core files.

## Phase D — US2: One gentle predictable Smart controller (P1)

- [ ] T019 [P] [US2] Add dated schedule, independent endpoint and short-night feasibility tests in test_smart_schedule.py.
- [ ] T020 [P] [US2] Add curve/rate/acceleration/replan/catch-up/ETA invariants in test_smart_transition.py.
- [ ] T021 [US2] Implement solar/personal occurrence planning and reachable-envelope peak reduction in smart_schedule.py.
- [ ] T022 [US2] Implement versioned bounded trajectory, transform limiter and moving-target catch-up in smart_transition.py.
- [ ] T023 [US2] Replace repeated fade restarts with planned tracking in smart_mode.py and nightlight_engine.py; preserve one-writer contract.
- [ ] T024 [US2] Wire temporary slider holds, Save nightly preference, Apply now and phase ETA in premium_ui.py and premium/desktop.js.
- [ ] T025 [US2] Add two-section schedule/comfort drafts and advanced timing/slower options in premium/settings.html and smart_ui.py.
- [ ] T026 [US2] Compare policy tuning and 5/10/20 Hz samples, freezing candidate constants in smart_transition.py and audit/smart-comfort/policy.json.
- [ ] T027 [US2] Record G2 fake-clock scenarios and truthful target/current labels in audit/smart-comfort/us2-smart.json.

Independent check: pure planner/controller pass without a real display; integrated fake owner proves every action. T019/T020 parallel, T021/T022 parallel after their tests, then single integrator for T023–T025. Full feature still needs real hardware/comfort gates.

## Phase E — US3: Easy setup and offline instructions (P1)

- [ ] T028 [P] [US3] Add setup/guide command-copy coverage and offline-content tests in test_onboarding.py and test_help_contract.py.
- [ ] T029 [P] [US3] Author versioned one-sentence instructions, exact pin/update/uninstall steps and troubleshooting in premium/help.en.json and docs/USER_GUIDE.md.
- [ ] T030 [US3] Implement skippable neutral-first onboarding and persisted progress in premium/settings.html, premium/desktop.js and config_manager.py.
- [ ] T031 [US3] Implement native preview tokens, 20-second comfort/10-second compare watchdogs and bounded restore in premium_ui.py with tests in test_premium_ui.py.
- [ ] T032 [US3] Add confirm summary, named-provider consent and truthful location/timezone explanation in premium/settings.html and smart_location.py.
- [ ] T033 [US3] Add optional pin/startup tips and reopenable offline Help/About in premium/settings.html and premium/desktop.js.
- [ ] T034 [US3] Capture native first-run/skip/upgrade/no-runtime/help and preview-failure proof in audit/smart-comfort/us3-onboarding.json.

Independent check: fake settings/clock can exercise the complete first-run flow; G3 proves actual native comprehension later. T028/T029 parallel; UI/bridge edits require serialization with US2/US4 integration.

## Phase F — US4: Premium accessible design (P1)

- [ ] T035 [P] [US4] Add material/color/preset/reset/contrast contracts in test_theme_contract.py and premium/verify-ui.cjs.
- [ ] T036 [P] [US4] Implement full Glass/Frosted/Solid token systems, legacy Ceramic and opaque fallback in premium/desktop.css.
- [ ] T037 [US4] Implement independent filled presets/custom inputs/resets and light/dark migration in premium/desktop.js and premium/settings.html.
- [ ] T038 [US4] Align native window clipping/hit testing/work-area bounds with continuous panel layout in premium_host.cs and premium/desktop.css.
- [ ] T039 [US4] Complete keyboard/live-region/slider/large-text/forced-color behavior in premium/settings.html and premium/desktop.js.
- [ ] T040 [US4] Record identical-content material comparisons and native Narrator/NVDA/DPI evidence in audit/smart-comfort/us4-design/.

Independent check: fixture snapshots verify all UI states without applying a display transform; installed host still requires G3/G4. T035/T036 parallel; one integrator owns CSS during T038 and HTML/JS across stories.

## Phase G — US5: Lifecycle, privacy and compatibility (P1)

- [ ] T041 [P] [US5] Add full civil-time edge cases, packaged-zone sweep and solar reference vectors in test_smart_timezones.py.
- [ ] T042 [US5] Implement fold/gap/travel/elapsed-pause behavior using smart_time.py, smart_schedule.py and smart_mode.py.
- [ ] T043 [P] [US5] Add availability/ownership/manual-resume/neutral-failure tests in test_smart_conflicts.py and test_windows_nightlight.py.
- [ ] T044 [US5] Implement sleep/clock/topology/high-contrast/Windows-clear handling with bounded retry in tray_app.py, smart_windows.py and nightlight_engine.py.
- [ ] T045 [US5] Implement explicit legacy/v2 migration preview, retained preferences and compatible rollback in config_manager.py, smart_mode.py and premium_ui.py.
- [ ] T046 [US5] Implement history/location/backup deletion and safe diagnostic export in smart_learning.py, smart_location.py and premium_ui.py.
- [ ] T047 [US5] Reconcile remaining native startup, IPC/ACL and helper error propagation issues in win32_tray.py, ipc_transport.py and main.py with targeted regressions.
- [ ] T048 [US5] Record real Windows state/lifecycle/hardware support matrix in audit/smart-comfort/us5-platform/ and docs/SUPPORTED_CONFIGURATIONS.md.

Independent check: G2 clocks plus G1 conflict fixtures; native G4 rows separately qualify support. T041/T043 parallel, then integration after US1/US2 contracts. Privacy edits cannot run concurrently with migration edits to the same modules.

## Phase H — US6: Website download and installation (P1)

- [ ] T049 [P] [US6] Add artifact manifest/signing/version/installer invariants in test_installer_contract.py and test_release_readiness.py.
- [ ] T050 [P] [US6] Implement per-user installer/staging/rollback/removal in installer/night-light.nsi and installer/README.md using the approved pinned builder.
- [ ] T051 [US6] Include new modules/assets/help and exact native/runtime inventory in build.py, build_premium.py, pyproject.toml and release.py.
- [ ] T052 [US6] Implement sign-then-hash manifest/SBOM/provenance enforcement in release.py and .github/workflows/ci.yml; private signing access is an explicit prerequisite.
- [ ] T053 [US6] Add manifest-driven direct CTA/requirements/notes to SITE/src/pages/night-light.astro via SITE/src/components/NightLightDownload.astro and SITE/src/data/nightLightRelease.ts.
- [ ] T054 [US6] Add accessible installation/update/removal help in SITE/src/pages/night-light/install.astro, reusing versioned app-guide content where practical.
- [ ] T055 [US6] Add artifact/redirect/cache/download validation in SITE/scripts/verify-night-light-release.mjs and SITE/public/_redirects without replacing unrelated rules.
- [ ] T056 [US6] Record clean install/upgrade/interruption/uninstall/stable-pin/rollback cases in audit/smart-comfort/us6-installer/.
- [ ] T057 [US6] After appropriate authorization, stage immutable signed assets on approved hosting and record headers/hashes/signatures in audit/smart-comfort/staging-download.json.
- [ ] T058 [US6] Test the actual site-preview download through clean installed native behavior and record SITE deployment plus app identity in audit/smart-comfort/us6-download-install.json.

Independent check: manifest/file validators run before hosting; real downloaded installation is separate. T049/T050 parallel after contracts; T053/T054 can run against a clearly non-publishable fixture while app build integration continues, with one site integrator. Public assets/site deploy are not implicit permission.

## Phase I — Cross-cutting quality and release

- [ ] T059 Rerun complete isolated regression and exact candidate build, recording logs and hashes in audit/smart-comfort/regression/.
- [ ] T060 Benchmark all process-tree/latency budgets and optimize failures, recording audit/smart-comfort/performance.json.
- [ ] T061 Run consented formative comfort/comprehension comparison and record de-identified findings in audit/smart-comfort/comfort-report.md.
- [ ] T062 Complete fourteen actual nightly candidate sessions with lifecycle/recovery receipts in audit/smart-comfort/soak/.
- [ ] T063 Generate exact final artifact-derived release evidence and requirement dispositions in docs/SMART_COMFORT_RELEASE_READINESS.md and audit/smart-comfort/final-manifest.json.
- [ ] T064 Complete security/dependency/redistribution/health-copy review of final app, installer, docs and SITE/src/pages/night-light.astro; record audit/smart-comfort/final-review.md.
- [ ] T065 Obtain explicit publication approval, promote verified assets/manifest/site and preserve previous stable pointers using the procedure in contracts/distribution.md.
- [ ] T066 Verify anonymous live download bytes/signature and installed native app against approved identity in audit/smart-comfort/public-release-receipt.json.
- [ ] T067 Exercise release-pointer and app/config rollback; document affected-user guidance in docs/ROLLBACK.md and audit/smart-comfort/rollback.json.
- [ ] T068 Deliver version/install URL/guide/support matrix/limitations/receipts and durable project/site handoff in docs/SMART_COMFORT_RELEASE_HANDOFF.md.

## Dependency graph and strategy

`A → B → US1 → US2 → US5 → final native/quality gates → signed distribution verification → approved release`

US3/US4 can use frozen US1/US2 contracts in parallel, but their shared premium files must be integrated sequentially. US6 tooling/page work can begin after A/B contracts; final artifact and downloaded-install proof depend on the completed candidate. G5 actual soak cannot be replaced by fast-forward simulation. G7 public completion cannot be claimed before authorization and anonymous download proof.

Recommended internal MVP: Phase A/B plus US1. Then add Smart and onboarding, design/lifecycle, and distribution. Each increment gets a local evidence receipt; none silently becomes a public release. All six stories are required for the user's requested complete version.

Counts: setup 3; foundations 6; US1 9; US2 9; US3 7; US4 6; US5 8; US6 10; final 10. Total 68. All checkboxes intentionally remain unchecked until implementation evidence exists.
