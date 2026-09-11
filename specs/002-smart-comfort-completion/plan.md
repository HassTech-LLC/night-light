# Completion Plan: Night Light Smart Comfort

Date: 2026-09-09 | Feature key: `002-smart-comfort-completion` | Actual checkout: `main`, unchanged | Status: implementation in progress; see ../../docs/SMART_COMFORT_IMPLEMENTATION_PROGRESS.md for verified increments and remaining work.

## Outcome and document map

Deliver one dependable Smart experience, a premium accessible native-hosted interface, easy offline instructions, and a signed app downloaded directly from the HassTech site. Completion means the website-to-working-desktop journey, not only a browser concept or successful build.

Read [spec.md](spec.md) for scope, [data-model.md](data-model.md) for state/migration, [UI contract](contracts/ui-and-commands.md) for design/help, [distribution contract](contracts/distribution.md) for download wiring, [tasks.md](tasks.md) for execution, [quickstart.md](quickstart.md) for gates, and [research.md](research.md) for rationale.

## 1. Current baseline and integration seams

Canonical source: `C:/Users/Owner/Desktop/HassTech/Products/night-light-by-ht`. Desktop payload: `C:/Users/Owner/Desktop/Projects/Night Light`, not the source repository. The worktree is dirty; preserve unrelated work. Historical test/build/install reports do not certify the new version.

The source contains solar Smart, opt-in idle-based learning, WebView2 UI, native tray/taskbar, owner-process IPC, Windows exclusion, manual controls, pause and comparison. The indexed `SmartController.tick` samples a target and starts a 25-second fade, with longer rejoin fades and a `fade_until` gate. `NightLightEngine.set_state` immediately assigns requested settings, then interpolates RGB through 16 ms callbacks using cubic ease-out. These are integration seams, not justification for a framework rewrite.

Website canonical repo: `C:/Users/Owner/Desktop/HassTech/Products/hasstech-site`, Astro/Tailwind on Cloudflare Pages per README. Its main checkout is older than a registered feature worktree. The existing Night Light page was located at `C:/Users/Owner/Documents/Codex/2026-09-08/do-y/work/hasstech-site-night-light/src/pages/night-light.astro`, clean worktree commit `d8a0d360fd08b8e84ae92fa6161dc43ea4c57ef1`. Extend this existing page rather than creating a duplicate. The web reader could not retrieve `https://hasstechapi.com/night-light/`; current live deployment is not verified. Confirm the newest remote/deployed state before implementation and preserve unrelated site work. Private-source distribution remains the safe default; no repository visibility change is part of this plan.

## 2. Technical context

Retain Python 3.11–3.14 compatibility, the pinned release runtime, native helpers and WebView2. Keep pytest, isolated bridge/UI tests and explicit native Windows checks. Extend the existing build/release pipeline; do not add a service or another app framework.

Introduce pure modules only where useful: `smart_state.py` (reducer), `smart_schedule.py` (dated trajectories), `smart_transition.py` (bounded output). Integrate through `smart_mode.py`, `nightlight_engine.py`, `premium_ui.py`, `tray_app.py` and `config_manager.py`. Update packaging declarations for new modules. Versioned local JSON remains the store.

Initial stable target is Windows 11 x64 on declared tested builds. ARM64, HDR, RDP/virtual displays and unusual GPU paths remain conditional until their rows pass. Global transforms cannot provide per-monitor calibration. No cloud accounts, health score, automatic updater service, ambient sensing or hardware backlight integration in this release.

## 3. Smart product behavior

### Two setup sections

**Timing:** Sunset schedule is preselected. Initial engineering proposal: preferred appearance ready one hour after local sunset; warmth ordinarily starts 180 minutes before that, optional dimming 60 minutes before. Show actual start/ready/return times before enabling, including earlier starts required by rate limits. This is convenience tuning, not a physiological optimum.

My schedule asks `Evening settings ready at` and `Return to normal by`. Neither requires location or tracking, and neither is called measured bedtime/wake time. Solar morning recovery ends at sunrise; personal recovery ends at the entered time. Initial requested morning transition is 45 minutes, extended where necessary by rate limits.

Advanced exposes evening warmth lead 60–240 minutes, separate dimming lead 15–120 minutes, and solar ready offset -120 to +180 minutes. These alter timing, not intensity. Do not proliferate Smart mode names.

**Appearance:** First-run preview starts at a proposed 4000 K software target, dimming off. Preview is reversible, not a saved default applied without consent. Warmth starting points: Soft 4500 K, Warm 3500 K, Deeper 2500 K, custom. Dimming: 0%, 5%, 10%, 20%, custom. These are preference examples, not health levels. Retain existing stronger settings through migration; put extremes behind Advanced/readability preview. Kelvin is approximate software targeting; dim percentage is this app's attenuation, not hardware brightness.

