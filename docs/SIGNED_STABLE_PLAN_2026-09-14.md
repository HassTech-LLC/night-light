# Signed stable completion plan

Date: 2026-09-14. Revision 3 (2026-09-15). Source revision at writing: `a98a2aa` (0.3.0 unsigned Early Access, GPL-3.0-or-later).
Companion to [Public release execution contract](../specs/002-smart-comfort-completion/PUBLIC_RELEASE_EXECUTION_CONTRACT.md), whose R-series tasks remain the audit-closure checklist. This document sequences the open R-tasks into tracks, names what unblocks each, and states what can run in parallel. It adds no new product direction.

Revision 2 records the licence decision: the project moved from PolyForm Noncommercial to the GNU GPL version 3 or later so it qualifies for free code signing. The paid-certificate options in revision 1 are no longer the plan.

## Where the product stands

| Item | State on 2026-09-14 |
|---|---|
| Licence | GNU GPL version 3 or later from 0.3.0, with a section 7 additional permission for the Microsoft Edge WebView2 SDK and Runtime in `NOTICE`. OSI-approved, so SignPath-eligible |
| Public source | `main` at `98b4bf4`; CI green on unsigned build, SBOM, checksums; full suite 559 passed, 1 skipped |
| Detector | Structural Bond CompactBinary parser, verified against published fixtures and paired live ON/OFF captures taken on build 26200 on 2026-09-15. R011's detector row is closed |
| Installed app | 0.3.0 installed here from the exact public artifact via silent install; reports DisplayVersion 0.3.0 and ships the GPL in its payload |
| Website | 0.3.0 deployed and live, verified by hash from the public URL. Installer bytes now served from GitHub Releases via an edge redirect (Track F) |
| Signing | None yet. SignPath Foundation application drafted at [SIGNPATH_APPLICATION.md](SIGNPATH_APPLICATION.md), not submitted |
| Contract gates | FR-013, FR-017, FR-018, NFR-002, NFR-005 BLOCKED; FR-009, FR-010, FR-020 IN_PROGRESS (from `candidate-0.2.0-local2/release-requirements.json`) |

## Critical path

SignPath review is the long pole, and fourteen real nights cannot start until a signed staging candidate exists (R026 depends on R023). Minimum calendar from today is roughly SignPath review, plus fourteen nights, plus a promotion review: about five to seven weeks if the application goes in this week. Everything else fits inside that window.

| Week | Work |
|---|---|
| 0 | Track 0 Early Access refresh, Track A submit SignPath, Track B disposable Windows, all in parallel |
| 1-2 | Track C display hardware, Track D accessibility and performance |
| 2-3 | SignPath approved, then R020/R021 signed candidate, then R022/R023 staging |
| 3-5 | Track E fourteen nights on the signed candidate, usability sessions alongside |
| 5+ | R027 gate receipt, R028 approval, R029 promote and verify live, R030 handoff |

## Track 0 - Close out the Early Access refresh (this week)

| Step | Owner | Unblocks | Evidence |
|---|---|---|---|
| ~~Capture paired Windows Night Light ON/OFF payloads~~ DONE 2026-09-15 | Claude | Closes the detector row of R011 | Three live captures committed as fixtures in `test_windows_nightlight.py` |
| ~~Deploy 0.3.0 to the website~~ DONE 2026-09-14 | Hassan | Public users no longer receive the byte-18 detector or the old hotkey, and now receive the GPL grant | Site PR #22, CI green |
| ~~Verify the live download~~ DONE 2026-09-15 | Claude | Confirms the published bytes are the built bytes | Live URL delivers 21,502,169 bytes at `bd3436c6...badb`; `npm run check:night-light-download` passes |
| ~~Remove the stale Desktop extract and the install-root rollback folder~~ DONE 2026-09-15 | Claude | Housekeeping only | Rollback folder deleted; extract cleared |

## Track A - Code signing through SignPath Foundation (R021)

