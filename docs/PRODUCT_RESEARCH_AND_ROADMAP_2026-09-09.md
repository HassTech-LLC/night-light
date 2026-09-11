# Night Light product evidence and development roadmap

## Executive assessment

Night Light has a credible purpose as a free, local-first tool for making evening computer use warmer, dimmer, predictable and easy to reverse. There is substantial evidence that the timing, spectrum and intensity of light influence human circadian physiology. There is not equivalent evidence that this particular application improves sleep, prevents eye damage, treats insomnia or replaces medication.

The recommended product direction is an **evening screen-control utility with research-informed scheduling**, not a melatonin-protection system. Its distinguishing value should be dependable Windows behavior, comfortable transitions, understandable automation, privacy and straightforward controls. More extreme filtering and more elaborate personalization are not inherently better.

Five decisions should govern the next version:

1. Separate schedule timing, transition speed and preferred night intensity.
2. Keep sunset as a convenient location-based option, but offer an explicit bedtime or custom schedule without requiring tracking.
3. Make gradual changes deadline-aware: do not remain unnecessarily bright late in the evening simply to stretch out a transition.
4. Replace automatic sleep inference with transparent, user-approved routine suggestions until the inference is validated.
5. Put optical measurement, readability, failure recovery and honest claims ahead of additional visual effects.

These are recommendations, not implemented changes. Review date: September 9, 2026. Scope: the Windows app's rationale, scheduling, output controls, learning, user experience, privacy, positioning and verification. This is a targeted evidence review, not a systematic review or a medical-device classification opinion. Research in healthy adults with regular daytime schedules cannot automatically be generalized to children, shift workers or people with sleep disorders.

## Current application baseline

The current source contains an offline solar scheduler, optional bedtime/quiet-hours inputs, opt-in local idle-time learning, a global Windows color transform, an embedded WebView2 interface, taskbar shortcuts, pause/resume, manual control and emergency reset. These provide a meaningful foundation; the product is not merely a browser concept.

Relevant inspected files are `smart_mode.py`, `smart_learning.py`, `nightlight_engine.py`, `premium_ui.py`, `premium/settings.html`, `premium/desktop.js`, `tray_app.py`, and the existing Smart specification. Source behavior takes precedence over older documents that still describe Smart as unimplemented. Earlier installation and release notes are historical receipts, not evidence that every later source state is release-certified.

The default Balanced solar curve starts one hour before sunset and progresses from a 6500 K software target and 1.0 output multiplier to 1700 K and 0.30 four hours after sunset. Maximum reaches 1200 K and 0.20. These numbers describe software settings, not measured screen color temperature, luminance, melanopic exposure or clinical effectiveness.

Smart normally evaluates every 25 seconds. The engine interpolates within each transition through approximately 16 ms callbacks. Rejoining normally takes 120 seconds, or 1200 seconds when a bedtime/learned guard applies. The three proposed speed presets are not currently present. Neither an optical calibration nor a product-specific sleep trial establishes an optimal default curve.

## Evidence assessment

### Evening light is a legitimate intervention target

Brown and colleagues' 2022 expert consensus recommends brighter daytime exposure, low melanopic exposure during the three hours before habitual bedtime, and a very dark sleep environment. Its numerical recommendations concern light measured at the eye: at least 250 lux melanopic EDI by day, at most 10 in the pre-bed interval and at most 1 during sleep. They are not screen-brightness percentages or guarantees for every individual. [1](https://pmc.ncbi.nlm.nih.gov/articles/PMC8929548/)

CIE's 2024 position statement endorses use of its S 026 metrology for evaluating these nonvisual effects and recognizes unresolved questions in practical application. The app should treat spectral measurement as the route to quantified claims, rather than converting Kelvin or a slider percentage into a biological score. [2](https://www.cie.co.at/publications/cie-position-statement-integrative-lighting-recommending-proper-light-proper-time-3rd)

**Product implication:** help people manage evening screen output and understand its limitations. Include a short room-light reminder; avoid an interface that suggests the screen is the entire lighting environment. Maintain a neutral daytime default rather than treating all blue-enriched light as undesirable.

### Mechanistic evidence is stronger than app-outcome evidence