### Everyday actions

- Normal Smart follows a continuous planned trajectory, not repeated 25-second ease-out restarts.
- Late enable/resume uses transient Catching up. Comfort-rate ceilings are hard; deadlines soft. Show a feasible projected completion, never jump to meet a missed time.
- Pause Smart requests neutral for 60 minutes by default, with alternate durations and a displayed return time.
- Adjusting a slider in Smart holds that appearance for 60 minutes. Show Temporary adjustment, Resume Smart, and Save as nightly preference.
- Manual stays Manual indefinitely. Selecting Smart explicitly clears a manual hold; selecting Manual cancels a Smart pause.
- Off/emergency neutral persists, cancels transient work and requests neutral promptly. Explicit recovery may bypass gradual limits.
- Apply now is a deliberate immediate endpoint action, still bounded by validated intensity and availability policy. Never invoked automatically.
- Compare temporarily shows neutral, ends on release/blur/close/Escape or ten-second native timeout, then resolves current intent rather than replaying a stale target. Provide a timed toggle alternative.

Ending a user-invoked preview restores the latest effective intended appearance through a short 500 ms transition, not the multi-minute catch-up path. This explicitly reversible preview exception also applies on timeout/blur/close, but never overrides a newer Off, safety conflict or invalidated token. The restoration target is the current schedule appearance, not the final nightly endpoint. Explicit Off remains prompt neutral.

### Short nights and morning priority

Planner aims to be neutral by the morning anchor. If evening/morning ramps overlap, reduce or omit the peak and explain it; do not extend deep dimming through the day or oscillate. Runtime comfort ceilings still win. If an unexpected event makes neutral-by-morning infeasible, show the later ETA plus Return to normal now. No promise that both a hard deadline and gentle change can always be met.

Compute a forward reachable evening envelope and a backward reachable-neutral envelope using the same rate/acceleration/transform limits. Their intersection bounds each channel independently. For overlap, scale each preferred peak by a factor in [0,1], solve the largest feasible factor by bisection (tolerance 1e-4, at most 32 iterations), and fit the smooth trajectory inside the intersection. Verify the final sampled trajectory against all limits, including the output limiter; if infeasible, reduce further or stay neutral. Show planned achievable peak separately from saved preference. Reuse this solver for ETA so planner and tracker do not promise incompatible morning behavior.

## 4. Controller and state design

Separate persisted intent, overrides, availability, trajectory phase and accepted software output. Commands carry request IDs; snapshots/configurations/trajectories have revisions. Stale callbacks cannot overwrite newer intent.

Wall clock determines dated schedule events. Monotonic active time advances the filter. Rebase interpolation after wake or long callback gaps; suspended time never becomes one giant step. A last accepted transform is not necessarily current after another writer acts, and is never optical proof.

### Initial tuning to evaluate

Warmth uses a defined inverse-temperature normalized coordinate mapped through the existing transform function; dimming has its own normalized attenuation coordinate. Neither is assumed perceptually uniform. Use floats internally, rounding only labels/backend resolution.

| Parameter | Normal | Temporary catch-up |
|---|---|---|
| Maximum normalized warmth rate | 1 full span / 120 min | 1 full span / 20 min |
| Maximum normalized dimming rate | 1 full span / 180 min | 1 full span / 30 min |
| Rate-change smoothing | at least 30 seconds to rate ceiling | at least 30 seconds |
| Preferred warmth lead | 180 min | computed from distance/trajectory |
| Preferred dimming lead | 60 min | computed from distance/trajectory |

These are engineering candidates, not scientific optima. Record final tested values under a policy version. Initially limit each unquantized RGB channel change to 1/1024 per 100 ms of active interpolation time; a gap of two seconds or more triggers rebase rather than accumulated output. This also protects steep regions of the warmth mapping. Validate backend quantization separately, then freeze any revised threshold before comfort evaluation; this is not a universal invisibility threshold.

For uninterrupted segments, use a smoothstep candidate `s(u)=10u^3-15u^4+6u^5`. Maximum first derivative is 1.875; maximum absolute second derivative is approximately 5.774. For normalized distance D, rate ceiling r and acceleration ceiling a, choose duration in seconds at least `max(preferred, 1.875*D/r, sqrt(5.774*D/a))`. Satisfy every channel. Use `a=r/30 seconds` initially.

Mid-transition replanning preserves position and velocity through a constrained splice; it must not restart at zero velocity every tick. A final bounded tracking limiter enforces rates, acceleration and transform increments. If a splice is infeasible, ease down velocity and extend arrival. Meaningful intent/schedule events replace plans; regular output samples do not.

