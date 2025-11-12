"""
Debug Adapter HTML Structures

This script inspects the actual HTML structure of the 3 problematic adapters
to understand why their selectors are failing. It does NOT modify any code.

Purpose:
- Fetch actual HTML from each website
- Inspect what elements exist
- Test different selector patterns
- Log detailed findings for diagnosis

Adapters to debug:
1. 3SSB - Stats table selector not finding data
2. MN Hub - Selector timeout (table element not found)
3. PSAL - Silent failure (no data returned)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup
from src.utils.http_client import HTTPClient
from src.utils.browser_client import BrowserClient
from src.config import Settings


async def debug_3ssb():
    """Debug 3SSB HTML structure."""
    print("\n" + "="*80)
    print("DEBUGGING: 3SSB (Adidas 3SSB)")
    print("="*80)

    url = "https://adidas3ssb.com/stats"
    print(f"\n[1] Fetching HTML from: {url}")

    try:
        client = HTTPClient(source="debug_3ssb")

        html = await client.get_text(url, use_cache=False)  # No cache for debug
        print(f"[OK] Fetched {len(html)} characters")

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Debug: What's on the page?
        print(f"\n[2] Inspecting page structure...")

        # Check title
        title = soup.find("title")
        print(f"   Page title: {title.get_text() if title else 'NO TITLE FOUND'}")

        # Check for any tables
        tables = soup.find_all("table")
        print(f"\n[3] Found {len(tables)} <table> elements")

        if tables:
            for idx, table in enumerate(tables):
                print(f"\n   Table #{idx + 1}:")
                # Check table classes
                table_classes = table.get("class", [])
                print(f"      Classes: {table_classes if table_classes else 'NONE'}")

                # Check table ID
                table_id = table.get("id")
                print(f"      ID: {table_id if table_id else 'NONE'}")

                # Count rows
                rows = table.find_all("tr")
                print(f"      Rows: {len(rows)}")

                # Check first row (header)
                if rows:
                    first_row = rows[0]
                    headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
                    print(f"      Header: {headers[:10]}...")  # First 10 columns

                # Check parent containers
                parent = table.find_parent()
                parent_classes = parent.get("class", []) if parent else []
                print(f"      Parent: <{parent.name if parent else 'NONE'}> classes={parent_classes}")
        else:
            print("   [WARN] NO TABLES FOUND!")

        # Check for divs with class containing "stats", "players", "roster"
        print(f"\n[4] Searching for divs with stats-related classes...")
        stats_divs = soup.find_all("div", class_=lambda x: x and any(keyword in x.lower() for keyword in ["stats", "players", "roster", "leaderboard"]))
        print(f"   Found {len(stats_divs)} stats-related divs")

        for div in stats_divs[:5]:  # First 5
            div_classes = div.get("class", [])
            print(f"      <div class=\"{' '.join(div_classes)}\">")
            # Check if contains table
            nested_table = div.find("table")
            print(f"         Contains table: {nested_table is not None}")

        # Check for JavaScript-rendered content indicators
        print(f"\n[5] Checking for JavaScript indicators...")
        scripts = soup.find_all("script")
        print(f"   Found {len(scripts)} <script> tags")

        # Look for popular frameworks
        framework_keywords = ["angular", "react", "vue", "next.js", "gatsby"]
        for script in scripts:
            script_src = script.get("src", "")
            script_content = script.string or ""

            for keyword in framework_keywords:
                if keyword in script_src.lower() or keyword in script_content.lower():
                    print(f"   [FOUND] Framework detected: {keyword}")
                    break

        # Check for "no-js" or client-side rendering messages
        no_js_msg = soup.find(string=lambda text: text and "javascript" in text.lower())
        if no_js_msg:
            print(f"   [WARN] Found JS-required message: {no_js_msg[:100]}...")

        # Summary
        print(f"\n[6] SUMMARY - 3SSB")
        print(f"   Tables found: {len(tables)}")
        print(f"   Stats-related divs: {len(stats_divs)}")
        print(f"   Likely JS-rendered: {len(scripts) > 10}")

        if len(tables) == 0:
            print(f"\n   [DIAGNOSIS] NO TABLES FOUND")
            print(f"   Possible causes:")
            print(f"      1. Page requires JavaScript rendering (needs Playwright)")
            print(f"      2. URL structure has changed")
            print(f"      3. Off-season (no data published)")
            print(f"   Recommendation: Test with browser automation")

        await client.close()

    except Exception as e:
        print(f"[ERROR] Failed to fetch 3SSB HTML: {e}")
        import traceback
        traceback.print_exc()


async def debug_mn_hub():
    """Debug MN Hub HTML structure."""
    print("\n" + "="*80)
    print("DEBUGGING: MN Hub (Minnesota Basketball Hub)")
    print("="*80)

    # Determine current season
    from datetime import datetime
    now = datetime.now()
    season_year = now.year if now.month >= 11 else now.year - 1
    season_str = f"{season_year}-{str(season_year + 1)[-2:]}"

    url = f"https://stats.mnbasketballhub.com/{season_str}-boys-basketball-stat-leaderboards"
    print(f"\n[1] Fetching HTML from: {url}")
    print(f"   Season: {season_str}")

    try:
        settings = Settings()
        browser = BrowserClient(
            settings=settings,
            timeout=60000,  # 60 second timeout for debug
            headless=True
        )

        # Test 1: Standard HTML fetch (will likely fail)
        print(f"\n[TEST 1] Standard HTTP fetch (no JS)...")
        client = HTTPClient(source="debug_mn_hub")
        html_nojs = await client.get_text(url, use_cache=False)
        print(f"   Fetched {len(html_nojs)} characters")

        soup_nojs = BeautifulSoup(html_nojs, "html.parser")
        tables_nojs = soup_nojs.find_all("table")
        print(f"   Tables found (no JS): {len(tables_nojs)}")

        # Check for Angular app root
        ng_app = soup_nojs.find("app-root") or soup_nojs.find(lambda tag: tag.name and "app-" in tag.name)
        print(f"   Angular app root found: {ng_app.name if ng_app else 'NONE'}")

        await client.close()

        # Test 2: Browser automation (should work)
        print(f"\n[TEST 2] Browser automation (with JS)...")
        html_js = await browser.get_rendered_html(
            url=url,
            wait_for="table",
            wait_timeout=60000,
            wait_for_network_idle=True
        )
        print(f"   Fetched {len(html_js)} characters")

        soup_js = BeautifulSoup(html_js, "html.parser")
        tables_js = soup_js.find_all("table")
        print(f"   Tables found (with JS): {len(tables_js)}")

        if tables_js:
            for idx, table in enumerate(tables_js):
                print(f"\n   Table #{idx + 1}:")
                table_classes = table.get("class", [])
                print(f"      Classes: {table_classes if table_classes else 'NONE'}")

                rows = table.find_all("tr")
                print(f"      Rows: {len(rows)}")

                if rows:
                    first_row = rows[0]
                    headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
                    print(f"      Headers: {headers[:10]}...")

                    # Check second row (data)
                    if len(rows) > 1:
                        second_row = rows[1]
                        cells = [td.get_text(strip=True) for td in second_row.find_all(["td", "th"])]
                        print(f"      Sample data: {cells[:10]}...")

        # Check for "no data" messages
        no_data_msg = soup_js.find(string=lambda text: text and ("no data" in text.lower() or "no stats" in text.lower() or "coming soon" in text.lower()))
        if no_data_msg:
            print(f"\n   [WARN] No data message found: {no_data_msg[:100]}...")

        # Summary
        print(f"\n[3] SUMMARY - MN Hub")
        print(f"   Tables (no JS): {len(tables_nojs)}")
        print(f"   Tables (with JS): {len(tables_js)}")
        print(f"   Angular app: {ng_app.name if ng_app else 'Not detected'}")

        if len(tables_nojs) == 0 and len(tables_js) > 0:
            print(f"\n   [DIAGNOSIS] JS RENDERING REQUIRED")
            print(f"   Current adapter uses browser automation: CORRECT APPROACH")
            if no_data_msg:
                print(f"   Issue: Off-season (no data published yet)")
            elif len(tables_js) == 0:
                print(f"   Issue: Timeout too short OR wrong season URL")
            else:
                print(f"   Issue: Unknown - adapter should be working!")

        # Clean up browser (singleton, but good practice)
        # await browser.close()  # Don't close singleton

    except Exception as e:
        print(f"[ERROR] Failed to debug MN Hub: {e}")
        import traceback
        traceback.print_exc()


async def debug_psal():
    """Debug PSAL HTML structure."""
    print("\n" + "="*80)
    print("DEBUGGING: PSAL (NYC Public Schools Athletic League)")
    print("="*80)

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"
    print(f"\n[1] Fetching HTML from: {url}")

    try:
        client = HTTPClient(source="debug_psal")

        html = await client.get_text(url, use_cache=False)
        print(f"[OK] Fetched {len(html)} characters")

        soup = BeautifulSoup(html, "html.parser")

        # Check title
        title = soup.find("title")
        print(f"   Page title: {title.get_text() if title else 'NO TITLE FOUND'}")

        # Check for tables
        print(f"\n[2] Inspecting tables...")
        tables = soup.find_all("table")
        print(f"   Found {len(tables)} <table> elements")

        if tables:
            for idx, table in enumerate(tables):
                print(f"\n   Table #{idx + 1}:")
                table_classes = table.get("class", [])
                table_id = table.get("id")
                print(f"      Classes: {table_classes if table_classes else 'NONE'}")
                print(f"      ID: {table_id if table_id else 'NONE'}")

                rows = table.find_all("tr")
                print(f"      Rows: {len(rows)}")

                if rows:
                    # Check header
                    first_row = rows[0]
                    headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
                    print(f"      Headers: {headers if headers else 'NONE'}")

                    # Check data row
                    if len(rows) > 1:
                        second_row = rows[1]
                        cells = [td.get_text(strip=True) for td in second_row.find_all(["td", "th"])]
                        print(f"      Sample data: {cells if cells else 'NONE'}")
        else:
            print("   [WARN] NO TABLES FOUND!")

        # Check for ASP.NET ViewState (indicator of .NET postback)
        print(f"\n[3] Checking for ASP.NET indicators...")
        viewstate = soup.find("input", {"id": "__VIEWSTATE"})
        print(f"   ViewState found: {viewstate is not None}")

        if viewstate:
            print(f"   [INFO] Page uses ASP.NET - may require form submission")

        # Check for error messages
        error_divs = soup.find_all("div", class_=lambda x: x and "error" in x.lower())
        if error_divs:
            print(f"\n[4] Error messages found:")
            for div in error_divs:
                print(f"      {div.get_text(strip=True)[:100]}...")

        # Check for empty state messages
        empty_msgs = soup.find_all(string=lambda text: text and any(keyword in text.lower() for keyword in ["no data", "no players", "no results", "coming soon", "not available"]))
        if empty_msgs:
            print(f"\n[5] Empty state messages found:")
            for msg in empty_msgs[:3]:
                print(f"      {msg[:100]}...")

        # Summary
        print(f"\n[6] SUMMARY - PSAL")
        print(f"   Tables found: {len(tables)}")
        print(f"   ASP.NET page: {viewstate is not None}")
        print(f"   Error messages: {len(error_divs)}")
        print(f"   Empty state messages: {len(empty_msgs)}")

        if len(tables) == 0:
            print(f"\n   [DIAGNOSIS] NO TABLES FOUND")
            print(f"   Possible causes:")
            print(f"      1. ASP.NET requires form submission/postback")
            print(f"      2. Off-season (no data published)")
            print(f"      3. URL structure has changed")
            if viewstate:
                print(f"   Recommendation: Investigate ASP.NET form handling")
        elif len(tables) > 0:
            # Check if tables have data
            total_data_rows = sum(len(table.find_all("tr")) - 1 for table in tables)  # -1 for header
            if total_data_rows == 0:
                print(f"\n   [DIAGNOSIS] TABLES FOUND BUT EMPTY")
                print(f"   Issue: Off-season (no data in tables)")
            else:
                print(f"\n   [DIAGNOSIS] TABLES WITH DATA FOUND ({total_data_rows} rows)")
                print(f"   Issue: Adapter parsing logic may be broken")
                print(f"   Recommendation: Debug adapter's _parse_player_from_leaders_row method")

        await client.close()

    except Exception as e:
        print(f"[ERROR] Failed to debug PSAL: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all debugging tests."""
    print("\n" + "#"*80)
    print("# ADAPTER HTML STRUCTURE DEBUGGING")
    print("# Purpose: Inspect actual HTML to diagnose selector failures")
    print("#"*80)

    # Debug all 3 adapters
    await debug_3ssb()
    await debug_mn_hub()
    await debug_psal()

    print("\n" + "#"*80)
    print("# DEBUGGING COMPLETE")
    print("#"*80)
    print("\nNext steps:")
    print("  1. Review findings above")
    print("  2. Identify root causes")
    print("  3. Plan selector fixes")
    print("  4. Test fixes incrementally")
    print()


if __name__ == "__main__":
    asyncio.run(main())