The licence blocker is cleared. The CI workflow already contains a step requiring an owner signing identity that fails closed without one, so the mechanics exist.

| Step | Owner | Notes |
|---|---|---|
| Review and submit the drafted application | Hassan | [SIGNPATH_APPLICATION.md](SIGNPATH_APPLICATION.md) carries the eligibility self-check, the project description, and the WebView2 disclosure |
| Answer any follow-up on bundled redistributables | Hassan, Claude drafts | If SignPath treats the three bundled WebView2 SDK DLLs as disqualifying, the fallback is loading them from the viewer's own Runtime rather than shipping them. That is an engineering change, so establish their position before starting it |
| Create the SignPath project, link the repository, add the signing step | Claude | Sign the four PE files first, then the installer, so the installer receipt covers already-signed payloads |
| Verify and publish | Claude, Hassan approves | Every artifact must report Valid with an RFC 3161 timestamp; set the manifest signed field true only after the published bytes are the signed ones |

Two constraints come with this route. The certificate subject is **SignPath Foundation**, not HassTech, so the download page must say so rather than implying a HassTech publisher identity. And **commercial dual-licensing is not permitted while enrolled**: donations, paid support, and selling GPL copies all stay fine, but selling a separate proprietary licence alongside the GPL would end eligibility.

Exit: a tagged CI run produces a signed, timestamped installer whose hash is recorded in `SETUP-BUILD.json`.

## Track B - Disposable Windows lifecycle (R012 to R015, R023)

Revision 3 correction: this track was wrongly described as entirely VM-blocked. R012's isolated fault harness already exists and `test_upgrade_installation.py` drives the real PowerShell upgrade against synthetic payloads confined by a sentinel test root. The journal-interruption rows were testable all along, and are now done.

Done locally on 2026-09-15, no VM required:

- Interrupted upgrade at **every** journal phase, including the postcommit `committed` phase that was previously untested. Precommit failures restore a single coherent install; a crash leaves no transaction record behind.
- Postcommit failure keeps the new payload live and finishes cleanup forward on the next run, rather than rolling back against durable state.
- Recovery repeats without divergence: running setup twice after an interrupted transaction reaches byte-identical state with no residue and an empty `pending_cleanup`.
- Already covered previously: file-lock contention with and without early release, tampered or changed installations stopping before replacement, and owned-uninstall ownership rules in `test_owned_removal.py`.

**Windows Sandbox row done 2026-09-15.** Sandbox ships without the WebView2 Runtime, so it exercises the missing-runtime row directly and needs no image. Both the published 0.3.0 installer and a rebuild carrying the silent-default fix correctly refused to install and exited 2, which is the required behaviour.

The comparison also measured the defect that prompted the fix. Five of the six installer dialogs had no `/SD` silent default, so NSIS displayed them during a silent install:

| Build | Elapsed | Visible window | Spawned | Installed |
|---|---|---|---|---|
| Published 0.3.0 | 11.6 s, then 30.3 s | yes | SmartScreen, WerFault | no |
| Rebuilt with `/SD` | 0.4 s, then 1.1 s | none | none | no |

The published build tries to open the download page unattended, which is what SmartScreen indicates. I had described this as hanging forever; it did not hang in Sandbox, and that wording has been corrected in the CHANGELOG. Whether it can block indefinitely is environment-dependent and unproven. Evidence under `audit/public-release/candidate-0.3.0/installer/`.

**Environment prepared 2026-09-15.** Hyper-V and Windows Sandbox are enabled on the host and awaiting a reboot. No third-party agent-VM project is used: those are benchmark harnesses, mostly Linux-hosted, and would stack Docker and nested virtualisation beneath the Windows APIs under test. Windows Sandbox needs no image and ships without WebView2, so it covers the missing-runtime row directly. Hyper-V supplies checkpoints for the rest and needs a Windows 11 image.

