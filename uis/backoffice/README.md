# TrackFlow Incident Manager — Backoffice UI

Frontend de administración para el Incident Manager de TrackFlow.

## Requisitos

- Node.js 18+
- pnpm
- Backend corriendo en `http://localhost:8000`

## Instalación

```bash
cd uis/backoffice
pnpm install
```

## Desarrollo

```bash
pnpm dev
```

Abre `http://localhost:5173`. Las peticiones a `/api/*` se proxean al backend.

## Build

```bash
pnpm build
```

## Estructura

```
src/
  main.ts       — Entrada y enrutador
  types.ts      — Interfaces compartidas del dominio (catálogos cerrados)
  api.ts        — Capa de comunicación con la API
  utils.ts      — Utilidades (fetch, formateo, validación)
  pages/        — Páginas (dashboard, listado, alta, detalle, edición)
  components/   — Componentes reutilizables (header, badges)
```

## Catálogos

Los catálogos se definen en `src/types.ts` y se importan desde
`packages/shared/types/incident.ts` sin modificar `package.json`.