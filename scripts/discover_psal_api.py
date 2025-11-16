"""
PSAL API Discovery Script - Phase HS-5

Discovers and tests PSAL's internal API endpoints.
The PSAL website uses a web service at https://www.psal.org/SportDisplay.svc

Usage:
    python scripts/discover_psal_api.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-5 - PSAL API Reverse Engineering
"""

import asyncio
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


async def discover_wsdl():
    """Check if the web service exposes a WSDL definition."""
    print("=" * 80)
    print("STEP 1: Check for WSDL Definition")
    print("=" * 80)

    wsdl_urls = [
        "https://www.psal.org/SportDisplay.svc?wsdl",
        "https://www.psal.org/SportDisplay.svc?WSDL",
        "https://www.psal.org/SportDisplay.svc/wsdl",
    ]

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in wsdl_urls:
            print(f"\nTrying: {url}")
            try:
                response = await client.get(url)
                print(f"  Status: {response.status_code}")

                if response.status_code == 200:
                    if "wsdl" in response.text.lower() or "soap" in response.text.lower():
                        print("  [SUCCESS] Found WSDL definition!")
                        # Save WSDL
                        with open("data/debug/psal_service.wsdl", "w", encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"  Saved to: data/debug/psal_service.wsdl")
                        return response.text

            except Exception as e:
                print(f"  Error: {e}")

    print("\n[INFO] No WSDL found - may be a REST API")
    return None


