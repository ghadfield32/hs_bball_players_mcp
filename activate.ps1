# PowerShell Activation Script for Basketball Stats API
# Activates virtual environment and sets up environment variables

Write-Host "🏀 Basketball Stats API - Environment Activation" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Check if .venv exists
if (Test-Path ".venv") {
    Write-Host "✅ Virtual environment found" -ForegroundColor Green

    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\.venv\Scripts\Activate.ps1"

    # Load environment variables from .env if it exists
    if (Test-Path ".env") {
        Write-Host "✅ Loading .env file" -ForegroundColor Green
        Get-Content .env | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                if ($name -and $value) {
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
    } else {
        Write-Host "⚠️  No .env file found (optional)" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Environment activated! Available commands:" -ForegroundColor Green
    Write-Host "  • pytest                    - Run tests" -ForegroundColor White
    Write-Host "  • uvicorn src.main:app      - Start API server" -ForegroundColor White
    Write-Host "  • python scripts/...        - Run utility scripts" -ForegroundColor White
    Write-Host ""
    Write-Host "Quick commands:" -ForegroundColor Cyan
    Write-Host "  • python scripts/verify_adapters.py --quick" -ForegroundColor White
    Write-Host "  • python scripts/generate_adapter.py" -ForegroundColor White
    Write-Host "  • pytest tests/ -v" -ForegroundColor White
    Write-Host ""

} else {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow

    # Try uv first (faster)
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "Using uv (fast)..." -ForegroundColor Cyan
        uv venv
        & ".\.venv\Scripts\Activate.ps1"
        uv pip install -r requirements.txt
    }
    # Fall back to standard venv
    else {
        Write-Host "Using standard Python venv..." -ForegroundColor Cyan
        python -m venv .venv
        & ".\.venv\Scripts\Activate.ps1"
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    }

    Write-Host ""
    Write-Host "✅ Environment created and activated!" -ForegroundColor Green
    Write-Host ""
}

# Set Python path to include src directory
$env:PYTHONPATH = "$PWD;$PWD\src;$env:PYTHONPATH"

Write-Host "Python: $(python --version)" -ForegroundColor Cyan
Write-Host "Location: $PWD" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
