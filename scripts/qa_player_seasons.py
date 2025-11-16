#!/usr/bin/env python3
"""
QA Validation for HS Player-Season Data

Runs comprehensive quality checks on the hs_player_seasons DuckDB table.
Validates schema compliance, data sanity, and coverage metrics.

Usage:
    python scripts/qa_player_seasons.py
    python scripts/qa_player_seasons.py --db data/hs_player_seasons.duckdb
    python scripts/qa_player_seasons.py --source eybl  # QA specific source
    python scripts/qa_player_seasons.py --export-report qa_report.md

Author: Phase 16 - First HS Player-Season Exports
Date: 2025-11-16
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

import duckdb


# ==============================================================================
# VALIDATION RULES (from hs_player_season_schema.yaml)
# ==============================================================================

VALIDATION_CHECKS = [
    {
        "name": "shooting_sanity",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE field_goals_made > field_goals_attempted
        """,
        "severity": "ERROR",
        "description": "FGM should never exceed FGA"
    },
    {
        "name": "three_point_sanity",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE three_pointers_made > three_pointers_attempted
        """,
        "severity": "ERROR",
        "description": "3PM should never exceed 3PA"
    },
    {
        "name": "free_throw_sanity",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE free_throws_made > free_throws_attempted
        """,
        "severity": "ERROR",
        "description": "FTM should never exceed FTA"
    },
    {
        "name": "three_pointers_subset",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE three_pointers_made > field_goals_made
              AND field_goals_made IS NOT NULL
              AND three_pointers_made IS NOT NULL
        """,
        "severity": "WARNING",
        "description": "3PM should be subset of FGM"
    },
    {
        "name": "games_started_sanity",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE games_started > games_played
        """,
        "severity": "ERROR",
        "description": "GS should never exceed GP"
    },
    {
        "name": "negative_stats",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE games_played < 0
               OR points < 0
               OR assists < 0
               OR total_rebounds < 0
        """,
        "severity": "ERROR",
        "description": "Stats should never be negative"
    },
    {
        "name": "reasonable_ppg",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE points_per_game > 100 OR points_per_game < 0
        """,
        "severity": "WARNING",
        "description": "PPG should be 0-100 (outliers flagged)"
    },
    {
        "name": "percentage_bounds",
        "query": """
            SELECT COUNT(*) as violations
            FROM hs_player_seasons
            WHERE (field_goal_percentage < 0 OR field_goal_percentage > 1)
               OR (three_point_percentage < 0 OR three_point_percentage > 1)
               OR (free_throw_percentage < 0 OR free_throw_percentage > 1)
        """,
        "severity": "ERROR",
        "description": "Shooting percentages should be 0-1"
    },
]


# ==============================================================================
# QA FUNCTIONS
# ==============================================================================

