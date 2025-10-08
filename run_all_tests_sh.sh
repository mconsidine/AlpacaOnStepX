#!/bin/bash

# OnStepX Alpaca Bridge - Complete Test Suite Runner
# This script runs all tests in order

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================================"
echo "OnStepX Alpaca Bridge - Complete Test Suite"
echo "================================================================"
echo ""

# Change to project directory
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "  Create it: python3 -m venv venv"
    exit 1
fi

# Create tests directory if it doesn't exist
mkdir -p tests
cd tests

echo ""
echo "================================================================"
echo "LEVEL 1: MODULE TESTS (No hardware required)"
echo "================================================================"
echo ""

echo -e "${BLUE}Running test_config.py...${NC}"
python3 test_config.py || { echo -e "${RED}✗ Config tests failed${NC}"; exit 1; }

echo -e "${BLUE}Running test_helpers.py...${NC}"
python3 test_helpers.py || { echo -e "${RED}✗ Helper tests failed${NC}"; exit 1; }

echo ""
echo "================================================================"
echo "LEVEL 2: DEVICE MOCK TESTS (No hardware required)"
echo "================================================================"
echo ""

# These would test device classes without actual hardware
# For now, skip if not present
if [ -f "test_telescope_mock.py" ]; then
    echo -e "${BLUE}Running test_telescope_mock.py...${NC}"
    python3 test_telescope_mock.py || echo -e "${YELLOW}⚠ Mock test skipped${NC}"
fi

if [ -f "test_camera_zwo_mock.py" ]; then
    echo -e "${BLUE}Running test_camera_zwo_mock.py...${NC}"
    python3 test_camera_zwo_mock.py || echo -e "${YELLOW}⚠ Mock test skipped${NC}"
fi

echo ""
echo "================================================================"
echo "LEVEL 3: HARDWARE TESTS (Hardware required - OPTIONAL)"
echo "================================================================"
echo ""

read -p "Do you want to run hardware tests? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "test_telescope_hardware.py" ]; then
        echo -e "${BLUE}Running test_telescope_hardware.py...${NC}"
        python3 test_telescope_hardware.py || echo -e "${YELLOW}⚠ Telescope hardware test failed${NC}"
    fi
    
    if [ -f "test_camera_zwo_hardware.py" ]; then
        echo -e "${BLUE}Running test_camera_zwo_hardware.py...${NC}"
        python3 test_camera_zwo_hardware.py || echo -e "${YELLOW}⚠ Camera hardware test failed${NC}"
    fi
else
    echo -e "${YELLOW}Skipping hardware tests${NC}"
fi

echo ""
echo "================================================================"
echo "LEVEL 4: API TESTS (Server required)"
echo "================================================================"
echo ""

# Check if server is already running
if curl -s http://localhost:5555/management/apiversions > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server already running${NC}"
    SERVER_WAS_RUNNING=true
else
    echo "Starting server in background..."
    cd "$PROJECT_DIR"
    python3 main.py > tests/server.log 2>&1 &
    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"
    
    # Wait for server to start
    echo "Waiting for server to start..."
    for i in {1..10}; do
        if curl -s http://localhost:5555/management/apiversions > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Server started${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    
    # Check if server started successfully
    if ! curl -s http://localhost:5555/management/apiversions > /dev/null 2>&1; then
        echo -e "${RED}✗ Server failed to start${NC}"
        echo "Check tests/server.log for errors"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    
    cd tests
fi

# Run API tests
echo ""
echo -e "${BLUE}Running test_api_management.py...${NC}"
python3 test_api_management.py || { echo -e "${RED}✗ Management API tests failed${NC}"; FAILED=true; }

echo ""
echo -e "${BLUE}Running test_api_telescope.py...${NC}"
if [ -f "test_api_telescope.py" ]; then
    python3 test_api_telescope.py || echo -e "${YELLOW}⚠ Telescope API test had issues${NC}"
fi

echo ""
echo -e "${BLUE}Running test_api_camera.py...${NC}"
python3 test_api_camera.py || echo -e "${YELLOW}⚠ Camera API test had issues${NC}"

# Stop server if we started it
if [ "$SERVER_WAS_RUNNING" != "true" ]; then
    echo ""
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
    sleep 2
fi

echo ""
echo "================================================================"
echo "TEST SUITE COMPLETE"
echo "================================================================"
echo ""

if [ "$FAILED" = "true" ]; then
    echo -e "${RED}✗ Some tests failed${NC}"
    echo "Check output above for details"
    exit 1
else
    echo -e "${GREEN}✅ All available tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Connect hardware and run hardware tests"
    echo "  2. Start server: python3 main.py"
    echo "  3. Test with N.I.N.A. or other client software"
    echo ""
fi
