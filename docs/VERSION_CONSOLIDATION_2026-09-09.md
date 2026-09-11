# Local version consolidation

**Superseded on 2026-09-10:** the old installation and obsolete launchable backup
artifacts below have now been removed. The premium app is installed at the stable
`Programs\Night Light\app\NightLight.exe` path. See
[current replacement proof](INSTALLED_REPLACEMENT_2026-09-10.md). The remainder
records the earlier consolidation, not the current installed state.

User requested that older copies be removed from normal use to prevent confusing development tests with installed releases.

- Canonical source: `C:\Users\Owner\Desktop\HassTech\Products\night-light-by-ht`.
- Retained installation: `C:\Users\Owner\AppData\Local\Programs\Night Light\feea8d1ae545e88dfb5f9123408edfccbea82238\NightLight.exe`.
- Retained executable SHA256: `87A59407FA4ABDDE1F4AC1969898F096FAD3BB194E3ACFFFD7D0FF141FA2F017`.
- Desktop and Start menu shortcuts now target this installation; the pinned taskbar shortcut already did. All three targets were reread and verified to exist.
- The duplicate executable in `Desktop\Projects\Night Light` had the same SHA256. It was archived, not permanently deleted.
- The older source-repository `dist` folder was archived. Its executable SHA256 was `C6922ECAAD355F46016EC8349E5AB91ECEDF2BB3E8BF1866319B09A519C614EC`.
- Recoverable archive: `C:\Users\Owner\AppData\Local\NightLight-backups\version-consolidation-20260909-204623`. Includes original Desktop/Start menu shortcuts, duplicate executable, and stale `dist` directory.
- Existing rollback archives were retained. User settings and the running installation were not changed.

The Smart Comfort completion plan is not yet a newly built/installed release. Source tests must run in the canonical repository with display-backend isolation; future installation must come from a freshly verified build, never the archived `dist` payload. Current installed appearance must not be presented as proof of the pending implementation.
