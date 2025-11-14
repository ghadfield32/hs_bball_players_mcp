"""
Test 301 Redirect Fixes

Quick test to verify Arizona AIA and Idaho IHSAA now work after removing www.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource


async def test_arizona():
    """Test Arizona AIA after 301 fix."""
    print("\n" + "="*60)
    print("Testing Arizona AIA (after removing www)")
    print("="*60)

    source = ArizonaAIADataSource()
    print(f"Base URL: {source.base_url}")

    # Test health check
    print("\n[Health Check]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")

    # Test bracket URL construction
    print("\n[URL Construction]")
    url = source._build_bracket_url("6A", "Boys", 2025)
    print(f"  URL: {url}")
    print(f"  Expected: https://aiaonline.org/sports/basketball/brackets/2025/boys/6a")


async def test_idaho():
    """Test Idaho IHSAA after 301 fix."""
    print("\n" + "="*60)
    print("Testing Idaho IHSAA (after removing www)")
    print("="*60)

    source = IdahoIHSAADataSource()
    print(f"Base URL: {source.base_url}")

    # Test health check
    print("\n[Health Check]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")

    # Test bracket URL construction
    print("\n[URL Construction]")
    url = source._build_bracket_url("6A", "Boys", 2025)
    print(f"  URL: {url}")
    print(f"  Expected: https://idhsaa.org/sports/basketball/brackets/2025/boys/6a")


async def main():
    """Run 301 fix tests."""
    await test_arizona()
    await test_idaho()

    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\nIf both health checks PASS, 301 fixes are working!")


if __name__ == "__main__":
    asyncio.run(main())
