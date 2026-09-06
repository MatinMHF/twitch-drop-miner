# ==========================================
# Stage 1: Build Frontend (Vite + React + Tailwind)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Backend Runtime
# ==========================================
FROM python:3.12-slim AS runner

# Environment Configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies including gosu for safe privilege dropping
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Backend Source
COPY backend/app /app/app

# Copy Built Static Frontend into Backend
COPY --from=frontend-builder /app/backend/static /app/static

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    groupadd -r appuser -g 1001 && \
    useradd -u 1001 -r -g appuser -d /app -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
