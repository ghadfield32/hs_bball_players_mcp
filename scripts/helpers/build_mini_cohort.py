#!/usr/bin/env python3
"""
Quick Cohort CSV Builder - Helper for Step 1

Creates a starter cohort CSV from example data, ready for you to append
real players from your database.

Usage:
    python scripts/helpers/build_mini_cohort.py --years 2018-2020

This script:
1. Copies example CSV as template
2. Filters to specified years
3. Creates output file ready for your DB exports

Author: Claude Code
Date: 2025-11-16
"""

import argparse
import csv
from pathlib import Path


def build_mini_cohort(start_year: int, end_year: int, output_file: Path):
    """
    Build mini cohort CSV from example, filtered by years.

    Args:
        start_year: Start graduation year (e.g., 2018)
        end_year: End graduation year (e.g., 2020)
        output_file: Output CSV path
    """
    # Read example CSV
    example_path = Path("data/college_cohort_example.csv")

    if not example_path.exists():
        print(f"❌ Example CSV not found: {example_path}")
        print("   Run from repository root")
        return

    # Filter to specified years
    filtered_players = []
    with open(example_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            grad_year = int(row.get("grad_year", 0))
            if start_year <= grad_year <= end_year:
                filtered_players.append(row)

    # Write to output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if filtered_players:
            writer = csv.DictWriter(f, fieldnames=filtered_players[0].keys())
            writer.writeheader()
            writer.writerows(filtered_players)

    print(f"✅ Created cohort template: {output_file}")
    print(f"   Filtered to {start_year}-{end_year}: {len(filtered_players)} players")
    print()
    print("📝 NEXT STEPS:")
    print(f"   1. Open {output_file} in your editor")
    print("   2. Append real D1 players from your database:")
    print()
    print("      # Example DuckDB export (adjust to your schema)")
    print(f"      duckdb your_db.duckdb -c \"")
    print("      COPY (")
    print("        SELECT player_name, hs_name, hs_state, grad_year,")
    print("               birth_date, college, college_years, drafted, nba_team")
    print("        FROM cbb_players")
    print(f"        WHERE grad_year BETWEEN {start_year} AND {end_year}")
    print(f"      ) TO '{output_file}' (HEADER, DELIMITER ',', APPEND);")
    print("      \"")
    print()
    print("   3. Or manually append rows in this format:")
    print("      player_name,hs_name,hs_state,grad_year,birth_date,college,college_years,drafted,nba_team")
    print()
    print(f"   Goal: ~50-150 players across key states (FL, TX, CA, GA, NJ, NY, IL)")


def main():
    parser = argparse.ArgumentParser(
        description="Build mini cohort CSV for coverage testing"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2018-2020",
        help="Year range (e.g., '2018-2020')"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (auto-generated if not specified)"
    )

    args = parser.parse_args()

    # Parse years
    if "-" in args.years:
        start_year, end_year = map(int, args.years.split("-"))
    else:
        start_year = end_year = int(args.years)

    # Auto-generate output filename
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = Path(f"data/college_cohort_d1_{start_year}_{end_year}.csv")

    build_mini_cohort(start_year, end_year, output_file)


if __name__ == "__main__":
    main()
