"""
Datasource Semantic Validation Harness

This script validates datasources at the DATA CORRECTNESS level, not just connectivity.

For each datasource with status "green" or "wip":
1. Loads test cases (known player + season combinations)
2. Calls search_players() and get_player_season_stats()
3. Runs sanity checks on the returned stats
4. Compares against expected values (if available)
5. Generates pass/fail report

This complements audit_all_datasources.py which only tests HTTP connectivity.
"""

import asyncio
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Test cases for known players per datasource
# These should be manually verified as correct before adding
TEST_CASES = {
    "eybl": [
        {
            "player_name": "Cooper Flagg",  # Replace with actual EYBL player
            "season": "2024",
            "expected_games": None,  # Set after manual verification
            "expected_ppg_min": 10.0,  # Minimum expected PPG
            "expected_ppg_max": 40.0,  # Maximum expected PPG
        },
    ],
    "sblive": [
        {
            "player_name": "Test Player",  # Replace with actual SBLive player
            "season": "2024-25",
            "state": "WA",
            "expected_games": None,
            "expected_ppg_min": 5.0,
            "expected_ppg_max": 50.0,
        },
    ],
    "angt": [
        {
            "player_name": "Test Player",  # Add after ANGT is working
            "season": "2023-24",
            "expected_games": None,
            "expected_ppg_min": 5.0,
            "expected_ppg_max": 40.0,
        },
    ],
    "osba": [
        {
            "player_name": "Test Player",  # Add after OSBA is working
            "season": "2023-24",
            "division": "Prep",
            "expected_games": None,
            "expected_ppg_min": 5.0,
            "expected_ppg_max": 50.0,
        },
    ],
}


def load_datasource_status() -> Dict:
    """Load datasource status from YAML."""
    status_file = Path(__file__).parent.parent / "config" / "datasource_status.yaml"
    if not status_file.exists():
        print(f"⚠️  Warning: {status_file} not found")
        return {}

    with open(status_file, 'r') as f:
        return yaml.safe_load(f)


def run_sanity_checks(stats: dict, test_case: dict) -> List[str]:
    """
    Run sanity checks on player stats.

    Returns list of validation errors (empty if all pass).
    """
    errors = []

    # Games played
    if stats.get("games_played"):
        if stats["games_played"] < 1:
            errors.append(f"Games played must be >= 1, got {stats['games_played']}")
        if test_case.get("expected_games") and stats["games_played"] != test_case["expected_games"]:
            errors.append(f"Expected {test_case['expected_games']} games, got {stats['games_played']}")

    # Minutes
    if stats.get("minutes_per_game"):
        if stats["minutes_per_game"] < 0:
            errors.append(f"Minutes cannot be negative: {stats['minutes_per_game']}")
        if stats["minutes_per_game"] > 48:
            errors.append(f"Minutes per game exceeds 48: {stats['minutes_per_game']}")

    # Points per game
    if stats.get("points_per_game"):
        ppg = stats["points_per_game"]
        if ppg < 0:
            errors.append(f"PPG cannot be negative: {ppg}")
        min_ppg = test_case.get("expected_ppg_min", 0)
        max_ppg = test_case.get("expected_ppg_max", 100)
        if not (min_ppg <= ppg <= max_ppg):
            errors.append(f"PPG {ppg} outside expected range [{min_ppg}, {max_ppg}]")

    # Field goals
    if stats.get("field_goals_made") is not None and stats.get("field_goals_attempted") is not None:
        fgm = stats["field_goals_made"]
        fga = stats["field_goals_attempted"]
        if fgm < 0 or fga < 0:
            errors.append(f"FGM/FGA cannot be negative: {fgm}/{fga}")
        if fgm > fga:
            errors.append(f"FGM ({fgm}) cannot exceed FGA ({fga})")

    # Three pointers
    if stats.get("three_pointers_made") is not None and stats.get("three_pointers_attempted") is not None:
        tpm = stats["three_pointers_made"]
        tpa = stats["three_pointers_attempted"]
        if tpm < 0 or tpa < 0:
            errors.append(f"3PM/3PA cannot be negative: {tpm}/{tpa}")
        if tpm > tpa:
            errors.append(f"3PM ({tpm}) cannot exceed 3PA ({tpa})")

    # Free throws
    if stats.get("free_throws_made") is not None and stats.get("free_throws_attempted") is not None:
        ftm = stats["free_throws_made"]
        fta = stats["free_throws_attempted"]
        if ftm < 0 or fta < 0:
            errors.append(f"FTM/FTA cannot be negative: {ftm}/{fta}")
        if ftm > fta:
            errors.append(f"FTM ({ftm}) cannot exceed FTA ({fta})")

    # Rebounds
    if stats.get("rebounds_per_game"):
        if stats["rebounds_per_game"] < 0:
            errors.append(f"RPG cannot be negative: {stats['rebounds_per_game']}")
        if stats["rebounds_per_game"] > 30:
            errors.append(f"RPG suspiciously high: {stats['rebounds_per_game']}")

    # Assists
    if stats.get("assists_per_game"):
        if stats["assists_per_game"] < 0:
            errors.append(f"APG cannot be negative: {stats['assists_per_game']}")
        if stats["assists_per_game"] > 20:
            errors.append(f"APG suspiciously high: {stats['assists_per_game']}")

    # Steals
    if stats.get("steals_per_game"):
        if stats["steals_per_game"] < 0:
            errors.append(f"SPG cannot be negative: {stats['steals_per_game']}")
        if stats["steals_per_game"] > 10:
            errors.append(f"SPG suspiciously high: {stats['steals_per_game']}")

    # Blocks
    if stats.get("blocks_per_game"):
        if stats["blocks_per_game"] < 0:
            errors.append(f"BPG cannot be negative: {stats['blocks_per_game']}")
        if stats["blocks_per_game"] > 10:
            errors.append(f"BPG suspiciously high: {stats['blocks_per_game']}")

    # Turnovers
    if stats.get("turnovers_per_game"):
        if stats["turnovers_per_game"] < 0:
            errors.append(f"TPG cannot be negative: {stats['turnovers_per_game']}")

    return errors


