# Use Python 3.13 slim image
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy the entire project context
COPY . .

# Install dependencies using uv (monorepo editable installs)
RUN uv pip install --system --no-cache-dir -e ./datametronome/pulse/core
RUN uv pip install --system --no-cache-dir -e ./datametronome/pulse/sqlite
RUN uv pip install --system --no-cache-dir -e ./datametronome/pulse/bigquery
RUN uv pip install --system --no-cache-dir -e ./datametronome/brain/base
RUN uv pip install --system --no-cache-dir -e ./datametronome/podium
RUN uv pip install --system --no-cache-dir 'logfire[fastapi,httpx]>=0.20.0'

# Create reports directory
RUN mkdir -p reports

# Expose port
EXPOSE 8001

# Set environment variables
ENV DATAMETRONOME_HOST=0.0.0.0
ENV DATAMETRONOME_PORT=8001
ENV DATAMETRONOME_DEBUG=false
ENV DATAMETRONOME_DATABASE_URL=sqlite+aiosqlite:////app/data/datametronome.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["/bin/sh", "-c", "curl -fsS \"http://localhost:${DATAMETRONOME_PORT:-8001}/health\" || exit 1"]

# Run Alembic migrations then start the application
# If upgrade fails (tables already exist from legacy runner), stamp as current and retry
CMD ["sh", "-c", "cd /app/datametronome/podium && DATABASE_URL=${DATAMETRONOME_DATABASE_URL} alembic upgrade head || (DATABASE_URL=${DATAMETRONOME_DATABASE_URL} alembic stamp head && DATABASE_URL=${DATAMETRONOME_DATABASE_URL} alembic upgrade head) && cd /app && python -m datametronome_podium.main"]
