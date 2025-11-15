#!/bin/bash
# Activate Recruiting CSV - Helper for Step 2
#
# Copies example recruiting CSV to active location so CSVRecruitingDataSource
# starts loading it immediately.
#
# Usage:
#   bash scripts/helpers/activate_recruiting.sh
#
# Author: Claude Code
# Date: 2025-11-16

set -e  # Exit on error

echo "🔄 Activating recruiting CSV..."
echo

# Create directory
mkdir -p data/recruiting

# Copy example to active
if [ ! -f "data/recruiting/247_rankings_example.csv" ]; then
    echo "❌ Example CSV not found: data/recruiting/247_rankings_example.csv"
    echo "   Run from repository root"
    exit 1
fi

cp data/recruiting/247_rankings_example.csv data/recruiting/247_rankings.csv

echo "✅ Recruiting CSV activated: data/recruiting/247_rankings.csv"
echo "   Source: 26 example top recruits (2018-2026)"
echo
echo "📝 WHAT THIS DOES:"
echo "   - CSVRecruitingDataSource now loads these rankings automatically"
echo "   - Coverage measurement will include recruiting data for these players"
echo "   - Expected impact: +20-30% coverage for top recruits"
echo
echo "📊 NEXT STEPS:"
echo "   1. Re-run coverage dashboard to see improvement:"
echo "      python scripts/dashboard_coverage.py \\"
echo "        --cohort data/college_cohort_d1_2018_2020.csv \\"
echo "        --export data/state_gaps_after_recruiting.csv"
echo
echo "   2. Compare before/after:"
echo "      diff data/state_gaps_baseline.csv data/state_gaps_after_recruiting.csv"
echo
echo "💡 TO REPLACE WITH FULL DATA LATER:"
echo "   - Export full 247/ESPN/On3 rankings to CSV (same format)"
echo "   - Overwrite data/recruiting/247_rankings.csv"
echo "   - Re-run coverage dashboard"
echo
