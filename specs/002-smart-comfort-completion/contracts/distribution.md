# Direct website download, installer and release contract

Status: planned integration; no download, hosting or deployment is claimed complete. Source remains private unless Hassan separately authorizes publication. Free downloads do not require open-sourcing the application or changing a repository's visibility.

## 1. Existing site and ownership

Canonical website repo: `C:/Users/Owner/Desktop/HassTech/Products/hasstech-site`.

Verified existing page worktree: `C:/Users/Owner/Documents/Codex/2026-09-08/do-y/work/hasstech-site-night-light`, clean at `d8a0d360fd08b8e84ae92fa6161dc43ea4c57ef1` during planning. Existing files: `src/pages/night-light.astro`, `src/data/products.ts`, `src/components/NavBar.astro`, `public/_redirects`. The existing page contains demonstration/research/support content and links to the HassTech organization. A focused literal download/installer search did not reveal a working download CTA in that source page.

Before execution inspect current remote/deployed revision and the actual live route. Do not overwrite the older canonical main checkout with this worktree blindly, or overwrite other product work. No current live-page audit was completed because the web reader could not retrieve the URL.

## 2. Visitor flow and layout

```text
Existing Night Light page
    → Download for Windows [version + requirements + size]
    → signed installer file
    → install / explicit missing-runtime handling
    → first launch neutral
    → optional Smart setup and comfort preview
    → optional pin/startup tips
    → working controls + offline Help
```

Hero primary CTA: `Download for Windows`. Adjacent text: `Free · Windows 11 · x64` and exact release version/file size from the manifest. Secondary action: `How to install`. Optional support remains secondary and never blocks access. Replace outdated availability claims only after a real release exists. Do not redesign the whole page or remove the existing demo/research/support work to add this flow.

Add a three-step installation section immediately below the download area or as an anchored expanded section:

1. `Download the Windows installer.`
2. `Open the downloaded file and follow the setup steps.`
3. `Open Night Light, choose a comfortable setting, and pin it to your taskbar if you like.`

Provide expandable help for locating the browser download, missing WebView2, the publisher shown by Windows, opening from Start, pinning, Smart setup, updates and uninstall. Use real screenshots from the final installer/app version; include text equivalents. Never direct users to disable antivirus, bypass an unknown publisher warning or enter administrator credentials into the app.

Keep primary download usable without JavaScript and with keyboard/screen reader. On mobile/macOS/Linux, show the Windows label and install help; no unsupported-platform success claim or automatic download. No signup, email requirement, fake urgency, preselected donation, payment prerequisite or new analytics is added.

## 3. Release manifest and URL design

One authoritative validated manifest generates website metadata, links, redirects and About/update information. Proposed manifest fields:

- schema, channel (`stable` or separate preview), product ID, semantic version, build ID, source revision, release UTC;
- supported Windows/architecture requirements, policy/config versions;
- installer filename, immutable HTTPS download URL, exact bytes, SHA-256;
- expected verified publisher identity, Authenticode verification result/timestamp metadata;
- release notes, privacy, checksums and install-help URLs;
- artifact inventory and dependency/SBOM/provenance references.

No live-looking example hashes or versions are invented. Manifest values are generated from the final signed bytes, never copied from an earlier candidate report. A manifest hash is not a replacement for a verified executable signature.

Installed About reads its bundled immutable build receipt. Online metadata is labelled Latest available and can never overwrite the Installed version/build/hash. A newer website does not make an old desktop executable current.

Proposed routes (contracts, not current live claims):

- `/night-light/`: existing product/download page.
- `/night-light/install/`: version-aware installation/help page if the expanded product section becomes too long.
- `/downloads/night-light/latest.json`: small release metadata, short cache/revalidation.
- `/downloads/night-light/windows-x64`: stable convenience redirect to the approved immutable setup file.
- `/downloads/night-light/v{version}/NightLightSetup-{version}-win-x64.exe`: immutable versioned route/file.

The page's primary anchor uses its manifest-pinned immutable download URL so an old cached page cannot display version A metadata while downloading version B through a moving alias. The stable alias is for bookmarks/update entry points. Both initiate normal file downloads without a repository interstitial. Use actual anchors, not fetch-the-entire-file-to-memory code. Do not rely on the HTML download attribute alone for cross-origin attachment behavior.

Serve executable bytes with attachment filename, appropriate binary MIME, `nosniff`, HTTPS, accurate length, range/resume support and immutable caching on versioned assets. Redirect/manifest use short or revalidated cache. Never replace bytes at an existing version URL. Missing assets fail clearly rather than return the site's HTML fallback with a 200 status.

## 4. Asset hosting decision

Use public binary hosting separate from private source. Proposed default: an owner-controlled Cloudflare R2 artifact bucket with a production custom download domain, connected by the site's normal download routes/links. Do not assume the bucket/domain already exists; creation, DNS, credentials and any cost require the appropriate execution authorization. Reuse an existing compliant artifact host if one is already configured.

Astro/Pages serves the page and small manifest; large installers belong on artifact storage rather than committing binaries to the private site repo or exceeding the static host's per-file limits. Private GitHub release URLs are not anonymous public downloads. A separately authorized public binary/docs hub is an alternative, not permission to publish private app source.

Proposed site additions, after resolving the correct checkout: `src/data/nightLightRelease.ts`, `src/components/NightLightDownload.astro`, release-manifest input under `src/data/`, `scripts/verify-night-light-release.mjs`, and install-help route/content. Extend existing `src/pages/night-light.astro`, `src/data/products.ts` and redirect configuration. These new filenames are implementation targets, not existing-code claims.