Compute ETA through the same constrained model, not distance/rate alone. Show minute-scale estimates/ranges; omit countdown when blocked, uncertain or target movement makes it misleading. Initial output sampler 10 Hz; benchmark 5/10/20 Hz and select the lowest rate passing comfort/precision tests. Skip unchanged writes. Visible status need not update faster than one second; screen readers announce semantic changes, not every tick.

Catch-up enters on late enable, wake, resume or confidently cleared Windows exclusion when error from the current scheduled trajectory exceeds 1/1024 in either normalized channel. It tracks that moving trajectory, never automatically the final nightly endpoint. Catch-up uses the disclosed temporary ceilings above, including automatic wake/Windows-clear recovery; the optional slower multiplier scales both normal and catch-up ceilings. Handoff starts only after error stays within 1/1024 for two active seconds and velocity has eased within normal bounds. A changing schedule can postpone arrival; phase/ETA reflect that. New commands may replan but cannot reset generation or velocity incorrectly.

### Ownership and recovery

One reducer and one display writer. The HT singleton does not reserve the system-wide transform against other apps. A known mismatch stops automatic competing writes and shows conflict. Do not repeatedly write identity over another accessibility tool as cleanup. Before automatic reset, check whether the shared transform is still HT's where possible; explicit reset warns that it affects the system-wide color transform.

Windows on/unknown prevents HT application. Preserve intent, not a false Applied status. A confidently cleared Windows exclusion may catch up automatically; unexpected external-writer/backend faults require explicit Retry with bounded backoff. Pending changes never bypass a safety block.

## 5. Civil time, location and lifecycle

- VPN independence (explicit user requirement): never derive location or timezone from IP, VPN endpoint, browser geolocation, proxy variables or the process TZ environment. Use saved coordinates and the Windows timezone. Failed explicit postal lookup must preserve saved location and offer offline entry. If Windows itself is deliberately changed, follow the OS policy and show the change; do not pretend network software cannot alter OS settings.

- Store local civil schedule times; create dated occurrences in the PC zone, compare UTC instants. Inject zone resolver and clocks; package timezone data where required, never hardcode Eastern offsets.
- DST gap: shift forward by the gap size. Fold: first occurrence. Date/zone/rule occurrence IDs prevent duplicate events. Display resolved times on affected days.
- Travel: changing timezone updates displayed event times but not saved solar coordinates. Show an Update location tip, never run unconsented geolocation.
- Personal intervals may cross midnight; equal start/end is invalid. Valid duration is >0 and <24 hours. Short cycles reduce feasible peak.
- Polar/missing/failed solar events use explicitly saved fallback times, otherwise neutral with setup guidance. Never invent sunset or infer it from an idle history.
- Pause counts suspended time, but display interpolation does not. Use monotonic elapsed duration in-process and bounded UTC expiry across restart. A clock correction cannot extend pause indefinitely; uncertain expired holds rejoin gently.
- Maintain a distinct elapsed-duration source that includes sleep for pause accounting. Across restart clamp remaining pause to [0, original duration], preserve original start/expiry rather than rebasing them on every launch, and detect rollback against the stored last-seen UTC time. On unresolved clock inconsistency expire the hold with an explanation and gentle catch-up. Do not reuse the output active-time clock for this.
- After crash/startup, establish current software-output validity rather than assuming persisted targets equal the screen.
- Retain existing high-contrast neutral/explicit-reenable policy pending separate validation. Reduced UI motion is not a command to jump screen color.

## 6. Product design, help and website

The [UI contract](contracts/ui-and-commands.md) specifies hierarchy, materials, colors, exact feedback and instruction snippets. Quick panel: state, power, Smart/Manual, warmth/dim, compare, next event, pause/resume, Settings/Help. Expanded preferences: Schedule, Appearance, Windows access, Help/About. Appearance/Advanced are collapsed; no card inside every card.

The guide is part of first run and remains offline/reopenable. Explain timing, dimming versus hardware brightness, comparison, temporary overrides, pinning, tray versus taskbar, startup, conflicts, travel and removal. A downloadable app must not depend on a preview server to explain itself.

The [distribution contract](contracts/distribution.md) defines one signed installer, immutable release assets, a promotable manifest and a direct Download for Windows CTA at the proposed `/night-light/` route. The button initiates a file download, not a repository visit; never auto-download on page load. Help, requirements, version/size, privacy and notes accompany it.

Select an existing installer toolchain if available. If absent, use the per-user installer proposal in the distribution contract after dependency/license review. No custom elevated updater. Manual updates use the same signed installer; background automatic updating is deferred. Valid signing does not guarantee no SmartScreen prompts. Do not teach users to disable protection to install unverified files.

## 7. Stages and exit gates

