# Privacy

Night Light by HT is designed as a local-first desktop utility.

## Current version

The current application stores warmth, brightness, enabled state, transition preference, autostart preference, and a random per-install localhost IPC token in the user's application-data folder. It does not require an account or analytics service. The token is used only to reject unauthenticated local commands and is never sent over a network interface.

## Smart Mode design

Smart Mode may store:

- country and ZIP/postal code;
- approximate postal-code centroid;
- calculated solar events;
- minimal evening last-active, lock/display-off, and morning first-active timestamps;
- an inferred sleep window and confidence;
- explicit manual overrides.

It must not store or transmit:

- street address or precise GPS location;
- application names, window titles, URLs, screenshots, keystrokes, or screen content;
- health records or a claim about actual melatonin levels;
- personal timing history to HassTech or another service without separate, explicit opt-in.

A one-time postal-code lookup may be used to obtain a coarse centroid. The UI must identify the service before the request, cache the result locally, and provide Delete Location and Reset Learning actions.

No telemetry is enabled in the repository baseline.
