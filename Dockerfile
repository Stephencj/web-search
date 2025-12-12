# Stage 1: Build the SvelteKit frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY src/ ./src/
COPY static/ ./static/
COPY svelte.config.js tsconfig.json vite.config.js ./

# Build the frontend (static SPA)
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY src-python/requirements.txt ./requirements.txt

# Remove Windows-specific dependency and install requirements
RUN sed -i '/pywin32/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy Python source
COPY src-python/app ./app/
COPY src-python/alembic.ini ./
COPY src-python/alembic ./alembic/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/build ./static/

# Create data directory
RUN mkdir -p /data

# Environment variables
ENV WEBSEARCH_HOST=0.0.0.0
ENV WEBSEARCH_PORT=8000
ENV WEBSEARCH_DATA_DIR=/data
ENV WEBSEARCH_MEILISEARCH__HOST=http://meilisearch:7700

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