| Stage | Deliverable | Exit gate |
|---|---|---|
| A — Baseline/contract | Exact source inventory, capability ledger, policy amendment, isolated tests | Historical/current truth reconciled, dirty work preserved |
| B — Truth/recovery | Reducer, generations, atomic Save, Off/conflict handling | US1 fault/precedence tests pass |
| C — Smart | Pure schedule/transition, catch-up, time rules, migration | US2/US5 invariant and migration tests pass |
| D — Experience | Setup, offline guide, materials/colors, native menu | US3/US4 native-host, accessibility and comprehension pass |
| E — Quality | Exact build, physical lifecycle, performance, formative comparison | Supported matrix and critical defect gates pass |
| F — Distribution | Signed setup, manifest, site CTA/help, upgrade/uninstall | Staging download and clean install/rollback proven |
| G — Release | Fourteen actual nightly sessions, approved promotion, live receipt | Live downloaded bytes equal signed approved build; installed behavior passes |

First vertical slice after B: save a manual preference, display truthful state, Off/recover. This is an internal milestone, not full release. C/D can proceed against frozen contracts; distribution tooling can be prepared without publishing. Shared bridge/config/engine files have one integrator.

New routine suggestions remain deferred. Existing opted-in history is retained only under old privacy/retention terms with deletion available. Switching to the new policy removes automatic inferred-schedule authority. A materially changed legacy schedule requires an informed migration preview; until decided, retain explicit legacy policy and label it. Never silently intensify filtering or expand collection.

## 8. Performance and comfort targets

Prospective targets on declared Windows 11 x64 reference/minimum hardware:

- Visible acknowledgement p95 ≤200 ms; warm panel open p95 ≤500 ms; cold usable window ≤3 seconds, excluding disclosed runtime installation.
- Normal local Save p95 ≤1 second; pending immediately; reconcile after 8 seconds without claiming definite failure.
- Hidden steady process-tree CPU average ≤0.5% over ten minutes; transitioning ≤1%. Record tool/CPU denominator.
- Whole process-tree resident memory target ≤180 MB hidden/≤300 MB visible, including WebView2 helpers. Investigate >20 MB settled growth after 100 open/close and 100 override cycles.
- No steady repeated transform writes; diagnostic instrumentation off in ordinary use.
- Formative comparison with 12–20 consenting adults, counterbalanced prior/candidate/unchanged conditions: record noticeability, annoyance, readability, confusion and overrides separately. Target ≥90% unassisted setup/enable/pause/Off and no unresolved critical restoration failure. This is usability work, not a powered sleep trial.

Freeze numeric evaluation budgets before running candidates. If minimum hardware cannot meet them, document optimization/support tradeoffs; do not mark an unmet gate Passed.

## 9. Finish line

All requirements mapped to tests; zero unresolved critical/high defects; supported hardware rows passed; migration/recovery proven; guide tested with new users; signed final artifact from exact clean source revision; checksums/SBOM/provenance generated after signing; staging install/upgrade/removal proven; fourteen real nightly sessions; explicit publication approval; live downloaded hash/signature/version and native installed behavior verified. Private candidates may exist earlier with accurate labels.

Software correctness, comfort and physiological evidence are separate ledgers. Optical instrumentation is required for calibrated light-exposure claims, not for shipping this honestly described utility. Clinical studies gate health outcomes, not basic screen-control release.

## 10. Constitution and workflow check

Safety, truth, privacy and test isolation conform. Sunset default is retained. Earlier-only automatic inferred timing needs the explicit v1.1.0 amendment/migration described in research.md before runtime implementation. No safety principle is waived.

Spec Kit safe setup refreshed its Codex integration manifest. Optional auto-commit hooks were skipped to preserve unrelated dirty work. No feature branch was created: the feature key was passed only to planning scripts. Image ideation was not used because this request is a completion specification, not new image alternatives.

## 11. Planning handoff verification

The planning package contains eight linked Markdown documents, 20 functional requirements, six non-functional requirements and 68 unchecked implementation tasks. `validate-plan.ps1` checks local links, sequential task IDs, task file paths, requirement inventory and unfilled templates. Its planning-only run passed; `git diff --check` also passed. Neither is a product test, installed verification or release clearance.

Two independent reviews were reconciled: controller/state review and UI/distribution review. Material corrections included preview while Off, emergency recovery despite save failure, generation-safe Save cancellation, brief preview restoration, explicit catch-up handoff, short-night reachability, Manual resumption, sleep-inclusive pause accounting, legacy-policy migration, truthful color-reset copy, immutable installed identity and literal update/uninstall instructions. No unresolved product-design choice requires an intermediate user review; implementation still requires its listed validation and genuine external-authority gates.
