# Signed stable completion plan

Date: 2026-09-14. Source revision at writing: `2efeafe` (0.2.1 unsigned Early Access).
Companion to [Public release execution contract](../specs/002-smart-comfort-completion/PUBLIC_RELEASE_EXECUTION_CONTRACT.md), whose R-series tasks remain the audit-closure checklist. This document sequences the open R-tasks into tracks, names what unblocks each, and states what can run in parallel. It adds no new product direction.

## Where the product stands

| Item | State on 2026-09-14 |
|---|---|
| Public source | `main` at `2efeafe`; CI green on unsigned build, SBOM, checksums |
| Detector | Structural Bond CompactBinary parser; verified against published ON/OFF fixtures and this host's live OFF payload. Paired live ON capture on build 26200 still missing |
| Installed app | 0.2.1 replaced through the journaled installer on the developer host; silent `/S` verified |
| Website | 0.2.0 file live; 0.2.1 staged on site branch `release/night-light-0.2.1-early-access`, awaiting deploy approval |
| Signing | None. SignPath's free OSS programme requires an OSI-approved licence; PolyForm Noncommercial is not OSI-approved, so the "free open-source signing" note on the site is not currently achievable |
| Contract gates | FR-013, FR-017, FR-018, NFR-002, NFR-005 BLOCKED; FR-009, FR-010, FR-020 IN_PROGRESS (from `candidate-0.2.0-local2/release-requirements.json`) |

## Critical path

The signing decision is the long pole, and fourteen real nights cannot start until a signed staging candidate exists (R026 depends on R023). Minimum calendar from today is therefore roughly: signing lead time plus fourteen nights plus a promotion review, or about five to seven weeks if enrolment starts this week. Everything else fits inside that window.

```
week 0   Track 0 (Early Access refresh)  ─┐
week 0   Track A enrol signing            ─┼─ parallel
week 0-1 Track B disposable Windows       ─┤
week 1-2 Track C display hardware         ─┤
week 2   Track D accessibility/perf       ─┘
week 2-3 Track A cert issued → R020/R021 signed candidate → R022/R023 staging
week 3-5 Track E fourteen nights on the signed candidate; usability sessions alongside
week 5+  R027 gate, R028 approval, R029 promote, R030 handoff
```

## Track 0 — Close out the Early Access refresh (this week)

| Step | Owner | Unblocks | Evidence |
|---|---|---|---|
| Turn Windows Night Light on, run the read-only detector check, turn it off, run again. Record both payloads as fixtures | Hassan (ten seconds) | Closes the last unverified safety claim in R011 | `test_windows_nightlight.py` fixtures; vault pending item |
| Approve deploy of site branch `release/night-light-0.2.1-early-access` | Hassan | Public users stop receiving the byte-18 detector and the Ctrl+Shift+N hotkey | Site CI run; live download hash equals `9bbcd32d…c868` |
| After deploy: clean-browser download, hash check, silent install on a spare account | Claude | R029-style live verification for Early Access | `audit/public-release/candidate-0.2.1/live/` |
| Remove stale `Desktop\Projects\Night Light` extract and `%LOCALAPPDATA%\Programs\Night Light\rollback` | Hassan (tool policy blocks agent deletes) | Housekeeping only | none |

## Track A — Code signing (R021)

Decision first, then enrolment, then CI wiring. The CI workflow already contains a "Require owner signing identity and sign tagged release PEs" step, so the mechanics exist; what is missing is the identity.

| Option | Cost and lead time | Fit |
|---|---|---|
| Azure Trusted Signing (public trust) | About US$10/month; organisation validation typically one to two weeks; no hardware token; CI-friendly | Recommended. HassTech LLC is a registered entity, which is the validation requirement |
| OV Authenticode certificate from a CA | US$200–400/year; hardware token or cloud HSM required since 2023; days to issue | Works, but the token complicates CI |
| SignPath Foundation (free OSS) | Free | Not eligible under PolyForm Noncommercial; would require relicensing |
| EV certificate | US$300–600/year | Immediate SmartScreen reputation, but same token constraints; not needed at this scale |

