# ==============================================================================
# ملف بناء الحاوية متعدد المراحل (Multi-Stage Dockerfile)
# My Road to be Trilunair Dr.MaJoOoOoOoD
# ==============================================================================

# المرحلة الأولى: بناء الواجهة الهولوغرامية الأمامية (React + TypeScript + Vite)
FROM node:24-bookworm-slim AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# المرحلة الثانية: تشغيل الخادم الخلفي (FastAPI + Uvicorn + SQLite) وتقديم الواجهة المبنية
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRILUNAIR_DEFAULT_MODE=PAPER \
    TRILUNAIR_DB_PATH=/app/backend/data/trilunair.db \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv \
    && useradd -m -u 10001 trilunair

COPY backend/pyproject.toml backend/uv.lock* /app/backend/
WORKDIR /app/backend
RUN uv sync --no-dev

COPY backend/ /app/backend/
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

RUN mkdir -p /app/backend/data && chown -R trilunair:trilunair /app

USER trilunair
EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/system/status || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
