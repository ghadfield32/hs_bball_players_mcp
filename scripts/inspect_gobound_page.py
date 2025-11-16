"""
Quick script to inspect GoBound leaders page HTML structure.

Fetches the Iowa leaders page and dumps table information for debugging.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.datasources.us.bound import BoundDataSource


async def main():
    """Fetch and inspect Iowa leaders page."""
    bound = BoundDataSource()

    url = "https://www.gobound.com/ia/ihsaa/boysbasketball/2024-25/leaders"
    print(f"Fetching: {url}\n")

    html = await bound.http_client.get_text(url, cache_ttl=0)  # No cache for debugging
    soup = BeautifulSoup(html, 'lxml')

    # Find all tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables\n")

    for i, table in enumerate(tables, 1):
        print(f"="*80)
        print(f"TABLE {i}")
        print(f"="*80)

        # Get table classes
        classes = table.get('class', [])
        print(f"Classes: {classes}")

        # Find headers
        headers = table.find_all(['th', 'td'], limit=20)
        if headers:
            print(f"\nFirst 10 headers/cells:")
            for j, h in enumerate(headers[:10], 1):
                text = h.get_text(strip=True)
                print(f"  {j}. [{h.name}] {text}")

        # Find first few rows
        rows = table.find_all('tr', limit=5)
        print(f"\nFirst 5 rows:")
        for j, row in enumerate(rows, 1):
            cells = row.find_all(['td', 'th'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            print(f"  Row {j}: {cell_texts}")

        print()

    await bound.close()


if __name__ == '__main__':
    asyncio.run(main())
