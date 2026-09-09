# Implementation Plan: Sunset-Led Adaptive Smart Mode

## Phase 1 — Pure foundations

1. Implement postal centroid model and cached location schema.
2. Implement tested solar calculations with NOAA reference vectors.
3. Implement the piecewise solar curve and eased interpolation.
4. Implement configuration migration without changing current display defaults.

## Phase 2 — Controller and state truth

1. Add a schedule controller that evaluates the pure target on a 15–30 second timer.
2. Reconcile every target through the Windows Night Light exclusion policy.
3. Add launch/resume catch-up fades and manual-pause expiry.
4. Expose configured stage, effective stage, next transition, and failure state.

## Phase 3 — Adaptive learning

1. Record minimal local session timing events.
2. Calculate a robust 14-night sleep window with confidence.
3. Add reset, edit, delete, and disable controls.
4. Verify the adaptive guard can only move protection earlier.

## Phase 4 — UI and release evidence

1. Add the compact Smart Mode setup and Tonight status.
2. Add accessibility and emergency-neutral controls.
3. Run the multi-monitor/HDR/sleep-wake device matrix.
4. Complete overnight soak testing and document optical measurement status.

## Architecture decisions

- Solar math, learning, and target calculation remain pure modules.
- Network geocoding is a replaceable one-shot adapter.
- Windows activity observation records timestamps only.
- The existing engine remains the sole owner of the HT display transform.
- Windows Night Light exclusion remains upstream of all engine applications.

