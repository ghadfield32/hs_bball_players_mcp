#!/bin/bash
# Compare Coverage - Before/After Analysis
#
# Diffs two state gap CSVs to show improvement from changes.
#
# Usage:
#   bash scripts/helpers/compare_coverage.sh
#
# Or with custom files:
#   bash scripts/helpers/compare_coverage.sh baseline.csv after_recruiting.csv
#
# Author: Claude Code
# Date: 2025-11-16

set -e  # Exit on error

# Default files
BASELINE="${1:-data/state_gaps_baseline.csv}"
AFTER="${2:-data/state_gaps_after_recruiting.csv}"

echo "📊 Comparing Coverage: Before vs After"
echo "======================================"
echo
echo "Baseline: $BASELINE"
echo "After:    $AFTER"
echo

# Check if files exist
if [ ! -f "$BASELINE" ]; then
    echo "❌ Baseline file not found: $BASELINE"
    echo "   Run baseline measurement first:"
    echo "   bash scripts/helpers/run_coverage_baseline.sh"
    exit 1
fi

if [ ! -f "$AFTER" ]; then
    echo "❌ After file not found: $AFTER"
    echo "   Run coverage measurement after your changes:"
    echo "   python scripts/dashboard_coverage.py --cohort YOUR_COHORT.csv --export $AFTER"
    exit 1
fi

echo "🔍 CHANGES DETECTED:"
echo

# Show diff (filter out header line, focus on actual changes)
if diff "$BASELINE" "$AFTER" > /dev/null 2>&1; then
    echo "⚠️  No changes detected - files are identical"
    echo
    echo "This could mean:"
    echo "  1. You haven't made any changes yet (e.g., recruiting CSV not activated)"
    echo "  2. The changes didn't impact coverage metrics"
    echo "  3. Using the same export file for both baseline and after"
else
    echo "📈 Coverage metrics changed! Here's the diff:"
    echo
    diff -u "$BASELINE" "$AFTER" || true
    echo
fi

echo
echo "💡 TIP: For cleaner comparison, use a CSV diff tool or spreadsheet:"
echo "   - Open both files in Excel/Sheets side-by-side"
echo "   - Sort by 'priority_score' (descending)"
echo "   - Compare avg_coverage column"
echo
echo "📊 QUICK PYTHON COMPARISON:"
echo "   python -c \""
echo "import csv"
echo ""
echo "# Load both CSVs"
echo "with open('$BASELINE') as f:"
echo "    baseline = {r['state']: float(r['avg_coverage']) for r in csv.DictReader(f)}"
echo "with open('$AFTER') as f:"
echo "    after = {r['state']: float(r['avg_coverage']) for r in csv.DictReader(f)}"
echo ""
echo "# Show improvements"
echo "print('STATE IMPROVEMENTS:')"
echo "print('-' * 40)"
echo "for state in sorted(baseline.keys()):"
echo "    before = baseline.get(state, 0)"
echo "    after_val = after.get(state, 0)"
echo "    delta = after_val - before"
echo "    if delta != 0:"
echo "        print(f'{state}: {before:.1f}% → {after_val:.1f}% ({delta:+.1f}%)')"
echo "\""
echo
