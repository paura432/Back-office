# shared-types.md

> Regla derivada de la estructura de `packages/shared/`.
> Define dónde y cómo se declaran los tipos TypeScript compartidos en el monorepo.

---

- **Aplicación:** `always_active`
- **Ámbito/patrón de archivos:** `packages/shared/**/*.ts`, `uis/**/*.ts`, `services/**/*.ts`, `agents/**/*.ts`

## Evidencia de origen

- `packages/shared/package.json` — `"name": "@repo/shared-types"`, `"main": "index.ts"`, `"types": "index.ts"`. Es el paquete designado para tipos compartidos. ⚠️ El entrypoint declarado no coincide con el código real (véase `docs/incident-manager/reconnaissance.md` sección 7).
- `packages/shared/types/index.ts` — Contiene `BaseEntity` e `Id`. Es el archivo de tipos real que existe.
- `packages/README.md` — "Shared packages for the monorepo: internal libraries, utilities, types, shared components, SDKs, clients."
- `packages/README.md` — "Rule: if `uis/` and `services/` both need the same interface → extract it here."

## Qué se debe hacer

- Declarar **todos los tipos TypeScript compartidos entre UIs y servicios** dentro de `packages/shared/types/`.
- Añadir un archivo por dominio (ej. `incident.ts`, `warehouse.ts`, `carrier.ts`).
- Exportar los tipos desde el archivo `index.ts` de `packages/shared/types/` para facilitar su consumo futuro.
- La estrategia de importación concreta (alias `@repo/shared-types`, ruta relativa, u otra) se definirá cuando se resuelva la inconsistencia del entrypoint documentada en `reconnaissance.md`. Hasta entonces, los consumidores pueden importar con una ruta relativa a `packages/shared/types/`.
- Entender que `packages/shared/types/` es la fuente única de tipos para consumidores **TypeScript**. El backend en **Python** debe declarar sus propios schemas/enums Pydantic equivalentes, con valores de catálogo coincidentes exactamente. No se exige que Python importe TypeScript.

## Qué NO se debe hacer

- ❌ Duplicar tipos de dominio dentro de una UI (`uis/`) sin extraerlos primero a `packages/shared/types/`.
- ❌ Definir los mismos tipos en `services/` y en `uis/` por separado — eso rompe la regla de fuente única.
- ❌ Modificar `packages/shared/package.json` para cambiar el entrypoint sin una decisión explícita documentada (la inconsistencia actual entre `main: index.ts` y el código real en `types/index.ts` está identificada como mejora pendiente en `docs/incident-manager/reconnaissance.md`).
- ❌ Exigir que el backend Python importe los tipos TypeScript — Python declara sus propios equivalentes con los mismos valores de catálogo.

## Cómo verificar su cumplimiento

- `ls packages/shared/types/*.ts` debe listar los archivos de tipos por dominio.
- Los imports en `uis/` y `services/` no deben contener definiciones locales duplicadas de tipos que ya existen en `packages/shared/types/`.
- `grep -r "interface\|type " uis/ --include="*.ts" | grep -v ".spec." | grep -v ".test."` no debe revelar interfaces de dominio que ya existen en `packages/shared/types/`.
- Los valores de catálogo en los enums Pydantic del backend deben coincidir exactamente con los declarados en `packages/shared/types/`.