## 5. Installer design

Preferred first release: per-user signed setup EXE. Reuse a suitable existing installer toolchain; if none exists, use pinned NSIS with a minimal reviewed script and explicit third-party notices. Start with zlib compression to keep the initial dependency/license surface simple. This is an engineering choice, not a popularity or performance claim.

Proposed app files: `installer/night-light.nsi`, `installer/README.md`, build integration in `build.py`/`build_premium.py`/`release.py`, and installer validation under `test_installer_contract.py` plus isolated Windows procedures. Lock the installer/compiler/toolchain version and hashes in the build receipt. Review all dependency redistribution obligations, including runtime/helper PEs, not only NSIS.

Use a stable per-user install root under LocalAppData Programs and a stable `app/NightLight.exe` target within it. Stage versioned payloads, stop the authenticated owner cleanly, switch the payload atomically where feasible, validate, then retain one matching rollback payload. Do not launch a half-updated mix of helpers/assets. Preserve stable AppUserModelID and repair only known app shortcuts so old pins do not keep launching a stale versioned copy. Do not rename unrelated user shortcuts or force repinning.

Flow: welcome/requirements → install location and optional desktop shortcut → explicit WebView2 requirement if absent → progress → completion/Open Night Light. Start with Windows is an optional unchecked app setting; no mandatory admin elevation for normal per-user payload. Dependency installation may have separate platform requirements, which must be explained rather than silently escalated. Preserve existing autostart preference on upgrade.

Detect Evergreen WebView2 by the documented Windows mechanism. If missing, offer explicit installation through Microsoft's official bootstrapper, verifying publisher before execution. Explain network use. Offer the official standalone runtime route for offline preparation; first stable package need not bundle a large offline runtime. Cancellation/failure leaves a recoverable, clearly explained installation and no background filtering. Do not assume Edge browser presence proves the runtime is usable. Test a machine without the runtime.

No display change during installation. First clean launch is Off/neutral; upgrade respects saved intent and the migration gate. Do not switch Windows Night Light off without an explicit user action. Keep GUI and helper assets packaged locally; guide works after installation without network access.

## 6. Upgrade, rollback, removal and updates

- Upgrade detects old app instances/installation roots, preserves preferences and consent, and asks before closing a running app. Block or defer safely if the user declines; no force-kill of unrelated processes.
- Back up matching config/payload before migration with appropriate ACLs. Test interrupted download, low disk, read-only settings, interruption at each swap stage, installer rerun, downgrade rejection and clean recovery.
- Rollback restores a known-good signed payload with its compatible config while stopped; verify About, shortcut destination and runtime after rollback.
- Uninstaller requests neutral cleanup where appropriate, stops only this app, removes only manifest-owned app files/registry/shortcuts, and leaves the shared WebView2 runtime alone. Preferences retained by default, with explicit Remove my settings/history/backups. Explain recovery implications.
- `Check for updates` is explicit. It retrieves only approved public version metadata or opens the download page, showing the installed version. User chooses the signed installer. No background telemetry or silent automatic installation.
- Downloads are not uploads: no logs, location, routine data or credentials accompany an update check. Hosting may process ordinary request metadata; disclose that accurately.

## 7. Promotion and exact proof

1. Freeze clean private source revision; run the complete isolated suite and side-effect-free build.
2. Audit every bundled PE/helper/runtime/asset and dependency/license. Sign and timestamp eligible app/helper/installer binaries; verify the actual full payload inventory rather than a stale hardcoded count.
3. Generate final manifest, SHA-256 checksums, SBOM and provenance after signing. Verify signature chain, publisher, timestamp and payload hashes. Credentials stay in approved signing storage, not repo/config/UI.
4. Stage immutable assets on the approved host. Verify GET bytes, headers, range request, signature, size and hash independently.
5. Build a site preview from the matching manifest. Verify keyboard/mobile/no-JS download/help and actual completed download. Download the exact file a visitor gets and install it in a clean Windows account/VM.
6. Verify installed About/build/hash, native UI, Smart, Off, startup, taskbar pin/second-instance behavior, update and uninstall. Record supported hardware separately from VM-only results.
7. Complete quality/soak gates in quickstart.md. Obtain explicit publication/deployment authorization; signing/hosting cost or new credentials also need real authority.
8. Promote by updating the single approved manifest/site deployment and stable alias only after asset checks succeed. Failed build must not replace stable pointers.
9. From the live public page, download again without authenticated repository access, verify final bytes/signature/version, install and test. Record website deploy revision plus app build revision together.
10. Prove rollback by restoring the previous approved manifest/alias, not deleting immutable old assets. Public rollback stops new downloads of the bad version but does not silently downgrade already installed apps; provide explicit affected-user guidance.

Receipts distinguish click, completed download, installed launch and physical display behavior. No new analytics is required to prove these controlled tests. Automatic monitoring after release is outside this plan's execution unless separately requested.

## Sources and access boundaries

- [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution): runtime detection/distribution choices; validate installed behavior separately.
- [NSIS license](https://nsis.sourceforge.io/License): licenses and commercial-use permission; include selected components' notices.
- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/) and [R2 public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/): hosting constraints and public custom-domain setup, not proof this project's hosting exists.

Signing identity, hosted domain/bucket, newest deployed source and physical device access remain explicit release prerequisites. None prevents completing this design; none is assumed granted by it.