def run_validation_checks(con: duckdb.DuckDBPyConnection, source_filter: str = None) -> List[Dict]:
    """
    Run validation checks from schema.

    Args:
        con: DuckDB connection
        source_filter: Optional source to filter (e.g., "eybl")

    Returns:
        List of check results
    """
    print(f"\n{'='*80}")
    print(f"Running Validation Checks")
    if source_filter:
        print(f"Source: {source_filter}")
    print(f"{'='*80}\n")

    results = []

    for check in VALIDATION_CHECKS:
        query = check["query"]

        # Add source filter if specified
        if source_filter:
            if "WHERE" in query:
                query = query.replace("WHERE", f"WHERE source = '{source_filter}' AND")
            else:
                query = query.replace("FROM hs_player_seasons", f"FROM hs_player_seasons WHERE source = '{source_filter}'")

        try:
            result = con.execute(query).fetchone()
            violations = result[0] if result else 0

            status = "✅ PASS" if violations == 0 else f"❌ FAIL ({violations} violations)"
            severity_icon = "🔴" if check["severity"] == "ERROR" else "⚠️ "

            print(f"{severity_icon} {check['name']:<25} {status:>20}")
            print(f"   {check['description']}")

            results.append({
                "check": check["name"],
                "severity": check["severity"],
                "violations": violations,
                "description": check["description"],
                "passed": violations == 0
            })

        except Exception as e:
            print(f"❌ {check['name']:<25} ERROR: {e}")
            results.append({
                "check": check["name"],
                "severity": "ERROR",
                "violations": -1,
                "description": f"Check failed: {e}",
                "passed": False
            })

    # Summary
    errors = sum(1 for r in results if r["severity"] == "ERROR" and not r["passed"])
    warnings = sum(1 for r in results if r["severity"] == "WARNING" and not r["passed"])

    print(f"\n{'='*80}")
    print(f"Validation Summary")
    print(f"{'='*80}")
    print(f"Total checks: {len(results)}")
    print(f"Passed: {sum(1 for r in results if r['passed'])}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    print(f"{'='*80}\n")

    return results


def get_coverage_metrics(con: duckdb.DuckDBPyConnection) -> Dict:
    """Get coverage metrics for the dataset."""
    print(f"\n{'='*80}")
    print(f"Coverage Metrics")
    print(f"{'='*80}\n")

    metrics = {}

    # Total records
    total = con.execute("SELECT COUNT(*) FROM hs_player_seasons").fetchone()[0]
    metrics["total_records"] = total
    print(f"📊 Total player-seasons: {total:,}")

    # By source
    print(f"\n📍 Coverage by source:")
    by_source = con.execute("""
        SELECT source,
               COUNT(*) as records,
               COUNT(DISTINCT season) as seasons,
               AVG(games_played) as avg_games,
               AVG(points_per_game) as avg_ppg
        FROM hs_player_seasons
        GROUP BY source
        ORDER BY records DESC
    """).fetchall()

    metrics["by_source"] = []
    for source, records, seasons, avg_games, avg_ppg in by_source:
        print(f"  - {source:15} {records:>6,} records | {seasons} seasons | {avg_games:.1f} avg games | {avg_ppg:.1f} PPG")
        metrics["by_source"].append({
            "source": source,
            "records": records,
            "seasons": seasons,
            "avg_games": avg_games,
            "avg_ppg": avg_ppg
        })

    # By season
    print(f"\n📅 Coverage by season:")
    by_season = con.execute("""
        SELECT season, COUNT(*) as records
        FROM hs_player_seasons
        GROUP BY season
        ORDER BY season DESC
    """).fetchall()

    metrics["by_season"] = []
    for season, records in by_season:
        print(f"  - {season}: {records:,} records")
        metrics["by_season"].append({"season": season, "records": records})

    # By state (top 15)
    print(f"\n🗺️  Top 15 states by coverage:")
    by_state = con.execute("""
        SELECT state_code, COUNT(*) as records
        FROM hs_player_seasons
        WHERE state_code IS NOT NULL
        GROUP BY state_code
        ORDER BY records DESC
        LIMIT 15
    """).fetchall()

    metrics["by_state"] = []
    for state, records in by_state:
        print(f"  - {state}: {records:,} records")
        metrics["by_state"].append({"state": state, "records": records})

    # Data completeness
    print(f"\n📈 Data completeness:")
    completeness = con.execute("""
        SELECT
            COUNT(CASE WHEN field_goals_made IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_fgm,
            COUNT(CASE WHEN three_pointers_made IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_3pm,
            COUNT(CASE WHEN assists IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_ast,
            COUNT(CASE WHEN total_rebounds IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_reb
        FROM hs_player_seasons
    """).fetchone()

    metrics["completeness"] = {
        "fgm": completeness[0],
        "3pm": completeness[1],
        "ast": completeness[2],
        "reb": completeness[3]
    }

    print(f"  - FGM/FGA populated: {completeness[0]:.1f}%")
    print(f"  - 3PM/3PA populated: {completeness[1]:.1f}%")
    print(f"  - Assists populated: {completeness[2]:.1f}%")
    print(f"  - Rebounds populated: {completeness[3]:.1f}%")

    # Statistical summary
    print(f"\n📊 Statistical summary (averages):")
    summary = con.execute("""
        SELECT
            AVG(points_per_game) as avg_ppg,
            AVG(rebounds_per_game) as avg_rpg,
            AVG(assists_per_game) as avg_apg,
            AVG(field_goal_percentage) as avg_fg_pct,
            AVG(three_point_percentage) as avg_3p_pct
        FROM hs_player_seasons
    """).fetchone()

    metrics["averages"] = {
        "ppg": summary[0],
        "rpg": summary[1],
        "apg": summary[2],
        "fg_pct": summary[3],
        "3p_pct": summary[4]
    }

    print(f"  - PPG: {summary[0]:.2f}")
    print(f"  - RPG: {summary[1]:.2f}")
    print(f"  - APG: {summary[2]:.2f}")
    print(f"  - FG%: {summary[3]*100:.1f}%")
    print(f"  - 3P%: {summary[4]*100:.1f}%")

    print(f"\n{'='*80}\n")

    return metrics


def export_qa_report(results: List[Dict], metrics: Dict, output_file: Path) -> None:
    """Export QA report to markdown."""
    print(f"📝 Exporting QA report to {output_file}...")

    with open(output_file, 'w') as f:
        f.write("# HS Player-Season Data Quality Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Validation results
        f.write("## Validation Checks\n\n")
        errors = [r for r in results if r["severity"] == "ERROR" and not r["passed"]]
        warnings = [r for r in results if r["severity"] == "WARNING" and not r["passed"]]

        f.write(f"- **Total checks**: {len(results)}\n")
        f.write(f"- **Passed**: {sum(1 for r in results if r['passed'])}\n")
        f.write(f"- **Errors**: {len(errors)}\n")
        f.write(f"- **Warnings**: {len(warnings)}\n\n")

        if errors:
            f.write("### ❌ Errors\n\n")
            for r in errors:
                f.write(f"- **{r['check']}**: {r['violations']} violations\n")
                f.write(f"  - {r['description']}\n")

        if warnings:
            f.write("\n### ⚠️ Warnings\n\n")
            for r in warnings:
                f.write(f"- **{r['check']}**: {r['violations']} violations\n")
                f.write(f"  - {r['description']}\n")

        # Coverage metrics
        f.write("\n---\n\n")
        f.write("## Coverage Metrics\n\n")
        f.write(f"**Total records**: {metrics['total_records']:,}\n\n")

        f.write("### By Source\n\n")
        f.write("| Source | Records | Seasons | Avg Games | Avg PPG |\n")
        f.write("|--------|---------|---------|-----------|----------|\n")
        for s in metrics["by_source"]:
            f.write(f"| {s['source']} | {s['records']:,} | {s['seasons']} | {s['avg_games']:.1f} | {s['avg_ppg']:.1f} |\n")

        f.write("\n### By Season\n\n")
        f.write("| Season | Records |\n")
        f.write("|--------|----------|\n")
        for s in metrics["by_season"]:
            f.write(f"| {s['season']} | {s['records']:,} |\n")

        f.write("\n### Top States\n\n")
        f.write("| State | Records |\n")
        f.write("|-------|----------|\n")
        for s in metrics["by_state"][:10]:
            f.write(f"| {s['state']} | {s['records']:,} |\n")

        f.write("\n---\n\n")
        f.write("## Data Quality Metrics\n\n")

        f.write("### Completeness\n\n")
        c = metrics["completeness"]
        f.write(f"- FGM/FGA: {c['fgm']:.1f}%\n")
        f.write(f"- 3PM/3PA: {c['3pm']:.1f}%\n")
        f.write(f"- Assists: {c['ast']:.1f}%\n")
        f.write(f"- Rebounds: {c['reb']:.1f}%\n\n")

        f.write("### Statistical Averages\n\n")
        a = metrics["averages"]
        f.write(f"- PPG: {a['ppg']:.2f}\n")
        f.write(f"- RPG: {a['rpg']:.2f}\n")
        f.write(f"- APG: {a['apg']:.2f}\n")
        f.write(f"- FG%: {a['fg_pct']*100:.1f}%\n")
        f.write(f"- 3P%: {a['3p_pct']*100:.1f}%\n")

    print(f"✅ Report exported to {output_file}")


# ==============================================================================
# CLI
# ==============================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run QA validation on HS player-season data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all QA checks
  python scripts/qa_player_seasons.py

  # QA specific source
  python scripts/qa_player_seasons.py --source eybl

  # Export report to markdown
  python scripts/qa_player_seasons.py --export-report qa_report.md

  # Custom database path
  python scripts/qa_player_seasons.py --db data/custom.duckdb
        """
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/hs_player_seasons.duckdb"),
        help="Path to DuckDB database (default: data/hs_player_seasons.duckdb)"
    )

    parser.add_argument(
        "--source",
        help="Filter QA to specific source (e.g., eybl, sblive)"
    )

    parser.add_argument(
        "--export-report",
        type=Path,
        help="Export QA report to markdown file"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if not args.db.exists():
        print(f"❌ Database not found: {args.db}")
        print(f"   Run load_to_duckdb.py first to create database")
        return

    # Connect to DuckDB
    print(f"🔧 Connecting to {args.db}...")
    con = duckdb.connect(str(args.db), read_only=True)

    try:
        # Run validation checks
        results = run_validation_checks(con, args.source)

        # Get coverage metrics
        metrics = get_coverage_metrics(con)

        # Export report if requested
        if args.export_report:
            export_qa_report(results, metrics, args.export_report)

        # Exit code based on errors
        errors = sum(1 for r in results if r["severity"] == "ERROR" and not r["passed"])
        if errors > 0:
            print(f"❌ QA FAILED: {errors} error(s) found")
            return 1
        else:
            print(f"✅ QA PASSED: All validation checks passed")
            return 0

    finally:
        con.close()


if __name__ == "__main__":
    exit(main())
