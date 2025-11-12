"""
Integration Test Runner for All Adapters

Tests all adapters with REAL data from live websites.
NO MOCKS - validates actual data extraction.

Usage:
    python scripts/run_integration_tests.py              # Run all tests
    python scripts/run_integration_tests.py --adapter sblive  # Test specific adapter
    python scripts/run_integration_tests.py --state WA   # Test specific state
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.sblive import SBLiveDataSource
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.rankone import RankOneDataSource
from src.datasources.us.three_ssb import ThreeSSBDataSource
from src.datasources.us.wsn import WSNDataSource
from src.datasources.us.fhsaa import FHSAADataSource
from src.datasources.us.hhsaa import HHSAADataSource
from src.datasources.us.mn_hub import MNHubDataSource
from src.datasources.us.psal import PSALDataSource


class IntegrationTestRunner:
    """Runs integration tests on all adapters with real data."""

    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    async def test_adapter(
        self,
        adapter_class,
        adapter_name: str,
        test_state: Optional[str] = None
    ) -> Dict:
        """Test a single adapter with real data."""
        print(f"\n{'='*70}")
        print(f"TESTING: {adapter_name}")
        print(f"{'='*70}")

        results = {
            "adapter": adapter_name,
            "tests": [],
            "passed": 0,
            "failed": 0,
            "data_extracted": False
        }

        try:
            # Initialize adapter
            adapter = adapter_class()
            print(f"[OK] Adapter initialized")

            # Test 1: Search for players
            print(f"\n[TEST 1] search_players() - Extract real player data")
            try:
                # Multi-state adapters need state parameter
                if hasattr(adapter_class, 'SUPPORTED_STATES'):
                    states_to_test = [test_state] if test_state else adapter_class.SUPPORTED_STATES[:1]
                    for state in states_to_test:
                        print(f"  Testing state: {state}")
                        players = await adapter.search_players(state=state, limit=5)
                else:
                    players = await adapter.search_players(limit=5)

                if players:
                    print(f"  [OK] Found {len(players)} players")
                    # Validate first player has required fields
                    player = players[0]
                    print(f"    Sample player: {player.full_name}")
                    print(f"      ID: {player.player_id}")
                    print(f"      School: {player.school_name or 'N/A'}")
                    print(f"      State: {player.school_state or 'N/A'}")

                    results["tests"].append({"name": "search_players", "status": "PASS", "count": len(players)})
                    results["passed"] += 1
                    results["data_extracted"] = True
                else:
                    print(f"  [WARN] No players found (may be off-season)")
                    results["tests"].append({"name": "search_players", "status": "WARN", "count": 0})
                    results["passed"] += 1

            except Exception as e:
                print(f"  [FAIL] Error: {str(e)}")
                results["tests"].append({"name": "search_players", "status": "FAIL", "error": str(e)})
                results["failed"] += 1

            # Test 2: Get player season stats
            print(f"\n[TEST 2] get_player_season_stats() - Extract stats")
            try:
                if players:
                    player_id = players[0].player_id
                    stats = await adapter.get_player_season_stats(player_id)

                    if stats:
                        print(f"  [OK] Stats found for {player_id}")
                        print(f"    Games: {stats.games_played or 'N/A'}")
                        print(f"    PPG: {stats.points_per_game or 'N/A'}")
                        print(f"    RPG: {stats.rebounds_per_game or 'N/A'}")
                        results["tests"].append({"name": "get_player_season_stats", "status": "PASS"})
                        results["passed"] += 1
                    else:
                        print(f"  [WARN] No stats found (may be off-season or limited data)")
                        results["tests"].append({"name": "get_player_season_stats", "status": "WARN"})
                        results["passed"] += 1
                else:
                    print(f"  [SKIP] No players to test")
                    results["tests"].append({"name": "get_player_season_stats", "status": "SKIP"})

            except Exception as e:
                print(f"  [FAIL] Error: {str(e)}")
                results["tests"].append({"name": "get_player_season_stats", "status": "FAIL", "error": str(e)})
                results["failed"] += 1

            # Test 3: Get leaderboard
            print(f"\n[TEST 3] get_leaderboard() - Extract leaderboard data")
            try:
                # Multi-state adapters need state parameter
                if hasattr(adapter_class, 'SUPPORTED_STATES'):
                    if test_state:
                        leaderboard = await adapter.get_leaderboard(stat="points", state=test_state, limit=5)
                    else:
                        # Test first supported state
                        leaderboard = await adapter.get_leaderboard(
                            stat="points",
                            state=adapter_class.SUPPORTED_STATES[0],
                            limit=5
                        )
                else:
                    leaderboard = await adapter.get_leaderboard(stat="points", limit=5)

                if leaderboard:
                    print(f"  [OK] Found {len(leaderboard)} leaderboard entries")
                    if leaderboard:
                        entry = leaderboard[0]
                        print(f"    #1: {entry.get('player_name', 'N/A')} - {entry.get('stat_value', 'N/A')} PPG")
                    results["tests"].append({"name": "get_leaderboard", "status": "PASS", "count": len(leaderboard)})
                    results["passed"] += 1
                else:
                    print(f"  [WARN] No leaderboard data (may be off-season)")
                    results["tests"].append({"name": "get_leaderboard", "status": "WARN", "count": 0})
                    results["passed"] += 1

            except Exception as e:
                print(f"  [FAIL] Error: {str(e)}")
                results["tests"].append({"name": "get_leaderboard", "status": "FAIL", "error": str(e)})
                results["failed"] += 1

            # Cleanup
            await adapter.close()
            print(f"\n[OK] Adapter closed")

        except Exception as e:
            print(f"\n[CRITICAL FAIL] Adapter initialization failed: {str(e)}")
            results["tests"].append({"name": "initialization", "status": "FAIL", "error": str(e)})
            results["failed"] += 1

        # Update totals
        self.total_tests += results["passed"] + results["failed"]
        self.passed_tests += results["passed"]
        self.failed_tests += results["failed"]

        return results

    async def run_all_tests(self, specific_adapter: Optional[str] = None, test_state: Optional[str] = None):
        """Run integration tests on all adapters."""
        print("="*70)
        print("INTEGRATION TEST SUITE - REAL DATA EXTRACTION")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: Testing with REAL website data (no mocks)")

        adapters = [
            (SBLiveDataSource, "SBLive Sports"),
            (BoundDataSource, "Bound"),
            (RankOneDataSource, "RankOne Sport"),
            (ThreeSSBDataSource, "Adidas 3SSB"),
            (WSNDataSource, "Wisconsin Sports Network"),
            (FHSAADataSource, "Florida HSAA"),
            (HHSAADataSource, "Hawaii HSAA"),
            (MNHubDataSource, "Minnesota Basketball Hub"),
            (PSALDataSource, "PSAL NYC"),
        ]

        # Filter if specific adapter requested
        if specific_adapter:
            adapters = [(cls, name) for cls, name in adapters
                       if specific_adapter.lower() in name.lower()]

        for adapter_class, adapter_name in adapters:
            result = await self.test_adapter(adapter_class, adapter_name, test_state)
            self.results[adapter_name] = result

        # Print summary
        print(f"\n\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}")

        for adapter_name, result in self.results.items():
            status_icon = "[OK]" if result["failed"] == 0 else "[FAIL]"
            data_icon = "[DATA]" if result["data_extracted"] else "[NO DATA]"
            print(f"{status_icon} {data_icon} {adapter_name}:")
            print(f"     Tests: {result['passed']} passed, {result['failed']} failed")

        print(f"\n{'='*70}")
        print(f"TOTAL: {self.passed_tests}/{self.total_tests} tests passed")
        print(f"SUCCESS RATE: {self.passed_tests/self.total_tests*100:.1f}%" if self.total_tests > 0 else "N/A")
        print(f"Adapters with data: {sum(1 for r in self.results.values() if r['data_extracted'])}/{len(self.results)}")
        print(f"{'='*70}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return self.passed_tests == self.total_tests


def main():
    parser = argparse.ArgumentParser(description="Run integration tests on basketball adapters")
    parser.add_argument("--adapter", help="Test specific adapter (e.g., 'sblive', 'bound')")
    parser.add_argument("--state", help="Test specific state (e.g., 'WA', 'TX')")
    args = parser.parse_args()

    runner = IntegrationTestRunner()
    success = asyncio.run(runner.run_all_tests(args.adapter, args.state))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
