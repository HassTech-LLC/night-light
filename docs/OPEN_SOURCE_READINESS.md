# Open-Source Readiness

## Present state

The repository has a name, MIT license, contribution and conduct guidance, a security policy, dependency metadata, Windows CI, Spec Kit structure, research citations, architecture notes, privacy boundaries, and an initial feature specification.

## Still required before a public release

- Create and review the GitHub remote under the intended HassTech organization.
- Validate the new authenticated localhost IPC across clean install, upgrade, concurrent launch, and multiple Windows user accounts; consider a Windows-native per-user IPC boundary before stable release.
- Add an emergency neutral-reset shortcut and crash watchdog.
- Validate autostart, install, upgrade, uninstall, and prior-state restoration.
- Complete HDR, multiple-monitor, sleep/wake, hot-plug, Remote Desktop, and Windows-version testing.
- Add signed installer and executable provenance, checksums, SBOM, and release notes.
- Verify third-party licenses and generated-helper source/build reproducibility.
- Measure representative displays before publishing biological efficacy comparisons.

The repository may be shared for source review now, but it should remain clearly labeled alpha and should not be marketed as a medically validated sleep product.
