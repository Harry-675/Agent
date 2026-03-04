#!/bin/bash

# Setup script for One News Aggregator

set -e

echo "🚀 Setting up One News Aggregator..."

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Current version: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Copy environment file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
else
    echo "ℹ️  .env file already exists"
fi

# Copy news sources config if not exists
if [ ! -f "config/news_sources.json" ]; then
    echo "📝 Creating news sources config from template..."
    cp config/news_sources.example.json config/news_sources.json
    echo "✅ news_sources.json created. Please edit it with your news sources."
else
    echo "ℹ️  news_sources.json already exists"
fi

# Start Docker services
echo "🐳 Starting Docker services (PostgreSQL and Redis)..."
docker-compose up -d
echo "✅ Docker services started"

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are healthy
if docker-compose ps | grep -q "healthy"; then
    echo "✅ Services are healthy"
else
    echo "⚠️  Services may not be fully ready yet. Please check with: docker-compose ps"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Alibaba Bailian API key"
echo "2. Edit config/news_sources.json with your news sources"
echo "3. Run tests: pytest"
echo "4. Start the application: uvicorn src.main:app --reload"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
