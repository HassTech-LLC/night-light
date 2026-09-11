# Night Light by HT Constitution

## Core Principles

### I. Neutral Display Is Always Recoverable

Every display-changing path MUST have a deterministic, tested route back to an identity color matrix and normal brightness. Startup, shutdown, crash recovery, suspend/resume, monitor hot-plug, and failed helper processes MUST NOT leave the user trapped in an altered display state.

### II. One Warmth Pipeline, Visible Truth

Night Light by HT MUST NOT layer its warmth transform over Windows Night Light. The UI, tray tooltip, and Jump List MUST distinguish configured state from effective state and MUST surface unknown native state rather than guessing.

### III. Health Claims Follow Measurement

Color temperature, RGB factors, screenshots, and user perception are not substitutes for melanopic measurement or clinical outcomes. Product wording MUST describe verified output behavior. Claims about melatonin, circadian treatment, or improved sleep require appropriately designed optical and human validation.

### IV. Local-First Privacy

The application MUST work without an account. Location is coarse and stored locally. Adaptive timing MUST never collect screen content, application names, window titles, URLs, or keystrokes. Any network lookup MUST be explicit, minimal, documented, and replaceable.

### V. Tests Cannot Touch the User's Real State

Automated tests MUST disable the physical display backend and redirect persistent configuration to an isolated temporary directory. Real-machine display tests are separate, explicit procedures with neutral-state cleanup and evidence.

### VI. Small, Understandable Windows Integration

Unsupported Windows behavior MUST be isolated behind a narrow adapter and fail safely. Helper executables MUST be reproducible from committed source. Build, test, and packaging commands MUST avoid modifying the current user's taskbar, registry, or display unless an explicit flag requests it.

## Product and Release Constraints

- Windows 11 is the initial supported platform.
- The public name is **Night Light by HT**; internal legacy identifiers may remain only when needed for upgrade compatibility.
- Sunset is the default convenience schedule. An explicitly chosen personal schedule is authoritative. Smart follows user-confirmed comfort limits; inferred routines cannot directly change the v2 schedule or display output. No new collection or expanded consent is implied by upgrading. A clearly labelled legacy adapter may retain previously consented behavior until the user chooses migration, without new data sources or extended retention.
- Generated binaries, personal settings, test residue, precise location, and secrets are not committed.
- An unsigned development bundle is not described as a production release.

## Development Workflow

1. Read the project Obsidian context and current feature specification.
2. Add or update pure tests before integrating a display-changing behavior.
3. Run the isolated unit suite.
4. Run the side-effect-free build.
5. Perform explicit real-machine validation only when authorized and restore neutral state afterward.
6. Record durable decisions, verification, and remaining boundaries in the project vault.

## Governance

This constitution governs repository changes. Amendments require an explicit rationale, version increment, migration impact, and updates to the corresponding project-vault decision. Safety, truth, and privacy principles cannot be waived by a convenience feature.

### Amendment 1.1.0

The approved Smart Comfort implementation separates convenience scheduling from health claims and gives explicit user preferences authority over inference. Existing users must choose migration before a materially different automatic schedule replaces their current one. The narrow legacy adapter exception preserves already-consented behavior without expanding collection. Neutral recovery, truthful status, isolated tests and privacy requirements are unchanged.

**Version**: 1.1.0 | **Ratified**: 2026-09-08 | **Last Amended**: 2026-09-09
