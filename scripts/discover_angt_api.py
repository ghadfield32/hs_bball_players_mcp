"""
Discover ANGT API Endpoints

Use browser automation with network monitoring to find the actual
API endpoints that the ANGT stats page calls to load player data.

Usage:
    python scripts/discover_angt_api.py

Author: Claude Code
Date: 2025-11-16
Phase: HS-4 - ANGT API Discovery
"""

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))


async def discover_angt_api():
    """Monitor network requests to find API endpoints."""
    print("=" * 80)
    print("ANGT API ENDPOINT DISCOVERY")
    print("=" * 80)

    stats_url = "https://www.euroleaguebasketball.net/ngt/stats?size=1000&statistic=PIR&statisticMode=perGame"

    api_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Monitor network requests
        def handle_request(request):
            url = request.url
            # Look for API calls (JSON endpoints)
            if any(keyword in url.lower() for keyword in ['api', 'stats', 'players', 'data', '.json']):
                api_requests.append({
                    'url': url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'headers': dict(request.headers)
                })
                print(f"\nAPI REQUEST DETECTED:")
                print(f"  URL: {url}")
                print(f"  Method: {request.method}")
                print(f"  Type: {request.resource_type}")

        def handle_response(response):
            url = response.url
            if any(keyword in url.lower() for keyword in ['api', 'stats', 'players', 'data']) and response.status == 200:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    print(f"\nAPI RESPONSE (JSON):")
                    print(f"  URL: {url}")
                    print(f"  Status: {response.status}")
                    print(f"  Content-Type: {content_type}")

        page.on('request', handle_request)
        page.on('response', handle_response)

        print(f"\nLoading: {stats_url}")
        print("Monitoring network requests...\n")

        # Load page
        await page.goto(stats_url, wait_until="networkidle", timeout=60000)

        # Wait for potential AJAX requests
        print("\nWaiting 10 seconds for AJAX requests...")
        await asyncio.sleep(10)

        await browser.close()

    # Save results
    output_file = Path(__file__).parent.parent / "data" / "debug" / "angt_api_requests.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(api_requests, indent=2), encoding='utf-8')

    print("\n" + "=" * 80)
    print("API DISCOVERY COMPLETE")
    print("=" * 80)
    print(f"\nTotal API requests detected: {len(api_requests)}")
    print(f"Saved to: {output_file}")

    if api_requests:
        print("\n" + "=" * 80)
        print("API ENDPOINTS SUMMARY")
        print("=" * 80)
        for i, req in enumerate(api_requests, 1):
            print(f"\n{i}. {req['method']} {req['url']}")
    else:
        print("\n⚠️ NO API requests detected!")
        print("\nPossible reasons:")
        print("1. Stats data is embedded in initial page load (check __NEXT_DATA__)")
        print("2. API calls use different patterns (websockets, GraphQL, etc.)")
        print("3. Stats page structure changed")
        print("\nRecommendation: Check browser DevTools Network tab manually")


if __name__ == "__main__":
    asyncio.run(discover_angt_api())
