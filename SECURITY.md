# Security Policy

## Supported versions

Night Light by HT is pre-release software. Security fixes are applied to the latest development version only.

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. Use the repository's private security-advisory channel once the GitHub remote is created, or contact the repository owner privately.

Reports should include affected version or commit, reproduction steps, impact, and any suggested mitigation. Never include credentials or unrelated personal information.

## Security boundaries

- The app changes a process-global Windows display color effect and must always restore neutral output on normal shutdown.
- Local IPC accepts commands only with a random per-install token, uses bounded reads, and returns an acknowledgement. Cross-version upgrade and multiple-user validation are still required before a public beta.
- The one-way Windows helper may turn Windows Night Light off; it must never turn it on or silently layer two warmth filters.
- ZIP/postal-code and learned activity data for Smart Mode must remain local except for an explicit one-time coarse geocoding lookup.
