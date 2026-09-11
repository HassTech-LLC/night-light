# Smart Mode local installation — 2026-09-09

Status: installed and locally smoke-tested; NOT approved for public release.

## Installed configuration

- Dearborn Heights, Michigan 48127, postal lookup confirmed coordinates 42.3353, -83.2864.
- Smart Mode enabled, Balanced profile, no manual hold. Learning remains off.
- Computed sunset today: 19:55:51 EDT; warm-up begins one hour earlier, approximately 18:56 EDT.
- Both existing executable locations updated: the pinned taskbar target under `%LOCALAPPDATA%/Programs/Night Light/feea8d1ae545e88dfb5f9123408edfccbea82238` and the Start menu target under `C:/Users/Owner/Desktop/Projects/Night Light`.
- Previous installed payload, desktop payload and private configuration backed up under `%LOCALAPPDATA%/NightLight-backups/smart-20260909`. Do not publish that configuration backup: it contains an IPC credential.

## Verified

- Built using isolated CPython 3.14.7, OpenSSL 3.5.8, Expat 2.8.2.
- Full 130-test suite reached 100%, process exit 0 using that runtime.
- Package verification passed with no errors; evidence in `audit/smart-install-20260909/evidence`.
- ZIP SHA256: `02184bc02d59bf5126d277cdf7b841227f05320ecd4996b974cd198ea17d9ddc`.
- Candidate and both installed NightLight.exe hashes match: `9fbee3f1284feb119e7a2cd582be381de4d472066585f1ee1a3a45e890f770f1`.
- Running process executable path matched the pinned taskbar target.
- Authenticated SHOW acknowledgement measured 18 ms (queue acknowledgement, not visual latency).
- Installed PRESET 3200 changed the actual Windows Magnification color matrix to RGB diagonal `[1.0, 0.7200782895, 0.4828211665]`.
- Installed STRENGTH 0 restored the exact identity matrix. Smart control was restored afterward and app restarted.
- All four packaged PE security-directory sizes are zero: no embedded Authenticode signatures. PowerShell signature cmdlet could not load its module; PE inspection was used instead.

## Remaining release gates

This is an unsigned local candidate, not a public release. The source, provenance, metadata/legal and external certification gates in RELEASE-HANDOFF.md remain open. No signing, public upload, overnight soak, real HDR/multi-monitor matrix, sleep/resume/logon/uninstall campaign, second-user security test, or screen-reader certification was completed here. Windows Night Light marker interpretation still needs independent native Settings ON/OFF verification. The earlier Tcl test-run flake is not proven resolved. Browser premium design remains a separate concept, not a completed native UI port.
