"""
Datasource Semantic Validation Harness

This script validates datasources at the DATA CORRECTNESS level, not just connectivity.

For each datasource with status "green" or "wip":
1. Loads test cases from config/datasource_test_cases.yaml
2. Calls search_players() and get_player_season_stats()
3. Runs sanity checks on the returned stats
4. Compares against expected values (if available)
5. Generates pass/fail report

This complements audit_all_datasources.py which only tests HTTP connectivity.

Usage:
    python scripts/validate_datasource_stats.py
    python scripts/validate_datasource_stats.py --source eybl  # Test specific source
    python scripts/validate_datasource_stats.py --verbose  # Show detailed output
"""

import asyncio
import yaml
import json
import sys
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# Paths
CONFIG_DIR = Path(__file__).parent.parent / "config"
STATUS_FILE = CONFIG_DIR / "datasource_status.yaml"
TEST_CASES_FILE = CONFIG_DIR / "datasource_test_cases.yaml"


def load_datasource_status() -> Dict:
    """Load datasource status from YAML."""
    if not STATUS_FILE.exists():
        print(f"⚠️  Warning: {STATUS_FILE} not found")
        return {}

    with open(STATUS_FILE, 'r') as f:
        data = yaml.safe_load(f)
        # Filter out non-dict entries (like comments)
        return {k: v for k, v in data.items() if isinstance(v, dict)}


