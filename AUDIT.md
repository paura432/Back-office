# Frontend performance audit

## Scope and method

This audit covers the production-built Next.js applications `uis/website` and `uis/backoffice`. The baseline was captured from source commit `9d0561b1517041804924f5a541db703ae6cf0b1e` before application changes. Builds ran in the existing `trackflow-dev-ui` Docker image; production `next start` servers ran at `http://127.0.0.1:3100/` (website) and `http://127.0.0.1:3101/` (backoffice). Both roots returned HTTP 200.

Lighthouse 12.8.2 with Chromium Headless 141.0.7390.37 on Node 22.15.0/Linux Codespaces measured each app at desktop and mobile three times, with fresh storage for each run. Desktop used Lighthouse's desktop preset (1350×940, DPR 1, 40 ms RTT, 10,240 Kbps, CPU multiplier 1); mobile used default mobile emulation (412×823, DPR 1.75, 150 ms RTT, 1,638.4 Kbps, CPU multiplier 4). Performance, Accessibility, Best Practices and SEO categories were enabled. Each original report is retained. Scores are medians of category scores; timing medians derive from each run's Lighthouse JSON `numericValue`.

Playwright 1.64.1 smoke checks and viewport screenshots used the same cached Chromium. TBT below is a lab metric, **not field INP**. Lighthouse `server-response-time` is a local lab TTFB estimate, not ongoing production monitoring. Lighthouse/CPU/network results vary between runs and should not be overinterpreted.

## Baseline

