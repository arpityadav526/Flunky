FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (optional but safe)
RUN apt-get update && apt-get install -y gcc

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ backend/

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]