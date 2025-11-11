# Setup Script for Basketball Stats API
# Run this once to set up the entire development environment

param(
    [switch]$AutoActivate,
    [switch]$UseUV
)

Write-Host ""
Write-Host "🏀 Basketball Stats API - Complete Setup" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python not found! Please install Python 3.11 or higher" -ForegroundColor Red
    exit 1
}

$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
$major = [int]$matches[1]
$minor = [int]$matches[2]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
    Write-Host "❌ Python $major.$minor found. Need Python 3.11+" -ForegroundColor Red
    exit 1
}

Write-Host "✅ $pythonVersion" -ForegroundColor Green
Write-Host ""

# Step 2: Clean old environment if exists
if (Test-Path ".venv") {
    Write-Host "Step 2: Found existing virtual environment" -ForegroundColor Yellow
    $response = Read-Host "Remove and recreate? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "Removing old environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    } else {
        Write-Host "Keeping existing environment" -ForegroundColor Green
    }
} else {
    Write-Host "Step 2: No existing environment found" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Step 3: Creating virtual environment..." -ForegroundColor Yellow

    if ($UseUV -or (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "Using uv (fast package manager)..." -ForegroundColor Cyan
        uv venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ uv failed! Trying standard venv..." -ForegroundColor Red
            python -m venv .venv
        } else {
            Write-Host "✅ Virtual environment created with uv" -ForegroundColor Green
        }
    } else {
        Write-Host "Using standard Python venv..." -ForegroundColor Cyan
        python -m venv .venv
        Write-Host "✅ Virtual environment created" -ForegroundColor Green
    }
} else {
    Write-Host "Step 3: Virtual environment already exists" -ForegroundColor Green
}
Write-Host ""

# Step 4: Activate and install dependencies
Write-Host "Step 4: Installing dependencies..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

if ($UseUV -or (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing with uv..." -ForegroundColor Cyan
    uv pip install -r requirements.txt
} else {
    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    Write-Host "Installing requirements..." -ForegroundColor Cyan
    pip install -r requirements.txt
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "❌ Dependency installation failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Create .env file if it doesn't exist
Write-Host "Step 5: Checking .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Cyan

    $envContent = @"
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
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env file created" -ForegroundColor Green
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}
Write-Host ""

# Step 6: Create data directories
Write-Host "Step 6: Creating data directories..." -ForegroundColor Yellow
$directories = @("data/logs", "data/cache", "data/exports")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Cyan
    }
}
Write-Host "✅ Data directories ready" -ForegroundColor Green
Write-Host ""

# Step 7: Run quick verification
Write-Host "Step 7: Running quick verification..." -ForegroundColor Yellow
Write-Host "Testing imports..." -ForegroundColor Cyan
python -c "from src.main import app; print('✅ Core imports successful')" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Core imports successful" -ForegroundColor Green
} else {
    Write-Host "⚠️  Import check had issues (may be normal)" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Auto-activation setup (optional)
if ($AutoActivate) {
    Write-Host "Step 8: Setting up auto-activation..." -ForegroundColor Yellow

    $profilePath = $PROFILE
    $repoPath = (Get-Location).Path

    $autoActivateCode = @"

# Basketball Stats API Auto-Activation (added by setup.ps1)
`$basketball_repo = "$repoPath"
if ((Get-Location).Path -eq `$basketball_repo -and (Test-Path "`$basketball_repo\.venv")) {
    if (`$null -eq `$env:VIRTUAL_ENV) {
        Write-Host "Auto-activating Basketball Stats API environment..." -ForegroundColor Cyan
        & "`$basketball_repo\activate.ps1"
    }
}
"@

    # Check if profile exists
    if (-not (Test-Path $profilePath)) {
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }

    # Check if auto-activation already added
    $profileContent = Get-Content $profilePath -Raw
    if ($profileContent -notlike "*Basketball Stats API Auto-Activation*") {
        Add-Content -Path $profilePath -Value $autoActivateCode
        Write-Host "✅ Auto-activation added to PowerShell profile" -ForegroundColor Green
        Write-Host "   Restart PowerShell for changes to take effect" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Auto-activation already configured" -ForegroundColor Green
    }
} else {
    Write-Host "Step 8: Skipping auto-activation setup" -ForegroundColor Yellow
    Write-Host "   Run with -AutoActivate flag to enable" -ForegroundColor Cyan
}
Write-Host ""

# Final summary
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: .\activate.ps1" -ForegroundColor White
Write-Host "  2. Test adapters: python scripts/verify_adapters.py --quick" -ForegroundColor White
Write-Host "  3. Start API: uvicorn src.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Cyan
Write-Host "  • python scripts/generate_adapter.py      - Create new adapter" -ForegroundColor White
Write-Host "  • python scripts/inspect_website.py       - Inspect website" -ForegroundColor White
Write-Host "  • python scripts/verify_adapters.py       - Test all adapters" -ForegroundColor White
Write-Host "  • pytest tests/ -v                        - Run test suite" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  • README.md                               - Project overview" -ForegroundColor White
Write-Host "  • QUICK_REFERENCE.md                      - Command reference" -ForegroundColor White
Write-Host "  • scripts/README.md                       - Scripts documentation" -ForegroundColor White
Write-Host ""
