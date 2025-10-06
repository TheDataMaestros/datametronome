#!/bin/bash

# DataMetronome Streamlit UI Startup Script
# This script sets up environment variables and starts the Streamlit UI

# Source configuration file if it exists
if [ -f "config.env" ]; then
    echo "📋 Loading configuration from config.env..."
    export $(grep -v '^#' config.env | xargs)
fi

# Set default environment variables
export PODIUM_PORT="${PODIUM_PORT:-8001}"
export PODIUM_API_BASE="${PODIUM_API_BASE:-http://localhost:${PODIUM_PORT}}"
export STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# Change to the streamlit directory
cd datametronome/ui-streamlit

echo "🎵 Starting DataMetronome Streamlit UI..."
echo "🌐 API Base: ${PODIUM_API_BASE}"
echo "🔌 Streamlit Port: ${STREAMLIT_PORT}"
echo ""

# Start the Streamlit app
streamlit run streamlit_app.py --server.port "${STREAMLIT_PORT}" --server.address 0.0.0.0
