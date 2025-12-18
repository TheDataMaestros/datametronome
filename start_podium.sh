#!/bin/bash

# DataMetronome Podium Startup Script
# This script sets up environment variables and starts the API server

set -euo pipefail

# Source configuration file if it exists
if [ -f "config.env" ]; then
    echo "📋 Loading configuration from config.env..."
    export $(grep -v '^#' config.env | xargs)
fi

# Normalize comma-separated CORS origins into JSON array for Pydantic
if [ -n "${DATAMETRONOME_ALLOWED_ORIGINS:-}" ]; then
    if [[ "${DATAMETRONOME_ALLOWED_ORIGINS}" != \[*\] ]]; then
        IFS=',' read -ra __origins <<< "${DATAMETRONOME_ALLOWED_ORIGINS}"
        __json_origins="["
        for __origin in "${__origins[@]}"; do
            __trimmed_origin="$(echo "${__origin}" | xargs)"
            if [ -n "${__trimmed_origin}" ]; then
                __json_origins="${__json_origins}\"${__trimmed_origin}\","
            fi
        done
        __json_origins="${__json_origins%,}]"
        DATAMETRONOME_ALLOWED_ORIGINS="${__json_origins}"
    fi
    export DATAMETRONOME_ALLOWED_ORIGINS
fi

# Set default environment variables
export DATAMETRONOME_SECRET_KEY="${DATAMETRONOME_SECRET_KEY:-demo-secret-key-for-development-only}"
export PODIUM_PORT="${PODIUM_PORT:-8000}"
export PODIUM_HOST="${PODIUM_HOST:-0.0.0.0}"
export PODIUM_API_BASE="http://localhost:${PODIUM_PORT}"
export DATAMETRONOME_PORT="${DATAMETRONOME_PORT:-${PODIUM_PORT}}"
export DATAMETRONOME_HOST="${DATAMETRONOME_HOST:-${PODIUM_HOST}}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Change to the podium directory
cd datametronome/podium

echo "🎵 Starting DataMetronome Podium API..."
echo "📍 Host: ${PODIUM_HOST}"
echo "🔌 Port: ${PODIUM_PORT}"
echo "🌐 API Base: ${PODIUM_API_BASE}"
echo "🔧 Environment: ${ENVIRONMENT}"
echo "📝 Log Level: ${LOG_LEVEL}"
echo ""

# Start the API server
python3 -m uvicorn datametronome_podium.main:app \
    --host "${PODIUM_HOST}" \
    --port "${PODIUM_PORT}" \
    --reload
