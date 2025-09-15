FROM ubuntu:24.04

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
COPY --chown=ubuntu:ubuntu pyproject.toml uv.lock README.md ./

# Create a minimal __init__.py to avoid sync issues
RUN mkdir -p src/kigaprio && touch src/kigaprio/__init__.py

# Install dependencies
RUN uv sync

# Copy source code (this will overwrite the dummy __init__.py)
COPY src/ ./src/

# Create directories
RUN mkdir -p uploads output

# Expose port
EXPOSE 8000

# Run with uv
CMD ["uv", "run", "python", "-m", "uvicorn", "kigaprio.main:app", "--host", "0.0.0.0", "--port", "8000"]
