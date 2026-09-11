# Installed premium replacement — 2026-09-10

Current app: `C:\Users\Owner\AppData\Local\Programs\Night Light\app\NightLight.exe`.
Build: `90a1e4ee9b6bf6d1`, Python 3.14.7, private unsigned candidate j.

## Verified outcome

- Installed EXE SHA256: `3627dc55d83890c43fbb8d96912c44de00a52afc79e1e83aa0b277e0b0804809`.
- Setup SHA256: `a66698667dccbe4e0b4ad43eec82bcd50e9356f346030095fd4b30c3cc554761`.
- ZIP SHA256: `a82d034bb7275e8babd7adf7ff3f2ef144647e24dc997e673a8280c866e31b42`.
- Old `feea8d1ae545e88dfb5f9123408edfccbea82238` installation directory deleted.
- Exactly one NightLight.exe under the installation root; PyInstaller parent/child processes use that same executable.
- Desktop, Start and pinned taskbar shortcuts reread: all target `app\NightLight.exe --show`.
- Uninstaller registered to the current root; pending old-file cleanup empty.
- Config before/after initial replacement had identical SHA256: `dd2d0f9d635bde7467ec078ff7eda43e43f9b50a63e856cfa96f0fbdbef092c9`. Later normal app session updates are distinct from installer changes.
- Native premium window opened and visually inspected: `C:\Users\Owner\AppData\Local\Temp\codex-shot-2026-09-10_08-58-10.png`.

## Automatic replacement and tests

NSIS stages incoming files and calls `installer/upgrade.ps1` with the compiled
receipt digest. Stable installs are identified by installation records; the old
unregistered version is recognized using exact file hashes in
`installer/legacy-installations.json`. Changed/unknown files stop replacement.
Paths are bounded and linked paths rejected. Normal authenticated shutdown is
attempted first. The legacy compatibility path targets only verified executable
paths and identified embedded UI children, then restores/read-backs neutral
display output. File locks retry for five seconds before any payload mutation.
Replacement verifies copied files, updates owned shortcuts/startup, records state,
then deletes old owned files. Personal settings and unrelated files are retained.

Thirty focused PowerShell/installer tests passed: fresh install, replacement,
repeat update leaving one executable, changed/unknown files, temporary/persistent
locks, preferences preservation and owned removal. Full app and setup builds
passed; NSIS treats compiler warnings as errors. Actual NSIS replacement while
the app was running completed with exit 0, including final i-to-j replacement.

The first legacy attempt closed its processes but stopped before copying; the
original error was not captured. Retrying the verified helper completed removal,
followed by successful NSIS runs. Persistent diagnostics and bounded lock retries
were then added and tested. This is not proof of one-attempt legacy migration on
every Windows configuration.

## Obsolete artifacts removed

At the user's explicit request, 62 obsolete app executable/setup/ZIP artifacts
were permanently deleted from the scoped NightLight backup, staging, rollback
and canonical project audit folders: 1,277,313,571 bytes. A final dry run found
zero matching obsolete launchable artifacts. Current j build/setup/ZIP retained.
Historical audit/source records and personal config backups were retained.
Deletion receipts: `audit/obsolete-launchers-removed-20260910.json` and
`audit/obsolete-launchers-removed-20260910-final.json`.

Public signing/download publication, comprehensive native display qualification,
the proposed Simple appearance and remaining Smart Comfort work are outstanding.
This receipt confirms local replacement and cleanup.
