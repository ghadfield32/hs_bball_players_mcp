"""
Test a specific RankOne school schedule page to check for player stats/rosters.

Testing Allen ISD - a well-known Texas school with strong basketball.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.utils.browser_client import BrowserClient


async def main():
    """Test Allen ISD schedule page."""
    browser = BrowserClient(headless=True)

    # Allen ISD schedule page
    url = "https://app.rankone.com/Schedules/View_Schedule_All_Web.aspx?D=1777D3E4-89A1-4958-AF4E-5D0EF15A42F5&"
    print(f"Testing Allen ISD Schedule Page: {url}\n")
    print("=" * 80)

    html = await browser.get_rendered_html(url, wait_for="table", wait_timeout=15000)
    soup = BeautifulSoup(html, 'lxml')

    # Extract title
    title = soup.find('title')
    print(f"Title: {title.get_text(strip=True) if title else 'None'}\n")

    # Find all tables
    tables = soup.find_all('table')
    print(f"Tables found: {len(tables)}\n")

    if tables:
        print("First 3 tables:")
        for i, table in enumerate(tables[:3], 1):
            headers = [th.get_text(strip=True) for th in table.find_all(['th', 'td'])[:10]]
            print(f"\nTable {i}: {len(table.find_all('tr'))} rows")
            print(f"  Headers/First cells: {headers[:10]}")

    # Look for basketball links/navigation
    links = soup.find_all('a', href=True)
    basketball_links = [
        link for link in links
        if any(keyword in (link.get('href', '') + link.get_text()).lower()
               for keyword in ['basketball', 'roster', 'player', 'stats', 'leader'])
    ]

    print(f"\n\nBasketball-related links: {len(basketball_links)}")
    if basketball_links:
        print("Basketball links:")
        for i, link in enumerate(basketball_links[:10], 1):
            text = link.get_text(strip=True)[:60]
            href = link.get('href', '')[:100]
            print(f"{i:2d}. {text:60s} -> {href}")

    # Look for dropdowns (sport/team selection)
    selects = soup.find_all('select')
    print(f"\n\nDropdown menus: {len(selects)}")
    for i, select in enumerate(selects, 1):
        select_id = select.get('id', 'unknown')
        options = select.find_all('option')
        print(f"\nDropdown {i} (id={select_id}): {len(options)} options")
        for j, option in enumerate(options[:15], 1):
            value = option.get('value', '')
            text = option.get_text(strip=True)[:70]
            print(f"  {j:2d}. {text:70s} (value={value[:30]})")

    # Save HTML
    output_file = Path("data/debug/rankone_allen_schedule.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n\nHTML saved to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
