#!/usr/bin/env bash
set -euo pipefail

# Enable Corepack and make pnpm available for JS/TS workspaces.
corepack enable || true
corepack prepare pnpm@latest --activate || true

python -m pip install --upgrade pip uv

synced=false
for project_dir in . services/api; do
	if [[ -f "$project_dir/pyproject.toml" ]] && python - "$project_dir/pyproject.toml" <<'PY'
import sys
import tomllib

try:
	with open(sys.argv[1], "rb") as project_file:
		project = tomllib.load(project_file)
	project_name = project.get("project", {}).get("name")
	valid = isinstance(project_name, str) and bool(project_name.strip())
except (OSError, ValueError, AttributeError):
	valid = False
sys.exit(0 if valid else 1)
PY
	then
		(
			cd "$project_dir"
			if [[ -f uv.lock ]]; then
				uv sync --frozen
			else
				uv sync
			fi
		)
		synced=true
		break
	fi
done

if [[ "$synced" == false ]]; then
	echo "No valid Python project found; skipping uv sync."
fi

echo "Devcontainer setup complete."
