#!/usr/bin/env python3
"""
Datasource Validation Script - Test All Data Sources

Validates that all datasources pull data correctly (current and historical).

Features:
- Tests each active datasource individually
- Validates current season data
- Tests historical data (multi-season)
- Reports success/failure for each source
- Generates validation summary report

Usage:
    # Test all datasources
    python scripts/validate_datasources.py

    # Test specific source
    python scripts/validate_datasources.py --source eybl

    # Test with detailed output
    python scripts/validate_datasources.py --verbose

    # Export results to CSV
    python scripts/validate_datasources.py --export data/validation_report.csv

Author: Claude Code
Date: 2025-11-15
Purpose: Data quality validation and historical retrieval testing
"""

import asyncio
import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services import DataSourceAggregator
from src.models import Player, PlayerSeasonStats


class ValidationResult:
    """Container for validation test results."""

    def __init__(self, source_name: str, source_type: str):
        self.source_name = source_name
        self.source_type = source_type
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.data_points = 0
        self.historical_seasons = 0
        self.timestamp = datetime.now().isoformat()

    @property
    def status(self) -> str:
        """Overall status of validation."""
        if self.tests_failed > 0:
            return "FAILED"
        elif self.warnings:
            return "WARNING"
        elif self.tests_passed > 0:
            return "PASSED"
        else:
            return "SKIPPED"

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = self.tests_passed + self.tests_failed
        return (self.tests_passed / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "status": self.status,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": f"{self.success_rate:.1f}%",
            "data_points": self.data_points,
            "historical_seasons": self.historical_seasons,
            "errors": " | ".join(self.errors) if self.errors else "",
            "warnings": " | ".join(self.warnings) if self.warnings else "",
            "timestamp": self.timestamp
        }


async def test_search_players(source: Any, source_name: str, result: ValidationResult, verbose: bool = False) -> bool:
    """
    Test search_players() method.

    Returns:
        True if test passed, False otherwise
    """
    try:
        if verbose:
            print(f"  [TEST] search_players(limit=5)...")

        players = await source.search_players(limit=5)

        if not players:
            result.warnings.append("search_players returned empty list")
            if verbose:
                print(f"    [!] Warning: No players found")
            return False

        result.data_points += len(players)

        if verbose:
            print(f"    [OK] Found {len(players)} players")
            for p in players[:3]:  # Show first 3
                print(f"         - {p.full_name} ({p.grad_year or 'N/A'})")

        return True

    except NotImplementedError:
        result.warnings.append("search_players not implemented")
        if verbose:
            print(f"    [-] Not implemented")
        return False
    except Exception as e:
        result.errors.append(f"search_players: {str(e)}")
        if verbose:
            print(f"    [X] Error: {e}")
        return False


async def test_get_player_stats(source: Any, source_name: str, result: ValidationResult, verbose: bool = False) -> bool:
    """
    Test get_player_season_stats() method.

    Returns:
        True if test passed, False otherwise
    """
    try:
        if verbose:
            print(f"  [TEST] get_player_season_stats...")

        # First get a player to test stats with
        players = await source.search_players(limit=1)
        if not players:
            result.warnings.append("Cannot test stats - no players found")
            return False

        player = players[0]
        stats = await source.get_player_season_stats(player.player_id, season="2024")

        if not stats:
            result.warnings.append("get_player_season_stats returned None")
            if verbose:
                print(f"    [!] Warning: No stats found for {player.full_name}")
            return False

        result.data_points += 1

        if verbose:
            print(f"    [OK] Stats for {player.full_name}: {stats.points_per_game or 'N/A'} PPG")

        return True

    except NotImplementedError:
        result.warnings.append("get_player_season_stats not implemented")
        if verbose:
            print(f"    [-] Not implemented")
        return False
    except Exception as e:
        result.errors.append(f"get_player_season_stats: {str(e)}")
        if verbose:
            print(f"    [X] Error: {e}")
        return False


async def test_historical_data(source: Any, source_name: str, result: ValidationResult, verbose: bool = False) -> bool:
    """
    Test historical data retrieval (multiple seasons).

    Returns:
        True if historical data available, False otherwise
    """
    try:
        if verbose:
            print(f"  [TEST] Historical data (2022-2024)...")

        players = await source.search_players(limit=1)
        if not players:
            return False

        player = players[0]
        seasons_found = 0

        for year in ["2022", "2023", "2024"]:
            try:
                stats = await source.get_player_season_stats(player.player_id, season=year)
                if stats:
                    seasons_found += 1
            except:
                pass

        result.historical_seasons = seasons_found

        if verbose:
            print(f"    [OK] Found {seasons_found}/3 historical seasons")

        return seasons_found > 0

    except NotImplementedError:
        if verbose:
            print(f"    [-] Not implemented")
        return False
    except Exception as e:
        result.errors.append(f"historical_data: {str(e)}")
        if verbose:
            print(f"    [X] Error: {e}")
        return False


