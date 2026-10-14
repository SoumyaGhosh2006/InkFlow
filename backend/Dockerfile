# ==============================================================================
# InkFlow Backend Dockerfile (Production Containerization)
# Multi-stage lightweight build using official Python 3.11 slim image
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation essentials for building wheel packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and build wheels to isolate build dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Final Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a non-privileged user to run the application securely
RUN groupadd -g 1001 inkflow && \
    useradd -u 1001 -g inkflow -s /bin/bash -m inkflow

# Copy installed python site-packages from builder stage
COPY --from=builder /root/.local /home/inkflow/.local

# Ensure the non-root user PATH points to installed binaries
ENV PATH=/home/inkflow/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application source code
COPY --chown=inkflow:inkflow . /app

# Switch to non-root user
USER inkflow

# Expose default HTTP port
EXPOSE 8000

# Start Uvicorn ASGI server with production concurrency settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
