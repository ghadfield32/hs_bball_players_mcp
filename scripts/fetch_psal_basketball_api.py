"""
Fetch PSAL Basketball-Specific JavaScript

Downloads and analyzes the basketball-specific JS file that contains
the actual API calls for player statistics.

Usage:
    python scripts/fetch_psal_basketball_api.py

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import json
import re

import httpx


async def fetch_basketball_js():
    """Fetch the basketball-specific JavaScript file."""
    url = "https://www.psal.org/scripts/Top_Players/Basketball.js"
    print(f"Fetching: {url}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)

        if response.status_code == 200:
            print(f"Status: {response.status_code} OK\n")

            js_content = response.text

            # Save the file
            with open("data/debug/psal_basketball.js", "w", encoding='utf-8') as f:
                f.write(js_content)
            print(f"Saved to: data/debug/psal_basketball.js\n")

            # Extract API calls
            print("=" * 80)
            print("Analyzing API Calls...")
            print("=" * 80 + "\n")

            # Find all AJAX/fetch calls
            ajax_patterns = [
                r'\.getJSON\(["\']([^"\']+)["\']',
                r'\.get\(["\']([^"\']+)["\']',
                r'\.post\(["\']([^"\']+)["\']',
                r'ajax\([^{]*url[:\s]*["\']([^"\']+)["\']',
            ]

            all_urls = set()
            for pattern in ajax_patterns:
                matches = re.findall(pattern, js_content)
                all_urls.update(matches)

            print("Found API URLs:")
            for url in sorted(all_urls):
                print(f"  - {url}")

            # Find function calls with parameters
            print("\n" + "=" * 80)
            print("Searching for GetTopPlayers function...")
            print("=" * 80 + "\n")

            # Look for GetTopPlayers function definition
            get_top_players = re.search(
                r'GetTopPlayers[:\s]*function\s*\([^)]*\)\s*{([^}]+)}',
                js_content,
                re.DOTALL
            )

            if get_top_players:
                print("Found GetTopPlayers function!")
                print(f"\nFunction body:\n{get_top_players.group(1)[:500]}...")
            else:
                print("GetTopPlayers function not found - searching for alternatives...")

                # Try to find any function that fetches player data
                functions = re.findall(
                    r'(Get\w+)[:\s]*function\s*\([^)]*\)',
                    js_content
                )
                print(f"\nFound {len(set(functions))} Get* functions:")
                for func in sorted(set(functions)):
                    print(f"  - {func}")

            return js_content

        else:
            print(f"Status: {response.status_code} - Failed to fetch")
            return None


async def test_discovered_endpoint():
    """Test any discovered API endpoints."""
    print("\n" + "=" * 80)
    print("Testing Discovered Endpoints")
    print("=" * 80 + "\n")

    # Common basketball API endpoint pattern
    test_urls = [
        "https://www.psal.org/SportDisplay.svc/GetSportStatisticalCategories?csports='001'",
        "https://www.psal.org/SportDisplay.svc/GetSportLeague?csports='001'",
        "https://www.psal.org/SportDisplay.svc/GetSportLeague?csports='001'&season=2025",
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in test_urls:
            print(f"Testing: {url}")
            try:
                response = await client.get(url)
                print(f"  Status: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"  Content-Type: {content_type}")

                    if 'json' in content_type:
                        data = response.json()
                        print(f"  [SUCCESS] JSON response!")
                        print(f"  Data: {json.dumps(data, indent=2)[:500]}...")

                        # Save response
                        filename = url.split('/')[-1].split('?')[0] + '.json'
                        with open(f"data/debug/{filename}", "w") as f:
                            json.dump(data, f, indent=2)
                        print(f"  Saved to: data/debug/{filename}")
                    else:
                        print(f"  Response length: {len(response.text)} chars")
                        if len(response.text) < 500:
                            print(f"  Response: {response.text}")

            except Exception as e:
                print(f"  Error: {e}")

            print()


async def main():
    """Main function."""
    print("PSAL BASKETBALL API DISCOVERY")
    print("=" * 80 + "\n")

    # Fetch basketball.js
    js_content = await fetch_basketball_js()

    if js_content:
        # Test discovered endpoints
        await test_discovered_endpoint()

        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Review data/debug/psal_basketball.js manually")
        print("2. Look for function calls with API endpoints")
        print("3. Test API endpoints with proper parameters")
        print("4. If API works, implement API-based adapter")
        print("5. Otherwise, use browser automation like EYBL")


if __name__ == "__main__":
    asyncio.run(main())
