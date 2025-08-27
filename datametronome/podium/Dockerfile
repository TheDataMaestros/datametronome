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

# Install dependencies using uv
RUN uv pip install --system --no-cache-dir -e ./datametronome/pulse/core
RUN uv pip install --system --no-cache-dir -e ./datametronome/pulse/sqlite
RUN uv pip install --system --no-cache-dir -r datametronome/podium/requirements.txt
RUN uv pip install --system --no-cache-dir -e ./datametronome/podium

# Create reports directory
RUN mkdir -p reports

# Expose port
EXPOSE 8000

# Set environment variables
ENV DATAMETRONOME_HOST=0.0.0.0
ENV DATAMETRONOME_PORT=8000
ENV DATAMETRONOME_DEBUG=true
ENV DATAMETRONOME_DATABASE_URL=sqlite:///./datametronome.db

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "datametronome_podium.main"]


