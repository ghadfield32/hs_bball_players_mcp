#!/usr/bin/env python
"""
Wisconsin WIAA Fixture Sanity Check Script

This script validates Wisconsin WIAA bracket HTML fixtures BEFORE they are marked as "present"
in the manifest. It helps catch parsing issues, data quality problems, and schema changes early.

Usage:
    # Check all "planned" fixtures from manifest
    python scripts/inspect_wiaa_fixture.py

    # Check specific fixture combinations
    python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2

    # Check multiple specific fixtures
    python scripts/inspect_wiaa_fixture.py --combos "2024,Boys,Div2" "2024,Girls,Div3"

What it checks:
    - Fixture file exists and is readable
    - Parses without errors
    - Produces > 0 games
    - No self-games (team vs itself)
    - Scores in valid range (0-200)
    - Expected rounds are present (Regional, Sectional, State)
    - Round name distribution looks reasonable
    - Sample of team names and scores

When to use:
    1. After downloading new fixture HTML files
    2. Before updating manifest status from "planned" to "present"
    3. To debug parser issues
    4. To verify fixture file quality

Example workflow:
    1. Download 2024_Basketball_Boys_Div2.html from WIAA site
    2. Save to tests/fixtures/wiaa/
    3. Run: python scripts/inspect_wiaa_fixture.py --year 2024 --gender Boys --division Div2
    4. If passes: Update manifest status to "present"
    5. If fails: Fix parser or fixture, repeat step 3
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource, DataMode
from src.models import Game


FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"


def load_manifest() -> dict:
    """Load the Wisconsin WIAA fixture manifest."""
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_planned_fixtures() -> List[Tuple[int, str, str]]:
    """Get all fixtures marked as 'planned' in manifest."""
    manifest = load_manifest()
    return [
        (entry["year"], entry["gender"], entry["division"])
        for entry in manifest["fixtures"]
        if entry.get("status") == "planned"
    ]


async def inspect_fixture(
    year: int,
    gender: str,
    division: str,
    verbose: bool = True
) -> bool:
    """
    Inspect a single Wisconsin WIAA fixture.

    Returns:
        True if fixture passes all sanity checks, False otherwise
    """
    fixture_path = FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"

    if verbose:
        print(f"\n{'='*80}")
        print(f"Inspecting: {year} {gender} {division}")
        print(f"File: {fixture_path}")
        print(f"{'='*80}")

    # Check 1: File exists
    if not fixture_path.exists():
        print(f"❌ FAIL: Fixture file does not exist")
        print(f"   Expected: {fixture_path}")
        return False

    if verbose:
        file_size = fixture_path.stat().st_size
        print(f"✅ File exists ({file_size:,} bytes)")

    # Check 2: Parse without errors
    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=year,
            gender=gender,
            division=division
        )
    except Exception as e:
        print(f"❌ FAIL: Parser error")
        print(f"   Error: {type(e).__name__}: {e}")
        await source.close()
        return False
    finally:
        await source.close()

    # Check 3: Produced games
    if len(games) == 0:
        print(f"❌ FAIL: Parsed 0 games")
        return False

    if verbose:
        print(f"✅ Parsed {len(games)} games")

    # Check 4: No self-games
    self_games = [g for g in games if g.home_team_name == g.away_team_name]
    if self_games:
        print(f"❌ FAIL: Found {len(self_games)} self-games (team vs itself)")
        for sg in self_games[:3]:
            print(f"   - {sg.home_team_name} vs {sg.away_team_name}")
        return False

    if verbose:
        print(f"✅ No self-games")

    # Check 5: Valid scores
    invalid_scores = []
    for game in games:
        if not (0 <= game.home_score <= 200 and 0 <= game.away_score <= 200):
            invalid_scores.append((game.home_team_name, game.home_score, game.away_score))

    if invalid_scores:
        print(f"❌ FAIL: Found {len(invalid_scores)} games with invalid scores")
        for team, home, away in invalid_scores[:3]:
            print(f"   - {team}: {home}-{away}")
        return False

    if verbose:
        score_min = min(min(g.home_score, g.away_score) for g in games)
        score_max = max(max(g.home_score, g.away_score) for g in games)
        print(f"✅ All scores valid (range: {score_min}-{score_max})")

    # Check 6: Expected rounds present
    round_names = {g.round for g in games}
    expected_round_keywords = ["Regional", "Sectional", "State"]
    missing_rounds = []

    for keyword in expected_round_keywords:
        if not any(keyword in r for r in round_names):
            missing_rounds.append(keyword)

    if missing_rounds:
        print(f"⚠️  WARNING: Missing expected round tiers: {', '.join(missing_rounds)}")
        print(f"   Found rounds: {sorted(round_names)}")
        # This is a warning, not a failure - some divisions might not have all tiers

    if verbose:
        from collections import Counter
        round_counts = Counter(g.round for g in games)
        print(f"\n📊 Round Distribution:")
        for round_name, count in sorted(round_counts.items(), key=lambda x: -x[1]):
            print(f"   {round_name}: {count} games")

    # Check 7: Unknown rounds < 20%
    unknown_count = sum(1 for g in games if "Unknown" in g.round)
    unknown_pct = (unknown_count / len(games) * 100) if games else 0

    if unknown_pct >= 20:
        print(f"⚠️  WARNING: High percentage of unknown rounds ({unknown_pct:.1f}%)")
        print(f"   This may indicate parser issues or schema changes")

    # Check 8: Sample teams and scores
    if verbose:
        teams = sorted({g.home_team_name for g in games} | {g.away_team_name for g in games})
        print(f"\n📋 Found {len(teams)} unique teams")
        print(f"   Sample teams: {', '.join(teams[:5])}")

        print(f"\n🏀 Sample games:")
        for game in games[:3]:
            print(f"   {game.round}: {game.away_team_name} @ {game.home_team_name} "
                  f"({game.away_score}-{game.home_score})")

    # Check 9: Championship game exists
    has_championship = any("Championship" in g.round for g in games)
    if not has_championship:
        print(f"⚠️  WARNING: No championship game found")
        print(f"   Fixture may be incomplete or from early season")

    print(f"\n✅ PASS: Fixture passed all critical checks")
    return True


async def inspect_all(fixtures: List[Tuple[int, str, str]], verbose: bool = True):
    """Inspect multiple fixtures and report summary."""
    results = []

    for year, gender, division in fixtures:
        passed = await inspect_fixture(year, gender, division, verbose=verbose)
        results.append(((year, gender, division), passed))

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")

    passed_count = sum(1 for _, passed in results if passed)
    failed_count = len(results) - passed_count

    print(f"\nTotal fixtures checked: {len(results)}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")

    if failed_count > 0:
        print(f"\nFailed fixtures:")
        for (year, gender, division), passed in results:
            if not passed:
                print(f"   - {year} {gender} {division}")
        print(f"\nRecommendation: Fix parser or fixture files before marking as 'present'")
        return False
    else:
        print(f"\n✅ All fixtures passed!")
        print(f"\nRecommendation: Update manifest status to 'present' for these fixtures")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Sanity check Wisconsin WIAA fixture files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--all-planned",
        action="store_true",
        help="Check all fixtures marked as 'planned' in manifest (default)"
    )

    group.add_argument(
        "--year",
        type=int,
        help="Check specific year (use with --gender and --division)"
    )

    parser.add_argument(
        "--gender",
        choices=["Boys", "Girls"],
        help="Gender for specific check"
    )

    parser.add_argument(
        "--division",
        choices=["Div1", "Div2", "Div3", "Div4", "Div5"],
        help="Division for specific check"
    )

    parser.add_argument(
        "--combos",
        nargs="+",
        help='Check specific combos: "2024,Boys,Div2" "2024,Girls,Div3"'
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    # Determine which fixtures to check
    if args.combos:
        # Parse combo strings
        fixtures = []
        for combo in args.combos:
            parts = combo.split(",")
            if len(parts) != 3:
                print(f"❌ Invalid combo format: {combo}")
                print(f"   Expected: year,gender,division (e.g., '2024,Boys,Div2')")
                sys.exit(1)
            try:
                year = int(parts[0])
                gender = parts[1]
                division = parts[2]
                fixtures.append((year, gender, division))
            except ValueError as e:
                print(f"❌ Error parsing combo: {combo}: {e}")
                sys.exit(1)

    elif args.year and args.gender and args.division:
        # Single specific fixture
        fixtures = [(args.year, args.gender, args.division)]

    elif args.year or args.gender or args.division:
        # Incomplete specification
        print("❌ Must specify all of --year, --gender, and --division together")
        sys.exit(1)

    else:
        # Default: all planned fixtures
        fixtures = get_planned_fixtures()
        if not fixtures:
            print("No 'planned' fixtures found in manifest")
            print(f"Manifest: {MANIFEST_PATH}")
            sys.exit(0)

        print(f"Found {len(fixtures)} planned fixtures in manifest:")
        for year, gender, division in fixtures:
            print(f"  - {year} {gender} {division}")

    # Run inspection
    verbose = not args.quiet
    success = asyncio.run(inspect_all(fixtures, verbose=verbose))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
