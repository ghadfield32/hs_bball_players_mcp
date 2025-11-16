"""
Test RankOne Texas districts page to understand navigation to basketball data.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.utils.browser_client import BrowserClient


async def main():
    """Test RankOne Texas districts page."""
    browser = BrowserClient(headless=True)

    # Test Texas districts page
    url = "https://www.rankone.com/districts?state=TX&type=0"
    print(f"Testing RankOne Texas Districts: {url}\n")
    print("=" * 80)

    html = await browser.get_rendered_html(url)
    soup = BeautifulSoup(html, 'lxml')

    # Extract title
    title = soup.find('title')
    print(f"Title: {title.get_text(strip=True) if title else 'None'}\n")

    # Find all links
    links = soup.find_all('a', href=True)
    print(f"Total links found: {len(links)}\n")

    # Look for basketball-related links
    basketball_links = [
        link for link in links
        if any(keyword in (link.get('href', '') + link.get_text()).lower()
               for keyword in ['basketball', 'boys', 'girls'])
    ]

    print(f"Basketball-related links: {len(basketball_links)}\n")

    if basketball_links:
        print("First 20 basketball-related links:")
        for i, link in enumerate(basketball_links[:20], 1):
            text = link.get_text(strip=True)[:60]
            href = link['href'][:100]
            print(f"{i:2d}. {text:60s} -> {href}")
    else:
        print("No basketball-specific links found. Showing first 30 links:")
        for i, link in enumerate(links[:30], 1):
            text = link.get_text(strip=True)[:60]
            href = link['href'][:100]
            print(f"{i:2d}. {text:60s} -> {href}")

    # Look for district or school navigation
    selects = soup.find_all('select')
    print(f"\n\nDropdown menus found: {len(selects)}")
    for i, select in enumerate(selects, 1):
        options = select.find_all('option')
        select_id = select.get('id', 'unknown')
        print(f"\nDropdown {i} (id={select_id}): {len(options)} options")
        if options:
            print("  First 10 options:")
            for j, option in enumerate(options[:10], 1):
                value = option.get('value', 'N/A')
                text = option.get_text(strip=True)[:60]
                print(f"    {j:2d}. {text:60s} (value={value})")

    # Save HTML for inspection
    output_file = Path("data/debug/rankone_texas_districts.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n\nHTML saved to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
