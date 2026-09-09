# Night Light by HT

Night Light by HT is a compact Windows 11 evening-light controller from HassTech. It provides visible, one-click control over display warmth and software dimming while refusing to stack its warmth transform over Windows Night Light.

> **Status: alpha.** The working desktop filter is present. The researched sunset-led adaptive Smart Mode is fully specified but is not yet wired into the installed application. The project does not claim to prevent melatonin suppression or treat a sleep condition.

## Current capabilities

- System-tray and pinned-taskbar integration with a compact Windows-style flyout.
- Left-click toggle and smooth display transition.
- Warmth control from 6500 K to an intentionally extreme 1200 K endpoint.
- Software brightness attenuation for darker late-night use.
- Presets for Candle, Night Owl, Cozy, and Daylight.
- Separate, visible Windows Night Light and Night Light by HT states.
- Automatic suspension of every HT display effect whenever Windows Night Light is detected.
- A one-way action that can turn Windows Night Light off but cannot turn it on.
- Jump List status and quick actions; sliders remain in the flyout because Windows taskbar right-click surfaces are Jump Lists, not arbitrary embedded UI.
- Per-install authenticated localhost commands for single-instance taskbar actions.

## Smart Mode direction

Smart Mode will be **sunset-led and locally adaptive**:

- ZIP/postal code supplies a coarse location for daily sunset and sunrise.
- A gentle dusk transition begins around local sunset, even when the user has no fixed bedtime.
- Local-only activity history can learn a likely sleep window and make sure the display reaches its protective state early enough.
- An optional bedtime acts as a guardrail, not a requirement.
- Sunrise and wake activity restore neutral daytime output.

See [Smart Mode specification](docs/SMART_MODE_SPEC.md) and [circadian research](docs/research/CIRCADIAN_LIGHTING.md).

## Install for development

Requirements: Windows 11, Python 3.11–3.14, and the .NET Framework C# compiler included with Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python main.py --background
```

To run tests or diagnostics without touching the physical display:

```powershell
$env:NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND = "1"
$env:NIGHT_LIGHT_BY_HT_CONFIG_DIR = Join-Path $env:TEMP "night-light-by-ht-test"
python -m pytest
```

## Build

```powershell
python build.py
```

The unsigned development bundle is created under `dist\`. Building is side-effect free by default. To register the Jump List on the current machine after a successful build:

```powershell
python build.py --register-jump-list
```

No generated executable is committed to the repository.

## Repository map

- `main.py` — command-line and single-instance entry point.
- `tray_app.py` — tray lifecycle, Jump List synchronization, and local IPC.
- `ui_flyout.py` — compact control flyout.
- `nightlight_engine.py` — Windows Magnification color matrix and transitions.
- `windows_nightlight.py` — read-only native-state detection.
- `display_status.py` — pure effective-state presentation model.
- `docs/` — architecture, privacy, research, and Smart Mode contract.
- `specs/001-sunset-smart-mode/` — Spec Kit feature definition and implementation plan.

## Privacy and scientific boundary

Night Light by HT is designed to work locally. Smart Mode should retain only coarse location and minimal timing observations; it must never collect screen content. See [Privacy](docs/PRIVACY.md).

Color temperature is not a biological measurement. Actual circadian exposure depends on display spectrum, output intensity, room lighting, viewing distance, timing, duration, and individual sensitivity. See [Research](docs/research/CIRCADIAN_LIGHTING.md).

## License

MIT © 2026 HassTech. See [LICENSE](LICENSE).