async def validate_single_source(
    source_name: str,
    source: Any,
    source_type: str,
    verbose: bool = False
) -> ValidationResult:
    """
    Validate a single datasource.

    Args:
        source_name: Name of the datasource
        source: Datasource instance
        source_type: Type of datasource
        verbose: Print detailed output

    Returns:
        ValidationResult with test results
    """
    result = ValidationResult(source_name, source_type)

    if verbose:
        print(f"\n[TESTING] {source_name} ({source_type})")
        print(f"{'-'*60}")

    # Test 1: search_players
    if await test_search_players(source, source_name, result, verbose):
        result.tests_passed += 1
    else:
        result.tests_failed += 1

    # Test 2: get_player_season_stats
    if await test_get_player_stats(source, source_name, result, verbose):
        result.tests_passed += 1
    else:
        result.tests_failed += 1

    # Test 3: historical data
    if await test_historical_data(source, source_name, result, verbose):
        result.tests_passed += 1
    else:
        result.tests_failed += 1

    if verbose:
        print(f"\n[{result.status}] {source_name}: {result.tests_passed}/{result.tests_passed + result.tests_failed} tests passed")

    return result


async def validate_all_sources(
    aggregator: DataSourceAggregator,
    source_filter: Optional[str] = None,
    verbose: bool = False
) -> List[ValidationResult]:
    """
    Validate all datasources in the aggregator.

    Args:
        aggregator: DataSourceAggregator instance
        source_filter: Optional source name to test only one source
        verbose: Print detailed output

    Returns:
        List of ValidationResult objects
    """
    results = []

    sources_to_test = aggregator.sources
    if source_filter:
        if source_filter in sources_to_test:
            sources_to_test = {source_filter: sources_to_test[source_filter]}
        else:
            print(f"[X] Source '{source_filter}' not found!")
            return []

    total_sources = len(sources_to_test)
    print(f"\n{'='*80}")
    print(f"DATASOURCE VALIDATION")
    print(f"Testing {total_sources} source(s)")
    print(f"{'='*80}\n")

    for i, (source_name, source) in enumerate(sources_to_test.items(), 1):
        if not verbose:
            print(f"[{i}/{total_sources}] Testing {source_name}...", end=" ")

        source_type = getattr(source, 'source_type', 'unknown')
        result = await validate_single_source(source_name, source, source_type, verbose)
        results.append(result)

        if not verbose:
            print(f"[{result.status}]")

    return results


def print_summary(results: List[ValidationResult]) -> None:
    """Print validation summary."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASSED")
    failed = sum(1 for r in results if r.status == "FAILED")
    warnings = sum(1 for r in results if r.status == "WARNING")
    skipped = sum(1 for r in results if r.status == "SKIPPED")

    print(f"\n{'='*80}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*80}\n")

    print(f"Total Sources:  {total}")
    print(f"Passed:         {passed} ({passed/total*100:.1f}%)")
    print(f"Failed:         {failed} ({failed/total*100:.1f}%)")
    print(f"Warnings:       {warnings} ({warnings/total*100:.1f}%)")
    print(f"Skipped:        {skipped} ({skipped/total*100:.1f}%)")
    print()

    # Failed sources
    if failed > 0:
        print(f"[!] FAILED SOURCES:\n")
        for r in results:
            if r.status == "FAILED":
                print(f"  {r.source_name}:")
                for error in r.errors:
                    print(f"    - {error}")
        print()

    # Historical data support
    historical_sources = [r for r in results if r.historical_seasons > 0]
    print(f"Historical Data Support: {len(historical_sources)}/{total} sources")
    print()


def export_results(results: List[ValidationResult], output_path: Path) -> None:
    """Export validation results to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        fieldnames = [
            "source_name", "source_type", "status", "tests_passed", "tests_failed",
            "success_rate", "data_points", "historical_seasons", "errors", "warnings",
            "timestamp"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow(result.to_dict())

    print(f"[OK] Validation results exported to: {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate all datasources (current and historical data)"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Test specific source only (e.g., 'eybl')"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output for each test"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to CSV file"
    )

    args = parser.parse_args()

    # Initialize aggregator
    print("[...] Initializing datasource aggregator...")
    aggregator = DataSourceAggregator()
    print(f"[OK] Loaded {len(aggregator.sources)} datasources\n")

    # Run validation
    results = await validate_all_sources(
        aggregator,
        source_filter=args.source,
        verbose=args.verbose
    )

    # Print summary
    print_summary(results)

    # Export if requested
    if args.export:
        export_results(results, Path(args.export))

    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
