# Premium desktop integration and installation

Status: locally installed and verified. Unsigned; not a public release certification.

## Delivered

The approved browser design now runs inside an embedded Windows WebView2 window, not a browser tab or a localhost preview server. The existing Python/Tk owner retains the display engine, Smart scheduler, tray, authenticated IPC and emergency reset. A private redirected-pipe protocol connects the UI helper to a bounded main-thread command queue. No IPC credential is sent to JavaScript, no HTTP control API is added, navigation is restricted to packaged local assets, and permissions/new windows/downloads are denied.

Real controls: warmth, dimming, power/off, Smart/Manual, one-hour pause/adjustment, resume, postal lookup/manual coordinates, optional bedtime, fallback quiet hours, opt-in local learning, delete location/history, startup setting, Windows-off helper, quit and guide. Compare affects the real display, restores on release/blur/window closure, and has a 10-second native timeout. Emergency reset and high contrast cancel the saved comparison state.

Appearance: independent light/dark palettes, four material treatments, filled individual accent/panel/background presets, custom colors, reduced motion and persistent local appearance. Browser appearance storage is intentionally separate from desktop appearance storage.

## User-directed visual correction

The user rejected the first embedded window's square title bar, heavy nested blocks and scrollbars. The installed revision intentionally departs from that earlier concept: one continuous surface, a fitted 28px rounded native window, integrated minimize/close controls, draggable header, no horizontal overflow, hidden scrollbar chrome, and a blue-gray default palette. Content remains vertically scrollable by wheel/touch/keyboard. Surface materials retain distinct control/elevation treatments without individual opaque blocks around every section.

Fidelity comparison inspected through image viewing: original concept capture, revised dark and light renders, ceramic render, and final installed WebView2 capture. Five concrete checks: brand/icon and primary control order retained; typography and control spacing verified; default palette intentionally changed per feedback; nested container geometry and OS chrome repaired; settings/presets remain reachable without horizontal overflow. Demo schedule and sample-only copy were intentionally replaced by live native state and actual-display comparison. Runtime status copy replaces invented demo activity.

## Verification

- Python suite: 148 collected, 147 passed, 1 skipped, 0 errors/failures (22.653 seconds). The skipped global-hotkey registration test cannot acquire the shortcut while the resident app owns it. Receipt: `audit/premium-qa/final-tests.xml`.
- Embedded-renderer interaction checks passed: native pause/resume and Manual response; all 4 styles × 2 themes; separate Ocean accent/panel/background choices; appearance persistence across renderer reload; no horizontal overflow; reachable Quit. Source harness disables display backend and uses isolated settings. Browser/IAB inspected first; direct Playwright CDP attachment was used for the embedded WebView2, which IAB does not host.
- Compiled WinForms host regression passed: redirected UTF-8 pipe startup, local navigation, capture, graceful exit. This caught and fixed an actual packaged-startup `Console.InputEncoding` invalid-handle error; the final host uses UTF-8 stream readers/writers rather than console codepage setters.
- Final build: CPython 3.14.7, pinned Microsoft.Web.WebView2 SDK 1.0.4191.47; SDK SHA256 pinned and checked, license included, embedded file hashes/compiler/source origin recorded. Unknown files in generated premium payload directory fail the build.
- ZIP verification passed: `audit/premium-installed/evidence/VERIFICATION.json`.
- Final ZIP SHA256: `eb465db214dcc234cb624d6bcd4bea5d8a6920562534529b30b16105b8bf822c`.
- Final NightLight.exe SHA256: `1018577726b867034300a96c3a1ddfedd954a8ab79b5e355e7f5fa973c5e5042`. Candidate, pinned-taskbar installation and desktop/Start-menu copy matched exactly.
- Verified running installed parent/child and its extracted `NightLight.Premium.exe` child. Authenticated resident START acknowledgement passed.
- Installed capture: `audit/premium-qa/installed.png`, 416×820 CSS pixels. It shows real Smart status, no backend-warning text, live 6309 K dusk target and Dearborn Heights timing.
- Actual Windows Magnification readback after final startup: RGB diagonal approximately `[0.9946380, 0.9875057, 0.9764145]`; native transform is active. Neutral identity matrix verified before each replacement.
- Final settings: Dearborn Heights 42.3353 / -83.2864; Balanced Smart enabled; hold cleared; learning not enabled.

## Installation and rollback

Updated both existing shortcut targets:

- `%LOCALAPPDATA%/Programs/Night Light/feea8d1ae545e88dfb5f9123408edfccbea82238/NightLight.exe`
- `C:/Users/Owner/Desktop/Projects/Night Light/NightLight.exe`

Pre-change files/settings are backed up under `%LOCALAPPDATA%/NightLight-backups/premium-20260909`. Configuration backup is private and contains an IPC credential; never publish it. Shortcut targets were preserved. The taskbar's existing click-to-toggle behavior remains; right-click the tray moon to open controls.

Public release gates from RELEASE-HANDOFF.md remain: signing, independent native Windows-state interpretation, broad HDR/multi-monitor/DPI/accessibility/lifecycle checks, longer-term Smart validation and release provenance/legal closure. WebView2 Evergreen Runtime must be installed. No public upload, overnight monitoring or all-timezone certification was performed.
