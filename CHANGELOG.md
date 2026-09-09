# Changelog

All notable changes to Night Light by HT will be documented here.

The project follows semantic versioning once a public release exists.

## Unreleased

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