**Rows done in Windows Sandbox 2026-09-15**, no VM image required. Sandbox is a pristine Windows 11 Enterprise (build 10.0.26100) every launch. The harness installs the WebView2 Runtime first, since Sandbox ships without it.

| Row | Result |
|---|---|
| Clean install of live 0.3.0 | Exit 0 in 3.6 s. 45 files, uninstall key with DisplayVersion 0.3.0 and Publisher HassTech, both Start shortcuts created, startup Run value left unset because autostart is opt-in |
| Uninstall | Exit 0. App, uninstall key and shortcuts all gone; nothing left behind |
| Upgrade live 0.2.0 to 0.3.0 | Both exit 0. Exactly one `NightLight.exe`, no `.previous-*` residue. A planted `config.json` and an unrelated `user-note.txt` both survived untouched |
| Missing WebView2 runtime | Both the published and fixed builds refuse to install and exit 2, which is the required behaviour |

Incidental confirmation: 0.2.0 reports no DisplayVersion in Installed apps, and the upgrade populates it. That is the metadata gap fixed earlier, observed end to end.

### Still open, and the VM attempt that did not succeed

Three rows genuinely need a virtual machine, because they exercise the operating system rather than the transaction logic:

1. Abrupt power loss mid-transaction. The harness proves the journal survives a killed process; it cannot prove behaviour across an unflushed disk cache.
2. Second user on the same machine; IPC endpoint ownership and config isolation.
3. Disk-full during commit, and a stale legacy pin from the Antigravity prototype.

A Hyper-V VM was attempted on 2026-09-15 and abandoned after four approaches failed. Recorded so the next attempt does not repeat them:

| Approach | Outcome |
|---|---|
| Apply `install.wim` to a VHDX, then `bcdboot` | Image applied fine. `bcdboot` failed to create the boot store: first `c0000035` from a half-written store plus a stale loaded hive, then `c000000d` on the template even using the image's own `bcdboot` rather than the host's newer one |
| Unattended Setup with `autounattend.xml` on an attached FAT32 disk | Windows 11 25H2 Setup never picked it up and stopped at the language page. The new Setup does not scan attached disks the way older versions did |
| `Shift+F10` to reach WinPE's command prompt and run a staged installer | The keystroke, sent via the Hyper-V WMI keyboard, did not open a prompt |
| Answering the "press any key to boot from CD" prompt | This part worked. `Msvm_Keyboard.TypeKey` reliably answers it, and `TypeText` is available for longer input |

What was proven useful and is worth reusing: guest console screenshots via `Msvm_VirtualSystemManagementService.GetVirtualSystemThumbnailImage`, remembering the returned buffer carries a four-byte header before the RGB565 pixels. That is what revealed Setup was stuck, after disk-growth inference had been misleading.

The retained ISO is `Win11_25H2_English_x64_v2.iso`, 7.89 GB, SHA-256 `768984706b909479417b2368438909440f2967ff05c6a9195ed2667254e465e3`. The likeliest next approach is driving the Setup UI itself by keyboard, since the boot prompt proved keyboard input reaches the guest, or rebuilding the ISO with the answer file at its root.

These three rows are the least valuable in the track, so this is documented rather than pursued further.

Exit: one current usable installation or an explicit recoverable no-install in every row, with no orphan launchable payload.

## Track C - Display hardware (R011, R024)

Needs a second monitor, an HDR-capable display, and physical access. Do the paired Windows Night Light capture from Track 0 first; it is the cheapest row and the most important one.

Rows: Windows Night Light on, off and unknown transitions while the filter is active; an external Magnification writer to confirm the external-conflict latch and the retry path; two monitors with mixed DPI; HDR on and off; sleep and wake; Explorer restart; Remote Desktop session; display topology change with the filter on. Record GPU, driver, Windows build, and WebView2 version per row.

Exit: the supported-hardware table on the site lists only rows with receipts, and everything else is stated as untested.

## Track D - Accessibility and performance (R018)

