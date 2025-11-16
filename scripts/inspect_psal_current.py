"""
PSAL Website Inspector - Phase HS-5

Inspects current PSAL website structure to debug adapter issues.
Checks leaders page, standings, teams for table structure.

Usage:
    python scripts/inspect_psal_current.py

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import httpx
from bs4 import BeautifulSoup


async def inspect_psal_leaders():
    """Inspect PSAL leaders page."""
    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"
    print("=" * 80)
    print(f"Inspecting PSAL Leaders Page")
    print("=" * 80)
    print(f"URL: {url}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[FAIL] Non-200 status code")
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all tables
            tables = soup.find_all('table')
            print(f"\nFound {len(tables)} table(s)\n")

            for i, table in enumerate(tables, 1):
                print(f"Table {i}:")
                print(f"  Classes: {table.get('class', [])}")
                print(f"  ID: {table.get('id', 'None')}")

                # Find headers
                thead = table.find('thead')
                if thead:
                    headers = [th.get_text(strip=True) for th in thead.find_all(['th', 'td'])]
                    print(f"  Headers (thead): {headers}")
                else:
                    # Try first row
                    first_row = table.find('tr')
                    if first_row:
                        headers = [cell.get_text(strip=True) for cell in first_row.find_all(['th', 'td'])]
                        has_th = any(cell.name == 'th' for cell in first_row.find_all(['th', 'td']))
                        if has_th:
                            print(f"  Headers (first row): {headers}")
                        else:
                            print(f"  First row (not headers): {headers[:5]}...")

                # Count rows
                tbody = table.find('tbody') or table
                rows = tbody.find_all('tr')
                print(f"  Rows: {len(rows)}")

                # Sample first data row
                if len(rows) > 1:  # Skip header row if present
                    sample_row = rows[1] if len(rows) > 1 else rows[0]
                    cells = [cell.get_text(strip=True) for cell in sample_row.find_all(['th', 'td'])]
                    print(f"  Sample row: {cells[:10]}")
                    print()

            # Check for divs/sections with stat data
            print("\nChecking for non-table stat containers...")
            stat_divs = soup.find_all('div', class_=lambda x: x and ('stat' in str(x).lower() or 'leader' in str(x).lower()))
            print(f"Found {len(stat_divs)} div(s) with 'stat' or 'leader' in class name")

            # Check for JavaScript/dynamic content
            scripts = soup.find_all('script')
            has_react = any('react' in str(script).lower() for script in scripts)
            has_angular = any('angular' in str(script).lower() for script in scripts)
            has_vue = any('vue' in str(script).lower() for script in scripts)

            if has_react or has_angular or has_vue:
                print("\n[WARNING] JavaScript framework detected:")
                if has_react:
                    print("  - React (may need browser rendering)")
                if has_angular:
                    print("  - Angular (may need browser rendering)")
                if has_vue:
                    print("  - Vue (may need browser rendering)")

            # Save HTML sample for manual inspection
            with open("data/debug/psal_leaders_page.html", "w", encoding='utf-8') as f:
                f.write(response.text)
            print(f"\nSaved full HTML to: data/debug/psal_leaders_page.html")

    except Exception as e:
        print(f"[ERROR] {e}")


async def inspect_psal_standings():
    """Inspect PSAL standings page."""
    url = "https://www.psal.org/sports/standings.aspx?spCode=001"
    print("\n" + "=" * 80)
    print(f"Inspecting PSAL Standings Page")
    print("=" * 80)
    print(f"URL: {url}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

            print(f"Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[FAIL] Non-200 status code")
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all tables
            tables = soup.find_all('table')
            print(f"\nFound {len(tables)} table(s)")

            if tables:
                table = tables[0]
                print(f"\nFirst table:")
                print(f"  Classes: {table.get('class', [])}")

                # Sample rows
                rows = table.find_all('tr')[:5]
                print(f"  Sample rows (first 5):")
                for row in rows:
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])]
                    print(f"    {cells}")

    except Exception as e:
        print(f"[ERROR] {e}")


async def main():
    """Run PSAL website inspection."""
    await inspect_psal_leaders()
    await inspect_psal_standings()

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Check data/debug/psal_leaders_page.html for full HTML")
    print("2. Look for table structure and column names")
    print("3. Update PSAL adapter based on findings")


if __name__ == "__main__":
    asyncio.run(main())
