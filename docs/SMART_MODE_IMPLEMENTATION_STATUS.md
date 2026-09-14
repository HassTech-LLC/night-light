# Smart Mode implementation — 2026-09-09

## Follow-up: integrated Smart candidate

The following items previously listed as missing are now implemented:

- Explicit online country/postal lookup through Zippopotam.us, asynchronous UI, timeout/size validation, multiple-area review and coordinate fallback. Scheduler never makes network requests. Lookup has mocked adapter tests; provider coverage is not guaranteed.
- Opt-in local inactivity/return timing estimates, seven-night minimum, latest 14 daily pairs, robust median/outlier filtering, confidence display, disable/reset and optional bedtime override. No content or application data. This is an inactivity proxy, not sleep measurement. Explicit winding-down/awake actions are available; automatic collection uses Windows idle timing rather than a separate lock/display-notification log.
- Earlier-only adaptive evening guard and minimum 20-minute catch-up when a bedtime/learned guard applies.
- User quiet-hours fallback and confident learned-window fallback when solar/location data is unavailable.
- Ctrl+Alt+Shift+N global neutral reset on an owned Windows message thread, GUI-thread dispatch, unavailable-shortcut messaging and shutdown unregistration.
- High-contrast detection stops Smart and restores neutral; the user must re-enable after disabling high contrast.
- Native Location, Schedule, Learning and Guide tabs, including taskbar versus tray explanation and plain-language controls.

Candidate: `audit/smart-mode-complete-candidate/dist/NightLight.exe` (unsigned, not installed). Full regression run passed 130 tests. One prior run, concurrent with a build, had a Tk `tcl_findLibrary` initialization failure; a sequential rerun passed. That failure is retained here rather than silently treated as a proven fix. Native UI construction and real hotkey message-loop lifecycle were tested with display effects disabled. Physical keypress-to-display recovery is not proven by the synthetic message test.

Remaining acceptance gates are real-time 14-night soak, native display/sleep-wake/HDR/monitor/high-contrast behavior, independently confirmed Windows marker semantics, postal provider live coverage, and release/signing/installation verification. The full specification is not certified complete by unit tests or a successful build. No location is inferred; the user must choose it before enabling.

Final follow-up verification: two sequential full-suite runs passed 130/130 each (22.70s and 22.84s). A live provider smoke test using the generic public example US 10001 returned New York City coordinates; this does not establish global postal coverage and was not saved as the user's location.

The sections below record the initial Solar Sync slice; where they list the above features as missing, this follow-up supersedes that initial status.

## Implemented in native source

- `smart_mode.py`: pure, cached NOAA fractional-year solar event approximation; UTC-based sunset/dawn/sunrise pairing; eased Balanced and Maximum curves; daylight neutral; morning recovery; explicit polar-event fallback to neutral.
- Injected schedule controller: 25-second evaluation, 120-second startup/rejoin fades, one-hour manual holds and pause, resume, manual disable, config persistence and input validation.
- Native flyout: Smart setup, pause, resume, Manual and status. Setup accepts approximate city coordinates, stored locally. No network requests.
- Native tray/Jump List manual actions suspend automation; App Off / zero warmth disables Smart so it cannot unexpectedly reactivate after reset.
- Existing engine remains sole display owner. Repeated unchanged Windows-status polls no longer interrupt fades. Windows active/unknown suppresses the full transform. Confirmed-off recovery fades to the current target.
- Native setup includes profile consequences and Delete Location / stop / neutral action.

## Not complete or release-proven

This is the Solar Sync implementation slice, not completion of the entire Adaptive Solar specification. Postal-code geocoding, optional bedtime/quiet-hours fallback, local session observation and learned sleep-window adaptation, a global emergency hotkey, and the broader onboarding/design work are not implemented here. UI explicitly labels learning/postal lookup unavailable.

The installed desktop executable is NOT replaced. Build output is an isolated unsigned candidate under `audit/smart-mode-candidate/dist`. No live display, registry, startup or pinned shortcut changes were made.

No 14-night soak, real sleep/wake/HDR/multi-monitor certification, or physical-display fade/neutral proof exists for this slice. Windows marker 0x10 semantics remain a separate prior native-state verification concern; these changes do not validate that marker. Solar math uses NOAA's approximate fractional-year equations, not the full Meeus calculator; reference test tolerance is five minutes.

## Verification

- Tests run with `NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND=1` and temporary isolated config through `conftest.py`.
- Pure tests: equatorial equinox reference, season/location bounds, timezone-equivalent instants, polar behavior, short-night morning continuity, override/pause expiry, missing location, no repeated fade restarts, Windows exclusion and rejoin.
- Native CTk controls constructed and pause/resume/manual callbacks exercised with a fake display engine.
- Run `python -m pytest` for the complete regression suite. Build with `python build.py --dist-dir audit/smart-mode-candidate/dist --build-dir audit/smart-mode-candidate/build`.

Reference: [NOAA solar equations](https://www.gml.noaa.gov/grad/solcalc/solareqns.PDF).
