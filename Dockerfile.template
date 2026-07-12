# SGU Brunnar MCP Server — production Docker image
# Python 3.12 slim base for Cloud Run compatibility
FROM python:3.12-slim

# Prevent .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user
RUN groupadd --system appgroup && useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

# Install build dependencies in one layer, then remove them
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification first for layer caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install the project and all dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Create a writable temp directory for exports
RUN mkdir -p /tmp/exports && chown appuser:appgroup /tmp/exports

# Switch to non-root user
USER appuser

# Cloud Run injects PORT; default to 8080
ENV PORT=8080

# Health check using the liveness endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/healthz')"

EXPOSE ${PORT}

CMD ["sh", "-c", "python -m uvicorn mcp_sgu.app:create_app --factory --host 0.0.0.0 --port ${PORT} --log-config /dev/null"]
