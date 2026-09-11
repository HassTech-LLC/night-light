# Public release execution contract

Date: 2026-09-10. Revision: 1. Status: executed through private candidate
`0.2.0-local2`; the authoritative candidate-bound task and requirement states are in
`audit/public-release/candidate-0.2.0-local2/release-requirements.json`. Public release
remains HOLD at the external qualification and promotion gates listed there.

Companion to [completion plan](PUBLIC_RELEASE_COMPLETION_PLAN_2026-09-10.md), [original requirements](spec.md), [architecture](plan.md) and [original tasks](tasks.md). This adds execution controls, not another product direction. Existing implementation may satisfy tasks after fresh verification; do not rewrite working code merely because a checkbox starts unchecked. New artifact/test filenames below are proposed unless already present.

## A. Execution rules

One continuous implementation effort means execute, test, diagnose failures, repair and repeat until the stated gates pass. It does not mean one attempt, zero defects, or permission to bypass external approvals. Do not ask Hassan to review routine intermediate designs. Ask only for missing authority, resources, or a materially different product decision.

Implementation and verification may proceed while signing or tester access is pending. Mark those dependencies BLOCKED and finish independent work; do not declare completion. This plan does not create background monitoring or authorize automatic agents. Use existing task IDs T001–T068 as historical implementation references; the R-series below is the final audit-closure checklist. Reconcile both inventories before release rather than clearing older unchecked tasks by implication.

Each R-task gets: responsible implementer, dependencies, affected requirements, exact source revision, changed files, test procedure, expected and observed outcome, evidence paths, outstanding defects, and status. Allowed statuses: NOT_STARTED, IN_PROGRESS, PASS, FAIL, BLOCKED, NOT_APPLICABLE_WITH_REASON. Required blocked/skipped tasks fail the release gate. PASS requires evidence, not a comment saying work is finished.

Keep evidence under `audit/public-release/<candidate-id>/`, using `baseline/`, `commands/`, `migration/`, `smart/`, `installer/`, `ui/`, `build/`, `distribution/`, `qualification/`, and `live/`. Commit sanitized plans and tests; keep binaries and private test data out of source control. Store no credentials in receipts.

## B. Decisions to implement and prove

### D1 — Moon activation and Windows pinning

Fixed user-facing behavior: a deliberate click on the pinned moon requests one On/Off toggle. Opening controls is a separate explicit action. Startup/background launch never toggles. First-run onboarding stays neutral until user activation. The Windows Jump List offers concise app-owned commands; its outer styling remains Windows-controlled.

Preferred implementation: a pin-capable toggle entry (`--toggle` or a dedicated app-owned launcher) with stable identity; explicit `--show` for controls and installer completion; explicit `--background` for startup. Do not infer launch provenance from focus, mouse location or window visibility. Do not change all Desktop/Start launch behavior to toggle merely to mask a pin problem. Give controls access an unmistakable label.

Windows may activate an existing grouped window instead of launching a new process. Therefore command-line tests alone cannot close D1. R004 must prove pin-from-Start and pin-from-running-window, app cold/running, panel hidden/visible, Explorer restart, unpin/repin, and an upgrade of an existing pin on declared Windows builds. Record which identity/window grouping makes each case work.

If the current host cannot satisfy that matrix, implement and test a narrow app-owned toggle launcher with a separate controls-window identity. It must not create a second filter engine, competing app version, extra startup owner or unexplained persistent taskbar icon. Document any necessary separate controls entry. Reject global hooks, undocumented pin automation, focus-triggered toggles, periodic rewrites of user pins, and speculative “fixed” claims. If neither architecture meets the required UX, D1 remains a release blocker requiring a bounded product choice—not a silent fallback to opening settings.

### D2 — Command, Save and output truth

Every deliberate action has a unique request ID; retries reuse it. Durable deduplication or an equivalent replay-safe protocol covers owner restart. Serialize reducer decisions through one owner and correlate acknowledgements with revision/generation. Test cancellation and response reordering. Do not conflate duplicate network delivery with two actual user clicks.

Saved configuration and applied output are separate states. Feedback covers saving, saved, scheduled-neutral, transitioning, paused, blocked, unconfirmed and error. Disk failure never displays Saved. Backend refusal never displays Active. Off invalidates stale work and requests safe recovery even when persistence fails, while explaining any inability to preserve Off after restart. Avoid unconditional identity writes over another application's transform.

### D3 — One new app with consent-preserving compatibility

