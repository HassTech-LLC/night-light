# Sunset-Led Adaptive Smart Mode

## Product contract

Smart Mode follows the local natural light-dark cycle without requiring a fixed bedtime. Sunset is the primary anchor. An optional user bedtime or a transparent, local-only learned sleep window can move protection earlier, but never silently later.

Smart Mode must never claim to know the user's melatonin concentration. It controls display output using research-informed timing and reports exactly which stage and filter are active.

## User-visible modes

### Solar Sync — default

- Requires country and ZIP/postal code.
- Calculates sunset, civil dusk, sunrise, and civil dawn locally after coarse geocoding.
- Begins a gradual transition near sunset.
- Does not require a bedtime.

### Adaptive Solar — recommended after learning

- Starts from the Solar Sync curve.
- Learns a broad likely sleep and wake window from local-only session timing.
- Ensures the stronger portion of the curve is not later than three hours before the likely sleep window.
- Shows the learned window and confidence; the user can edit, pause, reset, or disable learning.

### Manual

- Keeps direct warmth and brightness controls.
- Manual changes suspend automation for 60 minutes by default, then rejoin the current curve gradually.

## Solar curve

The initial uncalibrated curve uses relative output, not a claim of absolute m-EDI.

| Solar time | Stage | Balanced proxy | Maximum Protection proxy |
|---|---|---:|---:|
| Sunset − 60 min | Dusk begins | 6500 K / 100% | 6500 K / 100% |
| Sunset | Solar boundary | 4800 K / 90% | 4200 K / 80% |
| Sunset + 60 min | Early evening | 3200 K / 65% | 2700 K / 50% |
| Sunset + 180 min | Biological night | 2200 K / 45% | 1700 K / 30% |
| Sunset + 240 min | Deep night | 1700 K / 30% | 1200 K / 15–20% |

The schedule is interpolated continuously. The initial progression function is:

`ease(x) = 0.5 - 0.5 × cos(πx)` for `x` from 0 to 1.

Recompute and apply the target every 15–30 seconds. A resumed or newly launched app fades to the current target over 90–180 seconds rather than jumping.

## Adaptive guardrail

The app records only these local events:

- date;
- last sustained active time in the evening;
- session lock or display-off time;
- first sustained activity after waking;
- manual “winding down” or “awake” actions.

It never records application names, window titles, keystrokes, screenshots, browsing, or content.

After at least seven usable nights, calculate a robust median sleep-start estimate using the latest 14 nights. Reject isolated nights more than three hours from the median unless the pattern repeats. Confidence is Low, Medium, or High based on sample count and variability.

If an estimated sleep time exists:

- `presleep_guard = estimated_sleep - 3 hours`
- the curve may move earlier so its early-evening target is reached by `presleep_guard`;
- the curve never moves later than the pure solar schedule;
- acceleration is limited to a minimum 20-minute transition unless the user chooses Immediate Maximum.

If data is missing or confidence is Low, use Solar Sync without pretending personalization.

## Location and privacy

1. Ask for country plus ZIP/postal code, not a street address.
2. Resolve it once to an approximate centroid and cache latitude/longitude locally.
3. Compute solar times offline using documented NOAA-style solar equations.
4. Send no recurring location requests.
5. Provide Delete Location and Reset Learning actions.
6. Use the Windows time zone as authoritative and recalculate after daylight-saving or time-zone changes.

For locations with no sunrise or sunset on a given date, Adaptive Solar uses the learned sleep/wake window. With no learned data, the UI requests an optional quiet-hours window rather than inventing a solar event.

## Windows Night Light exclusion

- Windows Night Light on: neutralize the entire HT display transform, including software dimming, and report `Windows ON · HT PAUSED`.
- Never automatically turn Windows Night Light on.
- Offer a one-way `Turn Windows Night Light off` action.
- Do not resume HT until Windows is confirmed off; then fade to the current Smart target.
- No mode may expose a “layer both” option.

## Status language

Examples:

- `Solar Sync · Dusk begins in 18 min`
- `Adaptive Solar · Early evening 42%`
- `Protected curve · estimated sleep window 11:20 PM–12:10 AM`
- `Windows Night Light ON · Night Light by HT paused`
- `Location unavailable · using learned schedule`

The word `protected` describes the selected product curve, not a guarantee of melatonin preservation.

## Accessibility and safety

- Always expose Reset to Neutral in the tray and Jump List.
- Add an emergency keyboard reset before public beta.
- Do not reduce contrast below readable minimums automatically.
- Pause warmth for color-critical work with a visible expiration.
- Respect high-contrast and assistive display modes.
- Recover correctly across HDR changes, monitor hot-plug, lock, sleep, wake, and crash restart.

## Acceptance gates

- Solar times pass known NOAA test vectors across seasons and time zones.
- No visible single-step transition during normal running, resume, or schedule edits.
- No HT warmth or dimming matrix is active while Windows Night Light is detected on.
- All scheduling tests run with the real display backend disabled.
- ZIP and learned timing never leave the machine after one-time coarse geocoding.
- At least 14 consecutive overnight soak runs produce no timer drift, orphaned filter, or failure to restore neutral.
- Representative LCD, OLED, HDR, and multi-monitor systems receive separate real-machine evidence.
- Health-facing claims remain relative until spectral measurement establishes m-EDI for representative conditions.
