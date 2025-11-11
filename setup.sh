#!/bin/bash
# Setup Script for Basketball Stats API (Linux/Mac)
# Run this once to set up the entire development environment

set -e  # Exit on error

AUTO_ACTIVATE=false
USE_UV=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-activate)
            AUTO_ACTIVATE=true
            shift
            ;;
        --use-uv)
            USE_UV=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "🏀 Basketball Stats API - Complete Setup"
echo "======================================================================"
echo ""

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found! Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ Python $PYTHON_VERSION found. Need Python 3.11+"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION"
echo ""

# Step 2: Clean old environment if exists
if [ -d ".venv" ]; then
    echo "Step 2: Found existing virtual environment"
    read -p "Remove and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing old environment..."
        rm -rf .venv
    else
        echo "Keeping existing environment"
    fi
else
    echo "Step 2: No existing environment found"
fi
echo ""

# Step 3: Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Step 3: Creating virtual environment..."

    if $USE_UV || command -v uv &> /dev/null; then
        echo "Using uv (fast package manager)..."
        uv venv || python3 -m venv .venv
        echo "✅ Virtual environment created"
    else
        echo "Using standard Python venv..."
        python3 -m venv .venv
        echo "✅ Virtual environment created"
    fi
else
    echo "Step 3: Virtual environment already exists"
fi
echo ""

# Step 4: Activate and install dependencies
echo "Step 4: Installing dependencies..."
source .venv/bin/activate

if $USE_UV || command -v uv &> /dev/null; then
    echo "Installing with uv..."
    uv pip install -r requirements.txt
else
    echo "Upgrading pip..."
    python -m pip install --upgrade pip
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies installed"
echo ""

# Step 5: Create .env file if it doesn't exist
echo "Step 5: Checking .env file..."
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."

    cat > .env << 'EOF'
# Basketball Stats API Environment Variables

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Logging
LOG_LEVEL=INFO
LOG_DIR=data/logs

# Cache Configuration
CACHE_ENABLED=true
CACHE_DIR=data/cache
CACHE_DEFAULT_TTL=3600

# Redis Configuration (optional)
# REDIS_URL=redis://localhost:6379/0
# REDIS_ENABLED=false

# Database Configuration
DATABASE_URL=sqlite:///data/basketball_stats.db

# Rate Limiting
RATE_LIMIT_ENABLED=true

# DuckDB Configuration
DUCKDB_PATH=data/analytics.duckdb
EOF

    echo "✅ .env file created"
else
    echo "✅ .env file exists"
fi
echo ""

# Step 6: Create data directories
echo "Step 6: Creating data directories..."
mkdir -p data/logs data/cache data/exports
echo "✅ Data directories ready"
echo ""

# Step 7: Run quick verification
echo "Step 7: Running quick verification..."
echo "Testing imports..."
python -c "from src.main import app; print('✅ Core imports successful')" 2>/dev/null || echo "⚠️  Import check had issues (may be normal)"
echo ""

# Step 8: Auto-activation setup (optional)
if $AUTO_ACTIVATE; then
    echo "Step 8: Setting up auto-activation..."

    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        REPO_PATH=$(pwd)
        AUTO_ACTIVATE_CODE="
# Basketball Stats API Auto-Activation (added by setup.sh)
basketball_repo=\"$REPO_PATH\"
if [ \"\$PWD\" = \"\$basketball_repo\" ] && [ -d \"\$basketball_repo/.venv\" ] && [ -z \"\$VIRTUAL_ENV\" ]; then
    echo \"Auto-activating Basketball Stats API environment...\"
    source \"\$basketball_repo/activate.sh\"
fi
"

        if ! grep -q "Basketball Stats API Auto-Activation" "$SHELL_RC" 2>/dev/null; then
            echo "$AUTO_ACTIVATE_CODE" >> "$SHELL_RC"
            echo "✅ Auto-activation added to $SHELL_RC"
            echo "   Restart your shell for changes to take effect"
        else
            echo "✅ Auto-activation already configured"
        fi
    else
        echo "⚠️  Could not detect shell type for auto-activation"
    fi
else
    echo "Step 8: Skipping auto-activation setup"
    echo "   Run with --auto-activate flag to enable"
fi
echo ""

# Final summary
echo "======================================================================"
echo "✅ Setup Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Run: source activate.sh"
echo "  2. Test adapters: python scripts/verify_adapters.py --quick"
echo "  3. Start API: uvicorn src.main:app --reload"
echo ""
echo "Quick commands:"
echo "  • python scripts/generate_adapter.py      - Create new adapter"
echo "  • python scripts/inspect_website.py       - Inspect website"
echo "  • python scripts/verify_adapters.py       - Test all adapters"
echo "  • pytest tests/ -v                        - Run test suite"
echo ""
echo "Documentation:"
echo "  • README.md                               - Project overview"
echo "  • QUICK_REFERENCE.md                      - Command reference"
echo "  • scripts/README.md                       - Scripts documentation"
echo ""