No retired UI executable or alternate old-app download. Migration can retain a clearly labelled old scheduling adapter inside the new app until accepted; that is data/behavior compatibility, not a second product. Fresh installations use the new policy. No inferred data gains new scheduling authority through upgrade. Do not delete settings/history without scoped consent.

### D4 — Upgrade atomicity and rollback

Keep the stable per-user installation entry. Write and flush a versioned transaction journal before each dependent mutation; make recovery idempotent and validate actual file identities. The precommit rollback restores payload plus shortcuts/startup changes, including removal of entries newly created by the failed transaction. Postcommit recovery completes cleanup. Never label cleanup failure a fully successful upgrade.

Retain only scoped temporary rollback data during the transaction; prefer a non-launchable container. Unknown files or ambiguous ownership stop deletion, not trigger broad cleanup. Installer rollback must respect config-schema compatibility. When no downgrade is safe, retain recoverable data and supply a forward fix; never reinstall the retired UI as a fallback.

### D5 — Supported platform and identity

Initial target remains Windows 11 x64. Record exact tested Windows builds, GPUs, display modes, DPI and WebView2 versions before qualification. Do not imply Windows 10, ARM, all HDR modes or every monitor topology is supported without evidence. Unsupported backend conditions should remain visible and safe, with a documented recovery path.

Use the constitution's full product identity, Night Light by HT, in legal/release identity; concise Night Light labels may remain in compact UI. Define a single copy inventory and adjust the branding test accordingly. Legacy identifiers are allowed only in a documented compatibility catalog. Version, source revision, build ID, config schema and policy version remain distinct fields.

## C. Early access and authority checklist

Complete this inventory in R002. Never print secrets or assume a resource exists merely because a tool is available.

| Dependency | Read-only check / record | Blocks | Safe progress if missing | Authority boundary |
|---|---|---|---|---|
| App source/release repo | canonical path, remote, branch, dirty-file ownership, CI permissions | clean release and artifact upload | local isolated implementation/tests | no unrelated commits or remote writes inferred from planning |
| Website | actual owning repo, deployed revision, staging/live environments, deploy method | staged/live download journey | prepare app contracts and page specification | public deployment requires approval |
| Artifact hosting | durable public HTTPS assets, immutable names, cache controls, rollback access | direct installer delivery | local signed-package verification | do not make private repositories public as a workaround |
| Publisher signing | authorized publisher, key/service location, timestamp/trust procedure, credential custodian | signed release | unsigned clearly private candidates only | purchase/enrollment and identity submission require approval |
| Disposable Windows | snapshot-capable VM, separate test user, supported OS images, reset procedure | destructive lifecycle and interruption tests | fake filesystem/backend tests | never power-cut or uninstall the daily-use app for fault injection |
| Hardware | supported GPU/display/HDR/DPI combinations and physical access | claimed support rows | qualify available subset honestly | narrowing previously promised scope must be explicit |
| Testers | consent process, recruitment authority, 12–20 adults, privacy-safe session method | existing formative usability gate | prepare guide/protocol | no unsolicited contact or data collection |
| Soak | candidate, consented test machine, session log, fourteen real nights | original soak gate | deterministic event simulations | monitoring requires separate authorization/mechanism |
| Final promotion | named approver and exact artifact/revision to approve | public release | stage and prepare receipt | obtain approval before external promotion |

Do not promise an elapsed completion date until these are known. Fourteen real nightly sessions are calendar work, not a loop of simulated timestamps. If Hassan later changes that requirement, amend the specification explicitly; do not quietly substitute a shorter gate.

## D. Numbered implementation and verification tasks

Dependencies refer to R-tasks. A task marked implementation includes test-first changes where behavior is missing. Existing file names provide orientation; use a fresh structural index before editing.

### Baseline and contracts — G0

- [ ] **R001 — Build the coverage ledger.** Depends: none. Map all FR/NFR, audit findings and T001–T068 into `release-requirements.json` (proposed). Capture source/install/version/schema identities without secrets, dirty ownership and test baseline. Evidence: baseline inventory and uncovered-requirement report. Complete only with zero unmapped requirements.
- [ ] **R002 — Resolve access inventory.** Depends: none. Fill section C with verified resources, owners, pending approval and blockers. Evidence: redacted access checklist. All unknowns must be explicit; missing access may be recorded BLOCKED while implementation continues.
- [ ] **R003 — Freeze safety, branding and bridge contracts.** Depends: R001. Reconcile constitution/copy tests; define commands, snapshot schema, request IDs, generations and source of effective state. Files: constitution, command/UI contracts, `main.py`, `premium_ui.py`, `ipc_transport.py` tests. Evidence: contract fixtures and compatibility-name regression. No runtime behavior is changed merely by amending a test.

