# Design decisions and evidence boundaries

Date: 2026-09-09. This is a decision record for implementation planning, not a new systematic review. Primary evidence ledger: [19-source product review](../../docs/PRODUCT_RESEARCH_AND_ROADMAP_2026-09-09.md). Numerical controller/UX budgets in this feature are hypotheses to validate.

## R1 — One Smart controller

Decision: one mode with independent timing and comfort, plus transient catch-up. Rationale: fewer conflicting profiles and clearer state ownership. Alternative rejected: several modes combining start time, fade duration and maximum strength, which obscures what each choice changes. No source establishes one universally optimal fade duration.

## R2 — Deadlines are goals, comfort limits are constraints

Decision: show a feasible ETA; do not accelerate automatically without bound to meet a missed time. Rationale: long fades can arrive too late, while rushed catch-up can bother users. The [Mao 2025 publisher abstract](https://www.sciencedirect.com/science/article/pii/S0141938225000642) motivates considering the whole exposure trajectory, but full methods were not available and its proposed exposure threshold is not adopted. The controller limits are engineering candidates, not conclusions of that paper.

## R3 — Explicit timing and preferred appearance, no biological inference

Decision: solar convenience or personal ready/return times; independent warm/dim preference preview. [Brown et al. consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC8929548/) concerns healthy adults and measured light at the eye, not screen slider percentages. [The Night Shift trial](https://pubmed.ncbi.nlm.nih.gov/33867308/) did not establish an overall sleep benefit from that phone feature. Do not generalize mechanism evidence into app efficacy. Idle-time consistency is not measured sleep; new routine suggestions remain deferred.

## R4 — Separate desired, accepted and physically verified state

Decision: owner reducer, transactional Save and explicit availability. [Microsoft's fullscreen color API](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magsetfullscreencoloreffect) returns command success and documents a system-wide last-transform behavior. It does not certify emitted light. A singleton protects HT against HT duplicates, not against all third-party tools. Off recovery bypasses storage gating but reports durability honestly.

## R5 — Premium means coherent and readable

Decision: one surface; small number of material systems; real independent color presets; opaque accessible fallback; short contextual help. [WCAG 2.2](https://www.w3.org/TR/WCAG22/) provides an embedded-web baseline; native host and assistive technology still need separate tests. A Windows Jump List remains native rendering, per [Microsoft's shell documentation](https://learn.microsoft.com/en-us/windows/win32/shell/taskbar-extensions). New palette seeds are aesthetic proposals, not claims that research ranks their popularity.

## R6 — Direct download without publishing private source

Decision: signed per-user installer, immutable public assets, single manifest and direct site CTA. Preserve the existing page and secondary optional support. NSIS is the fallback installer-builder proposal under its [documented licenses](https://nsis.sourceforge.io/License); validate exact bundled components. Follow [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution). Store large assets outside Pages when needed under [Pages limits](https://developers.cloudflare.com/pages/platform/limits/); proposed production hosting is [R2 with a custom domain](https://developers.cloudflare.com/r2/buckets/public-buckets/). Hosting/signing configuration remains execution work. No source publication or billing change follows from free distribution.

## R7 — Finite release, separate evidence ledgers

Decision: software, supported hardware, accessibility, comfort and distribution gates define this utility's release. Fourteen nightly sessions are a practical reliability gate, not scientific validation. Optical measurements gate quantified exposure claims; proper clinical evidence gates health outcomes. Neither is a required research project just to ship honest warmth/dimming controls.

## Constitution amendment proposal v1.1.0

Replace the v1.0.0 sunset/inferred-timing product constraint with:

> Sunset is the default convenience schedule. An explicitly chosen personal schedule is authoritative. Smart follows user-confirmed comfort limits; inferred routines cannot directly change the v2 schedule or display output. No new collection or expanded consent is implied by upgrading. A clearly labelled legacy adapter may retain previously consented behavior until the user chooses migration, without new data sources or extended retention.

Rationale: user accepted the refined planning direction; research does not validate desktop inactivity as biological timing. Migration preserves existing expectations rather than silently changing them. Increment version/date and update the project decision note when implementation begins. Do not amend the immutable safety/privacy/truth principles. No runtime implementation may claim v2 compliance while silently retaining legacy inference authority.

## Planning access/validation record

Main agent read current constitution, prior spec/plan, research, graph architecture and controller bodies; inspected website worktree and actual page download/support literals. Two independent read-only reviews challenged controller and UI/release requirements. Incorporated preview-from-Off, emergency-Off storage failure, preview restoration timing, moving-target catch-up, short-night feasibility, Manual resume, separate pause clock, and explicit legacy migration exception.

The live product page could not be retrieved by the web reader; no live download is certified. Existing source test counts, installation hashes and older release receipts were not rerun as product verification during planning. No claim of new controller, installer or site behavior is made.