| App / viewport | Performance | Accessibility | Best Practices | SEO | LCP (ms) | CLS | TBT (ms) | TTFB estimate (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Website desktop | 99 | 95 | 96 | 100 | 643.282 | 0.053153 | 0 | 4.141 |
| Website mobile | 92 | 95 | 93 | 100 | 2664.057 | 0.050702 | 98 | 3.113 |
| Backoffice desktop | 100 | 95 | 96 | 100 | 687.978 | 0.015558 | 0 | 5.646 |
| Backoffice mobile | 94 | 95 | 93 | 100 | 2588.299 | 0.022816 | 0 | 4.784 |

All 12 run-level scores and metrics are in `audit/before/summary.json`, with original JSON and HTML reports alongside four Playwright viewport screenshots. The website mobile Performance run scores were 92/93/92; backoffice mobile 94/94/96. The desktop backoffice is already at the Performance ceiling of 100.

## Findings and root-cause assessment

### Website

- **Mobile LCP is the clearest performance opportunity (confirmed).** Median 2.664 s; the sampled LCP is the hero heading (`main#top > section.hero > div.hero-copy > h1`). In `website-mobile-2.report.json`, Lighthouse's LCP breakdown attributes approximately 81% to render delay. The hero illustration is CSS-built; the evidence does not point to an unoptimized hero image.
- **Client boundary is broader than the interaction requires (confirmed architectural opportunity).** `app/page.tsx` is a Client Component for the mobile navigation's `useState`, so static page sections and cards are included in that client module. Lighthouse reports unused JavaScript (~59 KiB in an inspected mobile run) and legacy JavaScript (~12 KiB); median mobile TBT is only 98 ms, so this is an opportunity, not evidence that JavaScript is the dominant LCP cause or that all flagged bytes are removable.
- **Duplicate font declarations (confirmed source duplication).** Both `app/layout.tsx` and `src/styles.css` request Google Fonts. CSS `@import` duplicates the layout's link declaration. The font-display audit passes; font loading is not proven to cause measured CLS.
- **CLS is measurable but below 0.1 (confirmed, source unknown).** Medians are 0.050702 mobile and 0.053153 desktop. The inspected layout-shift audit identifies no element, and there are no unsized content images. Do not attribute it to fonts or claim a fix until further evidence exists.
- **Favicon console error (observed).** Lighthouse's console audit reports `/favicon.ico` as 404 on port 3100. A Playwright direct visit did not reproduce it consistently; this is minor hygiene, not a demonstrated performance problem.

### Backoffice

- **Desktop Performance is already 100 (confirmed).** Do not claim a desktop score gain if it stays at 100; mobile and other metrics remain measurable.
- **Mobile LCP is substantially higher than desktop (confirmed).** Mobile median is 2.588 s versus 688 ms desktop. Mobile median TBT is 0 ms, although one of the three runs measured 183 ms; the page is otherwise a static Server Component.
- **Five CSS pixels of horizontal overflow at 412 px (confirmed symptom, cause not yet isolated).** Playwright measured 417 px body scroll width. Fixed/minimum layout widths in `src/styles.css` are candidates. Identify the actual overflowing element before any CSS adjustment. This is a responsive defect, not yet a proven Lighthouse score cause.
- **CLS remains below 0.1 (confirmed; source unknown).** Medians: 0.022816 mobile, 0.015558 desktop. No specific shifting element was identified by the inspected report.
- **Favicon console error (observed).** Lighthouse reports `/favicon.ico` 404; as with the website, this has no demonstrated performance impact.

## Prioritized, testable corrections

1. Remove the redundant CSS Google Fonts `@import` only after confirming the layout link remains the sole font owner; compare resource requests, rendering and CLS.
2. Move the interactive website navigation into a focused Client Component while leaving static content server-rendered. Preserve menu open/close, `aria-expanded`, keyboard operation, content, responsive layout and visuals. Rebuild, run interactions/screenshots, and remeasure; the LCP heading/render delay might remain unchanged.
3. Inspect actual mobile computed widths on backoffice, then correct only the source of the 5 px overflow and verify desktop/mobile layout and content remain unchanged.
4. Investigate the favicon request; add an asset only if an approved brand asset is available. Do not invent branding. This is not a performance optimization.
5. Phase 4 requires extracting one genuine reusable component or hook grounded in verified duplication. Do not force a common component across dissimilar website and dashboard cards; the exact extraction is not yet selected.

## Phase 3 verification log

### Font `@import` removal

Cause: each app declared the same Google Fonts stylesheet in `app/layout.tsx` and again with CSS `@import`. The baseline network log already showed one `fonts.googleapis.com` CSS request plus the woff2 files; Next had inlined the `@import` into the app CSS bundle, so the duplication was in source, not a second font CSS request.

Change: removed the `@import` from both `src/styles.css` files in `07dc18f`. Layout links remain the font owners. `audit/before/` was not modified.

Measured result, same Lighthouse 12.8.2 / Chrome 141 method, three fresh runs, source `07dc18f` only: font CSS requests stayed at 1 and woff2 counts stayed at 3 (website) and 2 (backoffice). Stylesheet count stayed at 2. CLS medians were unchanged (website desktop 0.053153, website mobile 0.050702, backoffice desktop 0.015558, backoffice mobile 0.022816). Layout-shift selectors were unchanged. Performance medians: website desktop 99→99, website mobile 92→93, backoffice desktop 100→100, backoffice mobile 94→93. LCP medians moved by tens of milliseconds and stayed inside run variance. This is not a demonstrated performance, rendering or CLS improvement. Evidence: `audit/after-fonts/`.

### Website navigation boundary

Cause: `uis/website/app/page.tsx` was a Client Component only because the mobile menu used `useState`. Static sections were in that same client module.

Change: menu state, `aria-expanded`, the toggle and nav close-on-click moved to `uis/website/app/site-header.tsx`. The page is a Server Component again. Markup, classes, copy and links are unchanged.

Measured result: production build in `trackflow-dev-ui` succeeded. Playwright confirmed desktop nav visible and toggle hidden; at 412 px the toggle opens by keyboard, sets `aria-expanded="true"` and `main-nav--open`, and a nav link closes the menu and sets `#services`. Desktop and mobile screenshots matched the baseline pixel for pixel. Lighthouse medians after this split (and the already-removed font import): website desktop Performance 99, LCP 645.060, CLS 0.053153, TBT 0; website mobile Performance 92 (runs 98/86/92), LCP 2643.309, CLS 0.050702, TBT 118. No score or LCP improvement is claimed. Evidence: `audit/after/`.

### Backoffice 412 px overflow

Cause: at a 412 px viewport, `article.team-card` was the element past the viewport. Its right edge was 416.5 px and `scrollWidth` was 417. The grid cell was 312 px wide; the card's min-content was about 333.5 px, so it overflowed the cell and 4.5 px past the viewport. Child text was not clipped.
: font remeasurement in `audit/after-fonts/`; navigation split and overflow fix remeasured in `audit/after/`. No Performance improvement is claimed. `audit/before/` was not modified
Change: only inside `@media(max-width:460px)`, horizontal padding of `.team-card` went from 10 px to 6 px. `min-width: 0` was tried and rejected because it clipped visible team text.

Measured result: `scrollWidth` is 412 and no `.team-info p` is clipped. Desktop screenshot is identical to baseline. The mobile screenshot differs by 30,899 of 1,038,240 pixels (2.98%) because the cards are 8 px narrower in total horizontal padding; content remains readable. Backoffice Lighthouse medians: desktop Performance 100, LCP 688.388, CLS 0.015558; mobile Performance 93 (runs 94/93/93), LCP 2602.723, CLS 0.022812, TBT 56.05. Do not claim a Performance gain; the mobile median is 1 point below baseline and within run variance. Evidence: `audit/after/`.

## Skills and security

Reviewed repository `skills/README.md`; no local `core-web-vitals`, `performance`, or `web-perf` skill was found. No unverified third-party skill was installed or executed. Lighthouse was used as an audit tool, not misrepresented as one of those skills. Any proposed external skill must have its source, publisher, contents, permissions and commands reviewed before execution.

## Evidence and phase status

- `audit/before/*.report.json` and `*.report.html`: 12 actual Lighthouse reports (three runs per app/viewport combination).
- `audit/before/{website,backoffice}-{desktop,mobile}.png`: actual Playwright viewport screenshots.
- `audit/before/summary.json`: run-level results and medians.
- Phase 1 baseline: committed and pushed as `a2eb603` on `feature/frontend-performance-audit`.
- Phase 2 diagnosis: findings and proposed corrections documented here.
- Phase 3 font check: `@import` removal remeasured in `audit/after-fonts/`; no request or CLS improvement. Navigation split and backoffice overflow are not in that measurement. The exact 23-task exercise checklist was not provided and is absent from repository files; do not fabricate it.
