FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

COPY helios /app/helios
COPY alembic /app/alembic

EXPOSE 8000
CMD ["uvicorn", "helios.main:app", "--host", "0.0.0.0", "--port", "8000"]
