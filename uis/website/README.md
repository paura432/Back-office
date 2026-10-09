# TrackFlow public website

## Objective

A public-facing corporate website introducing TrackFlow’s e-commerce logistics services, its Los Angeles and Zaragoza operations, and how it supports brands from warehouse storage through delivery and returns. Public copy is limited to the company context; it does not expose internal systems, employee details, or unverified performance claims.

## Stack

- Next.js 16.4.0 with TypeScript and App Router
- React 19.3.0; the mobile navigation uses React state
- Existing global CSS and content preserved without redesign

Google Fonts are loaded as an optional font resource; the site has local system fallbacks.

## Run locally

From this directory:

```sh
npm ci
npm run dev
```

Open http://localhost:3000 (the root route `/`). Development uses webpack with
polling for bind mounts. `next.config.ts` rewrites relative `/api/...` requests
to the server-only `API_PROXY_TARGET`, defaulting locally to port 8000. Compose
sets the target to `http://api:8000`; browsers never use that Docker hostname.

## Production build

```sh
npm run build
```

Next.js output is written to `.next/`. Use `npm start` to run the build locally.
From the repository root, `docker compose up --build -d --wait` starts both
frontends in one supervised `ui` container. Dependencies and `.next` caches are
isolated in named volumes; sources are bind-mounted. `docker compose down` stops
the development stack.
