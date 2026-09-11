# Material and palette refinement — 2026-09-09

User correction: a finish must change the full interface treatment, not just its border. Retain independently editable colors and existing vivid choices.

Primary-source research:

- [Apple: Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/) describes glass as a material with optical depth and fluidity. Application here: translucent panel, highlighted raised controls and pill geometry. This browser approximation does not implement native refraction.
- [Microsoft: Materials](https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/materials) distinguishes materials and their role beneath interactive controls. Application here: denser Frosted surfaces, explicit opaque Solid fallback, retained text contrast.
- [Pantone: Cloud Dancer 2026](https://www.pantone.com/na/en-us/color-of-the-year/2026) is a contemporary neutral color direction, not evidence of app-palette popularity. Cloud is a custom neutral palette, not an official Pantone color reproduction.

Added custom curated Mocha, Midnight, Jade and Cloud presets, with distinct accent, panel and background values for each theme. These are design judgments informed by contemporary material and neutral directions, not a ranked popularity list. Existing saturated presets remain available.

Liquid, Frosted, Ceramic and Solid now affect panel treatment, segmented controls, action buttons, settings selectors and palette containers. Liquid/Ceramic also have distinct slider wells; Solid removes decorative shadows and rounds less. Glass styles add restrained backdrop lighting. Native app unchanged.

Verification: seven automated tests, including 80 palette/theme/material token combinations. Browser screenshot inspected for Liquid/Mocha; material control geometry and shadows compared through computed styles. No native rendering or performance claim.
