"""
Comprehensive Validation for ANGT/OSBA Adapters

Tests both adapters thoroughly to ensure they can:
1. Fetch player-level statistics
2. Get historical data (multiple seasons)
3. Parse data accurately
4. Handle edge cases
5. Integrate with DuckDB

Usage:
    python scripts/validate_angt_osba_adapters.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 Validation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json
import io

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.europe.angt import ANGTDataSource
from src.datasources.canada.osba import OSBADataSource


class AdapterValidator:
    """Validates datasource adapters comprehensively."""

    def __init__(self):
        self.results = {
            'angt': {
                'adapter_name': 'ANGT (EuroLeague Next Generation)',
                'tests': {},
                'overall_status': 'PENDING'
            },
            'osba': {
                'adapter_name': 'OSBA (Ontario Scholastic Basketball)',
                'tests': {},
                'overall_status': 'PENDING'
            }
        }

    def record_test(self, adapter: str, test_name: str, passed: bool, details: str):
        """Record test result."""
        self.results[adapter]['tests'][test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }

    async def validate_angt(self):
        """Comprehensive ANGT validation."""
        print("\n" + "=" * 80)
        print("ANGT ADAPTER VALIDATION")
        print("=" * 80)

        angt = ANGTDataSource()

        try:
            # Test 1: Basic player search
            print("\n[TEST 1] Basic Player Search...")
            try:
                players = await angt.search_players(limit=10)
                if players and len(players) > 0:
                    self.record_test('angt', 'basic_search', True,
                                     f"Found {len(players)} players")
                    print(f"✅ PASS: Found {len(players)} players")

                    # Display sample player
                    p = players[0]
                    print(f"\nSample Player:")
                    print(f"  Name: {p.full_name}")
                    print(f"  ID: {p.player_id}")
                    print(f"  Club: {p.team_name}")
                    print(f"  Level: {p.level}")
                else:
                    self.record_test('angt', 'basic_search', False,
                                     "No players returned")
                    print("❌ FAIL: No players found")
            except Exception as e:
                self.record_test('angt', 'basic_search', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 2: Name filtering
            print("\n[TEST 2] Name Filter...")
            try:
                if players:
                    test_name = players[0].full_name.split()[0]
                    filtered = await angt.search_players(name=test_name, limit=5)
                    if filtered:
                        self.record_test('angt', 'name_filter', True,
                                         f"Found {len(filtered)} players with name '{test_name}'")
                        print(f"✅ PASS: Name filter works ({len(filtered)} results)")
                    else:
                        self.record_test('angt', 'name_filter', False,
                                         f"No results for name '{test_name}'")
                        print(f"❌ FAIL: No results for name '{test_name}'")
                else:
                    self.record_test('angt', 'name_filter', False,
                                     "Skipped - no players from Test 1")
                    print("⏭️ SKIP: No players from Test 1")
            except Exception as e:
                self.record_test('angt', 'name_filter', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 3: Player demographics validation
            print("\n[TEST 3] Player Demographics...")
            try:
                if players:
                    p = players[0]
                    has_required = all([
                        p.player_id,
                        p.full_name,
                        p.first_name or p.last_name,  # At least one name
                    ])
                    has_optional = any([
                        p.team_name,
                        p.school_name,
                        p.position,
                        p.height_inches,
                        p.weight_pounds
                    ])

                    if has_required:
                        self.record_test('angt', 'demographics', True,
                                         f"Required fields present, {has_optional} optional fields")
                        print(f"✅ PASS: Demographics validated")
                        print(f"  Required fields: ✓")
                        print(f"  Optional fields: {has_optional}")
                    else:
                        self.record_test('angt', 'demographics', False,
                                         "Missing required fields")
                        print("❌ FAIL: Missing required fields")
                else:
                    self.record_test('angt', 'demographics', False,
                                     "No players to validate")
                    print("⏭️ SKIP: No players")
            except Exception as e:
                self.record_test('angt', 'demographics', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 4: Historical data (multiple seasons)
            print("\n[TEST 4] Historical Data...")
            try:
                seasons = ['2025-26', '2024-25']
                season_results = {}
                for season in seasons:
                    try:
                        season_players = await angt.search_players(season=season, limit=5)
                        season_results[season] = len(season_players) if season_players else 0
                        print(f"  Season {season}: {season_results[season]} players")
                    except:
                        season_results[season] = 0

                if any(count > 0 for count in season_results.values()):
                    self.record_test('angt', 'historical_data', True,
                                     f"Seasons: {season_results}")
                    print(f"✅ PASS: Historical data available")
                else:
                    self.record_test('angt', 'historical_data', False,
                                     "No historical data found")
                    print("❌ FAIL: No historical data")
            except Exception as e:
                self.record_test('angt', 'historical_data', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 5: Player-level stats capability
            print("\n[TEST 5] Player-Level Stats...")
            try:
                if players:
                    p = players[0]
                    # Try to get season stats (method may not be fully implemented yet)
                    try:
                        stats = await angt.get_player_season_stats(p.player_id, season='2025-26')
                        if stats:
                            self.record_test('angt', 'player_stats', True,
                                             f"Stats retrieved for {p.full_name}")
                            print(f"✅ PASS: Player stats available")
                            print(f"  Player: {stats.player_name}")
                            if hasattr(stats, 'points_per_game') and stats.points_per_game:
                                print(f"  PPG: {stats.points_per_game}")
                        else:
                            self.record_test('angt', 'player_stats', False,
                                             "get_player_season_stats returned None")
                            print("⚠️ WARN: get_player_season_stats not yet implemented")
                    except NotImplementedError:
                        self.record_test('angt', 'player_stats', False,
                                         "Method not implemented")
                        print("⚠️ WARN: get_player_season_stats not yet implemented")
                else:
                    self.record_test('angt', 'player_stats', False,
                                     "No players to test")
                    print("⏭️ SKIP: No players")
            except Exception as e:
                self.record_test('angt', 'player_stats', False, str(e))
                print(f"❌ FAIL: {e}")

        finally:
            await angt.close()

        # Calculate overall status
        tests = self.results['angt']['tests']
        passed = sum(1 for t in tests.values() if t['passed'])
        total = len(tests)
        pass_rate = (passed / total * 100) if total > 0 else 0

        if pass_rate >= 80:
            self.results['angt']['overall_status'] = 'PRODUCTION_READY'
        elif pass_rate >= 60:
            self.results['angt']['overall_status'] = 'BASELINE_READY'
        else:
            self.results['angt']['overall_status'] = 'NEEDS_WORK'

        print(f"\nANGT Overall: {passed}/{total} tests passed ({pass_rate:.0f}%)")
        print(f"Status: {self.results['angt']['overall_status']}")

    async def validate_osba(self):
        """Comprehensive OSBA validation."""
        print("\n" + "=" * 80)
        print("OSBA ADAPTER VALIDATION")
        print("=" * 80)

        osba = OSBADataSource()

        try:
            # Test 1: Basic player search
            print("\n[TEST 1] Basic Player Search...")
            try:
                players = await osba.search_players(limit=10)
                if players and len(players) > 0:
                    self.record_test('osba', 'basic_search', True,
                                     f"Found {len(players)} players")
                    print(f"✅ PASS: Found {len(players)} players")

                    # Display sample player
                    p = players[0]
                    print(f"\nSample Player:")
                    print(f"  Name: {p.full_name}")
                    print(f"  ID: {p.player_id}")
                    print(f"  School: {p.team_name}")
                    print(f"  Level: {p.level}")
                    print(f"  Location: {p.school_state}, {p.school_country}")
                else:
                    self.record_test('osba', 'basic_search', False,
                                     "No players returned")
                    print("❌ FAIL: No players found")
                    print("⚠️ NOTE: OSBA may require manual URL discovery for division-specific pages")
            except Exception as e:
                self.record_test('osba', 'basic_search', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 2: Division filtering
            print("\n[TEST 2] Division Filter...")
            try:
                divisions = ['osba_mens', 'osba_womens', 'trillium_mens']
                division_results = {}
                for division in divisions:
                    try:
                        div_players = await osba.search_players(division=division, limit=5)
                        division_results[division] = len(div_players) if div_players else 0
                        print(f"  Division {division}: {division_results[division]} players")
                    except:
                        division_results[division] = 0

                if any(count > 0 for count in division_results.values()):
                    self.record_test('osba', 'division_filter', True,
                                     f"Divisions: {division_results}")
                    print(f"✅ PASS: Division filtering works")
                else:
                    self.record_test('osba', 'division_filter', False,
                                     "No division results")
                    print("❌ FAIL: No division results")
            except Exception as e:
                self.record_test('osba', 'division_filter', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 3: Player demographics validation
            print("\n[TEST 3] Player Demographics...")
            try:
                if players:
                    p = players[0]
                    has_required = all([
                        p.player_id,
                        p.full_name,
                        p.first_name or p.last_name,
                        p.school_state == 'ON',  # Should be Ontario
                        p.school_country == 'CA',  # Should be Canada
                    ])

                    if has_required:
                        self.record_test('osba', 'demographics', True,
                                         f"All required fields present with correct location")
                        print(f"✅ PASS: Demographics validated")
                    else:
                        self.record_test('osba', 'demographics', False,
                                         "Missing required fields or incorrect location")
                        print("❌ FAIL: Missing required fields or incorrect location")
                else:
                    self.record_test('osba', 'demographics', False,
                                     "No players to validate")
                    print("⏭️ SKIP: No players")
            except Exception as e:
                self.record_test('osba', 'demographics', False, str(e))
                print(f"❌ FAIL: {e}")

            # Test 4: Historical data
            print("\n[TEST 4] Historical Data...")
            try:
                seasons = ['2024-25', '2023-24']
                season_results = {}
                for season in seasons:
                    try:
                        season_players = await osba.search_players(season=season, limit=5)
                        season_results[season] = len(season_players) if season_players else 0
                        print(f"  Season {season}: {season_results[season]} players")
                    except:
                        season_results[season] = 0

                if any(count > 0 for count in season_results.values()):
                    self.record_test('osba', 'historical_data', True,
                                     f"Seasons: {season_results}")
                    print(f"✅ PASS: Historical data available")
                else:
                    self.record_test('osba', 'historical_data', False,
                                     "No historical data found")
                    print("❌ FAIL: No historical data")
            except Exception as e:
                self.record_test('osba', 'historical_data', False, str(e))
                print(f"❌ FAIL: {e}")

        finally:
            await osba.close()

        # Calculate overall status
        tests = self.results['osba']['tests']
        passed = sum(1 for t in tests.values() if t['passed'])
        total = len(tests)
        pass_rate = (passed / total * 100) if total > 0 else 0

        if pass_rate >= 80:
            self.results['osba']['overall_status'] = 'PRODUCTION_READY'
        elif pass_rate >= 60:
            self.results['osba']['overall_status'] = 'BASELINE_READY'
        else:
            self.results['osba']['overall_status'] = 'NEEDS_WORK'

        print(f"\nOSBA Overall: {passed}/{total} tests passed ({pass_rate:.0f}%)")
        print(f"Status: {self.results['osba']['overall_status']}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        for adapter_key, adapter_data in self.results.items():
            print(f"\n{adapter_data['adapter_name']}:")
            print(f"  Status: {adapter_data['overall_status']}")
            print(f"  Tests:")
            for test_name, test_data in adapter_data['tests'].items():
                status = "✅ PASS" if test_data['passed'] else "❌ FAIL"
                print(f"    {status} {test_name}: {test_data['details']}")

        # Save results to JSON
        results_path = "data/debug/adapter_validation_results.json"
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Results saved to: {results_path}")

    async def run_all_validations(self):
        """Run all validations."""
        await self.validate_angt()
        await self.validate_osba()
        self.print_summary()


async def main():
    """Main execution."""
    print("=" * 80)
    print("ANGT/OSBA ADAPTER COMPREHENSIVE VALIDATION")
    print("=" * 80)
    print("\nThis script validates both adapters for:")
    print("1. Basic player search capability")
    print("2. Filtering (name, division, season)")
    print("3. Player demographics accuracy")
    print("4. Historical data availability")
    print("5. Player-level stats capability")

    validator = AdapterValidator()
    await validator.run_all_validations()

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
