# TrackFlow Operations Backoffice

## Objective

An internal, frontend-only operations dashboard for TrackFlow. It provides a structured view of the warehouse, carrier, reverse-logistics, customer-experience, and technology areas and summarizes documented operational needs. It is a static context overview: no backend is connected, no live data is shown, and status labels describe needs in `CONTEXT.md` rather than live alerts.

## Stack

- Next.js 16.4.0 with TypeScript and App Router
- React 19.3.0; existing content, anchors and global CSS preserved
- No redesign or live business data added

DM Sans and DM Mono are self-hosted with `next/font` and `font-display: swap`. System fallbacks remain in CSS.

## Run locally

From this directory:

```sh
npm ci
npm run dev
```

Open http://localhost:3001 (the root route `/`). Development uses webpack with
polling for bind mounts. `next.config.ts` rewrites relative `/api/...` requests
to the server-only `API_PROXY_TARGET`, defaulting locally to port 8000. Compose
sets the target to `http://api:8000`; browsers never use that Docker hostname.

## Telemetry

`src/services/telemetry.ts` exposes `track(eventType, properties)` for the
contract in `docs/telemetry/event-schemas.json`. It batches events in memory
(flush every 30 s or 20 events), retries up to 3 times with exponential
backoff, and uses `sendBeacon` when the page is hidden or closed.
`app/telemetry-reporter.tsx` captures `page_viewed`, `frontend_error_occurred`
and `web_vitals_measured`; `BackendStatus` reports failed `/api/status` calls.
Copy `.env.example` to `.env.local` to set `NEXT_PUBLIC_TELEMETRY_ENDPOINT`
(default `/api/telemetry/events`, same-origin via the `/api` rewrite). Details,
pending events and evidence: `docs/telemetry/frontend-capture.md`.

```sh
npm test          # node:test unit tests for the telemetry client
npm run typecheck
```

## Production build

```sh
npm run build
```

Next.js output is written to `.next/`. Use `npm start` to run the build locally.
From the repository root, `docker compose up --build -d --wait` starts both
frontends in one supervised `ui` container. Dependencies and `.next` caches are
isolated in named volumes; sources are bind-mounted. `docker compose down` stops
the development stack.
