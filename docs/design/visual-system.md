# DojoPulse visual system

Updated 2026-10-05. Requirements: M13.01, M13.04, M13.07, M13.09, M16.02 and M19.02.
Local visual implementation; no real-player, gameplay, accessibility or hosted release approval.

## Direction and reference

The owner requested a distinct design inspired by [MetaPunish](https://metapunish.com/).
Reviewed its public HTML/CSS and original hero asset on 2026-10-05: near-black surfaces,
red/cyan highlights, technical labels, oversized headings and cinematic fighter imagery.
A connected browser was unavailable; this reference review used public page/style/asset
inspection, not an interactive rendered-site review. Reference downloads stay in ignored
reports; none are distributed with DojoPulse.

DojoPulse uses graphite and warm ember orange, condensed Barlow headings, quiet blue links,
a pulse mark and an original training-arena scene. The composition, language, navigation
and training overview are DojoPulse's own. No reference logo, character asset, CSS, testimonials,
statistics, pricing or live-analysis claims are reused. Decorative art is never gameplay evidence.

## Behavior and accessibility

The visitor entry explains the training loop and links to working local sign-in/account tools.
The authenticated entry links to matches, capture instructions and the visible training path.
Training tools precede account/privacy controls; those controls remain available via section links.
Prototype/validation notices, unknowns, provenance, disabled reviewed-drill gates and private
account flows retain their existing meanings and backend rules.

Global design tokens style player and operator pages consistently. Body text and form fields
remain readable; every input stays labeled, buttons are at least 44px tall,
focus uses a contrasting blue outline, mobile grids stack, long evidence wraps and tables
retain their existing narrow-screen cards. Reduced-motion and forced-colors rules are included.
No animated ticker, boot overlay, fake data or theme tracking was added. Manual screen-reader,
real device/browser and participant testing remain M13.07 requirements.

All assets/fonts are self-hosted; no third-party image/font calls occur during page use.
Next Image reserves the decorative hero area and serves responsive sizes. The web runtime
copies public assets; CI fetches and byte-compares the hero and icon from the actual container.

## Asset provenance

| Asset | Origin | Delivery |
|---|---|---|
| [dojo-training.webp](../../frontend/public/images/dojo-training.webp) | Built-in imagegen; original fictional martial artist and dojo, generated 2026-10-05 | 1536 x 1024, WebP quality 84, 169,594 bytes; SHA-256 ac14b9abc5fd2afb8ee56ddc63f31dbf862549a9658f7821f5e64444d54f75a6 |
| [icon.svg](../../frontend/public/icon.svg) | Original code-native pulse mark | Small vector icon, same mark as header |
| [Barlow regular](../../frontend/app/fonts/Barlow-Regular.ttf), [semibold](../../frontend/app/fonts/Barlow-SemiBold.ttf) | [Google Fonts Barlow source](https://github.com/google/fonts/tree/main/ofl/barlow), downloaded 2026-10-05 | Bundled locally; [SIL OFL 1.1](../../frontend/app/fonts/barlow-OFL.txt) |
| [Barlow Condensed bold](../../frontend/app/fonts/BarlowCondensed-Bold.ttf) | [Google Fonts Barlow Condensed source](https://github.com/google/fonts/tree/main/ofl/barlowcondensed), downloaded 2026-10-05 | Bundled locally; [SIL OFL 1.1](../../frontend/app/fonts/barlowcondensed-OFL.txt) |

The generated PNG was inspected before a format-only Sharp WebP conversion. Its original
remains at the tool's generated-images location, with a workspace copy under ignored reports.
The committed WebP is the final production asset. No existing project art was overwritten.

Exact built-in imagegen prompt:

```text
Use case: stylized-concept
Asset type: original website hero artwork for DojoPulse, a Tekken practice and evidence workspace.
Primary request: premium cinematic fighting-game concept art of an original martial artist preparing to train in a futuristic underground dojo, grounded and focused rather than fantasy.
Scene/backdrop: charcoal industrial arena, a circular training floor, a single warm amber light strip, subtle smoke, textured concrete, sparse ember sparks.
Subject: one original athletic martial artist in a dark sleeveless training jacket and hand wraps, short cropped hair, seen in three-quarter profile facing left, raised guarded hands, realistic anatomy. This is an original fictional person, not a recognizable game character or celebrity.
Style/medium: highly polished dramatic 3D concept illustration with tactile fabric and film grain, sophisticated game key art.
Composition/framing: wide landscape 1536 by 1024. Subject occupies the right half with head and both hands fully inside the frame; left half is dark quiet atmospheric negative space, intended for a separate HTML heading. Strong silhouette and measured, deliberate posture.
Lighting/mood: amber edge lighting from behind, cool soft steel-blue fill, deep graphite shadows; composed, intense training atmosphere.
Color palette: near-black graphite, warm ivory highlights, ember orange and muted slate blue.
Constraints: no text, no logos, no watermark, no UI, no statistics, no electric glowing eyes, no recognizable copyrighted characters. Must feel original, not a replica of another website's character artwork. Artwork is decorative and never gameplay evidence.
```

## Qualification

Implementation checks and screenshots are recorded in [the UI receipt](../experiment-results/m13-visual-system.md).
Existing ownership, evidence and scientific gates are unchanged. M13.09 describes local visual
engineering; M13 overall remains PARTIAL until its real workflow and acceptance dependencies pass.
