# Night Light: the best version I would build

Date: 2026-09-09. Status: proposed product direction and interactive design concept, not an implemented desktop upgrade. Source baseline inspected: `3dba3aa811973a9567d45457ed06c5bd7439049f`. This extends the existing sunset-led Smart Mode specification rather than replacing its product contract.

## Product thesis

A small, beautifully finished Windows light control that follows the evening, responds immediately, and makes its behavior easy to understand. The premium feeling should come from precision: a deliberate click always has a visible response, automation never fights an override, and the user can always restore a neutral screen.

The core stays free, works without an account, and keeps preferences locally. Optional support belongs in About or settings, away from everyday controls.

## What exists, and what does not

- Present in source: manual warmth and software attenuation, presets, native tray integration, taskbar command routing, authenticated single-instance transport, separate Windows/app states, and a CustomTkinter flyout. `NightLight.spec` packages the Python application as one executable.
- Specified but absent from the running application's controller: solar calculation, location setup, an automatic evening curve, override expiry, and adaptive timing. See `docs/SMART_MODE_SPEC.md` and `specs/001-sunset-smart-mode/plan.md`.
- This turn adds a design proposal, browser-only interaction concept, and a small non-toggling performance measurement. It does not install Smart Mode, replace the desktop UI, alter display settings, or release a binary.
- Correction to the earlier fix's confidence: the previous change made `0x10` return OFF, but the conversation contains no independently paired Windows Settings ON/OFF observation proving that interpretation. Synthetic tests establish the chosen mapping, not its truth. The best-version work must resolve this with labeled fixtures; it cannot count that patch as completed Windows compatibility validation.

## Features I would prioritize

| Order | Capability | Experience | Implementation boundary |
|---|---|---|---|
| 1 | Instant control and truthful status | Click the crescent and get immediate acknowledgement; show Active, Off, Scheduled, Paused, or Failed with one useful explanation | Separate requested state, accepted target, backend result, and observed OS state; do not call an acknowledgement visible output proof |
| 2 | Complete Solar Sync | Set country/postal code once; preview tonight; local calculations carry on offline through sunset, dawn and DST | Build the existing pure solar/schedule design before adding learning; ask before any location lookup; allow manually configured quiet hours without a network request. When traveling, solar timing continues to use the saved location until the user changes it or explicitly enables location updates |
| 3 | Overrides with an expiration | Pause for 30/60 minutes, until sunrise, or turn off indefinitely; show the actual resume time | A timed pause does not change the preferred schedule. Restart/resume must reconcile expiry. Persistent Off wins until deliberately re-enabled |
| 4 | Personal evening curve | Choose comfortable warmth and dimming for dusk, evening and late night; gently join those points | Keep the default simple, advanced editor optional. Exact kelvin numbers are software targets, not calibrated display measurements |
| 5 | Original-colors preview | Hold a button/hotkey to remove Night Light's own effect; release to return to the current target | Restore on key-up, focus loss and timeout; provide a toggle/timed alternative for people who cannot hold a control. This does not remove other color management or certify calibration |
| 6 | “Wind down now” | Begin a chosen comfortable fade earlier tonight, without editing tomorrow's schedule | Explicit manual intent; stop or undo remains easy; no assertion about sleep or physiology |
| 7 | A setup that teaches by doing | One preview, a comfort adjustment, optional Solar setup, then done | Manual use works immediately. Startup is opt-in; no forced account, location or learning |
| 8 | Recovery users can trust | Dock, wake, restart Explorer or change display mode without stale state or surprise jumps | Verify native initialization, topology changes and restoration; emergency neutral shortcut independent of the flyout; retain a usable failure state |
| 9 | Preference suggestions | “You keep choosing this warmth after 9 PM. Save it for evenings?” | Opt-in history of the app's own edits; local retention/reset controls. Ask before applying suggestions. Session-idle timing alone does not establish sleep |
| 10 | Advanced display support | Identify connected displays and show which combinations are supported; later, hardware dimming on compatible monitors | The current fullscreen matrix is global. Independent per-monitor warmth and HDR correctness require a separate validated backend, not a new settings screen |

Smart timing and dimming should be independently adjustable. The existing draft's very low automatic dimming endpoints need comfort/readability testing before becoming defaults. Extreme warmth is a deliberate advanced choice. Avoid names like “Maximum Protection” or “Biological Night” in normal controls; use “Late night” and describe the actual behavior.

