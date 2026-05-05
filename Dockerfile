# --- Stage 1: build the Next.js reviewer app ---
FROM node:20-alpine AS reviewer
WORKDIR /web

# install deps separately for caching
COPY web/package.json ./
RUN npm install --no-audit --no-fund

# copy sources (excluding node_modules and out via .dockerignore)
COPY web/ ./

# produce static export at /web/out (basePath="/app")
RUN npm run build

# --- Stage 2: Python API serving both the landing page and the reviewer ---
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/pyproject.toml /app/
RUN pip install --no-cache-dir -e .

COPY backend/helios /app/helios
COPY backend/alembic /app/alembic

# Landing page + assets (everything from /web except node_modules / next build cache)
COPY web/index.html /web/index.html
COPY web/v2 /web/v2
# Next.js export — mounted at /app by FastAPI
COPY --from=reviewer /web/out /web/out

EXPOSE 8000
CMD ["sh", "-c", "uvicorn helios.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
