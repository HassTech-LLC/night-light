# Privacy

Night Light is designed as a local-first desktop utility.

## Current version

The current application stores warmth, brightness, enabled state, transition preference, autostart preference, and a random per-user localhost IPC secret in `%APPDATA%/NightLightWidget` (or the platform fallback directory). It does not require an account or analytics service. The reusable secret stays on disk and is never transmitted. Bounded local loopback messages contain fresh nonces, direction-bound authentication proofs, commands, and command-bound acknowledgements. The client verifies the server proof before sending a command. This protects against an unauthenticated first listener and replay; it does not protect against software that can already read the same user's configuration. Configuration writes are serialized across processes and atomically replaced. Legacy bearer-first clients are intentionally incompatible and must be closed by the user before upgrading; the new client fails closed rather than taking over an occupied endpoint.

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
