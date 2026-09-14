# SignPath Foundation application

Prepared 2026-09-14 for submission at <https://signpath.org/apply>. This is a
working draft for Hassan to review, adjust and submit; nothing here has been
sent. Certificates issued through the programme carry the subject name
**SignPath Foundation**, not HassTech. That is inherent to the programme, and
the download page must not imply otherwise.

## Eligibility self-check

SignPath Foundation's published conditions, checked against this project.

| Condition | Night Light by HT | Status |
|---|---|---|
| OSI-approved license for all components, no commercial dual-licensing | GNU GPL version 3 or later from 0.3.0 onward. No dual-licensing offered or planned while enrolled | Met |
| No malware or potentially unwanted behaviour | Local display filter; no telemetry, no bundled offers, no network calls except one user-initiated postal lookup | Met |
| No proprietary, non open-source component, "especially code published by a maintainer or an affiliated person/organization" | No HassTech proprietary code. Three third-party Microsoft redistributables ship in the payload; see the disclosure below | Disclose |
| Actively maintained | Continuous commits; public CI on every push | Met |
| Already released in the form to be signed | Unsigned Early Access 0.3.0 published from the website | Met |
| Functionality documented on the download page | <https://hasstechapi.com/night-light/> plus an illustrated install guide | Met |
| Binaries built from source in a verifiable way | GitHub Actions builds the payload, emits a source manifest, binary-origin receipts, SBOM and checksums, then verifies the archive | Met |
| Every release manually approved for signing | Intended workflow: tag, review, approve in SignPath | Met |

## Disclosure to include in the application

State this plainly rather than waiting to be asked:

> The Windows control surface is hosted in Microsoft Edge WebView2. The payload
> therefore includes three Microsoft redistributables from the WebView2 SDK:
> `Microsoft.Web.WebView2.Core.dll`, `Microsoft.Web.WebView2.WinForms.dll` and
> `WebView2Loader.dll`. These are third-party components redistributed under
> Microsoft's WebView2 SDK license, not proprietary code authored by the
> maintainer. The WebView2 Runtime itself ships with Windows 11 and is not
> bundled. `NOTICE` carries a GPL section 7 additional permission covering
> these components, and `THIRD-PARTY-NOTICES.txt` records their licenses.
> Every other binary in the payload is built from the public source: the
> application executable (PyInstaller over CPython) and three small C# helpers
> compiled from `.cs` files in the repository.

If SignPath treats bundled third-party redistributables as disqualifying, the
fallback is to load the WebView2 SDK assemblies from the user's own Runtime
installation rather than shipping them. That is a real engineering change, not
a documentation change, so establish SignPath's position before starting it.

## Application content

**Project name.** Night Light by HT

**Project URL.** <https://github.com/HassTech-LLC/night-light>

**Download page.** <https://hasstechapi.com/night-light/>

**License.** GNU General Public License version 3 or later, with a section 7
additional permission for the Microsoft Edge WebView2 SDK and Runtime recorded
in `NOTICE`.

**Description.** Night Light by HT is a free Windows 11 utility that reduces
evening screen output. It applies a warmth and software-dimming transform
through the Windows Magnification API, offers a sunset-led automatic schedule
computed locally from saved coordinates, and refuses to stack its transform on
top of the built-in Windows Night Light. It stores settings locally, requires
no account, and makes no medical or sleep claims.

**Maintainer.** HassTech LLC. Sole copyright holder; all commits to date are
from the maintainer's own accounts.

**Artifacts to sign.** One installer, `NightLightSetup-<version>-Early-Access.exe`,
and the four PE files it carries: `NightLight.exe`, `wpf_jumplist.exe`,
`shortcut_appid_register.exe`, `windows_nightlight_off.exe`.

**Build system.** GitHub Actions on `windows-latest`, pinned by SHA. The
workflow installs an exact managed CPython through `uv`, runs the full test
suite, builds the payload with PyInstaller, packages a deterministic archive,
and generates a CycloneDX SBOM, a source manifest and SHA-256 checksums. A
signing step already exists in the workflow and currently fails closed when no
signing identity is configured.

**Release process.** Work merges to `main` through pull requests with CI
required. A release is cut by tagging. The tagged run produces the candidate;
signing is then approved manually before the artifact is published to the
website. Release identity, size and SHA-256 are recorded in a manifest in the
website repository and verified by a check script at build time.

**Code review policy.** The project is currently maintained by one person.
Changes land through pull requests, CI must pass, and the repository has secret
scanning, push protection and Dependabot enabled. Security review evidence for
the current release lives under `docs/security/`. State this honestly rather
than implying a multi-reviewer process that does not exist.

## After approval

1. Create the SignPath project and link the GitHub repository.
2. Add the signing step to the tagged-release job using SignPath's GitHub
   Action, keeping the existing fail-closed behaviour when signing is
   unavailable.
3. Sign all four PEs and then the installer, in that order, so the installer's
   own receipt covers already-signed payloads. The repository's release
   contract already forbids signing first and modifying receipt-bound payloads
   afterwards.
4. Verify with `Get-AuthenticodeSignature` that every artifact reports `Valid`
   and carries an RFC 3161 timestamp.
5. Set `signed` to true in the website release manifest only after the
   published bytes are the signed ones, and update the download page to say the
   publisher shown by Windows is SignPath Foundation.
6. Record the SignPath account custodian and recovery path in the vault,
   without credentials.

## Constraints this creates

- **No commercial dual-licensing while enrolled.** Selling a separate
  proprietary license alongside the GPL would end eligibility. Donations, paid
  support and selling GPL copies all remain fine.
- **The publisher name is SignPath Foundation.** SmartScreen reputation accrues
  to that shared identity, which builds trust faster than a brand-new private
  certificate would, but it is not the HassTech name.
- **Leaving the programme means buying a certificate.** If the project later
  goes proprietary or adopts dual-licensing, signing reverts to a paid route.
