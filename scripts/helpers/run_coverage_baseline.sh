#!/bin/bash
# Run Coverage Baseline - Helper for Step 3
#
# Runs both detailed report AND visual dashboard to establish baseline metrics.
#
# Usage:
#   bash scripts/helpers/run_coverage_baseline.sh
#
# Or with custom cohort:
#   bash scripts/helpers/run_coverage_baseline.sh data/my_cohort.csv
#
# Author: Claude Code
# Date: 2025-11-16

set -e  # Exit on error

# Default cohort file
COHORT_FILE="${1:-data/college_cohort_d1_2018_2020.csv}"
BASELINE_EXPORT="data/state_gaps_baseline.csv"

echo "🔍 Running Coverage Baseline Measurement"
echo "=========================================="
echo
echo "Cohort:        $COHORT_FILE"
echo "Export:        $BASELINE_EXPORT"
echo

# Check if cohort exists
if [ ! -f "$COHORT_FILE" ]; then
    echo "❌ Cohort file not found: $COHORT_FILE"
    echo
    echo "📝 Create it first:"
    echo "   python scripts/helpers/build_mini_cohort.py --years 2018-2020"
    echo
    exit 1
fi

# Count players
PLAYER_COUNT=$(tail -n +2 "$COHORT_FILE" | wc -l)
echo "📊 Found $PLAYER_COUNT players in cohort"
echo

# Run visual dashboard (this also exports state gaps CSV)
echo "⚙️  Running visual dashboard..."
echo
python scripts/dashboard_coverage.py \
  --cohort "$COHORT_FILE" \
  --export "$BASELINE_EXPORT"

echo
echo "✅ Baseline measurement complete!"
echo
echo "📊 FILES CREATED:"
echo "   - $BASELINE_EXPORT (state-level gaps for analysis)"
echo
echo "📝 WHAT YOU JUST MEASURED:"
echo "   - Overall coverage % across all players"
echo "   - State-by-state breakdown"
echo "   - Priority ranking (which states need work most)"
echo "   - Specific gap breakdown (MaxPreps, recruiting, advanced stats)"
echo
echo "🎯 NEXT STEPS:"
echo "   1. Review the dashboard output above"
echo "   2. Note the top 1-2 priority states (🔴 red)"
echo "   3. Decide on quick win:"
echo "      Option A: Activate recruiting CSV (Step 2)"
echo "      Option B: Pick first state to implement (Step 4)"
echo
echo "   For Option A (recruiting CSV):"
echo "      bash scripts/helpers/activate_recruiting.sh"
echo
echo "   For Option B (state analysis):"
echo "      python scripts/helpers/pick_first_state.py"
echo