Optional later convenience: a display-off action and manual color-work session with automatic return. Foreground-application exceptions are deferred because collecting application names conflicts with the current privacy constitution; do not quietly add app tracking.

## Premium visual direction: quiet, warm, precise

Use iOS as a reference for hierarchy and tactile controls, while using Windows-native focus, context menus, window placement and accessibility behavior.

- A compact flyout approximately 360–380 logical pixels wide, with content-responsive height and access at 100–200% scaling. This is a prototype target to validate, not a fixed height that can clip settings.
- One restrained surface. Warm ivory/light gray in light mode; deep charcoal in dark mode; amber used for warmth and selected controls. Use system theme by default with a manual override.
- Segoe UI Variable or the installed Windows system font, 14–16 logical-pixel body text, clear weights, readable secondary text. Avoid turning every status into an uppercase badge.
- Rounded panel and pill controls; generous spacing; mostly alignment and typography instead of nested bordered cards. Restrained material/blur only where legible, with opaque, high-contrast and reduced-transparency alternatives.
- Header: app identity, power switch, accessible settings entry. Main controls: Smart/Manual selector, warmth, dimming, and a small Tonight timeline. The line below the heading explains what is effective now and what happens next.
- The schedule preview communicates cause and effect: “Gradually warmer until 10 PM,” “Paused until 9:15 PM,” or “Windows Night Light is active.” A fault replaces the normal description with a repair action; it does not add another panel of redundant ON/OFF labels.
- Warmth uses an understandable intensity label with optional kelvin detail. Software dimming is explicitly labeled; it is not monitor-backlight brightness.
- Controls acknowledge a press immediately. Use roughly 120–180 ms interface transitions, subtle press feedback and interruptible movement. No endless pulsing moon, animated background or unnecessary celebratory toast. Respect reduced motion.
- At least 44-logical-pixel primary hit targets as a design target, full keyboard operation, visible focus, accessible slider values, Escape dismissal and clear status independent of color.

Preserve the existing user's left-click-to-toggle habit. A dedicated taskbar toggle stays a toggle; tray context action opens controls; the Windows taskbar right-click remains a Jump List. Do not promise arbitrary custom sliders inside a Windows taskbar context menu.

The HTML concept at `docs/design/night-light-premium-concept.html` demonstrates the hierarchy, themes, ranges, temporary override and preview interactions with example data. It does not call Windows APIs or run the real scheduling engine.

## Speed: evidence and changes

Read-only behavior probe on Hassan's machine, 2026-09-09: sent the idempotent `START` command to the existing resident. No toggle or display modification was requested. Installed path: `%LOCALAPPDATA%\Programs\Night Light\feea8d1ae545e88dfb5f9123408edfccbea82238\NightLight.exe` (this folder name predates the subsequent local patch).

| Path measured | Samples in milliseconds | Median |
|---|---|---|
| Direct Python client to existing authenticated resident; wait for acknowledgement | 31.742, 9.840, 20.787, 32.101, 30.941 | 30.941 ms |
| Start installed full EXE with `--background`; wait for command process exit | 1024.231, 1042.385, 1053.479 | 1042.385 ms |

All three EXE processes returned zero. These are different end-to-end boundaries (acknowledgement versus process exit); the difference is evidence of launcher overhead, not a measured 34x improvement in screen response. It is a tiny warm-machine sample, not a percentile study, cold-start result or hardware measurement.

Recommended sequence:

1. Put a small native command executable on the taskbar. It sends the same mutually authenticated command to the resident; if no resident exists, start it once. Never weaken authentication or let command-only processes own the display.
2. Avoid repeatedly extracting/starting the full Python UI bundle for a toggle. Consider one-folder installation as an interim improvement. PyInstaller documents extraction overhead for one-file programs [1].
3. Register shortcut identities during installation/path changes, rather than every ordinary tray refresh. `TrayApp._ensure_jumplist` currently starts a fresh worker and helper processes; serialize/coalesce updates and only publish changed state. This is a source-identified opportunity, not a measured cause of every delay.
4. Cache the flyout, icons and stable UI. Paint input feedback before optional disk/helper work; persist through the existing safe writer rather than blocking each drag event. Flush important state safely on commit/shutdown.
5. Coalesce slider targets so the newest position wins; do not queue every mouse movement or append animations. Separate control animation, manual effect fade and slow scheduled transition.
6. Use OS events for resume, display and time changes plus a modest scheduler timer; avoid busy polling. Retain conservative fallback checks where Windows has no supported notification.

