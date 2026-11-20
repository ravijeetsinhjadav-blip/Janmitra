# JanMitra Assist Backend - Production Dockerfile for Render Cloud
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==============================================================================
# Final Runner Stage
# ==============================================================================
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    WEB_CONCURRENCY=2 \
    PYTHONPATH=/app/backend \
    ENVIRONMENT=development \
    DEBUG=true \
    OCR_PROVIDER=mock \
    AI_PROVIDER=mock

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN groupadd -g 1001 janmitra && \
    useradd -u 1001 -g janmitra -s /bin/bash -m janmitra

WORKDIR /app/backend

# Copy backend application source code
COPY --chown=janmitra:janmitra backend/ /app/backend

RUN mkdir -p /app/backend/storage/documents && \
    chown -R janmitra:janmitra /app/backend/storage

USER janmitra

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
