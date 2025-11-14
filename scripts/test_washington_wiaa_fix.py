"""
Test Washington WIAA URL Fix

Verifies the updated URL structure works after research findings:
- Changed from www.wiaa.com to www.wpanetwork.com/wiaa/brackets
- Using /tournament/?sportid=3 (boys) or sportid=12 (girls) endpoint
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.washington_wiaa import WashingtonWIAADataSource


async def test_washington_wiaa():
    """Test Washington WIAA after URL structure fix."""
    print("\n" + "="*60)
    print("Testing Washington WIAA (after URL fix)")
    print("="*60)

    source = WashingtonWIAADataSource()
    print(f"Base URL: {source.base_url}")
    print(f"Classifications: {source.CLASSIFICATIONS}")

    # Test URL construction
    print("\n[URL Construction]")
    boys_url = source._build_bracket_url("4A", "Boys", 2025)
    girls_url = source._build_bracket_url("3A", "Girls", 2025)
    print(f"  Boys URL: {boys_url}")
    print(f"  Expected: https://www.wpanetwork.com/wiaa/brackets/tournament/?sportid=3")
    print(f"  Match: {boys_url == 'https://www.wpanetwork.com/wiaa/brackets/tournament/?sportid=3'}")
    print(f"\n  Girls URL: {girls_url}")
    print(f"  Expected: https://www.wpanetwork.com/wiaa/brackets/tournament/?sportid=12")
    print(f"  Match: {girls_url == 'https://www.wpanetwork.com/wiaa/brackets/tournament/?sportid=12'}")

    # Test health check
    print("\n[Health Check]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
        if is_healthy:
            print("  ✅ Washington WIAA fix SUCCESSFUL!")
        else:
            print("  ⚠️  Health check failed - may need HTML parsing update")
    except Exception as e:
        print(f"  Result: ERROR - {e}")
        print("  ⚠️  May need to update HTML parsing logic")

    # Test bracket fetch (will show if page structure works)
    print("\n[Bracket Fetch Test]")
    try:
        brackets = await source.get_tournament_brackets(season="2024-25", gender="Boys")
        print(f"  Games found: {len(brackets.get('games', []))}")
        print(f"  Teams found: {len(brackets.get('teams', []))}")
        if brackets.get('games'):
            print("  ✅ Successfully parsed tournament data!")
        else:
            print("  ⚠️  No games found - data may not be published yet OR parsing needs update")
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  ⚠️  HTML parsing may need to be updated for new page structure")


async def main():
    """Run Washington WIAA test."""
    await test_washington_wiaa()

    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("- If health check PASS: URL fix successful ✅")
    print("- If parsing errors: May need to update _parse_bracket_html() for new page structure")
    print("- If no data found: Tournament data may not be published yet (expected for Nov 2025)")


if __name__ == "__main__":
    asyncio.run(main())
