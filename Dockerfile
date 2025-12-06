# ==============================================================================
# NAHD TRAVELS - Unified Dockerfile for Frontend and Backend
# ==============================================================================
# This Dockerfile uses multi-stage builds to create both frontend and backend images
# Use --target to build specific stages:
#   - backend: Django backend service
#   - frontend-builder: Frontend build stage
#   - frontend: Frontend nginx runtime
# ==============================================================================

# ==============================================================================
# FRONTEND BUILD STAGE
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy all frontend files (excluding what's in .dockerignore)
# This copies the entire frontend directory structure
COPY frontend/ .

# Verify file structure and critical files exist
RUN echo "=== Build Environment Verification ===" && \
    echo "Working directory: $(pwd)" && \
    echo "" && \
    echo "=== Root directory contents ===" && \
    ls -la && \
    echo "" && \
    echo "=== Checking src/ directory ===" && \
    test -d src && ls -la src/ || (echo "ERROR: src/ directory not found!" && exit 1) && \
    echo "" && \
    echo "=== Checking src/lib/ directory ===" && \
    test -d src/lib && ls -la src/lib/ || (echo "ERROR: src/lib/ directory not found!" && exit 1) && \
    echo "" && \
    echo "=== Verifying utils.ts file ===" && \
    if [ -f src/lib/utils.ts ]; then \
      echo "✓ src/lib/utils.ts exists" && \
      echo "File size: $(stat -c%s src/lib/utils.ts) bytes"; \
    else \
      echo "✗ ERROR: src/lib/utils.ts NOT FOUND!" && \
      echo "Searching for any utils.ts files:" && \
      find . -name "utils.ts" -type f 2>/dev/null || echo "No utils.ts files found" && \
      echo "Full directory tree:" && \
      find src -type f 2>/dev/null | head -20 && \
      exit 1; \
    fi && \
    echo "" && \
    echo "=== Verifying configuration files ===" && \
    test -f vite.config.ts && echo "✓ vite.config.ts found" || (echo "✗ vite.config.ts missing!" && exit 1) && \
    test -f tsconfig.json && echo "✓ tsconfig.json found" || echo "⚠ tsconfig.json not found (may be optional)" && \
    echo "" && \
    echo "=== All verifications passed ==="

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build the frontend application
RUN echo "=== Starting build process ===" && \
    npm run build

# ==============================================================================
# FRONTEND RUNTIME STAGE
# ==============================================================================
FROM nginx:1.25-alpine AS frontend

WORKDIR /app

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend files from builder stage
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ==============================================================================
# BACKEND STAGE
# ==============================================================================
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
        curl \
        python3-dev \
        libcairo2-dev \
        libpango1.0-dev \
        pkg-config \
        python3-pip \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt /app/

# Upgrade pip and install requirements
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --upgrade setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend project
COPY backend/ /app/

# Create directories for static and media files
RUN mkdir -p /app/staticfiles \
    && mkdir -p /app/media

# Collect static files (allow failure for initial setup)
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8001

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "travelcrm.wsgi:application", "--bind", "0.0.0.0:8001"]

