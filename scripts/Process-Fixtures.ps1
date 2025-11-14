<#
.SYNOPSIS
    Wisconsin WIAA Fixture Batch Processor (PowerShell Wrapper)

.DESCRIPTION
    Convenient Windows interface for processing Wisconsin WIAA fixtures.
    Wraps the Python batch processor with git integration and interactive prompts.

.PARAMETER Fixtures
    Specific fixtures to process (e.g., "2024,Boys,Div2", "2024,Girls,Div3")

.PARAMETER Planned
    Process all fixtures marked as 'planned' in manifest

.PARAMETER DryRun
    Validate only, don't update manifest

.PARAMETER Commit
    Automatically commit changes after successful processing

.EXAMPLE
    .\scripts\Process-Fixtures.ps1 -Planned
    Process all planned fixtures

.EXAMPLE
    .\scripts\Process-Fixtures.ps1 -Fixtures "2024,Boys,Div2", "2024,Girls,Div3"
    Process specific fixtures

.EXAMPLE
    .\scripts\Process-Fixtures.ps1 -Planned -DryRun
    Test processing without making changes

.EXAMPLE
    .\scripts\Process-Fixtures.ps1 -Planned -Commit
    Process and auto-commit successful additions
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false, Position=0)]
    [string[]]$Fixtures,

    [Parameter(Mandatory=$false)]
    [switch]$Planned,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun,

    [Parameter(Mandatory=$false)]
    [switch]$Commit,

    [Parameter(Mandatory=$false)]
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Warning2 { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error2 { param($Message) Write-Host $Message -ForegroundColor Red }

# Banner
Write-Host "`n" -NoNewline
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  Wisconsin WIAA Fixture Batch Processor" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Check we're in the right directory
if (-not (Test-Path "tests/fixtures/wiaa")) {
    Write-Error2 "❌ Error: Must run from repository root"
    Write-Error2 "   Current directory: $(Get-Location)"
    Write-Error2 "   Expected: hs_bball_players_mcp/"
    exit 1
}

# Check Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Info "✅ Python: $pythonVersion"
} catch {
    Write-Error2 "❌ Error: Python not found in PATH"
    Write-Error2 "   Install Python or activate your venv"
    exit 1
}

# Check scripts exist
$processScript = "scripts/process_fixtures.py"
if (-not (Test-Path $processScript)) {
    Write-Error2 "❌ Error: $processScript not found"
    exit 1
}

# Build command
$cmd = @("python", $processScript)

if ($Fixtures) {
    $cmd += "--fixtures"
    $cmd += $Fixtures
} else {
    $cmd += "--planned"
}

if ($DryRun) {
    $cmd += "--dry-run"
    Write-Warning2 "🏃 DRY RUN MODE: No changes will be saved"
    Write-Host ""
}

if ($Quiet) {
    $cmd += "--quiet"
}

# Run Python batch processor
Write-Info "🚀 Running batch processor..."
Write-Host ""

& $cmd[0] $cmd[1..$cmd.Length]
$exitCode = $LASTEXITCODE

Write-Host ""

# Handle results
if ($exitCode -eq 0) {
    Write-Success "✅ Batch processing completed successfully"

    if (-not $DryRun) {
        # Check if manifest was modified
        $manifestChanged = git diff --name-only | Select-String "manifest_wisconsin.yml"
        $fixturesAdded = git status --short | Select-String "tests/fixtures/wiaa/.*\.html"

        if ($manifestChanged -or $fixturesAdded) {
            Write-Host ""
            Write-Info "📝 Changes detected:"
            git status --short | Where-Object { $_ -match "manifest_wisconsin.yml|tests/fixtures/wiaa" }

            if ($Commit) {
                Write-Host ""
                Write-Info "💾 Auto-committing changes..."

                # Stage changes
                git add tests/fixtures/wiaa/

                # Count new fixtures
                $newFixtureCount = (git diff --cached --name-only | Select-String "tests/fixtures/wiaa/.*\.html" | Measure-Object).Count

                # Generate commit message
                $commitMsg = "Add $newFixtureCount Wisconsin WIAA fixture(s)`n`n"
                $commitMsg += "Fixtures added:`n"

                git diff --cached --name-only | Select-String "tests/fixtures/wiaa/.*\.html" | ForEach-Object {
                    $filename = Split-Path $_ -Leaf
                    $commitMsg += "- $filename`n"
                }

                $commitMsg += "`nValidated with inspect_wiaa_fixture.py and pytest.`n"
                $commitMsg += "Manifest updated to mark as 'present'."

                # Commit
                git commit -m $commitMsg

                if ($LASTEXITCODE -eq 0) {
                    Write-Success "✅ Changes committed"

                    # Prompt to push
                    Write-Host ""
                    $push = Read-Host "Push to remote? (y/N)"
                    if ($push -eq "y" -or $push -eq "Y") {
                        $branch = git branch --show-current
                        git push origin $branch

                        if ($LASTEXITCODE -eq 0) {
                            Write-Success "✅ Pushed to origin/$branch"
                        } else {
                            Write-Error2 "❌ Push failed"
                        }
                    }
                } else {
                    Write-Error2 "❌ Commit failed"
                }
            } else {
                Write-Host ""
                Write-Info "💡 Next steps:"
                Write-Host "   1. Review changes: git diff tests/fixtures/wiaa/"
                Write-Host "   2. Stage changes: git add tests/fixtures/wiaa/"
                Write-Host "   3. Commit: git commit -m 'Add Wisconsin WIAA fixtures'"
                Write-Host "   4. Push: git push"
                Write-Host ""
                Write-Host "   Or re-run with -Commit flag to auto-commit"
            }
        } else {
            Write-Info "ℹ️  No changes to commit"
        }
    }
} else {
    Write-Error2 "❌ Batch processing completed with failures"
    Write-Host ""
    Write-Info "💡 Common issues:"
    Write-Host "   - Fixture files not downloaded yet (needs_download)"
    Write-Host "   - Fixture HTML is malformed or incomplete (inspection_failed)"
    Write-Host "   - Parser needs updates for changed WIAA markup (tests_failed)"
    exit 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
