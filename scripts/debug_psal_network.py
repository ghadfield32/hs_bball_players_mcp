#!/usr/bin/env python3
"""
PSAL Website Network Traffic Analysis
Monitors network requests to see if SportDisplay.svc is being called
"""

import asyncio
from playwright.async_api import async_playwright


async def analyze_psal_network():
    """Analyze PSAL website network traffic."""

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"

    print(f"[...] Launching browser for {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Track network requests
        requests = []
        responses = []

        async def log_request(request):
            requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type,
            })
            if 'SportDisplay.svc' in request.url or 'json' in request.url.lower():
                print(f"[→] REQUEST: {request.method} {request.url}")

        async def log_response(response):
            responses.append({
                'url': response.url,
                'status': response.status,
            })
            if 'SportDisplay.svc' in response.url or 'json' in response.url.lower():
                print(f"[←] RESPONSE: {response.status} {response.url}")
                # Try to get response body
                try:
                    body = await response.text()
                    print(f"    Body (first 500 chars): {body[:500]}")
                except:
                    print(f"    (could not read body)")

        page.on('request', log_request)
        page.on('response', log_response)

        print(f"[...] Navigating to page...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"[OK] Page loaded (network idle)")

            # Wait additional time
            print(f"[...] Waiting 8 seconds for any delayed AJAX calls...")
            await page.wait_for_timeout(8000)

            print(f"\n[INFO] Total requests: {len(requests)}")
            print(f"[INFO] Total responses: {len(responses)}")

            # Filter for API-like requests
            api_requests = [r for r in requests if 'api' in r['url'].lower() or 'svc' in r['url'].lower() or 'json' in r['url'].lower() or r['resource_type'] == 'xhr']
            print(f"\n[INFO] API/XHR/JSON requests: {len(api_requests)}")
            for req in api_requests:
                print(f"  {req['method']} {req['url']} (type: {req['resource_type']})")

            # Check for SportDisplay.svc specifically
            sport_display_requests = [r for r in requests if 'SportDisplay.svc' in r['url']]
            print(f"\n[INFO] SportDisplay.svc requests: {len(sport_display_requests)}")
            if sport_display_requests:
                for req in sport_display_requests:
                    print(f"  {req}")
            else:
                print(f"  [!] NO requests to SportDisplay.svc found!")

            # Check final page state
            tables = await page.locator('table').all()
            print(f"\n[INFO] Final state: {len(tables)} tables on page")

        except Exception as e:
            print(f"\n[X] Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()
            print("\n[OK] Browser closed")


if __name__ == "__main__":
    asyncio.run(analyze_psal_network())
