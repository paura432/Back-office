# TrackFlow Operations Backoffice

## Objective

An internal, frontend-only operations dashboard for TrackFlow. It provides a structured view of the warehouse, carrier, reverse-logistics, customer-experience, and technology areas and summarizes documented operational needs. It is a static context overview: no backend is connected, no live data is shown, and status labels describe needs in `CONTEXT.md` rather than live alerts.

## Stack

- Vite
- TypeScript (vanilla DOM; no UI framework)
- Plain CSS; no external UI dependencies

Google Fonts are loaded as an optional font resource; the interface has local system fallbacks.

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
