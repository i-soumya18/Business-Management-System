#!/bin/bash

# Business Management System - Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up Business Management System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update the .env file with your configuration!"
fi

# Start Docker containers
echo "🐳 Starting Docker containers..."
docker-compose up -d postgres redis mongodb

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 10

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

# Initialize default data
echo "🌱 Initializing default data..."
python scripts/init_default_data.py

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
cd ..
pre-commit install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the backend server:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To run tests:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  pytest"
echo ""
echo "API documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""
