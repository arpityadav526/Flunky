FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY cli/ cli/
COPY backend/ backend/
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
