"""
Test Washington WIAA Final URL Fix

Tests the corrected tournament.php endpoint.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.washington_wiaa import WashingtonWIAADataSource


async def test_washington_wiaa_final():
    """Test Washington WIAA with corrected URL."""
    print("\n" + "="*60)
    print("Testing Washington WIAA (Final URL Fix)")
    print("="*60)

    source = WashingtonWIAADataSource()
    print(f"Base URL: {source.base_url}")

    # Test URL construction
    print("\n[URL Construction]")
    url = source._build_bracket_url("4A", "Boys", 2025)
    print(f"  Generated URL: {url}")
    print(f"  Expected: https://www.wpanetwork.com/wiaa/brackets/tournament.php")
    print(f"  Match: {url == 'https://www.wpanetwork.com/wiaa/brackets/tournament.php'}")

    # Test raw HTTP access
    print("\n[Direct HTTP Test]")
    try:
        status, content, headers = await source.http_get(url, timeout=10.0)
        print(f"  Status: {status}")
        print(f"  Content Length: {len(content)} bytes")
        if status == 200:
            print("  [SUCCESS] Tournament page is accessible!")
            # Show content type
            content_type = headers.get('content-type', 'unknown')
            print(f"  Content-Type: {content_type}")
            # Check if content exists
            if len(content) > 100:
                print("  [OK] Page has content (not empty)")
            else:
                print("  [WARN] Page appears empty or minimal")
        else:
            print(f"  [FAIL] Non-200 status")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # Test health check
    print("\n[Health Check]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")

    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_washington_wiaa_final())
