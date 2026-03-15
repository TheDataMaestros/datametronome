#!/bin/bash

# DataMetronome Podium Startup Script
# This script sets up environment variables and starts the API server

set -euo pipefail

# Source configuration file if it exists
if [ -f ".env" ]; then
    echo "📋 Loading configuration from .env..."
    export $(grep -v '^#' .env | xargs)
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

# Track if PODIUM_PORT was explicitly set (before we assign defaults)
# We check this by seeing if it exists in the environment before we touch it
_PODIUM_PORT_WAS_SET="${PODIUM_PORT+yes}"

# Set PODIUM_PORT: use explicit value, or DATAMETRONOME_PORT if set, or default
if [ -n "${PODIUM_PORT:-}" ]; then
    # PODIUM_PORT was explicitly set, use it
    export PODIUM_PORT="${PODIUM_PORT}"
elif [ -n "${DATAMETRONOME_PORT:-}" ]; then
    # PODIUM_PORT not set, but DATAMETRONOME_PORT is - use it for PODIUM_PORT
    export PODIUM_PORT="${DATAMETRONOME_PORT}"
else
    # Neither set, use default (must match UI NUXT_PUBLIC_API_BASE / PODIUM_PORT)
    export PODIUM_PORT="8001"
fi

export PODIUM_HOST="${PODIUM_HOST:-0.0.0.0}"
export PODIUM_API_BASE="http://localhost:${PODIUM_PORT}"

# Set DATAMETRONOME_PORT: PODIUM_PORT takes precedence only if it was explicitly set
# Otherwise, preserve DATAMETRONOME_PORT if it was explicitly set
if [ -n "${_PODIUM_PORT_WAS_SET}" ]; then
    # PODIUM_PORT was explicitly set, it takes precedence
    export DATAMETRONOME_PORT="${PODIUM_PORT}"
elif [ -z "${DATAMETRONOME_PORT:-}" ]; then
    # Neither was explicitly set, use PODIUM_PORT value (which may have come from DATAMETRONOME_PORT)
    export DATAMETRONOME_PORT="${PODIUM_PORT}"
fi
# If DATAMETRONOME_PORT was explicitly set and PODIUM_PORT was not, DATAMETRONOME_PORT is preserved

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
# Check for venv in root directory first, then podium directory
if [ -d "../.venv" ]; then
    echo "🐍 Using root virtual environment (../.venv)..."
    python_cmd="../.venv/bin/python3"
elif [ -d ".venv" ]; then
    echo "🐍 Using virtual environment (.venv)..."
    python_cmd=".venv/bin/python3"
else
    echo "🐍 Using system python..."
    python_cmd="python3"
fi

$python_cmd -m uvicorn datametronome_podium.main:app \
    --host "${PODIUM_HOST}" \
    --port "${PODIUM_PORT}" \
    --reload