async def validate_datasource(source_id: str, source_config: dict, test_cases: List[dict]) -> dict:
    """
    Validate a single datasource with test cases.

    Returns validation result dict.
    """
    result = {
        "source_id": source_id,
        "source_name": source_config.get("name", source_id),
        "status": source_config.get("status", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "test_cases_run": 0,
        "test_cases_passed": 0,
        "test_cases_failed": 0,
        "errors": [],
        "details": []
    }

    # Skip if not green or wip
    if source_config.get("status") not in ["green", "wip"]:
        result["errors"].append(f"Skipped - status is '{source_config.get('status')}', not 'green' or 'wip'")
        return result

    # Skip if no test cases
    if not test_cases:
        result["errors"].append("No test cases defined")
        return result

    try:
        # Dynamically import the datasource adapter
        # This assumes adapters follow naming convention: src.datasources.{region}.{source_id}
        # For now, we'll note this needs manual implementation per source
        result["errors"].append("TODO: Implement dynamic adapter import and testing")

        # Placeholder for actual implementation:
        # adapter = await load_adapter(source_id, source_config)
        #
        # for test_case in test_cases:
        #     result["test_cases_run"] += 1
        #
        #     # Search for player
        #     players = await adapter.search_players(name=test_case["player_name"], limit=5)
        #     if not players:
        #         result["test_cases_failed"] += 1
        #         result["details"].append({
        #             "test_case": test_case,
        #             "status": "FAIL",
        #             "error": "Player not found"
        #         })
        #         continue
        #
        #     player = players[0]
        #
        #     # Get season stats
        #     stats = await adapter.get_player_season_stats(
        #         player_id=player.player_id,
        #         season=test_case["season"]
        #     )
        #
        #     if not stats:
        #         result["test_cases_failed"] += 1
        #         result["details"].append({
        #             "test_case": test_case,
        #             "status": "FAIL",
        #             "error": "Stats not found"
        #         })
        #         continue
        #
        #     # Run sanity checks
        #     stats_dict = stats.model_dump() if hasattr(stats, 'model_dump') else stats
        #     validation_errors = run_sanity_checks(stats_dict, test_case)
        #
        #     if validation_errors:
        #         result["test_cases_failed"] += 1
        #         result["details"].append({
        #             "test_case": test_case,
        #             "status": "FAIL",
        #             "errors": validation_errors,
        #             "stats": stats_dict
        #         })
        #     else:
        #         result["test_cases_passed"] += 1
        #         result["details"].append({
        #             "test_case": test_case,
        #             "status": "PASS",
        #             "stats": stats_dict
        #         })

    except Exception as e:
        result["errors"].append(f"Validation failed: {str(e)}")

    return result


async def validate_all_datasources():
    """Run validation on all eligible datasources."""
    print("=" * 100)
    print("DATASOURCE SEMANTIC VALIDATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Load datasource status
    datasource_status = load_datasource_status()
    if not datasource_status:
        print("❌ No datasource status found. Run audit_all_datasources.py first.")
        return

    # Filter to green/wip sources
    eligible_sources = {
        source_id: config
        for source_id, config in datasource_status.items()
        if isinstance(config, dict) and config.get("status") in ["green", "wip"]
    }

    print(f"\nFound {len(eligible_sources)} eligible sources (status='green' or 'wip'):")
    for source_id, config in eligible_sources.items():
        print(f"  - {source_id}: {config.get('name', 'Unknown')}")

    if not eligible_sources:
        print("\n⚠️  No sources with status 'green' or 'wip'")
        print("   Once you fix ANGT/OSBA/EYBL, update their status in datasource_status.yaml")
        return

    # Run validation for each source
    results = []
    for source_id, config in eligible_sources.items():
        test_cases = TEST_CASES.get(source_id, [])
        result = await validate_datasource(source_id, config, test_cases)
        results.append(result)

    # Generate report
    print("\n" + "=" * 100)
    print("VALIDATION RESULTS")
    print("=" * 100)

    total_passed = 0
    total_failed = 0

    for result in results:
        print(f"\n{result['source_name']} ({result['source_id']})")
        print("-" * 100)
        print(f"Status: {result['status']}")
        print(f"Test Cases: {result['test_cases_run']} run, {result['test_cases_passed']} passed, {result['test_cases_failed']} failed")

        if result['errors']:
            print("Errors:")
            for error in result['errors']:
                print(f"  ❌ {error}")

        if result['details']:
            print("Details:")
            for detail in result['details']:
                status_icon = "✅" if detail['status'] == "PASS" else "❌"
                print(f"  {status_icon} {detail.get('test_case', {}).get('player_name', 'Unknown')}")
                if detail.get('errors'):
                    for err in detail['errors']:
                        print(f"      - {err}")

        total_passed += result['test_cases_passed']
        total_failed += result['test_cases_failed']

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total Sources Validated: {len(results)}")
    print(f"Total Test Cases Passed: {total_passed}")
    print(f"Total Test Cases Failed: {total_failed}")

    success_rate = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")

    # Export results
    output_file = "validation_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_sources": len(results),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "success_rate": success_rate,
            "results": results
        }, f, indent=2)

    print(f"\n📄 Results exported to: {output_file}")

    # Generate markdown summary
    markdown_file = "VALIDATION_SUMMARY.md"
    with open(markdown_file, 'w') as f:
        f.write(f"# Datasource Validation Summary\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Overview\n\n")
        f.write(f"- **Total Sources Validated**: {len(results)}\n")
        f.write(f"- **Total Test Cases Passed**: {total_passed}\n")
        f.write(f"- **Total Test Cases Failed**: {total_failed}\n")
        f.write(f"- **Success Rate**: {success_rate:.1f}%\n\n")

        f.write(f"## Results by Datasource\n\n")
        for result in results:
            status_icon = "✅" if result['test_cases_passed'] > 0 and result['test_cases_failed'] == 0 else "❌"
            f.write(f"### {status_icon} {result['source_name']}\n\n")
            f.write(f"- **Status**: {result['status']}\n")
            f.write(f"- **Test Cases**: {result['test_cases_run']} run, {result['test_cases_passed']} passed, {result['test_cases_failed']} failed\n")

            if result['errors']:
                f.write(f"\n**Errors**:\n")
                for error in result['errors']:
                    f.write(f"- {error}\n")

            f.write("\n")

    print(f"📄 Markdown summary exported to: {markdown_file}")
    print("\n" + "=" * 100)
    print("\nNEXT STEPS:")
    print("1. Update TEST_CASES in this script with real player names after manual verification")
    print("2. Implement dynamic adapter loading in validate_datasource()")
    print("3. Fix ANGT/OSBA/EYBL adapters until they pass validation")
    print("4. Update datasource_status.yaml status to 'green' once validated")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(validate_all_datasources())
