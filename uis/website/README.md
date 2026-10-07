# TrackFlow public website

## Objective

A public-facing corporate website introducing TrackFlow’s e-commerce logistics services, its Los Angeles and Zaragoza operations, and how it supports brands from warehouse storage through delivery and returns. Public copy is limited to the company context; it does not expose internal systems, employee details, or unverified performance claims.

## Stack

- Vite
- TypeScript (vanilla DOM; no UI framework)
- Plain CSS; no external UI dependencies

Google Fonts are loaded as an optional font resource; the site has local system fallbacks.

## Run locally

From this directory:

```sh
npm install
npm run dev
```

Open the local URL printed by Vite (the root route `/`).

## Production build

```sh
npm run build
```

The static output is written to `dist/`.
