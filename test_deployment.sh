#!/bin/bash
# Test deployment script for DataMetronome
# Validates that the entire system can start and function correctly

set -e  # Exit on error

echo "🎵 DataMetronome Deployment Test"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Step 1: Check prerequisites
echo ""
echo "Step 1: Checking Prerequisites"
echo "------------------------------"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

if ! command -v docker &> /dev/null; then
    print_error "Docker not found"
    exit 1
fi
print_success "Docker found: $(docker --version | head -n1)"

# Step 2: Install Python dependencies
echo ""
echo "Step 2: Installing Dependencies"
echo "-------------------------------"

python3 -m pip install --quiet httpx || {
    print_error "Failed to install httpx"
    exit 1
}
print_success "Dependencies installed"

# Step 3: Start test database (if using Docker)
echo ""
echo "Step 3: Starting Test Database (Optional)"
echo "----------------------------------------"

if docker ps | grep -q postgres-test; then
    print_info "Test database already running"
else
    print_info "To run with PostgreSQL, start test database with:"
    echo "  docker run -d --name postgres-test \\"
    echo "    -e POSTGRES_DB=testdb \\"
    echo "    -e POSTGRES_USER=testuser \\"
    echo "    -e POSTGRES_PASSWORD=testpass \\"
    echo "    -p 5432:5432 postgres:15"
fi

# Step 4: Start Podium API
echo ""
echo "Step 4: Testing Podium API"
echo "-------------------------"

print_info "Starting Podium API in background..."

cd datametronome/podium

# Kill any existing instance
pkill -f "datametronome_podium.main" || true

# Start API in background
python3 -m datametronome_podium.main &
API_PID=$!

cd ../..

# Wait for API to start
print_info "Waiting for API to be ready..."
sleep 5

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    print_error "API failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

print_success "Podium API is running (PID: $API_PID)"

# Step 5: Run realistic demo
echo ""
echo "Step 5: Running Realistic Demo"
echo "------------------------------"

if python3 demo_realistic.py; then
    print_success "Demo completed successfully"
    DEMO_SUCCESS=true
else
    print_error "Demo failed"
    DEMO_SUCCESS=false
fi

# Step 6: Test health endpoint
echo ""
echo "Step 6: Testing Health Endpoint"
echo "-------------------------------"

HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    print_success "Health check passed"
    echo "$HEALTH" | python3 -m json.tool
else
    print_error "Health check failed"
fi

# Step 7: Test metrics endpoint
echo ""
echo "Step 7: Testing Metrics Endpoint"
echo "--------------------------------"

METRICS=$(curl -s http://localhost:8000/metrics)
if echo "$METRICS" | grep -q "http_requests_total"; then
    print_success "Metrics endpoint working"
    echo "Sample metrics:"
    echo "$METRICS" | grep -E "(http_requests_total|system_health|active_)" | head -5
else
    print_error "Metrics endpoint failed"
fi

# Step 8: Cleanup
echo ""
echo "Step 8: Cleanup"
echo "--------------"

print_info "Stopping Podium API..."
kill $API_PID 2>/dev/null || true
wait $API_PID 2>/dev/null || true
print_success "Podium API stopped"

# Final summary
echo ""
echo "================================"
echo "Test Summary"
echo "================================"

if [ "$DEMO_SUCCESS" = true ]; then
    print_success "All tests passed!"
    echo ""
    echo "Your DataMetronome installation is working correctly."
    echo ""
    echo "Next steps:"
    echo "  1. Start services: docker-compose up -d"
    echo "  2. Generate test data: python3 scripts/generate_test_data.py"
    echo "  3. Run demo: python3 demo_realistic.py"
    echo "  4. Open UI: http://localhost:8501"
    exit 0
else
    print_error "Some tests failed"
    echo ""
    echo "Check the errors above and ensure:"
    echo "  - Python dependencies are installed"
    echo "  - Database is accessible"
    echo "  - Ports 8000, 8501 are available"
    exit 1
fi
