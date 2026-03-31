# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    redis-tools \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy uv configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY model/ ./model/
COPY examples/ ./examples/
COPY scripts/ ./scripts/
COPY server.py ./

# Create necessary directories, set permissions, and handle MediaPipe model
RUN mkdir -p /app/data /app/logs /app/.celery_pids /tmp/test_session_frames /app/model/mediapipe && \
    chmod +x scripts/*.sh && \
    if [ ! -f "/app/model/mediapipe/detector.tflite" ]; then \
        echo "MediaPipe model will be mounted as volume"; \
    fi

# Expose ports
EXPOSE 8000 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Default command for API server
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8002"]

# Labels for metadata
LABEL maintainer="Focus Tracker Team" \
      version="2.0" \
      description="Focus Management System with Batch Processing" \
      architecture="x86_64" \
      os="linux"
