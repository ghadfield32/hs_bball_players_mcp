"""
Test script to investigate RankOne data availability for Texas basketball.

Checks what kind of data (rosters, stats, schedules) is actually available.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.utils.http_client import HTTPClient


async def main():
    """Test RankOne website for Texas basketball data."""
    http_client = HTTPClient(source="rankone")

    # Try different potential URLs for Texas basketball
    test_urls = [
        "https://www.rankone.com/texas/basketball",
        "https://www.rankone.com/tx/basketball",
        "https://www.rankone.com/texas/boys-basketball",
        "https://www.rankone.com/tx/boys-basketball",
        "https://www.rankone.com/texas",
        "https://www.rankone.com/tx",
    ]

    print("Testing RankOne URLs for Texas Basketball Data\n")
    print("=" * 80)

    for url in test_urls:
        print(f"\nTesting: {url}")
        try:
            response = await http_client.get(url)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                title = soup.find('title')
                h1 = soup.find('h1')

                print(f"Title: {title.get_text(strip=True) if title else 'None'}")
                print(f"H1: {h1.get_text(strip=True) if h1 else 'None'}")

                # Look for tables
                tables = soup.find_all('table')
                print(f"Tables found: {len(tables)}")

                # Look for links related to stats/rosters/schedules
                links = soup.find_all('a', href=True)
                basketball_links = [
                    link for link in links
                    if any(keyword in link['href'].lower() or keyword in link.get_text().lower()
                           for keyword in ['basketball', 'roster', 'stats', 'schedule', 'player', 'leader'])
                ]
                print(f"Basketball-related links found: {len(basketball_links)}")

                if basketball_links:
                    print("\nFirst 10 basketball-related links:")
                    for link in basketball_links[:10]:
                        print(f"  - {link.get_text(strip=True)[:50]}: {link['href'][:80]}")

                print(f"\nHTML preview (first 1000 chars):")
                print(response.text[:1000])
                print("=" * 80)

        except Exception as e:
            print(f"Error: {e}")
            print("=" * 80)

    await http_client.close()


if __name__ == '__main__':
    asyncio.run(main())
