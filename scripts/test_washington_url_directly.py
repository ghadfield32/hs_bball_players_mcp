"""
Test Washington WIAA Tournament URL Directly

Tests the actual tournament endpoint to see if it's accessible.
"""

import asyncio
import httpx


async def test_urls():
    """Test Washington WIAA URLs directly."""
    print("\n" + "="*70)
    print("Testing Washington WIAA URLs (Direct HTTP Test)")
    print("="*70)

    urls = [
        "https://www.wpanetwork.com/wiaa/brackets",
        "https://www.wpanetwork.com/wiaa/brackets/",
        "https://www.wpanetwork.com/wiaa/brackets/tournament/?sportid=3",
        "https://www.wpanetwork.com/wiaa/brackets/tournament.php",
    ]

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            print(f"\n[Testing] {url}")
            try:
                response = await client.get(url)
                print(f"  Status: {response.status_code}")
                print(f"  Content Length: {len(response.content)} bytes")
                if response.status_code == 200:
                    print("  [SUCCESS] URL is accessible")
                    # Show first 500 chars to understand page structure
                    text = response.text[:500]
                    print(f"  Preview: {text[:200]}...")
                elif response.status_code == 403:
                    print("  [FAIL] 403 Forbidden - Site blocking automated requests")
                elif response.status_code == 404:
                    print("  [FAIL] 404 Not Found - URL doesn't exist")
                else:
                    print(f"  [WARN] Unexpected status code")
            except Exception as e:
                print(f"  [ERROR] {type(e).__name__}: {e}")

    print("\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_urls())