Acceptance targets, to be measured on supported hardware: resident command feedback p95 under 100 ms; warm flyout first paint p95 under 150 ms; slider input-to-application request under 50 ms; manual fade around 150–250 ms with immediate/comfortable choices; no idle helper churn; near-zero idle CPU. Track memory/working set and energy before/after. Measure cold launch separately. These are proposed budgets, not existing guarantees. A visual browser concept does not prove native performance.

## Smart Mode behavior contract

One controller should resolve every request before calling a single display owner:

`inputs → desired schedule/manual target → override and OS exclusion policy → display adapter → acknowledged/effective status → UI`

Priority: emergency neutral / explicit Off; native conflict, unknown or backend error pause; temporary original preview / timed neutral pause; explicit manual target; current automatic target. Time-bound overrides keep the base schedule and join its current value gradually when they end.

- Manual adjustment in Smart Mode creates a visible 60-minute override, with immediate Resume Smart and optional duration change. Choosing persistent Manual disables automatic application without deleting schedule preferences.
- Power Off stays Off across restarts. A timed pause is a separate action. Re-enabling recomputes the saved mode's current target.
- During native Windows Night Light activity, apply no competing app warmth or dimming. After a verified off transition, recompute the current target; do not replay old frames.
- On wake/timezone/DST change, recompute from local date/time and actual solar events for the saved coordinates; a timezone change must not imply new coordinates. Surface the saved location and provide a quick update action for travel. Use monotonic time for animation, wall clock for schedule boundaries, and a defined persisted expiry for overrides.
- Offline geocoding cache remains usable. Invalid postal input, network failure, missing sunrise/sunset, and insufficient learning data each have an explicit fallback, never fabricated solar events.
- Any learning remains optional, local and resettable. The already specified solar curve works on day one. Later adaptation can suggest earlier timing within the existing contract; do not silently delay the curve.

## Engineering approach

Keep the pure solar math, preferences, state resolver and display adapter independently testable. My preferred native shell candidate is C# with WinUI 3, which Microsoft recommends for new native Windows apps [4]. WPF with its supported Fluent theme is a credible fallback [5]. Build one vertical slice (toggle, sliders, theme, tray, keyboard, state reporting), compare it with the optimized current app, then commit to the shell based on measured startup, accessibility, idle cost and mixed-DPI behavior. A visual rewrite alone does not improve the display API.

Use Windows Acrylic for a transient flyout and Mica for a persistent settings surface where supported [6]. Fall back to opaque material according to user preferences and capability. There is no need to copy proprietary Apple widgets or assume its exact rendering technology is available on Windows.

The current `MagSetFullscreenColorEffect` primitive applies a single desktop-wide matrix; the last writer wins [7]. Independent monitor warmth is therefore research work. HDR, mixed SDR/HDR, secure desktop and protected-content behavior need hardware evidence. Do not casually substitute `SetDeviceGammaRamp`: Microsoft discourages it and documents false-success and undefined HDR/calibration behavior [8]. Hardware brightness is a later adapter for validated monitors; DDC/CI support is inconsistent, so probe capabilities and coalesce writes away from the UI [9].

Do not add Electron, a cloud LLM, analytics collection or an always-running web server merely for this utility. The browser concept is a portable design artifact only.

## Delivery order and completion criteria

1. **Trust and instant controls.** Resolve paired native-state fixtures and restore proof; lightweight launcher; coalesced helpers; verify stable install target and shortcuts. Demonstrate real ON/OFF output and neutral restoration, not just config values or API success.
2. **Premium shell.** Implement this design as a native vertical slice. Validate light/dark, keyboard, Narrator/UIA, reduced motion/transparency, scaling, placement and normal/paused/error states. Choose the shell after measurements.
3. **Solar Sync.** Implement the existing pure solar plan, location setup, personal curve, visible next transition, and override expiry. Use a controllable clock for DST, midnight, polar/no-event, sleep/resume and clock-jump cases. Geocoding failure must not disable manual use.
4. **Daily-use polish.** Original-color preview, wind-down action, comfort floor, settings/export/reset and stable rollback/update. Field-test on supported monitor configurations and run the existing planned overnight soak before claiming dependable automatic use.
5. **Optional adaptation and advanced hardware.** Add explainable local suggestions after manual/solar use is proven. Investigate hardware brightness and independent monitors behind capability detection; unsupported hardware keeps a clear fallback.

