"""
Test RankOne with BrowserClient to handle JavaScript-rendered content.

RankOne appears to be a SPA that requires browser execution.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.utils.browser_client import BrowserClient


async def main():
    """Test RankOne website with browser client."""
    browser = BrowserClient(headless=True)

    # Test homepage first to understand site structure
    url = "https://www.rankone.com"
    print(f"Testing RankOne Homepage: {url}\n")
    print("=" * 80)

    html = await browser.get_rendered_html(url)
    soup = BeautifulSoup(html, 'lxml')

    # Extract title
    title = soup.find('title')
    print(f"Title: {title.get_text(strip=True) if title else 'None'}\n")

    # Find all links
    links = soup.find_all('a', href=True)
    print(f"Total links found: {len(links)}\n")

    # Filter basketball-related links
    basketball_links = [
        link for link in links
        if any(keyword in (link.get('href', '') + link.get_text()).lower()
               for keyword in ['basketball', 'roster', 'stats', 'schedule', 'player', 'leader', 'texas'])
    ]

    print(f"Basketball/State-related links: {len(basketball_links)}\n")

    if basketball_links:
        print("First 20 basketball/state-related links:")
        for i, link in enumerate(basketball_links[:20], 1):
            text = link.get_text(strip=True)[:60]
            href = link['href'][:80]
            print(f"{i:2d}. {text:60s} -> {href}")
    else:
        # Show all links if no basketball links found
        print("\nFirst 20 links (no basketball-specific found):")
        for i, link in enumerate(links[:20], 1):
            text = link.get_text(strip=True)[:60]
            href = link['href'][:80]
            print(f"{i:2d}. {text:60s} -> {href}")

    # Look for navigation or menu items
    nav = soup.find_all(['nav', 'header', 'menu'])
    print(f"\n\nNavigation elements found: {len(nav)}")

    # Save HTML for inspection
    output_file = Path("data/debug/rankone_homepage.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML saved to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
