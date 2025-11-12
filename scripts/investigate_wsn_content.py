"""
Investigate WSN (Wisconsin Sports Network) Content - Phase 12.2

Earlier diagnostic found WSN website EXISTS (40k chars) contrary to "defunct" hypothesis.
This script investigates HTML structure to determine:
1. Does website have basketball content?
2. What's the page structure?
3. Why isn't adapter working if website exists?
4. What needs updating in parsing logic?
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup
from src.datasources.us.wsn import WSNDataSource
from src.utils.http_client import HTTPClient


async def investigate_wsn():
    """Investigate WSN website content and structure."""
    print("=" * 80)
    print("PHASE 12.2: WSN CONTENT INVESTIGATION")
    print("=" * 80)
    print("Known: Website exists (40,972 chars) - NOT defunct!")
    print("Goal: Determine why adapter isn't working\n")

    client = HTTPClient(source="wsn_investigation")
    adapter = None

    try:
        # STEP 1: Test main website
        print("[STEP 1] Testing Main Website")
        print("=" * 80)
        main_url = "https://www.wissports.net"
        print(f"Fetching: {main_url}")

        html = await client.get_text(main_url, use_cache=False, timeout=15)
        print(f"[OK] Fetched {len(html):,} characters")

        soup = BeautifulSoup(html, 'html.parser')

        # Analyze content
        title = soup.find('title')
        print(f"\nPage Title: {title.get_text() if title else 'NO TITLE'}")

        # Look for basketball indicators
        html_lower = html.lower()
        indicators = {
            "basketball": "basketball" in html_lower,
            "stats": "stats" in html_lower or "statistics" in html_lower,
            "player": "player" in html_lower,
            "team": "team" in html_lower,
            "schedule": "schedule" in html_lower or "scores" in html_lower,
            "game": "game" in html_lower,
        }

        print(f"\nContent Indicators:")
        for key, found in indicators.items():
            status = "✓" if found else "✗"
            print(f"  {status} {key}: {'Found' if found else 'Not found'}")

        # STEP 2: Find navigation/links
        print(f"\n[STEP 2] Analyzing Navigation")
        print("=" * 80)

        # Look for basketball-related links
        links = soup.find_all('a', href=True)
        basketball_links = [
            link for link in links
            if link['href'] and 'basketball' in link['href'].lower()
        ]

        print(f"Total links found: {len(links)}")
        print(f"Basketball-related links: {len(basketball_links)}")

        if basketball_links:
            print(f"\nBasketball Links (first 10):")
            for i, link in enumerate(basketball_links[:10], 1):
                href = link['href']
                text = link.get_text(strip=True)
                print(f"  {i}. {text[:50]:50} -> {href}")

        # STEP 3: Test basketball-specific URLs
        print(f"\n[STEP 3] Testing Basketball-Specific URLs")
        print("=" * 80)

        test_urls = [
            ("Basketball", "https://www.wissports.net/basketball"),
            ("Boys Basketball", "https://www.wissports.net/boys-basketball"),
            ("Basketball Stats", "https://www.wissports.net/basketball/stats"),
            ("Stats", "https://www.wissports.net/stats"),
        ]

        working_urls = []
        for name, url in test_urls:
            print(f"\nTesting: {name}")
            print(f"  URL: {url}")

            try:
                test_html = await client.get_text(url, use_cache=False, timeout=10)
                print(f"  [OK] Fetched {len(test_html):,} chars")

                test_soup = BeautifulSoup(test_html, 'html.parser')

                # Quick analysis
                tables = test_soup.find_all('table')
                stats_indicators = {
                    "tables": len(tables),
                    "has_stats": "stats" in test_html.lower(),
                    "has_player": "player" in test_html.lower(),
                    "has_ppg": "ppg" in test_html.lower() or "points" in test_html.lower(),
                }

                print(f"  Analysis:")
                print(f"    - Tables found: {stats_indicators['tables']}")
                print(f"    - Has 'stats': {stats_indicators['has_stats']}")
                print(f"    - Has 'player': {stats_indicators['has_player']}")
                print(f"    - Has scoring stats: {stats_indicators['has_ppg']}")

                if stats_indicators['tables'] > 0:
                    working_urls.append((name, url, test_html))
                    print(f"  [PROMISING] Has tables - likely has data!")

            except Exception as e:
                print(f"  [FAIL] {type(e).__name__}: {str(e)[:60]}")

        # STEP 4: Detailed table analysis for working URLs
        if working_urls:
            print(f"\n[STEP 4] Detailed Table Analysis")
            print("=" * 80)

            for name, url, html in working_urls[:2]:  # Analyze first 2 working URLs
                print(f"\n{name}: {url}")
                soup = BeautifulSoup(html, 'html.parser')
                tables = soup.find_all('table')

                print(f"  Found {len(tables)} table(s)")

                for i, table in enumerate(tables[:3], 1):  # First 3 tables
                    print(f"\n  Table #{i}:")

                    # Get table headers
                    headers = []
                    header_row = table.find('thead')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                    else:
                        # Try first row
                        first_row = table.find('tr')
                        if first_row:
                            headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]

                    if headers:
                        print(f"    Headers: {', '.join(headers[:10])}")  # First 10 headers
                    else:
                        print(f"    Headers: [Could not parse headers]")

                    # Count data rows
                    body = table.find('tbody') or table
                    rows = body.find_all('tr')
                    print(f"    Data rows: {len(rows)}")

                    # Sample first row
                    if rows:
                        first_row_data = [td.get_text(strip=True) for td in rows[0].find_all(['td', 'th'])]
                        if first_row_data:
                            print(f"    Sample row: {', '.join(first_row_data[:5])}")

        # STEP 5: Test current WSN adapter
        print(f"\n[STEP 5] Testing Current WSN Adapter")
        print("=" * 80)

        adapter = WSNDataSource()
        print(f"Adapter base URL: {adapter.base_url}")

        print(f"\nTrying adapter.search_players(limit=5)...")
        players = await adapter.search_players(limit=5)

        if players and len(players) > 0:
            print(f"[SUCCESS] Adapter found {len(players)} players!")
            for player in players:
                print(f"  - {player.full_name} ({player.school_name})")
        else:
            print(f"[ISSUE] Adapter found 0 players")
            print(f"Possible reasons:")
            print(f"  1. URL pattern incorrect (adapter looking at wrong page)")
            print(f"  2. Table selectors don't match HTML structure")
            print(f"  3. Parsing logic expects different column names")
            print(f"  4. Off-season - no data published")

        # STEP 6: Recommendations
        print(f"\n[STEP 6] Recommendations")
        print("=" * 80)

        if working_urls:
            print(f"✓ WSN website HAS basketball content")
            print(f"✓ Found {len(working_urls)} working basketball URLs")
            print(f"\nNext Steps:")
            print(f"  1. Update WSN adapter base_url if needed")
            print(f"  2. Update table selectors to match found structure")
            print(f"  3. Update column parsing to match header names")
            print(f"  4. Test with updated adapter")
        else:
            print(f"✗ Could not find basketball stats tables")
            print(f"\nNext Steps:")
            print(f"  1. Manual website inspection needed")
            print(f"  2. Check if stats behind login/paywall")
            print(f"  3. Consider alternative Wisconsin sources")

        print(f"\n{'=' * 80}")
        print(f"INVESTIGATION COMPLETE")
        print(f"{'=' * 80}")

    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()
        if adapter:
            await adapter.close()
        print(f"\n[OK] Cleanup complete")


if __name__ == "__main__":
    asyncio.run(investigate_wsn())
