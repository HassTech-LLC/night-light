# Interface, instructions and command contract

Status: implementation design. Example times below are illustrative, not the user's current schedule.

## 1. One coherent product surface

Quick panel target: 400 logical px wide, 560–640 logical px high when content permits. Minimum usable width 320 logical px. Expanded preferences may grow to 520 px. Cap height to current monitor work area; below comfortable height, use one visible vertical scroll region with all actions reachable. Never horizontal scrolling or hiding scrollbars as the only clipping fix. At large text/scaling, let labels wrap and height grow.

Use one outer native window shape and one inset keyline, no square frame around a separate rounded card. Align WebView2 content clipping, native hit testing, radius and shadow. Draggable header does not steal clicks/keyboard focus from buttons. Close hides the controls while background behavior remains; Quit is a separate labelled command with neutral cleanup. Reopen restores reasonable position inside the current work area.

```text
Moon  Night Light                         power  close
Adjusting gradually
Evening setting expected around 8:40 PM

                 Smart | Manual
Warmth                           target 3,500 K
-----------------------------------------------
Dim screen                       target 10%
-----------------------------------------------
Compare with original

Tonight: starts 5:45  ready 8:45  normal 7:10 AM
Pause for 1 hour
Settings                                  Help
```

The main state area chooses one primary message; technical details are expandable. Do not display several contradictory status badges. The numeric controls always label targets while adjusting; an expandable detail shows accepted software output without claiming physical measurement. Progress is elapsed trajectory progress, not percent health protection.

Settings sections: Schedule, Appearance, Windows access, Help/About. Use spacing/dividers before extra cards. Body text 14–16 logical px, strong state heading, 44 px preferred interactive targets; compact chrome may be smaller with adequate spacing and accessible names. Use system fonts; no remote font dependency. UI motion is brief opacity/position response, not continuous shimmer or animated wallpaper.

## 2. Materials and color presets

| Finish | Whole-panel material | Controls and hierarchy | Fallback |
|---|---|---|---|
| Glass | tinted translucent app surface, restrained highlights and depth | translucent control wells, light keyline, subtle elevation | opaque version of chosen surface |
| Frosted | higher-opacity diffuse surface, subdued backdrop | softer wells/dividers, lower specular highlight | opaque frosted palette |
| Solid | fully opaque, no backdrop treatment | crisp controls, flat dividers, minimal shadow | same |
| Ceramic (legacy) | retain existing user selection | migrate tokens without silently changing it | opaque equivalent |

Do not claim true desktop-backdrop blur if the native host only composites the app's own canvas. Native DWM material support must be proved; otherwise describe the finish as a glass-style app surface. Do not add animated effects to compensate for insufficient contrast.

Color properties: Accent, Text, Panel surface, Window background, Controls, Borders/separators. If any additional color property is exposed, it must receive the same preset/custom/reset contract. Each editor is independently collapsible and contains filled swatches, name, hex input, color picker, selected checkmark/outline, Reset this color. Whole-mode Reset is separate and reversible. Theme-wide palettes are shortcuts, not replacements for per-property presets.

Proposed palette seeds, aesthetic choices rather than researched popularity rankings:

| Palette | Light background / panel / text / accent | Dark background / panel / text / accent |
|---|---|---|
| Pearl & Blue | #F3F5F8 / #FFFFFF / #18212F / #2459A9 | #101722 / #1A2534 / #F1F5FB / #9AC3FF |
| Stone & Amber | #F5F1EA / #FFFCF7 / #29231D / #87510E | #191714 / #29251F / #F7F1E6 / #EDBE78 |
| Sage | #EEF3EE / #FAFDFA / #1A2D24 / #356648 | #111B17 / #1B2C23 / #ECF6EF / #9BCCAD |
| Plum | #F3EFF7 / #FCFAFF / #30233F / #6C438F | #1B1623 / #2C2239 / #F6EEFD / #CCA8EC |

Each property's preset row uses appropriate values from these palettes plus neutral choices. Control/separator colors are separately defined tokens, not inferred by darkening a user-selected accent without explanation. Numeric contrast tests select a suitable foreground; preserve the entered raw value and explain effective adaptive text when enabled. Explicit text customization gets a contrast warning and accessible repair suggestion, not silent replacement. Critical Off/error controls retain a protected readable treatment. Preset labels never rely only on their background color.

