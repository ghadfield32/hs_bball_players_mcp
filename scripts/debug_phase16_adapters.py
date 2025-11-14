"""
Phase 16 Adapters Debug Script

Comprehensive debugging for Phase 16 adapters with detailed output.
Tests each adapter step-by-step to identify root causes of failures.

Date Context: November 12, 2025 - 2024-25 tournament data should be available.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.oregon_osaa import OregonOSAADataSource
from src.datasources.us.nevada_niaa import NevadaNIAADataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.vendors.fibalivestats_federation import FIBALiveStatsFederationDataSource


async def test_raw_http_request(url: str, adapter_name: str, test_user_agents: bool = True):
    """
    Test raw HTTP request to understand response.

    This helps us see:
    - What status code we get
    - What headers the server returns
    - Whether User-Agent makes a difference
    """
    print(f"\n{'='*80}")
    print(f"RAW HTTP TEST: {adapter_name}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Date Context: November 12, 2025 (2024-25 season data should exist)")

    # Test 1: Default httpx client (minimal User-Agent)
    print(f"\n[TEST 1] Default httpx client (minimal headers)")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            print(f"  Status Code: {response.status_code}")
            print(f"  Response Headers:")
            for key, value in response.headers.items():
                print(f"    {key}: {value}")
            print(f"  Content Length: {len(response.content)} bytes")
            if response.status_code == 200:
                print(f"  [SUCCESS] Got 200 OK")
            else:
                print(f"  [FAIL] Non-200 status")
                print(f"  Response preview (first 500 chars):")
                print(f"    {response.text[:500]}")
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")

    if not test_user_agents:
        return

    # Test 2: Browser User-Agent (Chrome)
    print(f"\n[TEST 2] Browser User-Agent (Chrome)")
    headers_chrome = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers_chrome)
            print(f"  Status Code: {response.status_code}")
            print(f"  Content Length: {len(response.content)} bytes")
            if response.status_code == 200:
                print(f"  [SUCCESS] Got 200 OK with browser User-Agent")
            else:
                print(f"  [FAIL] Non-200 status even with browser headers")
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")

    # Test 3: Search engine bot User-Agent (Googlebot)
    print(f"\n[TEST 3] Search engine bot User-Agent (Googlebot)")
    headers_bot = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers_bot)
            print(f"  Status Code: {response.status_code}")
            print(f"  Content Length: {len(response.content)} bytes")
            if response.status_code == 200:
                print(f"  [SUCCESS] Got 200 OK with bot User-Agent")
            else:
                print(f"  [FAIL] Non-200 status with bot headers")
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")


async def test_adapter_urls(name: str, source, url_builders: list):
    """
    Test URL construction for an adapter.

    Shows:
    - What URLs are being constructed
    - Whether URLs follow expected patterns
    - If URLs are season-appropriate
    """
    print(f"\n{'='*80}")
    print(f"URL CONSTRUCTION TEST: {name}")
    print(f"{'='*80}")

    for desc, build_func in url_builders:
        try:
            url = build_func()
            print(f"\n{desc}:")
            print(f"  URL: {url}")

            # Check if URL looks reasonable
            if "2024" in url or "2025" in url:
                print(f"  [OK] URL contains 2024/2025 season identifier")
            else:
                print(f"  [WARN] URL does not contain 2024/2025 season identifier")

        except Exception as e:
            print(f"\n{desc}:")
            print(f"  [ERROR] Failed to build URL: {e}")


async def debug_arizona_aia():
    """Debug Arizona AIA adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: Arizona AIA")
    print(f"# Expected: 2024-25 tournament brackets should be available")
    print(f"{'#'*80}")

    source = ArizonaAIADataSource()
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Conferences: {source.CONFERENCES}")

    # Test URL construction
    await test_adapter_urls(
        "Arizona AIA",
        source,
        [
            ("Boys 6A 2024-25", lambda: source._build_bracket_url("6A", "Boys", 2025)),
            ("Girls 5A 2024-25", lambda: source._build_bracket_url("5A", "Girls", 2025)),
        ]
    )

    # Test raw HTTP
    test_url = source._build_bracket_url("6A", "Boys", 2025)
    await test_raw_http_request(test_url, "Arizona AIA", test_user_agents=True)

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def debug_oregon_osaa():
    """Debug Oregon OSAA adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: Oregon OSAA")
    print(f"# Issue: 403 Forbidden")
    print(f"# Expected: 2024-25 tournament brackets should be available")
    print(f"{'#'*80}")

    source = OregonOSAADataSource()
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Classifications: {source.CLASSIFICATIONS}")

    # Test URL construction
    await test_adapter_urls(
        "Oregon OSAA",
        source,
        [
            ("JSON URL - Boys 6A 2024-25", lambda: source._build_json_bracket_url("6A", "Boys", 2025)),
            ("HTML URL - Boys 6A 2024-25", lambda: source._build_bracket_url("6A", "Boys", 2025)),
        ]
    )

    # Test raw HTTP on base URL first
    print(f"\n[TESTING BASE URL]")
    await test_raw_http_request(source.base_url, "Oregon OSAA (base)", test_user_agents=True)

    # Test JSON endpoint
    print(f"\n[TESTING JSON ENDPOINT]")
    json_url = source._build_json_bracket_url("6A", "Boys", 2025)
    await test_raw_http_request(json_url, "Oregon OSAA (JSON)", test_user_agents=True)

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def debug_nevada_niaa():
    """Debug Nevada NIAA adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: Nevada NIAA")
    print(f"# Issue: 403 Forbidden")
    print(f"# Expected: 2024-25 tournament brackets should be available")
    print(f"# Special: Requires pdfplumber for PDF parsing")
    print(f"{'#'*80}")

    source = NevadaNIAADataSource()
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Divisions: {source.DIVISIONS}")
    print(f"  PDF Cache Size: {len(source.pdf_cache)}")

    # Check pdfplumber availability
    try:
        import pdfplumber
        print(f"  pdfplumber: INSTALLED (version: {pdfplumber.__version__})")
    except ImportError:
        print(f"  pdfplumber: NOT INSTALLED (PDF parsing will fail)")

    # Test URL construction
    await test_adapter_urls(
        "Nevada NIAA",
        source,
        [
            ("Boys 5A 2024-25", lambda: source._build_bracket_url("5A", "Boys", 2025)),
            ("Girls 4A 2024-25", lambda: source._build_bracket_url("4A", "Girls", 2025)),
        ]
    )

    # Test raw HTTP on base URL first
    print(f"\n[TESTING BASE URL]")
    await test_raw_http_request(source.base_url, "Nevada NIAA (base)", test_user_agents=True)

    # Test bracket URL
    print(f"\n[TESTING BRACKET URL]")
    bracket_url = source._build_bracket_url("5A", "Boys", 2025)
    await test_raw_http_request(bracket_url, "Nevada NIAA (bracket)", test_user_agents=True)

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def debug_washington_wiaa():
    """Debug Washington WIAA adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: Washington WIAA")
    print(f"# Expected: 2024-25 tournament brackets should be available")
    print(f"{'#'*80}")

    source = WashingtonWIAADataSource()
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Classifications: {source.CLASSIFICATIONS}")

    # Test URL construction
    await test_adapter_urls(
        "Washington WIAA",
        source,
        [
            ("Boys 4A 2024-25", lambda: source._build_bracket_url("4A", "Boys", 2025)),
            ("Girls 3A 2024-25", lambda: source._build_bracket_url("3A", "Girls", 2025)),
        ]
    )

    # Test raw HTTP
    test_url = source._build_bracket_url("4A", "Boys", 2025)
    await test_raw_http_request(test_url, "Washington WIAA", test_user_agents=True)

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def debug_idaho_ihsaa():
    """Debug Idaho IHSAA adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: Idaho IHSAA")
    print(f"# Expected: 2024-25 tournament brackets should be available")
    print(f"{'#'*80}")

    source = IdahoIHSAADataSource()
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Classifications: {source.CLASSIFICATIONS}")

    # Test URL construction
    await test_adapter_urls(
        "Idaho IHSAA",
        source,
        [
            ("Boys 6A 2024-25", lambda: source._build_bracket_url("6A", "Boys", 2025)),
            ("Girls 5A 2024-25", lambda: source._build_bracket_url("5A", "Girls", 2025)),
        ]
    )

    # Test raw HTTP
    test_url = source._build_bracket_url("6A", "Boys", 2025)
    await test_raw_http_request(test_url, "Idaho IHSAA", test_user_agents=True)

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def debug_fiba_federation():
    """Debug FIBA Federation adapter."""
    print(f"\n{'#'*80}")
    print(f"# DEBUGGING: FIBA Federation (Egypt)")
    print(f"# Issue: DNS resolution failure for livestats.fiba.basketball")
    print(f"# Expected: FIBA API should be accessible")
    print(f"{'#'*80}")

    source = FIBALiveStatsFederationDataSource(federation_code="EGY", season="2024-25")
    print(f"\nAdapter Info:")
    print(f"  Source Name: {source.source_name}")
    print(f"  Federation Code: {source.federation_code}")
    print(f"  Season: {source.season}")

    # Check if BASE_API_URL attribute exists
    if hasattr(source, 'BASE_API_URL'):
        print(f"  Base API URL: {source.BASE_API_URL}")
        base_api = source.BASE_API_URL
    else:
        print(f"  [WARN] No BASE_API_URL attribute found")
        base_api = None

    # Try to find base URL
    if hasattr(source, 'base_url'):
        print(f"  Base URL: {source.base_url}")
        base_url = source.base_url
    else:
        base_url = None

    # Test different FIBA domains
    print(f"\n[TESTING FIBA DOMAINS]")
    domains_to_test = [
        "https://livestats.fiba.basketball",
        "https://www.fiba.basketball",
        "https://fiba.basketball",
        "https://api.fiba.basketball",
        "https://fiba3x3.com",
    ]

    for domain in domains_to_test:
        print(f"\n  Testing: {domain}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(domain)
                print(f"    Status: {response.status_code}")
                print(f"    [SUCCESS] Domain resolves")
        except httpx.ConnectError as e:
            print(f"    [DNS ERROR] {e}")
        except Exception as e:
            print(f"    [ERROR] {type(e).__name__}: {e}")

    # Test adapter health check
    print(f"\n[ADAPTER HEALTH CHECK]")
    try:
        is_healthy = await source.health_check()
        print(f"  Result: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"  Result: ERROR - {e}")


async def main():
    """Run all debug tests."""
    print("="*80)
    print("PHASE 16 ADAPTERS - COMPREHENSIVE DEBUG")
    print(f"Date: November 12, 2025")
    print(f"Context: 2024-25 basketball season data should be available")
    print("="*80)

    # Debug each adapter
    await debug_arizona_aia()
    await asyncio.sleep(2)

    await debug_oregon_osaa()
    await asyncio.sleep(2)

    await debug_nevada_niaa()
    await asyncio.sleep(2)

    await debug_washington_wiaa()
    await asyncio.sleep(2)

    await debug_idaho_ihsaa()
    await asyncio.sleep(2)

    await debug_fiba_federation()

    print(f"\n{'='*80}")
    print("DEBUG COMPLETE")
    print(f"{'='*80}")
    print("\nNext Steps Based on Findings:")
    print("1. Review status codes and error messages above")
    print("2. Check if User-Agent headers make a difference for 403 errors")
    print("3. Verify FIBA domain is correct")
    print("4. Check if 404 errors are due to missing 2024-25 data or incorrect URLs")


if __name__ == "__main__":
    asyncio.run(main())