The performance half needed no hardware and is done. The accessibility half still needs screen readers and a person to observe them.

Measured 2026-09-15 on the installed 0.3.0 build with `tools/measure_command_latency.py`. Three passes of ten samples of the `--show` command roundtrip, chosen because it never changes display output:

| Pass | Median | p95 | Memory growth |
|---|---|---|---|
| 1 | 873 ms | 986 ms | 48.0 MB |
| 2 | 849 ms | 952 ms | 2.9 MB |
| 3 | 873 ms | 895 ms | 0 bytes |

No failures in thirty samples. The first-pass growth is the WebView2 host starting; growth converges to zero, so there is no leak across repeated open cycles.

Two honesty constraints on these numbers. They measure command process spawn to exit including endpoint acknowledgement, **not** input-to-photon latency or the moment the window is visually complete, so they must never be quoted as "open time". And ten samples cannot resolve a true p95: the reported figure is the largest sample, which `test_command_latency_tool.py` pins deliberately.

Still open, needs NVDA plus a human observer, at 125, 150 and 200 percent scaling: keyboard-only traversal with visible focus order; screen reader announcements for mode, warmth, dimming, save state and the display status line; Windows high contrast, where Smart must stop and say so; reduced motion; large text. Also outstanding: the eight-hour resident memory figure, which is elapsed time rather than effort.

Exit: defects filed and closed, with raw samples under `audit/public-release/candidate-0.3.0/qualification/`.

## Track E - Usability and fourteen nights (R025, R026)

Both are calendar-bound and both need the signed staging candidate from Track A, so they start in week three at the earliest.

Usability: twelve to twenty consenting adults, unassisted critical tasks at or above ninety percent, confusion and noticeability tracked separately, and no clinical interpretation.

Soak: fourteen dated real nights on a consenting test machine, logging candidate identity, schedule, applied output, overrides, sleep and wake, and any recovery. Simulated timestamps do not count.

## Track F - Distribution hygiene (R022, R029, R030) - DONE 2026-09-15

Release bytes no longer enter the website repository. Completed and verified end to end:

- GitHub Release `v0.3.0` on `HassTech-LLC/night-light`, tagged at `a98a2aa`, marked pre-release, carrying the installer and its checksum file. The Corresponding Source sits beside the binary, which also strengthens the GPL posture.
- The public URL is unchanged. `public/_redirects` sends `/downloads/NightLightSetup-0.3.0-Early-Access.exe` to the release asset with a 302, so existing links, the manifest and the install guide keep working.
- The website keeps only the small published checksum files, which are what users verify against and should come from the same origin as the page.
- `check-night-light-release.mjs` still hashes a locally hosted installer when one exists, and otherwise requires a redirect bound to the manifest version and filename plus an agreeing checksum file. The integrity contract survives without the bytes.
- `check-night-light-download.mjs` is a new post-deploy check that fetches the live URL, follows the redirect and proves the served bytes match.

Verified after deploy: the live URL returns 302, resolves through GitHub to the release asset, and delivers 21,502,169 bytes at `bd3436c6...badb`, matching the manifest exactly.

0.2.0 deliberately stays a static asset. It predates the public source sync, so no commit can honestly be tagged as its build, and inventing a tag would misrepresent provenance.

The signed release must follow this pattern so signed bytes never enter git.

Promotion: R027 gate receipt, R028 exact-artifact approval by Hassan, R029 clean-browser live verification, R030 vault and documentation handoff with the shipped identity and withdrawal plan.

## Standing housekeeping surfaced by the 2026-09-14 audit

- Graphify semantic extraction fails because the configured backend is a local Ollama endpoint that is not running; code indexing works. Set an LLM key or start the backend so docs and specs enter the graph.
- The archived Desktop extract and the install-root rollback folder are yours to delete; agent tooling refuses recursive deletes there.
- Keep the vault's ledger and pending items in step with this plan. The R-series contract remains the source of truth for task status.
