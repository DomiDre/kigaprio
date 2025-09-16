FROM ubuntu:24.04 AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ubuntu

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/ubuntu/.local/bin:$PATH"


# Set work directory
WORKDIR /app

# Copy project files
COPY --chown=ubuntu:ubuntu pyproject.toml uv.lock .python-version ./

# Create a minimal __init__.py to avoid sync issues
RUN mkdir -p src/kigaprio && touch src/kigaprio/__init__.py && touch README.md



FROM base AS development

# Install dependencies
RUN uv sync

# Copy source code (this will overwrite the dummy __init__.py)
COPY src/ ./src/

# Create directories
RUN mkdir -p /app/static

# Expose port
EXPOSE 8000

# Run with uv
CMD ["uv", "run", "python", "-m", "uvicorn", "kigaprio.main:app", "--host", "0.0.0.0", "--port", "8000"]




FROM base AS builder
RUN uv sync --frozen --no-dev



# Production stage
FROM python:3.12-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy uv and installed packages from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Copy source code
COPY src/ ./src/

# Create directories for static files and uploads
RUN mkdir -p /app/static /app/uploads

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with gunicorn for better performance
CMD ["uv", "run", "gunicorn", "kigaprio.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
