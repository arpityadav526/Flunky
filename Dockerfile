FROM python:3.13-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY cli/ cli/
COPY backend/ backend/
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=sqlite+aiosqlite:////data/flunky.db
WORKDIR /app
RUN groupadd --gid 10001 flunky && useradd --uid 10001 --gid flunky --create-home flunky \
    && mkdir /data && chown flunky:flunky /data
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels flunky && rm -rf /wheels
COPY alembic.ini ./
COPY migrations/ migrations/
USER flunky
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"]
CMD ["gunicorn", "backend.main:app", "--worker-class", "uvicorn_worker.UvicornWorker", "--workers", "2", "--bind", "0.0.0.0:8000"]