def load_test_cases() -> Dict[str, List[Dict]]:
    """
    Load known-good test cases per datasource from YAML.

    Returns:
        dict: { datasource_name: [ {player_name: ..., season: ..., ...}, ... ], ... }
    """
    if not TEST_CASES_FILE.exists():
        print(f"⚠️  No test cases file found at {TEST_CASES_FILE}")
        print(f"   Create it with test player names for validation.")
        return {}

    with open(TEST_CASES_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    # Normalize: ensure every value is a list, filter out placeholders
    normalized = {}
    for ds_name, cases in data.items():
        if cases is None or cases == []:
            normalized[ds_name] = []
        elif isinstance(cases, dict):
            normalized[ds_name] = [cases]
        elif isinstance(cases, list):
            # Filter out placeholder cases (contain "REPLACE_WITH")
            real_cases = [
                case for case in cases
                if not any("REPLACE_WITH" in str(v) for v in case.values())
            ]
            normalized[ds_name] = real_cases
        else:
            print(f"⚠️  Unexpected test case format for {ds_name}: {type(cases)}")
            normalized[ds_name] = []

    return normalized


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
        if test_case.get("expected_min_games") and stats["games_played"] < test_case["expected_min_games"]:
            errors.append(f"Expected >= {test_case['expected_min_games']} games, got {stats['games_played']}")

    # Minutes
    if stats.get("minutes_per_game") is not None:
        if stats["minutes_per_game"] < 0:
            errors.append(f"Minutes cannot be negative: {stats['minutes_per_game']}")
        if stats["minutes_per_game"] > 48:
            errors.append(f"Minutes per game exceeds 48: {stats['minutes_per_game']}")

    # Points per game
    if stats.get("points_per_game") is not None:
        ppg = stats["points_per_game"]
        if ppg < 0:
            errors.append(f"PPG cannot be negative: {ppg}")
        min_ppg = test_case.get("expected_min_ppg", 0)
        max_ppg = test_case.get("expected_max_ppg", 100)
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
    if stats.get("rebounds_per_game") is not None:
        if stats["rebounds_per_game"] < 0:
            errors.append(f"RPG cannot be negative: {stats['rebounds_per_game']}")
        if stats["rebounds_per_game"] > 30:
            errors.append(f"RPG suspiciously high: {stats['rebounds_per_game']}")

    # Assists
    if stats.get("assists_per_game") is not None:
        if stats["assists_per_game"] < 0:
            errors.append(f"APG cannot be negative: {stats['assists_per_game']}")
        if stats["assists_per_game"] > 20:
            errors.append(f"APG suspiciously high: {stats['assists_per_game']}")

    # Steals
    if stats.get("steals_per_game") is not None:
        if stats["steals_per_game"] < 0:
            errors.append(f"SPG cannot be negative: {stats['steals_per_game']}")
        if stats["steals_per_game"] > 10:
            errors.append(f"SPG suspiciously high: {stats['steals_per_game']}")

    # Blocks
    if stats.get("blocks_per_game") is not None:
        if stats["blocks_per_game"] < 0:
            errors.append(f"BPG cannot be negative: {stats['blocks_per_game']}")
        if stats["blocks_per_game"] > 10:
            errors.append(f"BPG suspiciously high: {stats['blocks_per_game']}")

    # Turnovers
    if stats.get("turnovers_per_game") is not None:
        if stats["turnovers_per_game"] < 0:
            errors.append(f"TPG cannot be negative: {stats['turnovers_per_game']}")

    return errors


def load_adapter(ds_name: str, meta: dict, verbose: bool = False):
    """
    Dynamically load datasource adapter.

    Args:
        ds_name: Datasource name (e.g., "eybl", "sblive")
        meta: Datasource metadata from datasource_status.yaml
        verbose: Print debug info

    Returns:
        Datasource adapter instance or None
    """
    # Map datasource names to module paths
    # This follows the convention: src.datasources.{region}.{name}
    module_map = {
        # US National Circuits
        "eybl": "src.datasources.us.eybl.EYBLDataSource",
        "eybl_girls": "src.datasources.us.eybl_girls.EYBLGirlsDataSource",
        "three_ssb": "src.datasources.us.three_ssb.ThreeSSBDataSource",
        "three_ssb_girls": "src.datasources.us.three_ssb_girls.ThreeSSBGirlsDataSource",
        "uaa": "src.datasources.us.uaa.UAADataSource",
        "uaa_girls": "src.datasources.us.uaa_girls.UAAGirlsDataSource",

        # US Multi-State
        "sblive": "src.datasources.us.sblive.SBLiveDataSource",
        "bound": "src.datasources.us.bound.BoundDataSource",
        "mn_basketball_hub": "src.datasources.us.mn_hub.MNBasketballHubDataSource",

        # US Single State
        "psal": "src.datasources.us.psal.PSALDataSource",

        # Global
        "fiba_youth": "src.datasources.europe.fiba_youth.FIBAYouthDataSource",
        "fiba_livestats": "src.datasources.global.fiba_livestats.FIBALiveStatsDataSource",

        # Europe
        "angt": "src.datasources.europe.angt.ANGTDataSource",
        "nbbl": "src.datasources.europe.nbbl.NBBLDataSource",
        "feb": "src.datasources.europe.feb.FEBDataSource",

        # Canada
        "osba": "src.datasources.canada.osba.OSBADataSource",
        "npa": "src.datasources.canada.npa.NPADataSource",

        # Australia
        "playhq": "src.datasources.australia.playhq.PlayHQDataSource",

        # Prep/Elite
        "ote": "src.datasources.us.ote.OTEDataSource",
        "grind_session": "src.datasources.us.grind_session.GrindSessionDataSource",
    }

    if ds_name not in module_map:
        if verbose:
            print(f"⚠️  No module mapping for datasource: {ds_name}")
        return None

    module_path = module_map[ds_name]
    module_name, class_name = module_path.rsplit('.', 1)

    try:
        # Import module and get class
        module = importlib.import_module(module_name)
        adapter_class = getattr(module, class_name)

        # Instantiate adapter
        adapter = adapter_class()

        if verbose:
            print(f"✅ Loaded adapter: {class_name}")

        return adapter

    except Exception as e:
        if verbose:
            print(f"❌ Failed to load adapter {ds_name}: {e}")
        return None


async def validate_single_case(
    ds_name: str,
    meta: dict,
    case: dict,
    verbose: bool = False
) -> dict:
    """
    Run validation for a single (datasource, test_case) combo.

    Args:
        ds_name: Datasource name
        meta: Datasource metadata
        case: Test case dict with player_name, season, etc.
        verbose: Print detailed output

    Returns:
        Validation result dict
    """
    player_name = case["player_name"]
    season = case.get("season")
    team_hint = case.get("team_hint")

    result = {
        "datasource": ds_name,
        "player_name": player_name,
        "season": season,
        "status": "UNKNOWN",
        "errors": [],
        "stats": None,
    }

    try:
        # Load adapter
        adapter = load_adapter(ds_name, meta, verbose=verbose)
        if not adapter:
            result["status"] = "ERROR"
            result["errors"].append("Failed to load adapter")
            return result

        if verbose:
            print(f"[VALIDATE] {ds_name}: {player_name} ({season})")

        # Search for player
        search_results = await adapter.search_players(
            name=player_name,
            team=team_hint,
            limit=5
        )

        if not search_results:
            result["status"] = "FAIL"
            result["errors"].append("Player not found in search results")
            if verbose:
                print(f"  ❌ Player not found: {player_name}")
            return result

        # Pick best match (first result for now)
        player = search_results[0]
        player_id = player.player_id if hasattr(player, 'player_id') else None

        if not player_id:
            result["status"] = "FAIL"
            result["errors"].append("Player found but no player_id")
            return result

        if verbose:
            print(f"  ✅ Found player: {player_id}")

        # Get season stats
        stats = await adapter.get_player_season_stats(
            player_id=player_id,
            season=season
        )

        if not stats:
            result["status"] = "FAIL"
            result["errors"].append("Stats not found for player/season")
            if verbose:
                print(f"  ❌ Stats not found for {player_id} ({season})")
            return result

        # Convert Pydantic model to dict if needed
        if hasattr(stats, 'model_dump'):
            stats_dict = stats.model_dump()
        elif hasattr(stats, 'dict'):
            stats_dict = stats.dict()
        else:
            stats_dict = stats

        result["stats"] = stats_dict

        if verbose:
            print(f"  ✅ Retrieved stats: GP={stats_dict.get('games_played')}, PPG={stats_dict.get('points_per_game')}")

        # Run sanity checks
        validation_errors = run_sanity_checks(stats_dict, case)

        if validation_errors:
            result["status"] = "FAIL"
            result["errors"].extend(validation_errors)
            if verbose:
                print(f"  ❌ Sanity check failures:")
                for err in validation_errors:
                    print(f"      - {err}")
        else:
            result["status"] = "PASS"
            if verbose:
                print(f"  ✅ All sanity checks passed")

        # Close adapter if it has close method
        if hasattr(adapter, 'close'):
            await adapter.close()

    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(f"Exception: {str(e)}")
        if verbose:
            print(f"  ❌ Exception: {e}")
            import traceback
            traceback.print_exc()

    return result


async def validate_all_datasources(source_filter: Optional[str] = None, verbose: bool = False):
    """
    Run validation on all eligible datasources.

    Args:
        source_filter: Only validate this specific datasource (optional)
        verbose: Print detailed output
    """
    print("=" * 100)
    print("DATASOURCE SEMANTIC VALIDATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Load configurations
    datasource_status = load_datasource_status()
    test_cases_map = load_test_cases()

    if not datasource_status:
        print("❌ No datasource status found. Check config/datasource_status.yaml")
        return

    # Filter to green/wip sources (or specific source if filter provided)
    if source_filter:
        if source_filter not in datasource_status:
            print(f"❌ Datasource '{source_filter}' not found in status file")
            return
        eligible_sources = {source_filter: datasource_status[source_filter]}
        print(f"\n📌 Validating specific source: {source_filter}")
    else:
        eligible_sources = {
            source_id: config
            for source_id, config in datasource_status.items()
            if isinstance(config, dict) and config.get("status") in ["green", "wip"]
        }

    print(f"\nFound {len(eligible_sources)} eligible sources (status='green' or 'wip'):")
    for source_id, config in eligible_sources.items():
        status = config.get("status", "unknown")
        name = config.get("name", source_id)
        print(f"  - {source_id}: {name} (status={status})")

    if not eligible_sources:
        print("\n⚠️  No sources with status 'green' or 'wip'")
        print("   Update datasource_status.yaml to mark sources as 'wip' when ready to validate")
        return

    # Check for test cases
    total_cases = sum(len(test_cases_map.get(sid, [])) for sid in eligible_sources)
    if total_cases == 0:
        print("\n⚠️  No test cases defined in config/datasource_test_cases.yaml")
        print("   Add real player names to test cases file before running validation")
        return

    print(f"\nTotal test cases to run: {total_cases}")
    print("")

    # Run validation for each source + test case
    results = []
    for source_id, config in eligible_sources.items():
        test_cases = test_cases_map.get(source_id, [])

        if not test_cases:
            print(f"⚠️  Skipping {source_id}: no test cases defined")
            continue

        print(f"\n{'='*100}")
        print(f"Validating {source_id}: {config.get('name', 'Unknown')}")
        print(f"{'='*100}")

        for i, case in enumerate(test_cases, 1):
            print(f"\nTest case {i}/{len(test_cases)}:")
            result = await validate_single_case(source_id, config, case, verbose=verbose)
            results.append(result)

    # Generate summary
    print("\n" + "=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)

    total_passed = sum(1 for r in results if r["status"] == "PASS")
    total_failed = sum(1 for r in results if r["status"] == "FAIL")
    total_errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\nTotal test cases run: {len(results)}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"⚠️  Errors: {total_errors}")

    if len(results) > 0:
        success_rate = (total_passed / len(results)) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")

    # Show failed cases
    if total_failed > 0 or total_errors > 0:
        print("\n" + "=" * 100)
        print("FAILED TEST CASES")
        print("=" * 100)
        for result in results:
            if result["status"] in ["FAIL", "ERROR"]:
                print(f"\n❌ {result['datasource']}: {result['player_name']} ({result['season']})")
                for error in result["errors"]:
                    print(f"   - {error}")

    # Export results
    output_file = "validation_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(results),
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "success_rate": success_rate if len(results) > 0 else 0,
            "results": results
        }, f, indent=2, default=str)

    print(f"\n📄 Results exported to: {output_file}")

    # Generate markdown summary
    markdown_file = "VALIDATION_SUMMARY.md"
    with open(markdown_file, 'w') as f:
        f.write(f"# Datasource Validation Summary\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Overview\n\n")
        f.write(f"- **Total Test Cases**: {len(results)}\n")
        f.write(f"- **Passed**: {total_passed}\n")
        f.write(f"- **Failed**: {total_failed}\n")
        f.write(f"- **Errors**: {total_errors}\n")
        if len(results) > 0:
            f.write(f"- **Success Rate**: {success_rate:.1f}%\n\n")

        f.write(f"## Results by Datasource\n\n")
        by_datasource = {}
        for result in results:
            ds = result['datasource']
            if ds not in by_datasource:
                by_datasource[ds] = []
            by_datasource[ds].append(result)

        for ds, ds_results in by_datasource.items():
            ds_passed = sum(1 for r in ds_results if r["status"] == "PASS")
            ds_total = len(ds_results)
            status_icon = "✅" if ds_passed == ds_total else "❌"

            f.write(f"### {status_icon} {ds}\n\n")
            f.write(f"- **Test Cases**: {ds_total}\n")
            f.write(f"- **Passed**: {ds_passed}/{ds_total}\n")

            if ds_passed < ds_total:
                f.write(f"\n**Failed cases**:\n")
                for result in ds_results:
                    if result["status"] != "PASS":
                        f.write(f"- {result['player_name']} ({result['season']})\n")
                        for error in result["errors"]:
                            f.write(f"  - {error}\n")

            f.write("\n")

    print(f"📄 Markdown summary exported to: {markdown_file}")
    print("\n" + "=" * 100)

    # Next steps guidance
    print("\nNEXT STEPS:")
    if total_passed == len(results):
        print("✅ All validation passed! Update datasource_status.yaml:")
        for ds in by_datasource.keys():
            print(f"   - Mark {ds} as status='green'")
            print(f"   - Add seasons_supported list")
    else:
        print("❌ Some validations failed. Fix issues in adapters:")
        for ds, ds_results in by_datasource.items():
            failed = [r for r in ds_results if r["status"] != "PASS"]
            if failed:
                print(f"   - {ds}: {len(failed)} failures")
                print(f"     Check adapter implementation in src/datasources/")

    print("=" * 100)


if __name__ == "__main__":
    # Parse command line args
    source_filter = None
    verbose = False

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--verbose" or arg == "-v":
                verbose = True
            elif arg.startswith("--source="):
                source_filter = arg.split("=")[1]
            elif not arg.startswith("-"):
                source_filter = arg

    asyncio.run(validate_all_datasources(source_filter=source_filter, verbose=verbose))
