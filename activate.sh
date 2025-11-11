#!/bin/bash
# Bash Activation Script for Basketball Stats API
# Activates virtual environment and sets up environment variables

echo "🏀 Basketball Stats API - Environment Activation"
echo "============================================================"

# Check if .venv exists
if [ -d ".venv" ]; then
    echo "✅ Virtual environment found"

    # Activate virtual environment
    echo "Activating virtual environment..."
    source .venv/bin/activate

    # Load environment variables from .env if it exists
    if [ -f ".env" ]; then
        echo "✅ Loading .env file"
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo "⚠️  No .env file found (optional)"
    fi

    echo ""
    echo "Environment activated! Available commands:"
    echo "  • pytest                    - Run tests"
    echo "  • uvicorn src.main:app      - Start API server"
    echo "  • python scripts/...        - Run utility scripts"
    echo ""
    echo "Quick commands:"
    echo "  • python scripts/verify_adapters.py --quick"
    echo "  • python scripts/generate_adapter.py"
    echo "  • pytest tests/ -v"
    echo ""

else
    echo "❌ Virtual environment not found!"
    echo ""
    echo "Creating virtual environment..."

    # Try uv first (faster)
    if command -v uv &> /dev/null; then
        echo "Using uv (fast)..."
        uv venv
        source .venv/bin/activate
        uv pip install -r requirements.txt
    else
        # Fall back to standard venv
        echo "Using standard Python venv..."
        python3 -m venv .venv
        source .venv/bin/activate
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    fi

    echo ""
    echo "✅ Environment created and activated!"
    echo ""
fi

# Set Python path to include src directory
export PYTHONPATH="$PWD:$PWD/src:$PYTHONPATH"

echo "Python: $(python --version)"
echo "Location: $PWD"
echo "============================================================"
