# Feature Specification: Sunset-Led Adaptive Smart Mode

**Feature branch:** `001-sunset-smart-mode`  
**Created:** 2026-09-08  
**Status:** Ready for implementation

## User scenarios

### 1. Automatic natural dusk without a bedtime

As a person whose bedtime varies, I enter my country and ZIP/postal code once. Night Light by HT begins a barely perceptible transition around local sunset, deepens it through the evening, and restores daylight output around sunrise without requiring a fixed bedtime.

**Acceptance:** The UI shows tonight's sunset, current stage, next stage, and effective filter. The transition never visibly jumps during normal operation.

### 2. Adaptive protection for an irregular schedule

As a person with irregular nights, I can enable local learning. The app estimates a broad sleep window from minimal session timing and moves the stronger evening curve earlier when necessary.

**Acceptance:** The inferred window and confidence are visible and editable. The app never delays protection later than the solar-only schedule. Reset Learning removes the observations and estimate.

### 3. No double filtering

As a Windows user, I can always tell whether Windows Night Light or Night Light by HT controls warmth.

**Acceptance:** When Windows Night Light is detected, the entire HT display effect pauses, the UI states that clearly, and the only native mutation offered is a user-triggered Turn Windows Night Light off action.

### 4. Safe manual override

As a user doing color-sensitive work, I can pause Smart Mode temporarily and know when it will return.

**Acceptance:** Pause defaults to 60 minutes, displays a countdown, and rejoins the current target over at least 90 seconds. Reset to Neutral is always available.

## Functional requirements

- **FR-001:** Store country and postal code locally.
- **FR-002:** Resolve postal code to a coarse centroid through an explicit one-time lookup and cache it.
- **FR-003:** Calculate sunset, sunrise, civil dusk, and civil dawn locally for each date.
- **FR-004:** Start the Solar Sync curve without requiring a bedtime.
- **FR-005:** Update the target no more frequently than every 15 seconds and no less frequently than every 30 seconds while active.
- **FR-006:** Use an eased, monotonic interpolation without discrete temperature or brightness steps.
- **FR-007:** Fade to the current target over 90–180 seconds after launch, resume, or a significant clock correction.
- **FR-008:** Optionally learn sleep/wake windows from local timing events without collecting content.
- **FR-009:** Show the learned window, sample count, variability/confidence, and next scheduled event.
- **FR-010:** Never move protection later than the Solar Sync baseline.
- **FR-011:** Pause the entire HT display matrix, including dimming, whenever Windows Night Light is on or cannot be safely disambiguated under the selected fail-safe policy.
- **FR-012:** Provide Delete Location, Reset Learning, Pause, Resume, and Reset to Neutral actions.
- **FR-013:** Handle daylight-saving, time-zone, clock, suspend/resume, and no-solar-event conditions.
- **FR-014:** Keep all health wording within the evidence boundary documented in the repository.

## Non-functional requirements

- Scheduler calculations are pure and independently testable.
- Automated tests never initialize the Windows display backend or use real application data.
- Normal scheduling consumes negligible CPU and performs no recurring network requests.
- The compact flyout remains usable at the current footprint.
- State survives restart without an unexpected filter jump.

## Success criteria

- All published solar test vectors are within one minute in the ordinary latitude range supported by the chosen algorithm.
- Unit tests cover solstices, equinoxes, DST changes, midnight crossings, polar no-event dates, manual pauses, resume catch-up, and native-filter exclusion.
- A 14-night simulated adaptive dataset produces a stable, explainable estimate and rejects a single extreme outlier.
- Fourteen overnight soak runs finish with the correct stage and neutral recovery.
- No automated test changes the physical screen, taskbar, autostart registry, or production config.

## Out of scope for this feature

- Diagnosing a circadian or sleep disorder.
- Estimating actual melatonin concentration.
- Automatically turning Windows Night Light on.
- Cloud accounts, cross-device activity synchronization, or behavioral telemetry.
- Public claims of guaranteed sleep improvement.
