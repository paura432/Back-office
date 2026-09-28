# dependency-management.md

> Regla derivada de la configuración del devcontainer.
> Fija los gestores de dependencias oficiales del monorepo.

---

- **Aplicación:** `always_active`
- **Ámbito/patrón de archivos:** `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `**/devcontainer.json`, `**/post-create.sh`

## Evidencia de origen

- `.devcontainer/post-create.sh` — Línea `corepack enable && corepack prepare pnpm@latest --activate`: establece pnpm + Corepack como gestor JS/TS.
- `.devcontainer/post-create.sh` — Línea `python -m pip install --upgrade pip uv && uv sync`: establece uv como gestor Python.
- `README.md` — Sección "Current status of the template": "no workspace runner is configured at root" — confirma que no hay configuración de workspace npm/pnpm en raíz todavía, pero la herramienta base (pnpm) ya está fijada.

## Qué se debe hacer

- Usar **pnpm** (vía Corepack) para gestión de dependencias JavaScript/TypeScript.
- Usar **uv** para gestión de dependencias Python.
- Documentar la elección de cualquier gestor adicional en un ADR dentro de `docs/` si fuera necesario.
- Mantener `package.json` en cada subproyecto JS/TS que se añada.
- Mantener `pyproject.toml` (o `uv sync` compatible) en cada subproyecto Python que se añada.

## Qué NO se debe hacer

- ❌ Usar `npm install` o `yarn add` para instalar dependencias. Usar siempre `pnpm install`.
- ❌ Crear archivos `requirements.txt` o `Pipfile` para proyectos Python. Usar `pyproject.toml` con uv.
- ❌ Introducir un gestor de dependencias diferente sin una decisión explícita y documentada (ADR en `docs/`).
- ❌ Asumir que npm o yarn están disponibles como alternativa — el devcontainer solo configura pnpm.

## Cómo verificar su cumplimiento

- `pnpm-lock.yaml` debe estar presente si hay proyectos JS/TS.
- `uv.lock` debe estar presente si hay proyectos Python con uv.
- Buscar `npm install`, `yarn add`, `pip install -r` en scripts o documentación: deben estar ausentes.
- `grep -r "npm install\|yarn add\|pip install -r" --include="*.md" --include="*.sh" --include="*.json"` no debe devolver resultados que propongan estos comandos como alternativa.