Verify all preset pairings analytically; test composed transparent surfaces against representative light/dark app canvases and custom black/white/extreme combinations. Full combinatorial screenshot generation is unnecessary; combine exhaustive token-contrast checks with risk-based rendered checks. Compare finishes at identical colors/content to prove a real material difference.

## 3. Save and bridge protocol

Preserve the private redirected native pipe. JS receives no IPC credential, and no local HTTP control server is introduced. Packaged navigation only; external help opens through a narrow allowlisted OS-browser action. Unknown commands/fields are rejected; bounded payloads, types and finite numeric ranges are enforced natively.

Command envelope: `protocol_version`, `session_id`, `request_id`, `kind`, `expected_config_revision` for mutations, validated payload. Snapshot: monotonic sequence plus session, config/intent/trajectory revisions. Responses: request ID, `outcome`, current revisions, safe message key, saved canonical fields, availability. UI text comes from message keys, not arbitrary HTML returned by the bridge.

Kinds: GetSnapshot, SaveSmartSettings, SetMode, SetTemporaryAppearance, SaveNightlyAppearance, PauseSmart, ResumeSmart, SetOff, ApplyNow, BeginPreview, EndPreview, RetryDisplay, DeleteLocation, DeleteRoutineHistory, SetAutostart, OpenApprovedLink, Quit. Reuse existing command paths where equivalent; changes are versioned and all native entry points route to the same reducer.

| Event | Visible response |
|---|---|
| Click Save and enable | immediate `Saving…`, disabled duplicate submission, accessible busy state |
| Durable success, scheduled for later | `Settings saved. Smart starts at 6:10 PM.` |
| Durable success, changing now | `Settings saved. Adjusting gradually.` |
| Durable success, blocked output | `Settings saved. Display adjustment is unavailable.` plus actionable reason |
| Validation error | exact field error, focus field, keep draft |
| Disk failure | `Couldn't save your settings. Your previous settings are unchanged.` |
| Eight seconds without acknowledgement | `Save not yet confirmed. Checking…`; query canonical revision |
| Still unknown | `Couldn't confirm the save. Your edits are kept here.` plus Check again/Reload saved settings |
| Stale draft | `Settings changed elsewhere. Review the latest settings before saving.` |
| No bridge/host unavailable | `Controls aren't connected. Reopen Night Light to try again.` |

Do not claim Apply/physical success from saving. Applied in user-facing copy means the software command was accepted; Help explains that display behavior depends on Windows/hardware. For unknown readback/current output, show uncertainty rather than stale values. Live regions announce semantic result once, not ETA ticks. Return focus sensibly and retain dirty edits through reconnects.

## 4. Onboarding and easy instructions

### First-run flow

1. **Welcome:** `Make evening screen changes automatic.` Secondary: `Choose a comfortable appearance. You can turn it off any time.` Buttons Set up Smart / Use Manual. Screen remains neutral.
2. **Timing:** Sunset schedule / My schedule. Country/postal lookup says it contacts a provider once; manual coordinates and personal times remain available. Show saved location and PC timezone. Never infer travel from timezone alone.
3. **Comfort:** real-display preview only after Preview click. Native countdown 20 seconds for comfort selection, Keep this preference / Restore / Escape. Keep stores the draft preference, not an unannounced change to the entire live schedule; final Save and enable commits it. Missing backend is explicit.
4. **Confirm:** show warmth/dim endpoint, start/ready/morning times, late-start catch-up if applicable. Save and enable has the transactional feedback above.
5. **Easy access, optional:** pin tip and Start with Windows checkbox, both unchecked/unapplied by default. Done does not enable either. Skip/reopen supported.

Comfort preview and Compare have different visible timeout lengths (20 seconds and 10 seconds). Native timeout, blur, window close and safety events end either; only explicit Keep preserves the draft selection. Off invalidates both tokens and cannot be undone by timeout cleanup.

An explicit comfort-preview action is allowed while saved mode is Off, without changing that saved mode. Ending either preview restores latest effective intent within the proposed 500 ms transition unless newer Off/conflict overrides it. If Off works for this session but cannot be saved, say `Off now. Couldn't save this for next startup.` with Retry saving; do not leave a generic Save failure while the user wonders whether the display was restored.

