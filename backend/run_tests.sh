#!/bin/bash

# Test Runner Script for Phase 1.4
# Runs all unit and integration tests for the inventory module

set -e  # Exit on error

echo "=========================================="
echo "Running Phase 1.4 Inventory Module Tests"
echo "=========================================="
echo ""

# Change to backend directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
fi

# Install test dependencies if needed
echo "Checking test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov httpx

echo ""
echo "=========================================="
echo "Running Unit Tests (Repositories)"
echo "=========================================="
echo ""

# Run repository tests
pytest tests/test_product_repository.py -v --tb=short
pytest tests/test_category_repository.py -v --tb=short
pytest tests/test_inventory_repository.py -v --tb=short

echo ""
echo "=========================================="
echo "Running Integration Tests (API)"
echo "=========================================="
echo ""

# Run API tests
pytest tests/test_product_api.py -v --tb=short
pytest tests/test_category_api.py -v --tb=short
pytest tests/test_import_export_api.py -v --tb=short

echo ""
echo "=========================================="
echo "Running All Tests with Coverage"
echo "=========================================="
echo ""

# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "✅ Unit tests completed"
echo "✅ Integration tests completed"
echo "✅ Coverage report generated in htmlcov/"
echo ""
echo "Phase 1.4 Testing Complete!"