async def analyze_javascript():
    """Analyze the Top_Player.js JavaScript file for API calls."""
    print("\n" + "=" * 80)
    print("STEP 2: Analyze JavaScript for API Calls")
    print("=" * 80)

    js_url = "https://www.psal.org/scripts/Top_Players/Top_Player.js"
    print(f"\nFetching: {js_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(js_url)

            if response.status_code == 200:
                print(f"Status: {response.status_code} OK")

                js_content = response.text

                # Save JavaScript file
                with open("data/debug/psal_top_player.js", "w", encoding='utf-8') as f:
                    f.write(js_content)
                print(f"Saved to: data/debug/psal_top_player.js")

                # Look for API endpoint patterns
                print("\nSearching for API patterns...")

                import re

                # Common patterns
                ajax_calls = re.findall(r'ajax.*?url.*?["\']([^"\']+)["\']', js_content, re.IGNORECASE | re.DOTALL)
                fetch_calls = re.findall(r'fetch\(["\']([^"\']+)["\']', js_content)
                service_calls = re.findall(r'SportDisplay\.svc/([^"\'\s]+)', js_content)

                if ajax_calls:
                    print(f"\nFound {len(ajax_calls)} AJAX URL(s):")
                    for url in set(ajax_calls):
                        print(f"  - {url}")

                if fetch_calls:
                    print(f"\nFound {len(fetch_calls)} Fetch call(s):")
                    for url in set(fetch_calls):
                        print(f"  - {url}")

                if service_calls:
                    print(f"\nFound {len(service_calls)} SportDisplay.svc endpoint(s):")
                    for endpoint in set(service_calls):
                        print(f"  - /SportDisplay.svc/{endpoint}")

                return js_content

            else:
                print(f"Status: {response.status_code} - JavaScript file not found")
                return None

    except Exception as e:
        print(f"Error: {e}")
        return None


async def test_common_endpoints():
    """Test common API endpoint patterns."""
    print("\n" + "=" * 80)
    print("STEP 3: Test Common API Endpoints")
    print("=" * 80)

    base_url = "https://www.psal.org/SportDisplay.svc"

    # Common endpoint patterns for sports stats APIs
    endpoints = [
        # REST-style
        "/GetTopPlayers",
        "/GetStatLeaders",
        "/GetPlayerStats",
        "/GetSeasonLeaders",
        "/GetLeaderboard",
        "/leaders",
        "/stats",
        "/players",
        # SOAP-style
        "/GetTopPlayersJson",
        "/GetStandingsJson",
        "/GetStatLeadersJson",
        # Parameter variations
        "/GetTopPlayers?spCode=001",  # Basketball code
        "/GetStatLeaders?spCode=001&season=2024",
    ]

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\nTrying: {url}")

            try:
                # Try GET
                response = await client.get(url)
                print(f"  GET Status: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"  Content-Type: {content_type}")

                    if 'json' in content_type:
                        print("  [SUCCESS] JSON response found!")
                        data = response.json()
                        print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                        # Save response
                        filename = endpoint.replace('/', '_').replace('?', '_') + '.json'
                        with open(f"data/debug/psal_api{filename}", "w") as f:
                            json.dump(data, f, indent=2)
                        print(f"  Saved to: data/debug/psal_api{filename}")

                elif response.status_code == 405:
                    # Method not allowed - try POST
                    print(f"  GET not allowed, trying POST...")
                    post_response = await client.post(url)
                    print(f"  POST Status: {post_response.status_code}")

            except Exception as e:
                print(f"  Error: {e}")

            await asyncio.sleep(0.5)  # Be polite


async def test_basketball_specific():
    """Test basketball-specific endpoints."""
    print("\n" + "=" * 80)
    print("STEP 4: Test Basketball-Specific Endpoints")
    print("=" * 80)

    # Basketball sport code is 001 (from the HTML)
    sport_code = "001"
    season = "2024-25"

    print(f"\nTesting with:")
    print(f"  Sport Code: {sport_code} (Basketball)")
    print(f"  Season: {season}")

    base_url = "https://www.psal.org"

    # Test if there's a JSON version of the leaders page
    test_urls = [
        f"{base_url}/SportDisplay.svc/GetLeaders/{sport_code}",
        f"{base_url}/SportDisplay.svc/GetTopPlayers/{sport_code}",
        f"{base_url}/api/sports/{sport_code}/leaders",
        f"{base_url}/api/sports/{sport_code}/stats",
        f"{base_url}/services/stats/leaders/{sport_code}",
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in test_urls:
            print(f"\nTrying: {url}")
            try:
                response = await client.get(url)
                print(f"  Status: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        print(f"  [SUCCESS] Found JSON endpoint!")
                        data = response.json()
                        print(f"  Data preview: {str(data)[:200]}...")
                        return data

            except Exception as e:
                print(f"  Error: {e}")


async def inspect_network_trace():
    """Provide guidance for manual network trace."""
    print("\n" + "=" * 80)
    print("STEP 5: Manual Network Trace Instructions")
    print("=" * 80)

    print("""
If automated discovery didn't find the API, perform manual network trace:

1. Open https://www.psal.org/sports/top-player.aspx?spCode=001 in Chrome

2. Open DevTools (F12) -> Network tab

3. Filter by XHR or Fetch

4. Refresh the page and watch for API calls

5. Look for calls to:
   - SportDisplay.svc/*
   - Any endpoints with JSON responses
   - Calls with spCode=001 parameter

6. Right-click on the API call -> Copy -> Copy as cURL

7. Paste the cURL command here for conversion to Python

Common patterns to look for:
   - POST requests with JSON payloads
   - GET requests with query parameters
   - Headers: Content-Type: application/json
   - Response: JSON with player data
""")


async def main():
    """Run PSAL API discovery."""
    print("PSAL API DISCOVERY - Phase HS-5")
    print("=" * 80)
    print("\nInvestigating PSAL's internal API for player statistics")
    print("Base URL: https://www.psal.org/SportDisplay.svc")

    # Step 1: Check for WSDL
    wsdl = await discover_wsdl()

    # Step 2: Analyze JavaScript
    js_content = await analyze_javascript()

    # Step 3: Test common endpoints
    await test_common_endpoints()

    # Step 4: Test basketball-specific endpoints
    await test_basketball_specific()

    # Step 5: Manual trace instructions
    await inspect_network_trace()

    print("\n" + "=" * 80)
    print("API DISCOVERY COMPLETE")
    print("=" * 80)
    print("\nCheck data/debug/ for:")
    print("  - psal_service.wsdl (if WSDL found)")
    print("  - psal_top_player.js (JavaScript analysis)")
    print("  - psal_api_*.json (any discovered API responses)")
    print("\nIf no API found, will implement browser automation instead.")


if __name__ == "__main__":
    asyncio.run(main())