Steps: choose and enrol (Hassan, needs the LLC's legal details); create the signing account and a CI credential with least privilege (Hassan); wire `signtool` with RFC 3161 timestamping into the tagged-release job and verify the four PEs plus the setup with `Get-AuthenticodeSignature` (Claude); update the site note about signing to reflect the actual route (Claude); record custodian and rotation in the vault without secrets.

Exit: a tagged CI run produces a signed, timestamped `NightLightSetup-<version>.exe` whose hash is recorded in `SETUP-BUILD.json`, and the `signed` manifest field can be set true honestly.

## Track B — Disposable Windows lifecycle (R012–R015, R023)

Needs: Hyper-V or VirtualBox with a Windows 11 evaluation image, snapshot capability, a second local user. Runs in parallel with Track A.

Matrix, each row from a fresh snapshot with evidence under `audit/public-release/candidate-0.2.1/installer/`:

1. Clean install of the live 0.2.1 file, first pin, Save and enable Smart, uninstall; inventory before and after.
2. Upgrade from the live 0.2.0 file to 0.2.1; preferences and pins preserved.
3. Interrupted upgrade at each journal phase using `upgrade.ps1 -TestFailurePoint` with `NIGHT_LIGHT_INSTALL_TEST_MODE=1` and the isolated test root; rerun recovers twice without divergence.
4. Process kill mid-copy and abrupt VM power-off mid-transaction; next run recovers.
5. Missing WebView2 runtime; setup stops without changing the app and links to Microsoft.
6. Second user on the same machine; IPC endpoint ownership and config isolation.
7. Same-version repair, stale legacy pin from the Antigravity prototype, disk-full during commit.

Exit: one current usable installation or an explicit recoverable no-install in every row; no orphan launchable payload.

## Track C — Display hardware (R011, R024)

Needs: a second monitor, an HDR-capable display, and physical access. Do the paired Windows Night Light capture from Track 0 first; it is the cheapest row and the most important one.

Rows: Windows Night Light on/off/unknown transitions while HT is active; an external Magnification writer (any colour tool) to confirm `external_conflict` latching and the retry path; two monitors with mixed DPI; HDR on and off; sleep/wake; Explorer restart; Remote Desktop session; display topology change with the filter on. Record GPU, driver, Windows build, and WebView2 version per row.

Exit: the supported-hardware table on the site lists only rows with receipts; everything else is stated as untested.

## Track D — Accessibility and performance (R018)

Needs: NVDA (free) and Narrator; 125/150/200 % scaling; a stopwatch.

Rows: keyboard-only traversal of the controls window with visible focus order; NVDA and Narrator announcements for mode, warmth, dimming, Save state and the display status line; Windows high contrast (Smart must stop and say so); reduced motion; large text. Performance: cold and warm open p95 over ten samples, Save latency, process-tree memory at start and after eight hours resident.

Exit: defects filed and closed, raw samples committed under `qualification/`.

## Track E — Usability and fourteen nights (R025, R026)

Both are calendar-bound and both need the signed staging candidate from Track A, so they start in week three at the earliest.

Usability: twelve to twenty consenting adults, unassisted critical tasks at or above ninety percent, confusion and noticeability tracked separately, no clinical interpretation.

Soak: fourteen dated real nights on a consenting test machine, logging candidate identity, schedule, applied output, overrides, sleep/wake, and any recovery. Simulated timestamps do not count.

## Track F — Distribution hygiene (R022, R029, R030)

The installer is currently committed into the site repository as a 21 MB binary per release. Two releases in, that is already 43 MB of history that can never be removed without rewriting. Move release bytes to GitHub Releases on `HassTech-LLC/night-light` (or R2) and have the site manifest point at that immutable URL; keep `check-night-light-release.mjs` verifying size and hash against the fetched file. Do this before the signed release so the signed bytes never enter git.

Promotion: R027 gate receipt, R028 exact-artifact approval by Hassan, R029 clean-browser live verification, R030 vault and documentation handoff with the shipped identity and withdrawal plan.

## Standing housekeeping surfaced by the 2026-09-14 audit

- Graphify semantic extraction fails because the configured backend is a local Ollama endpoint that is not running; code indexing works. Set an LLM key or start the backend so docs and specs enter the graph.
- The archived Desktop extract and the install-root `rollback` folder are yours to delete; agent tooling refuses recursive deletes there.
- Keep the vault's ledger and pending items in step with this plan; the R-series contract remains the source of truth for task status.
