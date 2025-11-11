# Auto-activation hook for PowerShell
# Add this to your PowerShell profile to enable auto-activation
#
# Installation:
# 1. Run: notepad $PROFILE
# 2. Add the following to the end:
#
# # Basketball Stats API Auto-Activation
# $basketball_repo = "C:\docker_projects\betts_basketball\hs_bball_players_mcp"
# if ((Get-Location).Path -eq $basketball_repo -and (Test-Path "$basketball_repo\.venv")) {
#     if ($null -eq $env:VIRTUAL_ENV) {
#         & "$basketball_repo\activate.ps1"
#     }
# }
#
# 3. Save and close
# 4. Run: . $PROFILE
# 5. Navigate to this directory - it will auto-activate!

Write-Host "⚠️  This file contains instructions for auto-activation setup" -ForegroundColor Yellow
Write-Host ""
Write-Host "To enable auto-activation:" -ForegroundColor Cyan
Write-Host "1. Run: notepad `$PROFILE" -ForegroundColor White
Write-Host "2. Add the code block from this file" -ForegroundColor White
Write-Host "3. Update the path to match your repository location" -ForegroundColor White
Write-Host "4. Save and restart PowerShell" -ForegroundColor White
Write-Host ""
Write-Host "Alternative: Run .\activate.ps1 manually each time" -ForegroundColor Yellow