### Ready-to-use help snippets

| Control/topic | Brief explanation |
|---|---|
| Smart | `Changes warmth and dimming automatically using your chosen schedule.` |
| Manual | `Keeps the appearance you choose until you change it.` |
| Warmth | `Makes colors look warmer. The temperature is an approximate software setting.` |
| Dim screen | `Darkens the image without changing your monitor's brightness setting.` |
| Timing | `Ready time is when you want your evening appearance—not a measured bedtime.` |
| Catching up | `Catching up to your schedule. We'll adjust gradually instead of jumping.` Add the actual late-start/wake/resume reason only when known. |
| Pause | `Temporarily removes this app's adjustment. Smart returns at the time shown.` |
| Temporary adjustment | `This change lasts until the time shown. Save it if you want it every night.` |
| Compare | `Briefly removes this app's adjustment, then returns to your current mode.` |
| Off | `Removes this app's adjustment and stays off until you turn it on.` Display failure/persistence limitations override this ordinary success description. |
| Start with Windows | `Starts Night Light when you sign in. It keeps your saved mode, including Off.` |
| Close / Quit | `Close hides the controls. Quit stops the app and removes its adjustment where available.` |
| Theme colors | `Changes the app's appearance, not the screen filter.` |
| Windows conflict | `Windows Night Light is on. This app is paused to avoid combining filters.` |
| Location | `Sunset uses the location saved here. Update it when you move.` |
| No visible change | `Check whether Smart starts later, is catching up, is paused, or reports a display issue.` |

### Pinning and access card

`For quicker access: open Night Light, right-click its icon on the Windows taskbar, then choose Pin to taskbar.` Follow with: `The small moon near the clock is a separate background-app icon. It may be under the hidden-icons arrow.` Use a real, version-appropriate screenshot with alt text at implementation time; do not rely solely on the screenshot. Link to Windows help optionally. Windows decides whether/how pinning is available; no forced pinning or fake Pin now button.

Offline Help index: Quick start; Every control; Smart timing/travel; Original colors and recovery; Windows Night Light conflicts; Color-sensitive work; Startup/pinning; Update/uninstall; Privacy and limitations; Diagnostics/About. Use short answers with optional More detail, not a mandatory long tour. Reuse the same content source for the website installation section where practical; version it with the release.

Explicit offline steps: `Help → About → Check for updates`, compare Installed and Latest available, then download the signed installer. To remove: `Windows Settings → Apps → Installed apps → Night Light → Uninstall`; preferences are retained unless Remove my settings/history/backups is selected. Explain that another color tool or Windows Night Light can still affect appearance after HT is off; unknown ownership/backend failure may prevent reset and must show its actual status.

Name the current lookup provider before a request (currently Zippopotam.us in source), state the exact country/postal fields sent, and explain that retries send another request. No request on every keystroke. One-time setup lookup means no recurring background lookup, not a promise that a failed lookup can never be retried.

## 5. Native menu and accessibility

Pinned taskbar Jump List: Open Night Light; Pause Smart for 1 hour or Resume Smart if applicable; Turn filter off. Optional warmth shortcuts off by default if retained. Windows owns the rendered menu, so improve names/order/icons/actions without promising custom glass. Stale Pause while already Manual must not enable Smart; stale Off never toggles On.

Keyboard: tab order follows hierarchy; focus visible; Space/Enter operate buttons/presets; sliders expose names/values and arrow/Home/End controls; Escape restores previews; all content reachable at 200% text scaling and supported DPI. Do not require dragging or sustained pointer hold. Narrator/NVDA read selected palettes and result feedback. Forced colors uses native system colors; unsupported transparency falls back automatically; reduced motion removes decorative animations. Test embedded web content and native chrome separately.

Use [WCAG 2.2](https://www.w3.org/TR/WCAG22/) as the embedded UI baseline (including contrast and keyboard/status requirements), not a blanket certification of the native app. Windows [taskbar guidance](https://support.microsoft.com/en-us/windows/experience/personalization/customize-the-taskbar-in-windows) and [Jump List documentation](https://learn.microsoft.com/en-us/windows/win32/shell/taskbar-extensions) inform the shell instructions and constraints.
