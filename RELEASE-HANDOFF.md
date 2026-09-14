# Night Light — Engineering Handoff

**Status:** Source integrated and locally verified; **not approved for binary publication**.

## Completed

- Renamed user-facing desktop application labels to **Night Light**, while retaining **Windows Night Light** where referring to the native Windows feature.
- Fixed startup ownership and command-only display isolation.
- Replaced bearer-first IPC with nonce/direction/command-bound proofs.
- Fixed configuration corruption recovery, concurrent token/settings writes, and the Windows reader/writer replacement race.
- Fixed restored warmth persistence, backend-effective status, cleanup independence, exact command parsing, and autostart error rollback.
- Fixed flyout clipping/footer visibility and added maintained keyboard navigation behavior.
- Removed `pystray` and `six`; added a native Win32 notification-area implementation.
- Added atomic release packaging, binary-origin checks, dependency locking, SBOM generation, checksums, third-party notices/licenses, and pinned GitHub Action references.
- Upgraded the isolated release build to CPython 3.14.7 with OpenSSL 3.5.8 and Expat 2.8.2; eliminated the observed JDK-origin DLL sweep.

## Verified before integration

- Independently approved round-four source state: **98 tests passed**, exit 0.
- `git diff --check`: exit 0.
- Round-three functional review: code/package gate passed, including repeated concurrency runs.
- Round-four local candidate hash: `1bcade96f8efb789fea5125b2fda40b140f98ea4ebcaea738a4388d98fe220d5`.
- The candidate is intentionally excluded from Git. Local audit/build evidence remains under `audit/` and is ignored because it is approximately 583 MB and contains disposable runtimes/build sandboxes.

## Not completed — source/release blockers

Independent round-four review identified these follow-ups. A round-five worker added failing tests but was stopped at the user's wrap-up request; those incomplete tests were removed before integration, and no partial product change was retained.

1. **Tray startup error propagation:** surface worker-thread startup failures to the application, suppress updates to a dead backend, and guarantee cleanup for every partial native initialization path.
2. **Exact final-report generation:** generate report hashes and runtime versions from the exact final archive; fail on stale build-series data.
3. **Signing-state metadata:** derive signed/unsigned state from all four PE payloads and enforce unsigned-development versus signed-release policy. Tagged signed builds must never be labeled unsigned.
4. **Complete artifact-derived SBOM/legal evidence:** include helper PEs, VCRUNTIME components, hashes, `bom-ref`s, dependency relationships, and authoritative Microsoft redistribution evidence or an approved alternative.
5. **CI provenance enforcement:** assert all runtime/toolchain properties, record mutable runner/compiler/signtool inputs, and verify a real clean-tag GitHub/OIDC run.

## External release gates

- Review this integrated commit, then run CI from a clean tagged source state.
- Supply an owner-controlled Authenticode certificate; sign and timestamp all four PEs, then rebuild/reverify the exact archive.
- Confirm Microsoft Visual C++ runtime redistribution eligibility or avoid bundling those DLLs.
- Validate labeled Windows Settings/CloudStore ON/OFF state on supported builds. The detector now parses the Bond CompactBinary structure (inner field 0 present = ON) instead of reading byte 18 as a marker; byte 18 is the inner payload length and differs per build (0x10/0x12 on 26200, 0x13/0x15 on older builds). Structures it cannot account for stay unknown and fail-safe.
- Run the exact candidate in a disposable Windows account/VM and suitable spare display hardware: tray/menu, Explorer restart, real output/restoration, HDR, multiple monitors, mixed DPI, sleep/wake/logout/crash, startup, shortcuts/Jump List, update/removal, and legacy migration.
- Run real second-user IPC/ACL checks and Narrator/NVDA/UIA accessibility validation.
- Perform SmartScreen/AV reputation checks and final post-signing artifact verification.

## Safety and publication boundary

No live display setting, registry entry, production IPC endpoint, installed executable, or preserved legacy process was changed during the remediation/audit. The source repository may be pushed privately for continuity. Do **not** publish the unsigned round-four ZIP as an end-user release.

## Evidence map

Local, ignored audit directories contain the complete receipts:

- `audit/2026-09-08/FINAL-REPORT.md`
- `audit/continuation-recheck-20260909T124546Z/REPORT.md`
- `audit/release-repair-round3/REPORT.md`
- `audit/round3-functional-review/REPORT.md`
- `audit/round3-provenance-review/REPORT.md`
- `audit/release-repair-round4/REPORT.md`
- `audit/round4-independent-review/REPORT.md`
