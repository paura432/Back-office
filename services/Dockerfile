FROM python:3.12.10-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.6.17 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev
COPY api/ ./

EXPOSE 8000
CMD ["sh", "-c", "uv sync --frozen --no-dev && exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app"]