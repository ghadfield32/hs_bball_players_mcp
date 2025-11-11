"""
Adapter Verification Utility

Systematically tests all datasource adapters and reports their status.
Helps identify broken adapters and provides diagnostics.

Usage:
    # Test all adapters
    python scripts/verify_adapters.py

    # Test specific adapter
    python scripts/verify_adapters.py --adapter eybl

    # Quick test (just health check)
    python scripts/verify_adapters.py --quick

    # Generate report
    python scripts/verify_adapters.py --report

Author: Claude Code
Date: 2025-11-11
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    try:
        # Try to enable UTF-8 mode
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Emoji replacements for Windows compatibility
EMOJI_MAP = {
    '🏀': '[BBALL]',
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⚠️': '[WARN]',
    '🔴': '[ERROR]',
    '💥': '[CRASH]',
    '❓': '[?]',
    '📊': '[STATS]',
    '1️⃣': '1.',
    '2️⃣': '2.',
    '3️⃣': '3.',
    '4️⃣': '4.',
    '5️⃣': '5.',
}

def safe_print(*args, **kwargs):
    """Print text with emoji handling for Windows."""
    # Convert all args to strings and handle emojis
    safe_args = []
    for arg in args:
        text = str(arg)
        if sys.platform == 'win32':
            # Replace emojis with ASCII on Windows
            for emoji, replacement in EMOJI_MAP.items():
                text = text.replace(emoji, replacement)
        safe_args.append(text)

    # Use built-in print with safe args
    import builtins
    builtins.print(*safe_args, **kwargs)

# Override print function globally for this script
print = safe_print

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.datasources.us.eybl import EYBLDataSource
    from src.datasources.us.psal import PSALDataSource
    from src.datasources.us.mn_hub import MNHubDataSource
    from src.datasources.europe.fiba_youth import FIBAYouthDataSource
    # Add other adapters as they're implemented
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class AdapterTester:
    """Test and verify datasource adapters."""

    def __init__(self, quick: bool = False):
        """Initialize tester."""
        self.quick = quick
        self.results = {}

    async def test_adapter(
        self,
        name: str,
        adapter_class,
        skip_search: bool = False
    ) -> Dict:
        """
        Test a single adapter.

        Returns:
            Dictionary with test results
        """
        result = {
            "name": name,
            "class": adapter_class.__name__,
            "status": "unknown",
            "healthy": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "player_count": 0,
            "sample_player": None,
        }

        adapter = None

        try:
            # Initialize adapter
            print(f"\n{'='*60}")
            print(f"Testing: {name} ({adapter_class.__name__})")
            print('='*60)

            adapter = adapter_class()
            result["source_name"] = adapter.source_name
            result["base_url"] = adapter.base_url

            # Test 1: Health Check
            print("\n1️⃣  Health Check...", end=" ")
            try:
                healthy = await adapter.health_check()
                result["healthy"] = healthy

                if healthy:
                    print("✅ PASS")
                    result["tests_passed"] += 1
                else:
                    print("❌ FAIL - Website not accessible")
                    result["tests_failed"] += 1
                    result["errors"].append("Health check failed")
                    result["status"] = "unhealthy"
                    return result

            except Exception as e:
                print(f"❌ ERROR - {e}")
                result["tests_failed"] += 1
                result["errors"].append(f"Health check error: {e}")
                result["status"] = "error"
                return result

            if self.quick:
                result["status"] = "healthy"
                return result

            # Test 2: Search Players
            if not skip_search:
                print("\n2️⃣  Search Players...", end=" ")
                try:
                    players = await adapter.search_players(limit=5)

                    if players and len(players) > 0:
                        print(f"✅ PASS - Found {len(players)} players")
                        result["tests_passed"] += 1
                        result["player_count"] = len(players)

                        # Sample player
                        sample = players[0]
                        result["sample_player"] = {
                            "id": sample.player_id,
                            "name": sample.full_name,
                            "team": sample.team_name,
                            "position": str(sample.position) if sample.position else None,
                        }

                        print(f"   Sample: {sample.full_name}", end="")
                        if sample.team_name:
                            print(f" ({sample.team_name})")
                        else:
                            print()

                    else:
                        print("⚠️  WARNING - No players found")
                        result["tests_failed"] += 1
                        result["warnings"].append("No players found in search")

                except Exception as e:
                    print(f"❌ ERROR - {e}")
                    result["tests_failed"] += 1
                    result["errors"].append(f"Search players error: {e}")

            # Test 3: Get Player (if we have one)
            if result.get("sample_player"):
                print("\n3️⃣  Get Player by ID...", end=" ")
                try:
                    player_id = result["sample_player"]["id"]
                    player = await adapter.get_player(player_id)

                    if player:
                        print("✅ PASS")
                        result["tests_passed"] += 1
                    else:
                        print("⚠️  WARNING - Player not found")
                        result["warnings"].append("Get player returned None")

                except Exception as e:
                    print(f"❌ ERROR - {e}")
                    result["tests_failed"] += 1
                    result["errors"].append(f"Get player error: {e}")

            # Test 4: Get Season Stats
            if result.get("sample_player"):
                print("\n4️⃣  Get Season Stats...", end=" ")
                try:
                    player_id = result["sample_player"]["id"]
                    stats = await adapter.get_player_season_stats(player_id)

                    if stats:
                        print("✅ PASS")
                        result["tests_passed"] += 1
                        print(f"   Games: {stats.games_played}", end="")
                        if stats.points_per_game:
                            print(f", PPG: {stats.points_per_game:.1f}", end="")
                        if stats.rebounds_per_game:
                            print(f", RPG: {stats.rebounds_per_game:.1f}", end="")
                        if stats.assists_per_game:
                            print(f", APG: {stats.assists_per_game:.1f}", end="")
                        print()
                    else:
                        print("⚠️  WARNING - No stats found")
                        result["warnings"].append("Season stats returned None")

                except Exception as e:
                    print(f"❌ ERROR - {e}")
                    result["tests_failed"] += 1
                    result["errors"].append(f"Get stats error: {e}")

            # Test 5: Get Leaderboard
            print("\n5️⃣  Get Leaderboard...", end=" ")
            try:
                leaderboard = await adapter.get_leaderboard("points", limit=5)

                if leaderboard and len(leaderboard) > 0:
                    print(f"✅ PASS - Found {len(leaderboard)} leaders")
                    result["tests_passed"] += 1

                    # Show top 3
                    print("   Top 3:")
                    for entry in leaderboard[:3]:
                        print(f"     {entry['rank']}. {entry['player_name']}: "
                              f"{entry['stat_value']}")
                else:
                    print("⚠️  WARNING - No leaderboard data")
                    result["warnings"].append("Leaderboard returned empty")

            except Exception as e:
                print(f"❌ ERROR - {e}")
                result["tests_failed"] += 1
                result["errors"].append(f"Get leaderboard error: {e}")

            # Determine overall status
            if result["tests_failed"] == 0:
                if len(result["warnings"]) == 0:
                    result["status"] = "passing"
                else:
                    result["status"] = "passing_with_warnings"
            else:
                result["status"] = "failing"

        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            result["status"] = "error"
            result["errors"].append(f"Fatal error: {e}")

        finally:
            # Cleanup
            if adapter:
                try:
                    await adapter.close()
                except:
                    pass

        return result

    async def test_all_adapters(self) -> Dict[str, Dict]:
        """Test all available adapters."""
        adapters = [
            ("EYBL", EYBLDataSource, False),
            ("PSAL", PSALDataSource, False),
            ("MN Hub", MNHubDataSource, False),
            ("FIBA Youth", FIBAYouthDataSource, True),  # Skip search for FIBA
        ]

        results = {}

        for name, adapter_class, skip_search in adapters:
            result = await self.test_adapter(name, adapter_class, skip_search)
            results[name] = result

            # Small delay between tests
            await asyncio.sleep(2)

        return results

    def print_summary(self, results: Dict[str, Dict]):
        """Print summary of test results."""
        print("\n" + "=" * 70)
        print("📊 ADAPTER TEST SUMMARY")
        print("=" * 70)

        status_symbols = {
            "passing": "✅",
            "passing_with_warnings": "⚠️",
            "failing": "❌",
            "unhealthy": "🔴",
            "error": "💥",
            "unknown": "❓",
        }

        total_passing = 0
        total_failing = 0
        total_warnings = 0

        for name, result in results.items():
            status = result["status"]
            symbol = status_symbols.get(status, "❓")

            print(f"\n{symbol} {name} - {status.upper()}")
            print(f"   Tests: {result['tests_passed']} passed, {result['tests_failed']} failed")

            if result["errors"]:
                print(f"   Errors: {len(result['errors'])}")
                for error in result["errors"][:3]:
                    print(f"     - {error}")

            if result["warnings"]:
                print(f"   Warnings: {len(result['warnings'])}")
                for warning in result["warnings"][:3]:
                    print(f"     - {warning}")

            if result["status"] in ["passing", "passing_with_warnings"]:
                total_passing += 1
            else:
                total_failing += 1

            if result["warnings"]:
                total_warnings += 1

        print("\n" + "=" * 70)
        print(f"Total: {total_passing} passing, {total_failing} failing, {total_warnings} with warnings")
        print("=" * 70)

    def generate_report(self, results: Dict[str, Dict], output_path: str = None):
        """Generate JSON report of test results."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_adapters": len(results),
                "passing": sum(1 for r in results.values() if r["status"] in ["passing", "passing_with_warnings"]),
                "failing": sum(1 for r in results.values() if r["status"] not in ["passing", "passing_with_warnings"]),
                "with_warnings": sum(1 for r in results.values() if r["warnings"]),
            },
            "adapters": results,
        }

        if output_path is None:
            output_path = f"adapter_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_file = Path(output_path)
        output_file.write_text(json.dumps(report, indent=2))

        print(f"\n📄 Report saved to: {output_file}")

        return report


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify datasource adapters")
    parser.add_argument(
        "--adapter",
        help="Test specific adapter (e.g., 'eybl', 'psal')"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test (health check only)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate JSON report"
    )

    args = parser.parse_args()

    tester = AdapterTester(quick=args.quick)

    print("=" * 70)
    print("🏀 Adapter Verification Utility")
    print("=" * 70)

    if args.quick:
        print("Mode: Quick (health check only)")
    else:
        print("Mode: Full (all tests)")

    if args.adapter:
        # Test specific adapter
        adapter_map = {
            "eybl": ("EYBL", EYBLDataSource, False),
            "psal": ("PSAL", PSALDataSource, False),
            "mn_hub": ("MN Hub", MNHubDataSource, False),
            "fiba_youth": ("FIBA Youth", FIBAYouthDataSource, True),
        }

        adapter_key = args.adapter.lower()
        if adapter_key in adapter_map:
            name, adapter_class, skip_search = adapter_map[adapter_key]
            result = await tester.test_adapter(name, adapter_class, skip_search)
            results = {name: result}
        else:
            print(f"❌ Unknown adapter: {args.adapter}")
            print(f"Available: {', '.join(adapter_map.keys())}")
            return

    else:
        # Test all adapters
        results = await tester.test_all_adapters()

    # Print summary
    tester.print_summary(results)

    # Generate report if requested
    if args.report:
        tester.generate_report(results)

    # Exit code
    failing = sum(1 for r in results.values() if r["status"] not in ["passing", "passing_with_warnings"])
    sys.exit(1 if failing > 0 else 0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(130)
