#!/bin/bash
# 🎵 DataMetronome Community Showcase Runner
# This script sets up and runs the complete DataMetronome showcase

set -e

echo "🎵 DataMetronome Community Showcase"
echo "=================================="

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Activating virtual environment..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please run:"
        echo "   python3 -m venv .venv"
        echo "   source .venv/bin/activate"
        echo "   ./run_showcase.sh"
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker is not running. Starting PostgreSQL manually..."
    echo "💡 For full showcase, start Docker and run: docker-compose up -d postgres"
    echo ""
    echo "🚀 Running basic community demo..."
    python3 community_demo.py
    exit 0
fi

echo "🐳 Setting up PostgreSQL database..."
docker-compose up -d postgres

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 15

echo "🔍 Checking PostgreSQL status..."
if docker-compose ps postgres | grep -q "Up"; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL failed to start. Check logs:"
    docker-compose logs postgres
    exit 1
fi

echo ""
echo "🎯 Running enhanced community demo with PostgreSQL..."
echo ""

python3 community_demo.py

echo ""
echo "🎉 Showcase completed!"
echo ""
echo "🚀 Next steps:"
echo "   • Start full services: make docker-prototype"
echo "   • View API docs: http://localhost:8000/docs"
echo "   • Try Streamlit UI: http://localhost:8501"
echo "   • Run realistic demo: python3 demo_realistic.py"
echo ""
echo "🛑 To stop services: docker-compose down"
