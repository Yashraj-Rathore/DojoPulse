# M13.09 original visual system — software qualification

2026-10-05; Architecture 2.17.0. Local UI engineering, not gameplay, participant,
accessibility or hosted-release acceptance. Publication and exact-source CI pending.

## Implemented

The owner requested a MetaPunish-inspired appearance before continuing real capture work.
Added an original graphite/ember design, generated dojo artwork, pulse branding, self-hosted
OFL fonts, responsive hero and local sign-in entry, a training overview and consistent player/
operator panels and controls. Authenticated navigation reaches real training/match/capture
sections. Account/privacy/security controls remain accessible below the training tools.
Existing local account/link scrubbing, ownership, consent, unknowns, scientific gates,
evidence selection and canonical processing contracts are unchanged.

Public assets are now copied into the standalone web container. Added actual HTTP asset
byte comparisons to the container CI smoke check so a successful HTML startup cannot mask
missing art or icon. No dependency/version, migration, backend API or live provider change.

Changed code: frontend/app/globals.css, layout.tsx, page.tsx, training-journey.tsx,
frontend/app/fonts (three fonts/two OFL licences), frontend/public (hero/icon),
frontend/tests/visual-experience.spec.ts, infrastructure/Dockerfile.web and CI workflow.
Updated the player-experience contract, visual-design/provenance notes, decision log and
both mandatory progress files. [Design and exact generation prompt](../design/visual-system.md).

## Actual local checks

| Check | Result / limits |
|---|---|
| ESLint and TypeScript | Both pass |
| Next 16.3.6 production build | Pass; all six application routes generated, plus not-found |
| Complete Edge browser suite | 54 pass in 57.9s, including existing ownership/consent/access/unknown/correction/upload/training/operator paths |
| Final heading spacing and entry recheck | Two new tests pass in 7.7s after the spacing adjustment; a preceding npm filter invocation ran no tests because the Windows wrapper dropped --grep, so the direct Playwright CLI was used |
| Responsive and keyboard checks | Visitor 1440/768/390/320px widths and player 390px have no horizontal overflow; decorative art loads; sign-in/training/matches/capture links and skip-to-workspace focus work; disabled account/capture gates remain |
| Visual review | Inspected desktop/mobile visitor, desktop/mobile training-path and mobile dataset screenshots; corrected missing sentence spacing in narrow training overview |
| Static color contrast | Body 17.02:1, muted on panel 8.50:1, primary button 8.96:1, field border 3.11:1, focus on panel 11.57:1. These selected pairs are not a full page or accessibility audit |
| Backend/Docker/Terraform locally | Not rerun for this UI change; latest prior backend qualification is dated in the G1 receipt. Full remote CI and new container asset checks pending |

Generated original artwork inspected before format-only WebP compression: 1536 x 1024,
169,594 bytes; no reference artwork copied. Fonts and licences are committed; no external
asset/font request is needed for page use. Reference site review used public HTML/CSS and
hero inspection because no browser connection was available.

Screenshots live in frontend/test-results; browser CI retains its artifacts. They use synthetic
fixtures, not real player data or gameplay. Manual screen-reader, real-device, additional browser,
participant usability, actual hosted delivery and G1–G6 remain unqualified.

## Delivery

Work stays on main; normal CI must verify the exact published source and any final receipt.
No feature branches, skip instructions, deployment, paid provisioning or data/provider activation.
