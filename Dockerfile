FROM python:3.13-slim AS builder
WORKDIR /build
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY cli/ cli/
COPY backend/ backend/
RUN pip install --no-cache-dir uv==0.9.21 \
    && uv export --locked --no-dev --no-emit-project --output-file requirements.txt > /dev/null \
    && pip wheel --no-cache-dir --require-hashes -r requirements.txt --wheel-dir /wheels \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=sqlite+aiosqlite:////data/flunky.db
WORKDIR /app
RUN groupadd --gid 10001 flunky && useradd --uid 10001 --gid flunky --create-home flunky \
    && mkdir /data && chown flunky:flunky /data
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels flunky && rm -rf /wheels
COPY alembic.ini ./
COPY migrations/ migrations/
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"]
CMD ["python", "-m", "backend.container"]
