# Night Light: Smart Comfort and Direct Download

Date: 2026-09-09. Status: detailed specification; implementation and release pending.

## Product contract

A free, local-first Windows 11 screen-control utility that responds immediately, changes appearance gently, explains its behavior, and is easy to download, install, reverse and remove. It does not measure sleep, circadian phase, melatonin, calibrated screen temperature or light exposure at the eye.

This specification refines [the product evidence review](../../docs/PRODUCT_RESEARCH_AND_ROADMAP_2026-09-09.md). One Smart controller replaces a growing collection of profiles. Timing, comfort limits and transient catch-up remain separate. Existing installation receipts are historical, not certification of this feature.

## Required scope

State correctness; sunset/personal timing; independent endpoints; reversible preview; clear feedback; accessible premium appearance; offline guide; user-controlled Windows integration; migration; signed installer; direct website download; upgrade/rollback/removal; supported-configuration tests; formative comfort comparison; fourteen actual nightly soak sessions on the candidate.

Deferred: new routine-suggestion collection, physiological personalization, optical calibration, sleep studies, hardware brightness, per-monitor transforms, ambient sensors, non-Windows apps, automatic updater service, cloud accounts and telemetry. Existing learning receives explicit migration treatment, not hidden authority over the new schedule.

This is planning authorization, not permission to change the running display, install, purchase signing, upload releases or deploy the website.

## User stories

### US1 — I know what happened and can always turn it off (P1)

Save is atomic, versioned and idempotent. Pending, saved, rejected and unconfirmed are distinct. A timeout queries state before retrying. Off persists, cancels transient work and promptly requests neutral. Stale replies cannot undo it. Backend uncertainty is never presented as active filtering. Only the owner process writes the display.

### US2 — Smart fits my evening without a maze of settings (P1)

Two setup sections: Timing and Appearance. Personal timing explicitly includes evening ready time and morning neutral time. Sunset is the preselected convenience choice; personal timing needs no location. Show actual dated times. Normal and catch-up use one controller, hard comfort-rate ceilings and soft deadlines. Warmth and dimming are independent. Smart slider edits are temporary unless explicitly saved as the nightly preference.

### US3 — Setup teaches me enough, then gets out of the way (P1)

First run is neutral and skippable. Manual needs no location/account/tracking. Preview has Keep, Restore, Escape, timeout and native cleanup. Optional taskbar-pinning and autostart tips follow setup; neither is silently enabled. Every essential control has brief accessible help. Guide and troubleshooting remain available offline.

### US4 — It is coherent, readable and customizable (P1)

A compact continuous-surface flyout opens expanded preferences. Glass, Frosted and Solid change the whole material system. Preserve existing Ceramic as a legacy finish. Each color property has its own filled labelled presets, custom input, selection and reset; light/dark stay independent. Background changes affect the canvas. Keyboard, screen readers, forced colors, reduced motion, opacity fallback, large text and mixed DPI are release gates. Theme changes never change display filtering.

### US5 — Real Windows events remain predictable (P1)

Explicit pause/manual/compare semantics; no suspended-time fade jump. Personal timing follows the PC zone; solar uses saved coordinates. Missing/polar events use an explicit fallback or neutral guidance. Windows Night Light on/unknown prevents HT filtering, without automatic takeover. Migration preserves consent and preferences, offering review when timing changes materially. Unsupported configurations fail visibly rather than receiving universal-support claims.

### US6 — I download the correct app directly from the site (P1)

One primary signed Windows installer, not a source ZIP or repository detour. Requirements, version, size, notes, privacy, instructions and verification accompany the CTA. Installer uses a stable per-user entry, handles WebView2 and creates an uninstaller. Optional startup/desktop shortcuts need consent. Website, manifest, downloaded bytes, installed About and launched executable agree. Upgrade/rollback/removal are tested; no account or donation gate.

## Requirement index

| ID | Required behavior | Story |
|---|---|---|
| FR-001 | One reducer and authorized display writer | US1 |
| FR-002 | Separate intent, trajectory, accepted output and availability | US1 |
| FR-003 | Atomic correlated Save and timeout reconciliation | US1 |
| FR-004 | Persistent Off and deterministic recovery | US1 |
| FR-005 | Independent timing, warmth and dimming | US2 |
| FR-006 | Bounded smooth transitions, no repeated ease restart | US2 |
| FR-007 | Temporary catch-up and honest ETA | US2 |
| FR-008 | Temporary override versus saved nightly preference | US2 |
| FR-009 | Skippable setup and reversible preview | US3 |
| FR-010 | Offline guide, access tips and pin instructions | US3 |
| FR-011 | Coherent responsive native-hosted layout | US4 |
| FR-012 | Distinct materials and independent color presets | US4 |
| FR-013 | Accessible keyboard, assistive and scaled display behavior | US4 |
| FR-014 | DST, travel, solar fallback and lifecycle policy | US5 |
| FR-015 | Conflict handling without automatic takeover | US5 |
| FR-016 | Versioned reversible migration, no expanded tracking consent | US5 |
| FR-017 | Signed per-user installer and WebView2 path | US6 |
| FR-018 | Direct site link and one release manifest | US6 |
| FR-019 | Exact downloaded/installed/released proof | US6 |
| FR-020 | Upgrade, uninstall and rollback | US6 |

## Non-functional requirements

- NFR-001: tests/builds never touch real display, taskbar, startup, config or credentials; use fake backend and isolated paths.
- NFR-002: performance budgets in plan.md are prospective targets, measured with declared hardware and whole process tree.
- NFR-003: no account, recurring lookup or behavior upload. Explicit location lookup and updates/downloads are disclosed separately.
- NFR-004: diagnostic exports omit credentials, raw activity and unnecessary personal data by default.
- NFR-005: supported configurations derive from evidence; optical/health claims have separate gates.
- NFR-006: test-first implementation and requirement-to-test traceability are required.

## Governance

Before runtime implementation, amend constitution v1.0.0 to v1.1.0: sunset stays the default convenience; explicitly selected personal timing is authoritative; inferred routines cannot directly change output; legacy learning requires informed migration. Safety, truth, privacy, isolation and free core remain unchanged. The rationale and migration are in research.md. This document does not silently rewrite prior records.

See [plan.md](plan.md), [data-model.md](data-model.md), [UI contract](contracts/ui-and-commands.md), [distribution contract](contracts/distribution.md), [tasks.md](tasks.md) and [quickstart.md](quickstart.md) for executable detail. External signing/hosting access and physical hardware are execution dependencies, not unresolved product-design decisions.
