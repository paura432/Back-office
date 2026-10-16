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

The redundant Google Fonts `@import` was removed from `uis/website/src/styles.css` and `uis/backoffice/src/styles.css`. Each `app/layout.tsx` still owns the matching stylesheet link (`Manrope`/`DM Mono` on the website; `DM Sans`/`DM Mono` on the backoffice). No other application source was changed.

Resource requests, rendering and CLS have not been compared after this removal. Do not treat it as a measured performance or CLS improvement. Baseline evidence in `audit/before/` is unchanged.

## Skills and security

Reviewed repository `skills/README.md`; no local `core-web-vitals`, `performance`, or `web-perf` skill was found. No unverified third-party skill was installed or executed. Lighthouse was used as an audit tool, not misrepresented as one of those skills. Any proposed external skill must have its source, publisher, contents, permissions and commands reviewed before execution.

## Evidence and phase status

- `audit/before/*.report.json` and `*.report.html`: 12 actual Lighthouse reports (three runs per app/viewport combination).
- `audit/before/{website,backoffice}-{desktop,mobile}.png`: actual Playwright viewport screenshots.
- `audit/before/summary.json`: run-level results and medians.
- Phase 1 baseline: committed and pushed as `a2eb603` on `feature/frontend-performance-audit`.
- Phase 2 diagnosis: findings and proposed corrections documented here.
- Phase 3 so far: only the duplicate CSS font `@import` was removed. No post-change Lighthouse run, refactor or final improvement has been performed or claimed. The exact 23-task exercise checklist was not provided and is absent from repository files; do not fabricate it. Request/locate its authoritative source before asserting task-by-task completion.
