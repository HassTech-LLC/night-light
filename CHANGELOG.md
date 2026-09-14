# Changelog

All notable changes to Night Light by HT will be documented here.

The project follows semantic versioning once a public release exists.

## 0.3.0 - 2026-09-14 (unsigned Early Access)

### Changed

- **License changed to the GNU General Public License version 3 or later.** Night Light is now OSI-approved free software: use, study, modify, redistribute, and sell it, provided recipients receive the source and the same rights. `NOTICE` adds a GPL section 7 additional permission covering the Microsoft Edge WebView2 SDK and Runtime, which host the control surface. Copies already distributed under PolyForm Noncommercial or MIT keep the rights granted to them; the change applies from 0.3.0 onward. The immediate reason is eligibility for free code signing through the SignPath Foundation, which requires an OSI-approved license.
- `CONTRIBUTING.md` now states that contributions are licensed under the GPL and that copyright is assigned to HassTech, so the project can be relicensed in future without tracing every contributor.

### Fixed

- Windows Night Light detection now decodes the CloudStore record as Microsoft Bond CompactBinary (inner field 0 present = on) instead of treating byte 18 as a state marker. That byte is the inner payload length and differs by Windows build, so on Windows 11 build 26200 the native ON state (0x12) was reported as unknown. Structures the parser cannot account for still fail safe as unknown.
- The emergency reset shortcut moved from Ctrl+Shift+N to Ctrl+Alt+Shift+N. A global Ctrl+Shift+N hotkey silently captured Explorer's New folder, Chrome/Edge InPrivate and VS Code's New window shortcuts while the app was running.
- `--preset` and the `PRESET` localhost command clamp to the supported 1200-6500 K range; values below 1200 K previously raised inside Smart Comfort's appearance validation.

### Added

- Setup registers DisplayVersion (from pyproject), Publisher, DisplayIcon, URLInfoAbout, NoModify and NoRepair so Windows Installed apps shows the version and publisher. Unattended `/S` install is documented and covered by a contract test.

## 0.2.0 - 2026-09-11 (unsigned Early Access)

### Added

- Formal HassTech repository and Spec Kit project structure.
- Reproducible Python dependency metadata and Windows CI definition.
- Open-source contribution, security, privacy, architecture, and research documentation.
- Evidence-based specification for a sunset-led adaptive Smart Mode.
- Per-install authenticated localhost IPC with bounded reads and acknowledgements.
- Test isolation for the Windows display backend and user configuration.

### Changed

- Product identity standardized as **Night Light by HT**.
- PyInstaller spec paths made repository-relative.
- Build no longer changes the current user's Jump List unless explicitly requested.
- Windows Night Light now pauses the entire HT matrix, including software dimming; unknown native state fails safely as paused.

### Known limitations

- Sunset-led scheduling is specified but not yet wired into the running tray application.
- The current display transform is not calibrated as melanopic EDI and must not be described as preventing melatonin suppression.
- The Windows Night Light state reader depends on an undocumented Windows CloudStore representation.
