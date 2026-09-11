# Architecture

## Current system

Night Light by HT is a Windows-only Python desktop application packaged with PyInstaller. Three small C# helpers provide Windows shell surfaces that are awkward to implement through Python alone.

```text
main.py
  -> single-instance command dispatch
  -> TrayApp
       -> PremiumFlyout
       -> NightLightEngine
       -> Windows Night Light detector
       -> effective display-status model
       -> tray icon and Jump List helpers
       -> localhost IPC
```

### Components

- `nightlight_engine.py` owns the Windows Magnification API color matrix and interpolation.
- `tray_app.py` coordinates state, tray input, Jump List refresh, and local command dispatch.
- `premium_ui.py` hosts the premium control surface and its private desktop bridge.
- `config_manager.py` persists settings under the user's roaming application-data folder and manages autostart.
- `windows_nightlight.py` reads the current native state. Windows exposes no supported public desktop toggle API, so this detector is explicitly best-effort.
- `display_status.py` derives honest visible states without touching Windows APIs.
- `windows_nightlight_off.cs` provides the user-triggered, one-way native-off action.
- `wpf_jumplist.cs` and `shortcut_appid_register.cs` register taskbar integration.

## Planned Smart Mode boundary

Smart scheduling should be implemented as pure, testable modules before UI wiring:

```text
postal_location.py       coarse one-time geocoding and local cache
solar_clock.py           sunrise/sunset/twilight calculations
sleep_window.py          local-only robust timing inference
smart_schedule.py        stage machine and target calculation
schedule_controller.py   timer, resume handling, and engine application
```

Pure calculations must have no display, registry, network, or UI side effects. The controller may call the engine only after resolving the Windows Night Light exclusion policy.

## Known technical risks

- Windows Magnification color effects are process-global and can conflict with another application using the same mechanism.
- Native Night Light detection relies on an undocumented CloudStore payload and can drift after Windows updates.
- Local TCP IPC uses a random per-install token and bounded reads; migration from the legacy unauthenticated protocol still needs installed-upgrade testing.
- Autostart behavior and crash recovery require additional fail-safe testing.
- Software color attenuation is not the same as hardware backlight control and is not calibrated to m-EDI.
- Multi-monitor, HDR, and remote-desktop behavior require a formal device matrix.

## Release boundaries

- Unit tests are not real display proof.
- A successful PyInstaller build is not an installer, signature, or public release.
- A local Git commit is not a GitHub publication.
- A visible orange display is not proof of a biological effect.