A 2023 controlled study exposed 72 healthy young men to low- and high-melanopic display light for four hours before habitual bedtime. A special five-primary display varied melanopic stimulation while preserving visual appearance. Low-melanopic conditions improved several measured responses, including sleep latency and melatonin measures. This supports the biological relevance of spectrum, but that display is not equivalent to an ordinary RGB monitor with a software filter, and the sample limits generalization. [3](https://www.nature.com/articles/s42003-023-04598-4)

Conversely, a 2021 study of 167 young adults compared iPhone Night Shift on, Night Shift off and no phone use for an hour before bedtime across seven nights. There were no significant overall between-condition differences in the measured sleep outcomes. Exploratory subgroup findings should not be promoted as proof of a general benefit. [4](https://pubmed.ncbi.nlm.nih.gov/33867308/)

A separate 2022 experiment with 29 participants found that one hour of different melanopic screen-light exposure changed melatonin suppression without corresponding significant changes in its other measured outcomes, including sleep. This is a direct warning against equating a hormone response with a guaranteed sleep improvement. [5](https://pmc.ncbi.nlm.nih.gov/articles/PMC9644120/)

**Interpretation:** these findings are not simply contradictory. Exposure duration, hardware, spectral contrast, populations and outcomes differ. They justify reducing an avoidable evening light stimulus, not promising that every user will sleep sooner. The app cannot neutralize engaging content, notifications, delayed bedtimes or other causes of poor sleep.

### Slower is not automatically biologically better

Mao and colleagues' 2025 display study compared fixed and changing smartphone night modes during the three hours before bedtime. Its abstract reports that dynamic modes could reach low exposure near sleep while retaining relatively high exposure earlier. The authors investigated cumulative melanopic exposure as an explanatory metric. Full methods were not available in this review, so this is provisional evidence rather than a basis for adopting their proposed numeric threshold. [6](https://www.sciencedirect.com/science/article/pii/S0141938225000642)

**Product implication:** distinguish a gentle transition from a late transition. Starting earlier can spread the same change over more time. Starting late and taking hours to catch up can leave the output high during the interval the user intended to change. The scheduler should show both when it starts and when it reaches the chosen evening setting.

Do not add a cumulative-exposure gauge using screen settings alone. Actual exposure would require validated optical information and accounting for the room, distance, content and viewing behavior. The paper's proposed exposure threshold is not a universal safety budget.

### Perceptual adaptation supports gradual changes, not invisibility claims

Rinner and Gegenfurtner measured several timescales of chromatic adaptation, including a slower component with an approximately 20-second half-life. This was a controlled color-appearance experiment, not an evaluation of night-mode comfort or optimal screen scheduling. [7](https://pubmed.ncbi.nlm.nih.gov/10837828/)

Spieringhs, Murdoch and Vogels studied adaptation to step changes and two rates of gradually changing room illumination. Their results demonstrate measurable temporal adaptation and observer differences. They do not establish a universal undetectable transition rate for desktop screens. [8](https://library.imaging.org/admin/apis/public/api/ist/website/downloadArticle/cic/27/1/art00004)

**Product implication:** continuous interpolation and adjustable rates are reasonable design choices. Literal one-percent steps, fixed Kelvin-per-minute limits, or a label such as “invisible mode” are not supported as universal perceptual solutions. Rate limits must be evaluated with different screen content, ambient light and display hardware.

### Personal sensitivity varies; inactivity does not measure sleep

Phillips and colleagues found more than a fifty-fold range in individual sensitivity to evening light when assessing melatonin suppression. That supports caution about universal settings. It does not mean preference sliders or computer activity can identify someone's physiological sensitivity. [9](https://pubmed.ncbi.nlm.nih.gov/31138694/)

The AASM's actigraphy guideline concerns validated movement-based methods used in specified clinical contexts. It provides no validation for treating desktop inactivity as sleep. Applying its recommendations to the app's idle-time heuristic would be an unjustified leap. [10](https://pmc.ncbi.nlm.nih.gov/articles/PMC6040807/)

**Product implication:** distinguish three things: visual preference, routine regularity and biological state. The application can directly ask about the first, tentatively describe the second, and does not measure the third. A person watching television, reading, leaving the computer running or sharing a computer can defeat the existing inference.

### Sunset is useful context, not a measured biological bedtime

Wright and colleagues' small natural-light field study found changes in circadian timing after a week under natural lighting. It changed the overall light-dark environment, not merely screen color. It supports the importance of the full daily light pattern, but does not establish a universally optimal sunset-offset app schedule. [11](https://pmc.ncbi.nlm.nih.gov/articles/PMC4020279/)

**Product implication:** Solar Sync is valuable because it is understandable and works without a fixed bedtime. A bedtime-aligned option is valuable because seasons, work and social schedules can diverge from sunset. Neither should claim to measure internal circadian phase. “Always move earlier, never later” is a conservative product rule, not a universally validated physiological rule.

### Eye-damage and eye-strain claims need a separate boundary

The 2023 Cochrane review found little or no short-term benefit for computer-related visual fatigue from blue-filtering spectacle lenses; sleep evidence was uncertain. Glasses are not this app, so the review cannot prove the app ineffective. It does undermine treating blue filtering as an established generic solution for eye strain. [12](https://doi.org/10.1002/14651858.cd013244.pub2)

CIE distinguishes retinal blue-light hazard from circadian effects and cautions against conflating them. Marketing should not imply that normal evening computer use is damaging eyes and that an orange screen prevents that damage. [13](https://www.cie.co.at/publications/position-statement-blue-light-hazard-april-23-2019)

**Product implication:** “Choose a more comfortable screen appearance” is appropriate positioning. “Prevents eye damage,” “eliminates eye strain,” and “protects your melatonin” are not established product outcomes. Make comfort a preference that can be adjusted or reversed, not a clinical promise.

## Recommended product design

### 1. Three independent decisions, with simple defaults

| Decision | Basic choices | Role |
|---|---|---|
| When | Sunset / My schedule | Determine the evening and morning anchors |
| How gradually | Gradual / Extra gradual | Control the normal transition, without changing the desired final intensity |
| How strong | User-selected warmth and maximum dimming | Set a comfortable output endpoint |

Quick catch-up belongs in the enable/resume flow, not as another all-night profile. This avoids turning three intuitive decisions into dozens of unexplained preset combinations. Preserve existing users' preferences during migration; do not silently substitute a new “healthier” curve.

For Solar Sync, keep the sunset relationship visible. For My schedule, allow bedtime, wake time and an adjustable evening start. Show an example with actual local dates and times. When bedtime is supplied, explain the research-informed pre-bed window without claiming the selected settings meet a measured exposure threshold.

The previously proposed automatic two-to-three-hours-before-sunset default should not be adopted on scientific grounds. In some seasons that would start during substantial daytime light, while in other cases it still would not match sleep timing. Offer earlier starts as a comfort preference, not a universal optimization.

### 2. Deadline-aware, continuous transitions

Define the desired appearance as a continuous function of time. Track the current applied state separately from the requested endpoint. When the schedule changes, begin from the current applied state and preserve continuity; do not restart a front-loaded animation on every target update.

The existing cubic ease-out is `1 - (1 - t)^3`, so mathematically 87.5% of a single transition's change occurs in its first half. This does not prove a visible jump, but it means a nominal two-minute fade is not uniform. A monotonic, bounded-rate controller with smooth changes in rate is a better candidate for testing than simply increasing that duration.

Keep wall-clock time for solar and schedule calculations and monotonic elapsed time for transitions. Reconcile after suspend, DST changes, timezone changes and clock corrections. A 25-second schedule evaluation can coexist with a continuous display trajectory; increasing the evaluation interval is not the same as making a transition gentler.

For late activation, show “Reach tonight's setting in…” with a short catch-up option and a slower comfort option. Test five- and ten-minute candidates, plus the current two-minute behavior, rather than presenting any as scientifically optimal. Large changes may need longer than small changes. Always allow cancel, pause or neutral reset.

### 3. Comfort limits before extreme presets

Balanced currently ends at 1700 K and a 0.30 software multiplier. That is an aggressive-looking endpoint for a general default, although this review does not establish that it is medically unsafe. It needs readability and preference testing rather than a stronger name.

During setup, let the person select a comfortable night appearance on readable sample content. Separate warmth from maximum dimming, include “Do not dim automatically,” and make the deepest settings an explicit advanced choice. Restore the previous state if the preview is not confirmed. A visually impaired person should not have to endure a dark screen to discover the reset control.

Treat displayed Kelvin as an approximate software target. Label dimming as a software effect, not monitor backlight brightness or percentage reduction in light reaching the eye. Hardware dimming could be explored later for supported displays, but it is a separate compatibility and restoration project—not a checkbox over the current backend.

### 4. Keep learning optional and subordinate to consent

Retain local storage, short retention and deletion controls. Rename the feature to “Routine suggestions” and its confidence label to “Pattern consistency,” with an explanation that it describes computer-use timing, not sleep quality or certainty about sleep.

The current seven-night threshold, fourteen-entry history and median/outlier rules are engineering heuristics. They should remain clearly identified as such. A suggestion should say, for example, “You often finish using this computer around 10:45 PM. Start your evening settings earlier?” Apply it only after confirmation.

For irregular schedules, shared computers and travel, suspend suggestions or request confirmation. User-entered schedule changes must outrank the inferred routine. Do not add application-name or browsing tracking to improve an uncertain estimate without a separate privacy decision.

### 5. Make the state truthful and the explanation local

Separate “settings saved,” “Smart scheduled,” “transitioning,” “filter applied” and “blocked.” The current save acknowledgement is useful but is not optical measurement. Display both current and target values while fading, or explicitly label the shown number “target.”

Show the next action in plain language: “Gradually warming until 9:30 PM,” “Paused until 10:15 PM,” or “Using quiet hours because sunrise is unavailable.” Replace physiological stage names with Evening and Late night. Explain travel behavior: the Windows timezone may change, but the saved coordinates do not automatically follow the person.

Keep the taskbar menu short and native. Maintain a visible pause expiration and an indefinitely persistent Off. Offer a timed alternative to hold-to-compare, so using the feature does not require sustained pointer pressure. Put brief room-light and screen-break guidance in setup/help rather than repeatedly interrupting work.

### 6. Premium appearance must remain readable

Keep the existing glass option and color presets, but provide an equally polished opaque mode. The primary UI should emphasize current state, pause, warmth and dimming; detailed appearance customization should stay collapsed. A visually quiet interface is a product judgment, not evidence of sleep benefit.

Use WCAG 2.2 as a baseline for the embedded web interface: text contrast, keyboard access, focus visibility, resizing, non-color status cues and announced status messages. Test actual custom color combinations rather than assuming presets remain accessible after independent changes. Native shell and assistive-technology testing is also required; web conformance alone does not certify the Windows app. [14](https://www.w3.org/TR/WCAG22/)

### 7. Reliability is central to the value proposition

Microsoft documents that the Magnification API applies one fullscreen transform to the desktop and that the most recent transform takes precedence. This makes coexistence with other color-transform tools an engineering concern. It is not a documented per-monitor calibration API. [15](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magsetfullscreencoloreffect)

Keep a single display owner and explicit Windows Night Light exclusion. Independently validate native-state detection rather than assuming undocumented registry markers remain stable. Report unsupported or uncertain states visibly. Do not silently fight another accessibility/color tool by continuously overwriting its transform.

Investigate idle efficiency. The current engine can schedule near-60 Hz callbacks during long transitions; this is not evidence of measured excessive CPU use. Benchmark before selecting a lower update rate, skip truly unchanged output and suspend unnecessary rendering while the panel is hidden. Performance claims need measured hardware and workload conditions.

## Competitive position and product scope

Windows already provides scheduled night light with sunset-to-sunrise or custom hours. Basic scheduling is therefore not a unique reason to install another application. [16](https://support.microsoft.com/en-us/windows/hardware/display-graphics/change-display-brightness-and-color-in-windows)

f.lux already offers warm presets, scheduling and slow transitions; its official FAQ documents a one-hour slow-transition option. These are established product patterns, not clinical validation or evidence that one hour is optimal. Avoid claiming a novel invention from those features alone. [17](https://justgetflux.com/faq.html)

The defensible product hypothesis is a better combination: independently adjustable dimming, easy Windows access, clear transition status, dependable pause/resume, discreet local preferences, accessible customization and transparent limitations. Validate that hypothesis through observed setup success, low override frustration, continued voluntary use and fewer support problems—not claims of outperforming competitors' physiology.

Keep core controls, safety, privacy and accessibility free. Optional donations should remain separate from the main workflow. Do not add health scores, engagement streaks or a subscription merely to make the product seem more sophisticated. Willingness to support the project is a business question that requires user evidence; the research does not establish a donation conversion rate.

## Claim and distribution policy

| Prefer | Avoid without appropriate product-specific evidence |
|---|---|
| “Automatically adjusts screen warmth and software dimming.” | “Clinically proven to improve sleep.” |
| “Research-informed evening scheduling.” | “Optimizes your circadian rhythm.” |
| “Choose a more comfortable evening appearance.” | “Prevents eye damage” or “eliminates eye strain.” |
| “Routine estimates stay on this device.” | “Learns when you sleep” or “measures your sleep.” |
| “Approximate color-temperature target.” | A measured-Kelvin, melanopic-lux or protection percentage claim without calibration |
| “An optional part of an evening routine.” | “Use this instead of sleep medication.” |

FTC guidance requires substantiation for both explicit and implied health claims; research about a mechanism is not automatically evidence for the marketed product. Disclaimers do not provide permission to make a contradictory headline claim. Have health-facing copy reviewed before broad distribution. [18](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)

FDA's January 2026 general-wellness guidance supersedes its 2019 version and distinguishes certain healthy-lifestyle software from disease-related device functions. The practical recommendation is to remain within clearly described screen-control/general-wellness functions and obtain qualified advice before making treatment claims. This is not a determination of the app's legal classification. [19](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices)

The founder's positive personal experience can be presented as personal motivation, clearly separated from typical results and clinical claims. The original aim of helping people consider their evening environment should not become a message that delays care or encourages stopping medication.

## Validation and delivery sequence

### Priority 0: truth and control

1. Reconcile contradictory historical product/release documents and create a current capability ledger tied to an exact build.
2. Distinguish applied state from requested target in the UI and diagnostics.
3. Audit all app, website, installer and support copy against the claim table. Public-page content was not successfully retrieved for this review, so no live-copy certification is implied.
4. Validate neutral recovery and ownership across normal quit, crash, restart, Windows Night Light changes and other assistive tools.
5. Finish keyboard, screen-reader, high-contrast, mixed-DPI and custom-theme checks before claiming accessibility.

### Priority 1: a clearer Smart experience

Implement independent timing, transition and intensity settings; a setup preview; deadline-aware interpolation; explicit catch-up; optional bedtime/wake schedule; and consent-based routine suggestions. Preserve old settings and make migration reversible. These changes supersede parts of the earlier proposed “earlier-only protection” and “always extra-gradual” direction and therefore should be accepted as a product decision before implementation.

The core acceptance condition is not “slower.” It is: no abrupt unintended discontinuities, clear next-action timing, comfortable readable output, and an override that always wins. Polar regions, short nights, DST folds/gaps, non-hour timezone offsets, changing coordinates and early wake times must have specified behavior rather than silent fallback guesses.

### Priority 2: optical and perceptual verification

Measure representative LCD and OLED screens in SDR and HDR, with known hardware brightness, distance, angle, ambient light and test content. Use appropriate spectral instrumentation to evaluate melanopic EDI, plus luminance and color measurements. A screenshot or RGB matrix readback proves neither the emitted spectrum nor total light at the eye.

For comfort, run a small formative counterbalanced study comparing current and candidate transitions, including an unchanged-screen control. Record whether and when changes are noticed, whether they bother the participant, readability, color-task errors and override frequency. Distinguish “noticed” from “disliked”; invisibility is not the sole success measure. A sample of roughly 12–20 users can expose usability problems but is not a powered clinical efficacy trial. Select a confirmatory sample size from pilot variability and a prespecified endpoint.

For performance, record CPU, memory, wakeups and responsiveness with the panel visible/hidden and the filter steady/transitioning. For recovery, repeat controlled suspend/resume, topology, HDR and Windows-state changes and an overnight soak. The existing proposed fourteen-night soak is a practical reliability gate, not scientific proof of safety or benefit.

### Priority 3: outcome evidence, if health claims remain a goal

Only after the implementation is stable and optically characterized should a sleep-outcome study be considered. Collaborate with qualified sleep researchers, define an appropriate comparator and prespecified primary outcome, account for room light and bedtime behavior, and use suitable validated measures. Obtain applicable ethics review and consent. No participant should be directed to change medication for app evaluation.

Keep three evidence ledgers separate: software correctness, perceptual comfort, and physiological/sleep outcomes. Positive results in one do not certify the others. Publish negative and inconclusive findings as well as favorable ones.

## Decision summary

Proceed with Night Light, but strengthen its precision rather than its promises. Keep the free/local-first model, reversible controls, solar convenience and premium interface. Change the Smart architecture to separate timing, intensity and transition behavior; make bedtime alignment explicit; use conservative, user-selected comfort limits; and demote sleep inference to optional suggestions.

Do not ship a universal “maximum protection” default, claim invisible transitions, or imply that a slower fade is automatically healthier. The next major investment should be trustworthy state, measurement and real-user transition testing—not additional preset names. No application settings, source behavior, installed binaries or public content were changed by this research review.

## Sources

1. Brown TM et al. **Recommendations for daytime, evening, and nighttime indoor light exposure to best support physiology, sleep, and wakefulness in healthy adults.** PLOS Biology, 2022. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC8929548/). Expert consensus; population and measurement limitations apply.
2. CIE. **Position Statement on Integrative Lighting—Recommending Proper Light at the Proper Time, 3rd Edition.** CIE PS 001:2024. [Official statement](https://www.cie.co.at/publications/cie-position-statement-integrative-lighting-recommending-proper-light-proper-time-3rd). Metrology and application guidance.
3. Schöllhorn I et al. **Melanopic irradiance defines the impact of evening display light on sleep latency, melatonin and alertness.** Communications Biology, 2023. [Article](https://www.nature.com/articles/s42003-023-04598-4). Controlled special-display study; young male sample.
4. Duraccio KM et al. **Does iPhone night shift mitigate negative effects of smartphone use on sleep outcomes in emerging adults?** Sleep Health, 2021. [Study record](https://pubmed.ncbi.nlm.nih.gov/33867308/). Abstract and indexed study details; not a Night Light by HT trial.
5. Blume C et al. **Melatonin suppression does not automatically alter sleepiness, vigilance, sensory processing, or sleep.** Sleep, 2022. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9644120/). Indexed full-text passages available; direct navigation intermittently challenged.
6. Mao J et al. **Quantifying the impact of night-shift display modes on evening melatonin production.** Displays 88, 103027, 2025. [Publisher abstract](https://www.sciencedirect.com/science/article/pii/S0141938225000642). Abstract/preview only; proposed exposure threshold not adopted.
7. Rinner O, Gegenfurtner KR. **Time course of chromatic adaptation for color appearance and discrimination.** Vision Research, 2000. [Study record](https://pubmed.ncbi.nlm.nih.gov/10837828/). Laboratory perceptual adaptation, not app effectiveness.
8. Spieringhs RM, Murdoch MJ, Vogels IMLC. **Time course of chromatic adaptation under dynamic lighting.** 27th Color and Imaging Conference, 2019. [Publisher PDF](https://library.imaging.org/admin/apis/public/api/ist/website/downloadArticle/cic/27/1/art00004). Full text; room illumination, not a desktop field study.
9. Phillips AJK et al. **High sensitivity and interindividual variability in the response of the human circadian system to evening light.** PNAS, 2019. [Study record](https://pubmed.ncbi.nlm.nih.gov/31138694/). Individual physiological variability.
10. Smith MT et al./AASM. **Use of Actigraphy for the Evaluation of Sleep Disorders and Circadian Rhythm Sleep-Wake Disorders.** Journal of Clinical Sleep Medicine, 2018. [Guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC6040807/). Not validation of desktop idle sensing.
11. Wright KP Jr et al. **Entrainment of the Human Circadian Clock to the Natural Light-Dark Cycle.** Current Biology, 2013. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4020279/). Small whole-environment field study; indexed text consulted.
12. Singh S et al. **Blue-light filtering spectacle lenses for visual performance, sleep, and macular health in adults.** Cochrane Database of Systematic Reviews, 2023. [Review](https://doi.org/10.1002/14651858.cd013244.pub2). Indirect evidence for this software product.
13. CIE. **Position Statement on the Blue Light Hazard.** April 23, 2019. [Official statement](https://www.cie.co.at/publications/position-statement-blue-light-hazard-april-23-2019). Distinguishes retinal hazard from circadian effects.
14. W3C. **Web Content Accessibility Guidelines 2.2.** [Recommendation](https://www.w3.org/TR/WCAG22/). Engineering baseline for the embedded interface, not native-app certification.
15. Microsoft. **MagSetFullscreenColorEffect function.** [API documentation](https://learn.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magsetfullscreencoloreffect). Fullscreen scope and last-transform behavior.
16. Microsoft. **Change display brightness and color in Windows.** [Support documentation](https://support.microsoft.com/en-us/windows/hardware/display-graphics/change-display-brightness-and-color-in-windows). Current native scheduling baseline.
17. f.lux. **Frequently Asked Questions.** [Official FAQ](https://justgetflux.com/faq.html). Vendor-documented features, not independent efficacy evidence.
18. FTC. **Health Products Compliance Guidance.** December 2022. [Official guidance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance). U.S. advertising substantiation considerations.
19. FDA. **General Wellness: Policy for Low Risk Devices.** January 6, 2026. [Current guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices). Supersedes 2019 guidance; no product-specific legal determination made.