### Activation and truth — G1

- [ ] **R004 — Resolve D1 on real Windows.** Depends: R002/R003. Reproduce current behavior, prototype preferred identity and fallback only if needed, complete the exact pin matrix in D1. Files: launcher/host, `create_shortcuts.py`, Jump List adapter. Evidence: decision record, `.lnk` fields, process/owner count and observed action per case. This is the bounded architecture gate before final shortcut implementation.
- [ ] **R005 — Implement one-owner activation.** Depends: R004. Route chosen launcher, tray and Jump List through the same controller; retain explicit show/background modes and neutral onboarding. Test cold start, races, rapid clicks and same-request replay across owner restart. Evidence: isolated command tests plus installed R004 matrix rerun.
- [ ] **R006 — Complete Save and Off semantics.** Depends: R003/R005. Files: `config_manager.py`, `smart_store.py`, `premium_ui.py`, UI feedback. Test disk-full, stale replies, timeouts, restart, canceled saves and newer Off. Evidence: persisted revisions, accepted-output traces and recorded UI feedback; successful Save cannot hide a blocked filter.

### Migration and Smart — G2/G3

- [ ] **R007 — Complete migration transaction.** Depends: R006. Files: migration/switch/store/controller modules. Add redacted fresh/v1/v2/corrupt/interrupted/repeated fixtures; backup and recover across each handoff boundary. Evidence: expected before/after schemas, preserved intent and single-writer assertions.
- [ ] **R008 — Complete migration review and privacy controls.** Depends: R007. Wire review/accept/defer, disable obsolete inferred authority after acceptance, explain retained data and safe deletion. Evidence: native migration flow, active policy ID, saved preferences and explicit consent boundaries. No old UI launch path.
- [ ] **R009 — Verify timing and VPN invariants.** Depends: R007. Files: `smart_time.py`, location/schedule/runtime adapters. Test the completion plan's zone/DST/polar/clock/offline/VPN cases, with injected clocks and provider contracts. Evidence: fixture table, resolved dated events and unchanged coordinates/zone inputs for network-only changes.
- [ ] **R010 — Verify trajectory and override invariants.** Depends: R006/R009. Files: transition/state/runtime. Test moving schedule catch-up, no easing restart, independent warmth/dim, preview restoration, pause across sleep/restart and permanent Off. Evidence: numerical output traces against original rate ceilings; do not replace existing limits with arbitrary percentages.
- [ ] **R011 — Verify actual display ownership/recovery.** Depends: R010 and authorized hardware access. Files: engine/status/Windows adapters. Exercise Windows Night Light on/off/unknown, external writer, backend failure, monitor changes, suspend/resume and owner crash. Evidence: physical/native readback with environment details and safe cleanup. Config state alone does not pass this task.

### Installation lifecycle — G4

- [ ] **R012 — Add isolated transaction fault harness.** Depends: R003. Proposed tests/harness under `tests/installer/`; redirect all filesystem/registry/shortcut targets. Prove the harness cannot reach live user state. Add named failure hooks for every transaction boundary. Evidence: sentinel preservation and isolation tests.
- [ ] **R013 — Implement journaled upgrade/recovery.** Depends: R012/R007. Files: `installer/upgrade.ps1`, build/receipt contracts. Persist prepared intent, validate state/bytes on rerun, roll back full integration state precommit and finish cleanup postcommit. Evidence: deterministic faults before/after each journal, rename, copy, integration, commit and cleanup step; repeat recovery twice without divergence.
- [ ] **R014 — Implement complete owned uninstall.** Depends: R013. Files: `installer/remove-owned.ps1`, NSIS. Cover Desktop/Start/pins/startup/uninstall registration and optional consented data deletion. Evidence: before/after inventory, retained unknown files/preferences, partial uninstall retry and reinstall. Reject path traversal, reparse points, tampered receipts and ambiguous ownership.
- [ ] **R015 — Prove interruption and upgrade matrix.** Depends: R013/R014 and disposable Windows. Test process kill, abrupt VM shutdown, disk-full, locks, missing WebView2, old catalog versions, same-version repair, two users and old/new shortcuts. Evidence: snapshots and recovery logs. One current usable installation or explicit recoverable no-install; no silent orphan launchable payload.

### Experience and instruction — G5

