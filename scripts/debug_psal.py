#!/usr/bin/env python3
"""
PSAL Website Structure Analysis
"""

import asyncio
import httpx
from bs4 import BeautifulSoup


async def analyze_psal():
    """Analyze PSAL website structure."""

    base_url = "https://www.psal.org"
    leaders_url = f"{base_url}/sports/top-player.aspx?spCode=001"

    print(f"[...] Fetching {leaders_url}")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(leaders_url)
            print(f"[OK] Status: {response.status_code}")
            print(f"[OK] Content length: {len(response.text)} chars\n")

            if response.status_code != 200:
                print(f"[X] HTTP {response.status_code} - {response.reason_phrase}")
                print(f"[INFO] Response text (first 500 chars):")
                print(response.text[:500])
                return

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for tables
            tables = soup.find_all('table')
            print(f"[INFO] Found {len(tables)} <table> elements")

            if tables:
                for i, table in enumerate(tables, 1):
                    classes = table.get('class', [])
                    print(f"  Table {i}: class={classes}")

                    # Count rows
                    rows = table.find_all('tr')
                    print(f"           rows={len(rows)}")

                    # Show headers
                    if rows:
                        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                        print(f"           headers={headers[:10]}")

                        # Show first data row if exists
                        if len(rows) > 1:
                            data_cells = [td.get_text(strip=True) for td in rows[1].find_all('td')]
                            print(f"           first_row={data_cells[:10]}")
            else:
                print("  [!] NO <table> ELEMENTS FOUND\n")

            # Check page title
            title = soup.find('title')
            print(f"\n[INFO] Page title: {title.get_text(strip=True) if title else 'N/A'}")

            # Get body text (first 800 chars)
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator=' ', strip=True)
                print(f"\n[INFO] Body text (first 800 chars):")
                print(body_text[:800])

            # Check for error messages
            error_divs = soup.find_all('div', class_=lambda x: x and 'error' in str(x).lower())
            if error_divs:
                print(f"\n[!] Found {len(error_divs)} error divs:")
                for div in error_divs[:3]:
                    print(f"  {div.get_text(strip=True)}")

            # Check for "no data" messages
            no_data = soup.find_all(string=lambda x: x and ('no data' in x.lower() or 'not found' in x.lower() or 'no results' in x.lower()))
            if no_data:
                print(f"\n[!] Found 'no data' messages:")
                for msg in no_data[:5]:
                    print(f"  {msg.strip()}")

            # Check for JavaScript data loading
            print(f"\n[INFO] Checking for JavaScript/AJAX data loading...")
            scripts = soup.find_all('script')
            print(f"  Found {len(scripts)} <script> tags")

            # Look for API endpoints, AJAX calls, or data loading
            for script in scripts:
                script_text = script.get_text()
                if any(keyword in script_text for keyword in ['ajax', 'fetch', 'XMLHttpRequest', 'WEB_SERVICE', '.svc', 'json']):
                    print(f"\n[!] Found data loading script:")
                    # Show snippet
                    for line in script_text.split('\n')[:20]:
                        if line.strip() and any(kw in line for kw in ['ajax', 'fetch', 'WEB_SERVICE', '.svc']):
                            print(f"    {line.strip()}")

            # Show HTML snippet
            print(f"\n[DEBUG] First 1500 chars of HTML:")
            print("=" * 80)
            print(response.text[:1500])
            print("=" * 80)

        except httpx.HTTPError as e:
            print(f"[X] HTTP Error: {e}")
        except Exception as e:
            print(f"[X] Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_psal())
