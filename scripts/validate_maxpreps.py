"""
MaxPreps Validation Script

**PURPOSE**: Validate MaxPreps adapter and document available metrics.

**LEGAL WARNING**: This script makes real network requests to MaxPreps.
Only run with explicit permission or for educational/research purposes.

**USAGE**:
    python scripts/validate_maxpreps.py [--state STATE] [--limit N]

**OUTPUT**:
    - Console output showing available metrics
    - HTML snapshot saved to data/validation/maxpreps_sample.html
    - Metrics report saved to data/validation/maxpreps_metrics.json

Author: Claude Code
Date: 2025-11-14
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.maxpreps import MaxPrepsDataSource
from src.models import Player
from src.utils import extract_table_data, parse_html


async def validate_maxpreps_adapter(
    state: str = "CA",
    limit: int = 5,
    save_html: bool = True
) -> Dict:
    """
    Validate MaxPreps adapter and document available metrics.

    Args:
        state: State to test (default: CA for most data)
        limit: Number of players to fetch
        save_html: Save HTML snapshot for analysis

    Returns:
        Dictionary with validation results
    """
    results = {
        "state": state,
        "test_date": "2025-11-14",
        "status": "pending",
        "errors": [],
        "warnings": [],
        "available_metrics": [],
        "sample_data": [],
        "html_columns": [],
        "recommendations": []
    }

    print(f"\n{'='*70}")
    print(f"MaxPreps Validation Script")
    print(f"{'='*70}")
    print(f"\n⚠️  LEGAL WARNING:")
    print(f"   This script makes real network requests to MaxPreps.")
    print(f"   MaxPreps ToS prohibits scraping.")
    print(f"   Only proceed if you have explicit permission.")
    print(f"\n{'='*70}\n")

    try:
        # Initialize MaxPreps adapter
        print(f"[1/6] Initializing MaxPreps adapter...")
        async with MaxPrepsDataSource() as maxpreps:
            print(f"      ✓ Adapter initialized successfully")
            print(f"      - Base URL: {maxpreps.base_url}")
            print(f"      - States supported: {len(maxpreps.ALL_US_STATES)}")
            print(f"      - Browser automation: Enabled")

            # Validate state
            print(f"\n[2/6] Validating state parameter...")
            try:
                validated_state = maxpreps._validate_state(state)
                print(f"      ✓ State '{state}' validated as '{validated_state}'")
                state_name = maxpreps.STATE_NAMES.get(validated_state, validated_state)
                print(f"      - Full name: {state_name}")
            except ValueError as e:
                results["errors"].append(f"State validation failed: {e}")
                print(f"      ✗ State validation failed: {e}")
                return results

            # Build stats URL
            print(f"\n[3/6] Building stats URL...")
            stats_url = maxpreps._get_state_url(validated_state, "stat-leaders")
            print(f"      ✓ Stats URL: {stats_url}")

            # Fetch and render HTML
            print(f"\n[4/6] Fetching HTML (this may take 30-60 seconds)...")
            print(f"      - Using browser automation to render React content...")

            try:
                html = await maxpreps.browser_client.get_rendered_html(
                    url=stats_url,
                    wait_for="table",
                    wait_timeout=60000,  # 60 seconds
                    wait_for_network_idle=True,
                )
                print(f"      ✓ HTML fetched successfully ({len(html):,} bytes)")

                # Save HTML snapshot
                if save_html:
                    output_dir = Path("data/validation")
                    output_dir.mkdir(parents=True, exist_ok=True)

                    html_file = output_dir / f"maxpreps_{validated_state.lower()}_sample.html"
                    html_file.write_text(html, encoding="utf-8")
                    print(f"      ✓ HTML saved to: {html_file}")

            except Exception as e:
                results["errors"].append(f"HTML fetch failed: {e}")
                print(f"      ✗ Failed to fetch HTML: {e}")
                return results

            # Parse HTML and extract table
            print(f"\n[5/6] Parsing HTML and extracting stats table...")
            soup = parse_html(html)

            # Find all tables
            tables = soup.find_all("table")
            print(f"      - Found {len(tables)} table(s) on page")

            if not tables:
                results["errors"].append("No tables found on page")
                print(f"      ✗ No tables found")
                return results

            # Extract data from first table (assume stats table)
            stats_table = tables[0]
            rows = extract_table_data(stats_table)

            if not rows:
                results["errors"].append("Stats table found but no rows extracted")
                print(f"      ✗ No rows extracted from table")
                return results

            print(f"      ✓ Extracted {len(rows)} rows from stats table")

            # Analyze columns
            if rows:
                first_row = rows[0]
                columns = list(first_row.keys())
                results["html_columns"] = columns

                print(f"\n      📊 Available Columns ({len(columns)}):")
                for idx, col in enumerate(columns, 1):
                    print(f"         {idx:2}. {col}")

                # Check for common stat columns
                stat_columns = {
                    "PPG": ["PPG", "Points", "PTS", "Pts Per Game"],
                    "RPG": ["RPG", "Rebounds", "REB", "Rebs Per Game"],
                    "APG": ["APG", "Assists", "AST", "Asts Per Game"],
                    "SPG": ["SPG", "Steals", "STL"],
                    "BPG": ["BPG", "Blocks", "BLK"],
                    "FG%": ["FG%", "FG Pct", "Field Goal %"],
                    "3P%": ["3P%", "3PT%", "3-PT%", "Three Point %"],
                    "FT%": ["FT%", "FT Pct", "Free Throw %"],
                    "GP": ["GP", "Games", "Games Played"],
                }

                found_stats = []
                for stat_name, possible_cols in stat_columns.items():
                    for col in columns:
                        if any(pc.lower() == col.lower() for pc in possible_cols):
                            found_stats.append((stat_name, col))
                            break

                if found_stats:
                    print(f"\n      ✓ Found {len(found_stats)} stat column(s):")
                    for stat_name, col_name in found_stats:
                        print(f"         - {stat_name}: '{col_name}'")
                        results["available_metrics"].append({
                            "stat": stat_name,
                            "column": col_name
                        })
                else:
                    results["warnings"].append("No standard stat columns found")
                    print(f"      ⚠️  No standard stat columns found")

            # Search for players
            print(f"\n[6/6] Testing player search...")
            players = await maxpreps.search_players(
                state=validated_state,
                limit=limit
            )

            print(f"      ✓ Found {len(players)} player(s)")

            # Analyze sample players
            for idx, player in enumerate(players[:3], 1):
                print(f"\n      Player {idx}:")
                print(f"         Name: {player.full_name}")
                print(f"         School: {player.school_name or 'N/A'}")
                print(f"         Position: {player.position or 'N/A'}")
                print(f"         Grad Year: {player.grad_year or 'N/A'}")
                print(f"         Height: {player.height_feet_inches or 'N/A'}")
                print(f"         Weight: {player.weight_lbs or 'N/A'} lbs" if player.weight_lbs else "         Weight: N/A")

                # Store sample
                results["sample_data"].append({
                    "name": player.full_name,
                    "school": player.school_name,
                    "position": str(player.position) if player.position else None,
                    "grad_year": player.grad_year,
                    "height_inches": player.height_inches,
                    "weight_lbs": player.weight_lbs,
                })

            # Generate recommendations
            print(f"\n{'='*70}")
            print(f"RECOMMENDATIONS:")
            print(f"{'='*70}\n")

            if found_stats:
                print(f"✅ MaxPreps provides statistics - enhance parser to extract:")
                for stat_name, col_name in found_stats:
                    print(f"   - {stat_name} (column: '{col_name}')")
                    results["recommendations"].append(f"Extract {stat_name} from column '{col_name}'")
            else:
                print(f"⚠️  No statistics found - may need to:")
                print(f"   1. Check different URL endpoint (e.g., /stats vs /stat-leaders)")
                print(f"   2. Verify React content rendered correctly")
                print(f"   3. Try different state (some states may have more data)")
                results["recommendations"].append("Investigate different endpoints or states")

            print(f"\n✅ Validation complete!")
            results["status"] = "success"

    except Exception as e:
        results["status"] = "error"
        results["errors"].append(f"Validation failed: {e}")
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

    # Save results
    output_dir = Path("data/validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / f"maxpreps_{state.lower()}_metrics.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {results_file}")

    return results


async def compare_states(states: List[str] = ["CA", "TX", "NY"]):
    """
    Compare MaxPreps data across multiple states.

    Args:
        states: List of state codes to compare
    """
    print(f"\n{'='*70}")
    print(f"Multi-State Comparison")
    print(f"{'='*70}\n")

    all_results = {}

    for state in states:
        print(f"\n{'='*70}")
        print(f"Testing {state}...")
        print(f"{'='*70}")

        results = await validate_maxpreps_adapter(state=state, limit=3, save_html=True)
        all_results[state] = results

        # Brief summary
        print(f"\n{state} Summary:")
        print(f"  Status: {results['status']}")
        print(f"  Metrics: {len(results['available_metrics'])}")
        print(f"  Samples: {len(results['sample_data'])}")

    # Save comparison
    output_dir = Path("data/validation")
    comparison_file = output_dir / "maxpreps_multi_state_comparison.json"

    with open(comparison_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n📄 Comparison saved to: {comparison_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate MaxPreps adapter")
    parser.add_argument("--state", default="CA", help="State to test (default: CA)")
    parser.add_argument("--limit", type=int, default=5, help="Number of players to fetch")
    parser.add_argument("--compare", action="store_true", help="Compare multiple states")

    args = parser.parse_args()

    print(f"\n⚠️  LEGAL NOTICE:")
    print(f"   This script will make real network requests to MaxPreps.")
    print(f"   MaxPreps Terms of Service prohibit scraping.")
    print(f"   Only proceed if you have explicit permission.\n")

    response = input("Do you have permission to proceed? (yes/no): ")

    if response.lower() != "yes":
        print("\n✋ Validation cancelled. Obtain permission before proceeding.")
        sys.exit(0)

    if args.compare:
        asyncio.run(compare_states(["CA", "TX", "NY", "FL", "GA"]))
    else:
        asyncio.run(validate_maxpreps_adapter(state=args.state, limit=args.limit))