For release, bind test/build/install receipts to the actual candidate, preserve settings, stop the single display owner gracefully, retain a rollback package, and validate signed update/remove behavior. Historical green unit tests are useful evidence but do not clear physical display, Windows state, packaging or accessibility claims.

## What I would deliberately leave out

An AI chat window, sleep scores, medical guarantees, camera-based sensing, daily streaks, social features, intrusive donation requests, and a large monitoring dashboard. The added value is reliable automatic behavior with controls that feel effortless.

## Concept verification

Browser checks on 2026-09-09 confirmed light/dark selection, Smart pause with 9:45 PM resume text, Resume Smart, keyboard warmth adjustment creating a 60-minute override, Windows-conflict suppression/explanation, expandable preferences, neutral reset, and a manual pause that preserves Manual mode. Normal panel measured 376 × 627 CSS pixels. At a 320-pixel browser viewport, no horizontal document overflow was present. Browser warning/error collection returned no entries. Inline JavaScript syntax was checked separately. These checks apply to the simulated HTML, not the native app, physical display, complete screen-reader behavior or overnight automation. Temporary responsive viewport was reset after verification.

## Sources

### Appearance studio follow-up

The interactive concept now includes six paired color presets (Amber, Ocean, Sage, Lavender, Rose, Graphite), custom accent/panel color pickers, and independent persisted light/dark palettes and material choices. Liquid, Frosted, Solid, and a distinct Ceramic treatment are available in both modes. Reset affects only the current mode. Gentle motion can be disabled; system reduced-motion and reduced-transparency rules still apply. Appearance is saved in this browser's local storage, not in native app settings. Filter/schedule controls remain simulated.

Verification: four Node tests cover all 48 theme/material/preset combinations, independent persistence, custom colors, per-mode reset, motion, invalid data and denied storage. Live browser checks confirmed Rose/Ceramic survives reload, custom panel/accent values persist, and switching back to dark retains Ocean/Liquid. Checked the desktop screenshot and 320px layout with no horizontal overflow. The existing heading, flyout hierarchy, typography, icons, filter controls, and timeline remain; intentional additions are appearance controls and material-specific styling. No native app changes or native performance claims are included.

1. [PyInstaller operating modes](https://pyinstaller.org/en/stable/operating-mode.html): the one-file bootloader extracts dependencies; one-folder installation avoids that repeated extraction path. Local timings above remain the relevant performance evidence.
2. [Apple Human Interface Guidelines — Materials](https://developer.apple.com/design/human-interface-guidelines/materials): material treatment and accessibility-aware appearance are design references, not a promise to reproduce Apple's platform effects on Windows.
3. Local source evidence: `main.py`, `NightLight.spec`, `ipc_transport.py`, `tray_app.py` (`_ensure_jumplist`, `toggle_nightlight`), `nightlight_engine.py` (`set_state`), and `premium_ui.py`; existing `docs/SMART_MODE_SPEC.md`, `specs/001-sunset-smart-mode/plan.md`, `.specify/memory/constitution.md`, and `RELEASE-HANDOFF.md`.
4. [Microsoft — Get started developing apps for Windows](https://learn.microsoft.com/en-us/windows/apps/get-started/).
5. [Microsoft — WPF .NET 9 Fluent theme](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/net90).
6. [Microsoft — Materials](https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/materials) and [Motion](https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion).
7. [Microsoft — MagSetFullscreenColorEffect](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magsetfullscreencoloreffect).
8. [Microsoft — SetDeviceGammaRamp](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setdevicegammaramp).
9. [Microsoft — SetMonitorBrightness](https://learn.microsoft.com/en-us/windows/win32/api/highlevelmonitorconfigurationapi/nf-highlevelmonitorconfigurationapi-setmonitorbrightness).