- [ ] **R016 — Finish native layout and appearance.** Depends: R006/R008. Files: premium host/CSS/HTML/JS. Continuous fitted surface, distinct materials, independent filled presets, custom values and mode-specific reset/persistence. Evidence: installed screenshots across each finish/light-dark combination; no horizontal overflow or color-setting/filter coupling.
- [ ] **R017 — Finish onboarding and offline guide.** Depends: R004/R008/R016. Neutral/skippable setup; reversible preview; understandable success/error; accurate pin/startup tips; help/troubleshooting/About/update/uninstall. Evidence: airplane/offline guide test and native first-user script. No preview-server dependence or silent startup consent.
- [ ] **R018 — Pass accessibility and performance.** Depends: R016/R017. Test keyboard, focus, screen reader announcements, forced colors, reduced motion, large text and mixed DPI; measure cold/warm open, Save latency, process-tree CPU/memory and repeated-cycle growth against existing budgets. Evidence: raw samples, declared hardware, p95 methodology, screenshots and defect closure.

### Candidate and distribution — G6/G7

- [ ] **R019 — Close regression gaps.** Depends: R005–R018 as applicable. Fix the compatibility branding assertion without deleting legacy handling; explain every skip; run full tests and required negative/security cases. Evidence: fresh JUnit, coverage ledger and zero required skipped cases. Any hardware rows run separately must have actual receipts.
- [ ] **R020 — Freeze and build clean source.** Depends: R019. Files: build/release scripts, dependency locks, identity and packaging. Capture reviewed clean revision, dependency licenses, SBOM and source provenance; exclude retired UI/private files. Evidence: isolated build receipt and package inventory. Preserve unrelated working files outside the release snapshot.
- [ ] **R021 — Sign and bind final bytes.** Depends: R020/signing access. Sign executable payloads, generate their ownership receipts, build installer, sign installer, then hash final artifact. Verify trust/timestamp and no post-sign mutation. Evidence: publisher verification, exact file hashes, package and source provenance. Never sign first and then silently modify receipt-bound payloads.
- [ ] **R022 — Implement direct download and manifest.** Depends: R002/R021. Files in verified website repo plus release manifest schema. Primary CTA, immutable asset URL, requirements/version/size, guide/privacy/notes and safe unsupported-platform copy. Evidence: staging page and manifest-contract tests; no auth/source ZIP/donation detour.
- [ ] **R023 — Verify staging through installation.** Depends: R015/R021/R022. Browser-download exact file, check hash/signature, install on clean Windows, verify About/running EXE/receipt, first pin, Save/Enable, upgrade and uninstall. Evidence: end-to-end staging receipt. This must use the downloaded signed installer, not a local lookalike.

### Qualification and promotion — G8

- [ ] **R024 — Complete supported hardware matrix.** Depends: R011/R018/R023. Fill every declared supported OS/GPU/display/session row; record exclusions accurately. Evidence: exact signed candidate runtime matrix. Unknown support is not PASS.
- [ ] **R025 — Complete formative usability.** Depends: R017/R023 and tester authority. Follow original 12–20 consenting-adult protocol and ≥90% unassisted critical-task target; track confusion, noticeability, annoyance and restoration separately. Evidence: privacy-safe aggregate results and resolved serious usability defects. No clinical interpretation.
- [ ] **R026 — Complete fourteen nightly sessions.** Depends: R023/R024 and test-machine consent. Log dated actual sessions, candidate identity, scheduled/applied behavior, sleep/wake, observed issues and safe recovery. Evidence: fourteen qualifying sessions under the original protocol. Do not count timestamp simulation as a session.
- [ ] **R027 — Run the candidate gate and release review.** Depends: R001–R026. Implement the fail-closed contract in section F, validate evidence and exact candidate binding, rerun automated checks after the final merge/source freeze. Evidence: machine-readable HOLD or READY_FOR_APPROVAL receipt; no unexplained high/critical defects.
- [ ] **R028 — Obtain exact promotion approval.** Depends: R027. Present exact version, revision, signed installer hash, known limitations and withdrawal plan. Record authority without secrets. Approval of planning or a prior build is not approval of arbitrary later bytes.
- [ ] **R029 — Promote and independently verify live.** Depends: R028. Publish verified assets before manifest/CTA, then use a clean browser context to download and install the live file and execute critical journeys. Evidence: live URL, downloaded/installed identities, signature and native result. Label RELEASE_VERIFIED only after these pass.
- [ ] **R030 — Deliver final receipt and recovery handoff.** Depends: R029. Update current documentation and project log with shipped identity, guide, supported matrix, known limits, removal/recovery instructions and evidence links. Verify rollback/withdrawal access. Configure ongoing checks only if separately authorized; do not silently introduce telemetry or automations.

