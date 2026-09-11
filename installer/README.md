# Windows installer integration

Status: lifecycle implementation complete for private-candidate testing. `night-light.nsi`
still builds an explicitly private replacement candidate, not a release-qualified setup. Follow the full contract in
`specs/002-smart-comfort-completion/contracts/distribution.md`.

## Private compile path

`build_installer.py --archive <current verified ZIP> --toolchain <NSIS directory>
--output-dir <new audit directory>` compiles without executing setup. The NSIS
3.12 package/compiler/extracted-tree digests are locked in `toolchain.json`;
changing any compiler input fails the gate. The archive must match current
source. Windows path aliases/traversal and duplicate payload names are rejected.
The setup receipt records the source ZIP, compiler, script and output hashes.

This first script uses zlib and per-user permissions, requires Windows 11/x64
and WebView2, offers Microsoft's official download page if the runtime is
absent, and never launches the app or enables startup automatically. It stages
incoming files and calls `upgrade.ps1` to replace recognized installations at the
stable per-user `app` directory. The helper verifies incoming and previous file
hashes, updates owned Desktop/Start/taskbar shortcuts and existing startup entries,
and deletes superseded owned files. Preferences stay outside the install payload.
`INSTALLATION.json` binds the current receipt and journals pending old-file cleanup.
Older builds without receipts are recognized using exact hashes in
`legacy-installations.json`. Unknown or changed app files stop replacement.
Precommit failures restore existing shortcuts, startup state, and the prior stable app
directory. A flushed transaction journal makes interrupted recovery idempotent; synthetic
exception and process-exit tests cover every precommit phase. Abrupt VM power-loss and
signed release qualification remain separate gates.

## Owned-file removal

The builder generates `OWNED-FILES.json` with exact hashes/sizes and embeds its
SHA-256 in the uninstaller. `remove-owned.ps1` checks that receipt, rejects linked
paths, running processes, changed files and file locks, then removes only the
listed files. All file verification finishes before deletion begins. Open read
handles deny concurrent readers/writers but permit the exact deletion operations.
Unknown files and preferences are retained. A partially completed deletion can
resume while the unchanged receipt remains available.

Only Desktop, Start, pinned-taskbar, and startup entries whose target and arguments still
match this app are removed. The primary Start/pinned entry uses `--toggle`; the separate
`Night Light Controls` entry uses `--show`.
NSIS removes its uninstall registration only if InstallLocation matches the fixed
per-user root; directory cleanup is nonrecursive. Registry cleanup, NSIS self-removal,
simultaneous installer/uninstaller execution and real signed-install removal need
additional execution proof. Read-only preflight is available with `-VerifyOnly`.
PowerShell execution policy is not bypassed; enterprise policy may block the helper.

## Authenticated graceful exit

After the user agrees to close Night Light, the installer can run the candidate
application with **only** `--request-exit`. This is a client-only command:

- It cannot reserve/start a display owner, show controls or toggle a filter.
- It reads a bounded existing configuration solely for mutual IPC authentication;
  it does not create a configuration, token, session or preference change.
- Exit code **0** means the authenticated resident acknowledged the exit request.
- Exit code **2** means exit was not confirmed, or incompatible flags were supplied.
  It does not prove the app is absent. The compatibility path may stop only exact
  hash-verified installed executable paths and their identified embedded UI children,
  then restore and read back the neutral display matrix. Never kill by name alone.

The resident acknowledges before queueing its normal GUI-owned `quit_app` path,
which requests neutral cleanup. **Acknowledgement is not process-exit proof.**
Before touching payloads, setup still must verify the exact owned process paths
have exited and the app files are no longer held open. Preserve settings and
preferences; do not rename a live payload based only on the acknowledgement.

## Remaining release qualification

Publisher signing and timestamp verification; disposable-VM interruption and two-user
matrices; clean-account installation; supported hardware/accessibility qualification;
and exact signed website download-to-install proof.

No installer should enable the visible migration switch until the previous
payload/config identity and rollback activation path are qualified.
