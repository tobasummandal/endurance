FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/pyproject.toml /app/
RUN pip install --no-cache-dir -e .

COPY backend/helios /app/helios
COPY backend/alembic /app/alembic
COPY web /web

EXPOSE 8000
CMD ["sh", "-c", "uvicorn helios.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
