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
RUN uv pip install --system --no-cache-dir -e ./datametronome/podium
RUN uv pip install --system --no-cache-dir -r datametronome/ui-streamlit/requirements.txt
RUN uv pip install --system --no-cache-dir -e ./datametronome/ui-streamlit

# Create reports directory
RUN mkdir -p reports

# Expose port
EXPOSE 8501

# Set environment variables
ENV PODIUM_API_BASE=http://podium:8000
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "datametronome/ui-streamlit/streamlit_app.py"]


