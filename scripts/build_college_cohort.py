#!/usr/bin/env python3
"""
Build College-Outcome Cohort (Step 3 of 8-step coverage plan)

Loads D1 college basketball players (2014-2023) to create a target cohort
for measuring REAL coverage (not design-time estimates).

**Purpose**: Measure coverage on players who actually went to college
**Cohort**: D1 players who played 2014-2023 (10 seasons)
**Data Sources**:
  - CSV file with D1 rosters (data/college_cohort_d1_2014_2023.csv)
  - Future: Scrape from college team rosters
  - Future: Import from existing college/pro databases

**Output**: List of player records with college outcomes for coverage measurement

Usage:
    python scripts/build_college_cohort.py [--source csv|scrape] [--years 2014-2023]

Author: Claude Code
Date: 2025-11-15
Enhancement: 11 (Coverage Enhancements 3, 4, 8)
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_from_csv(csv_path: Path) -> List[Dict]:
    """
    Load college cohort from CSV file.

    Expected CSV format:
        player_name,hs_name,hs_state,grad_year,birth_date,college,college_years,drafted,nba_team

    Example:
        "Cooper Flagg","Montverde Academy","FL",2025,"2006-12-21","Duke","2025-2026",True,"TBD"

    Args:
        csv_path: Path to CSV file

    Returns:
        List of player dicts
    """
    if not csv_path.exists():
        logger.warning(f"CSV file not found: {csv_path}")
        logger.info("Creating sample CSV template at data/college_cohort_template.csv")

        # Create template
        template_path = Path("data/college_cohort_template.csv")
        template_path.parent.mkdir(parents=True, exist_ok=True)

        with open(template_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "player_name", "hs_name", "hs_state", "grad_year", "birth_date",
                "college", "college_years", "drafted", "nba_team"
            ])
            # Sample data
            writer.writerow([
                "Cooper Flagg", "Montverde Academy", "FL", "2025", "2006-12-21",
                "Duke", "2025-2026", "False", ""
            ])
            writer.writerow([
                "Cameron Boozer", "Christopher Columbus", "FL", "2025", "2007-05-13",
                "Duke", "2025-2026", "False", ""
            ])
            writer.writerow([
                "AJ Dybantsa", "Utah Prep", "UT", "2026", "2007-10-20",
                "BYU", "2026-2027", "False", ""
            ])

        logger.info(f"Created template at: {template_path}")
        logger.info("Please populate with D1 players (2014-2023) and re-run")
        return []

    players = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            players.append({
                "player_name": row["player_name"],
                "hs_name": row.get("hs_name", ""),
                "hs_state": row.get("hs_state", ""),
                "grad_year": int(row["grad_year"]) if row.get("grad_year") else None,
                "birth_date": row.get("birth_date"),
                "college": row["college"],
                "college_years": row.get("college_years", ""),
                "drafted": row.get("drafted", "").lower() == "true",
                "nba_team": row.get("nba_team", ""),
            })

    logger.info(f"Loaded {len(players)} players from CSV: {csv_path}")
    return players


async def scrape_from_college_rosters(
    min_year: int = 2014,
    max_year: int = 2023
) -> List[Dict]:
    """
    Scrape D1 college rosters for the specified years.

    **STUB**: Not yet implemented. Requires:
    - NCAA or college athletics website scraping
    - Per-school roster pages
    - Identity matching (college name -> high school name)

    Args:
        min_year: Start year (e.g., 2014)
        max_year: End year (e.g., 2023)

    Returns:
        List of player dicts

    Raises:
        NotImplementedError: Stub not yet implemented
    """
    raise NotImplementedError(
        "College roster scraping not yet implemented. "
        "Use CSV source (--source csv) with data/college_cohort_d1_2014_2023.csv"
    )


def filter_by_years(
    players: List[Dict],
    min_year: int = 2014,
    max_year: int = 2023
) -> List[Dict]:
    """
    Filter players by graduation year range.

    Args:
        players: List of player dicts
        min_year: Minimum grad year (inclusive)
        max_year: Maximum grad year (inclusive)

    Returns:
        Filtered list
    """
    filtered = [
        p for p in players
        if p.get("grad_year") and min_year <= p["grad_year"] <= max_year
    ]

    logger.info(
        f"Filtered {len(players)} players to {len(filtered)} "
        f"(grad years {min_year}-{max_year})"
    )

    return filtered


def analyze_cohort(players: List[Dict]) -> Dict:
    """
    Analyze the college cohort and print statistics.

    Args:
        players: List of player dicts

    Returns:
        Summary stats dict
    """
    if not players:
        return {
            "total_players": 0,
            "by_grad_year": {},
            "by_college": {},
            "drafted_count": 0,
        }

    # Count by grad year
    by_year = {}
    for p in players:
        year = p.get("grad_year")
        if year:
            by_year[year] = by_year.get(year, 0) + 1

    # Count by college
    by_college = {}
    for p in players:
        college = p.get("college", "Unknown")
        by_college[college] = by_college.get(college, 0) + 1

    # Count drafted
    drafted_count = sum(1 for p in players if p.get("drafted"))

    stats = {
        "total_players": len(players),
        "by_grad_year": by_year,
        "by_college": by_college,
        "drafted_count": drafted_count,
        "draft_rate": drafted_count / len(players) * 100 if players else 0,
    }

    # Print summary
    print(f"\n{'='*80}")
    print(f"COLLEGE COHORT ANALYSIS")
    print(f"{'='*80}")
    print(f"Total Players: {stats['total_players']}")
    print(f"Drafted to NBA: {drafted_count} ({stats['draft_rate']:.1f}%)")
    print(f"\nBy Graduation Year:")
    for year in sorted(stats['by_grad_year'].keys()):
        count = stats['by_grad_year'][year]
        print(f"  {year}: {count} players")

    print(f"\nTop 10 Colleges:")
    top_colleges = sorted(
        stats['by_college'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for college, count in top_colleges:
        print(f"  {college}: {count} players")

    print(f"{'='*80}\n")

    return stats


def save_cohort(players: List[Dict], output_path: Path) -> None:
    """
    Save cohort to CSV for use by report_coverage.py.

    Args:
        players: List of player dicts
        output_path: Path to output CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        if not players:
            logger.warning("No players to save")
            return

        writer = csv.DictWriter(f, fieldnames=players[0].keys())
        writer.writeheader()
        writer.writerows(players)

    logger.info(f"Saved {len(players)} players to: {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build college-outcome cohort for coverage measurement"
    )
    parser.add_argument(
        "--source",
        choices=["csv", "scrape"],
        default="csv",
        help="Data source (csv or scrape)"
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="data/college_cohort_d1_2014_2023.csv",
        help="Path to input CSV file"
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2014,
        help="Minimum graduation year (inclusive)"
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=2023,
        help="Maximum graduation year (inclusive)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/college_cohort_filtered.csv",
        help="Path to output CSV file"
    )

    args = parser.parse_args()

    logger.info(f"Building college cohort from source: {args.source}")

    # Load players
    if args.source == "csv":
        players = load_from_csv(Path(args.csv_path))
    elif args.source == "scrape":
        players = await scrape_from_college_rosters(
            min_year=args.min_year,
            max_year=args.max_year
        )
    else:
        raise ValueError(f"Unknown source: {args.source}")

    if not players:
        logger.warning("No players loaded. Exiting.")
        return

    # Filter by years
    players = filter_by_years(players, args.min_year, args.max_year)

    # Analyze cohort
    stats = analyze_cohort(players)

    # Save filtered cohort
    save_cohort(players, Path(args.output))

    logger.info(f"✅ College cohort built successfully!")
    logger.info(f"   Total players: {stats['total_players']}")
    logger.info(f"   Output saved to: {args.output}")
    logger.info(f"\nNext step: Run coverage measurement on this cohort:")
    logger.info(f"   python scripts/report_coverage.py --cohort {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