## E. Coverage map and revalidation

| Requirement | Tasks |
|---|---|
| FR-001–004: owner, truthful state, Save, Off | R003–R006, R011 |
| FR-005–008: endpoints, transitions, catch-up, overrides | R009–R010 |
| FR-009–010: onboarding, guide, access tips | R017, R025 |
| FR-011–013: layout, materials, accessibility | R016–R018 |
| FR-014–016: time/lifecycle, conflicts, migration | R007–R011 |
| FR-017–020: signed installation, download, identity, lifecycle | R012–R015, R020–R023, R029 |
| NFR-001: test/build isolation | R012, R019–R020 |
| NFR-002: measured performance | R018 |
| NFR-003–004: privacy, redacted diagnostics | R008–R009, R017, R025 |
| NFR-005: evidence-based support/claims | R011, R024–R026 |
| NFR-006: test-first traceability | R001, R019, R027 |
| Audit 1–7 | R022–R023; R007–R008; R013/R015; R014; R004–R005; R021; R003/R019 respectively |

Every original T-task gets an explicit evidence link, superseding R-task or documented still-open status in R001. This table is coverage routing, not proof of completion.

Any runtime/policy/config/backend/installer change creates a new candidate identity and invalidates dependent evidence. Always rerun automated gates and critical downloaded-install flows. Restart affected physical/soak qualification for material behavior changes. Cosmetic-only changes still rerun affected UI/accessibility/usability checks; retaining unrelated prior evidence requires a written change-impact justification and exact source/payload hashes. No automatic inheritance of PASS. Signing timestamps/packaging-only differences may retain behavior evidence only when payload identity and relevant install tests justify it.

## F. Fail-closed final release gate

Implement a proposed `verify_public_release.py` plus versioned JSON schema and negative tests. Do not simply parse checked Markdown boxes. Each evidence item must identify candidate, source revision, environment, required case IDs, timestamps, observed results and artifact hashes. Verify files exist and their hashes match; validate nested test counts and required-case coverage. Human-observed hardware/usability/soak results require an explicit assessor and procedure, not fabricated automated proof. A manifest is an index of evidence, not independent proof that the observations occurred.

Required fields: `schema_version`, `candidate_id`, `product_version`, `source_revision`, `payload_manifest_sha256`, `installer_sha256`, `signature_evidence`, `requirements`, `task_results`, `test_runs`, `hardware_rows`, `usability_result`, `night_sessions`, `open_defects`, `staging_receipt`, `approval`, and `live_receipt`.

State progression:

`HOLD → READY_FOR_APPROVAL → APPROVED_FOR_PROMOTION → RELEASE_VERIFIED`

The candidate checker emits READY_FOR_APPROVAL only if all prepublication R001–R027 requirements are satisfied, signatures and identities agree, critical/high defects are zero, required cases have no failures/skips/blockers, fourteen valid nightly sessions and the original usability target are evidenced, and staging verification used the exact final installer. Noncritical defects require documented disposition and must not violate mandatory requirements. Invalid/missing/foreign-candidate evidence produces HOLD and a nonzero exit code. Negative tests cover missing files, forged status-only PASS, incorrect hashes, stale revisions, duplicate session IDs, skipped required tests and unresolved defects.

A separate promotion check requires explicit exact-artifact approval. A separate live check requires the approved artifact to match public downloaded bytes and installed state; website-only deployment cannot produce RELEASE_VERIFIED. Production promotion must fail if the candidate changes after approval. Never accept `--force`/`--ignore-failures` for public release. Private development packaging may remain available through a visibly separate non-release command.

Release jobs use least-privilege credentials, protected approval boundaries and immutable versioned assets. A local JSON file cannot itself grant publication authority. Avoid private credential values, personal paths and raw user data in public receipts.

## G. Exit, failure and handoff behavior

At the end of each work period, leave the task ledger current with last passed test, next safe task and exact blocker. Continue independent work without repeatedly requesting intermediate plan approval. When external access or a material product choice is the only remaining blocker, report it plainly and stop rather than inventing authority.

If live verification fails, release remains HOLD/not verified: stop promotion, withdraw the faulty CTA/asset or restore the last qualified new-UI release under the approved recovery procedure, preserve evidence and open a blocking defect. No old-UI resurrection. A new fix requires a new candidate and revalidation.

Final completion message must state public URL, version and source revision, downloaded installer hash/signature verification, installed runtime confirmation, passed scope and known limitations. If any of those is unproven, say precisely what remains; never replace them with “perfect,” “all done,” or a readiness percentage.
