"""
Test RankOne states page to find Texas basketball data.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.utils.browser_client import BrowserClient


async def main():
    """Test RankOne states page."""
    browser = BrowserClient(headless=True)

    # Test states page
    url = "https://www.rankone.com/states?type=0"
    print(f"Testing RankOne States Page: {url}\n")
    print("=" * 80)

    html = await browser.get_rendered_html(url)
    soup = BeautifulSoup(html, 'lxml')

    # Extract title
    title = soup.find('title')
    print(f"Title: {title.get_text(strip=True) if title else 'None'}\n")

    # Find all links
    links = soup.find_all('a', href=True)
    print(f"Total links found: {len(links)}\n")

    # Look for Texas-related links
    texas_links = [
        link for link in links
        if 'texas' in (link.get('href', '') + link.get_text()).lower()
    ]

    print(f"Texas-related links: {len(texas_links)}\n")

    if texas_links:
        print("Texas-related links:")
        for i, link in enumerate(texas_links, 1):
            text = link.get_text(strip=True)[:60]
            href = link['href'][:100]
            print(f"{i:2d}. {text:60s} -> {href}")

    # Look for state list or navigation
    # Try to find div/section with state names
    state_elements = soup.find_all(['div', 'a', 'button'],
                                   text=lambda t: t and any(s in t.lower() for s in ['texas', 'kentucky', 'indiana', 'ohio', 'tennessee']))

    print(f"\n\nState elements found: {len(state_elements)}")
    if state_elements:
        print("\nFirst 10 state elements:")
        for i, elem in enumerate(state_elements[:10], 1):
            text = elem.get_text(strip=True)[:80]
            tag = elem.name
            href = elem.get('href', 'N/A')[:80]
            print(f"{i:2d}. [{tag}] {text} -> {href}")

    # Save HTML for inspection
    output_file = Path("data/debug/rankone_states.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n\nHTML saved to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
