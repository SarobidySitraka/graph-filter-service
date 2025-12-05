#!/bin/bash
# setup.sh - Quick setup script for the project

set -e

echo "========================================="
echo "Neo4j Filter Service - Setup Script"
echo "========================================="

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "UV is already installed"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please update .env with your Neo4j credentials"
else
    echo ".env file already exists"
fi

# Install dependencies
echo "Installing dependencies..."
uv sync

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Update .env with your Neo4j credentials"
echo "  2. Start Neo4j database"
echo "  3. Run: uv run uvicorn app.main:app --reload"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
"""

print("=" * 60)
print("PROJECT SETUP COMPLETE")
print("=" * 60)
print("""
All files have been generated!

QUICK START GUIDE:
==================

1. Create project structure:
   mkdir -p neo4j-filter-service/{app/{core,services,api/{routes},utils},tests}
   cd neo4j-filter-service

2. Copy all file contents to their respective locations

3. Install UV (if not installed):
   curl -LsSf https://astral.sh/uv/install.sh | sh

4. Set up project:
   cp .env.example .env
   # Edit .env with your Neo4j credentials
   uv sync

5. Run locally:
   uv run uvicorn app.main:app --reload

6. OR run with Docker:
   docker-compose up -d

7. Access API documentation:
   http://localhost:8000/docs

TESTING:
========
uv run pytest                    # Run all tests
uv run pytest -v                 # Verbose output
uv run pytest --cov=app          # With coverage

CODE QUALITY:
=============
uv run black app/                # Format code
uv run ruff check app/           # Lint code

The project is production-ready with:
UV for fast dependency management
FastAPI with async support
Complete test suite
Docker support with health checks
Comprehensive error handling
Structured logging
Type hints throughout
Clean architecture