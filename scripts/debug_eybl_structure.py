#!/usr/bin/env python3
"""
EYBL Website Structure Analysis - Find how player stats are rendered
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def analyze_stats_structure():
    """Analyze how EYBL renders player stats."""
    url = "https://nikeeyb.com/cumulative-season-stats"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"[...] Loading {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)  # Let React finish

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        print(f"[OK] Page loaded ({len(html)} chars)\n")

        # Look for player names we saw in the text
        print("[INFO] Searching for player data structure...")

        # The body text showed: "Jason Crowe Jr", "Tyran Stokes", "Brandon McCoy Jr."
        # Let's find these in the HTML

        jason_elements = soup.find_all(string=lambda x: x and 'Jason Crowe Jr' in x)
        print(f"\n[1] Found 'Jason Crowe Jr' in {len(jason_elements)} elements")
        for elem in jason_elements[:2]:
            parent = elem.parent
            print(f"  - Parent tag: {parent.name}")
            print(f"    Parent class: {parent.get('class')}")
            print(f"    Parent text: {parent.get_text(strip=True)[:100]}")

            # Go up a few levels to see structure
            gp = parent.parent
            if gp:
                print(f"    Grandparent: {gp.name}, class={gp.get('class')}")
            ggp = gp.parent if gp else None
            if ggp:
                print(f"    Great-grandparent: {ggp.name}, class={ggp.get('class')}")

        # Look for elements with "player" in class
        print(f"\n[2] Elements with 'player' in class:")
        player_divs = soup.find_all(class_=lambda x: x and 'player' in str(x).lower())
        print(f"  Found {len(player_divs)} elements")
        for div in player_divs[:5]:
            print(f"  - {div.name}: {div.get('class')}")

        # Look for elements with "stat" in class
        print(f"\n[3] Elements with 'stat' in class:")
        stat_divs = soup.find_all(class_=lambda x: x and 'stat' in str(x).lower())
        print(f"  Found {len(stat_divs)} elements")
        for div in stat_divs[:10]:
            print(f"  - {div.name}: {div.get('class')} | text={div.get_text(strip=True)[:50]}")

        # Look for elements with "row" or "item" in class
        print(f"\n[4] Elements with 'row' in class:")
        row_divs = soup.find_all(class_=lambda x: x and 'row' in str(x).lower())
        print(f"  Found {len(row_divs)} elements")
        for div in row_divs[:5]:
            print(f"  - {div.name}: {div.get('class')}")

        # Look for list items
        print(f"\n[5] List items (<li>):")
        list_items = soup.find_all('li')
        print(f"  Found {len(list_items)} <li> elements")

        # Find ones with player data
        for li in list_items:
            text = li.get_text(strip=True)
            if 'Oakland Soldiers' in text or 'Jason Crowe' in text:
                print(f"  - Found player li: class={li.get('class')}")
                print(f"    Text (first 200 chars): {text[:200]}")
                print(f"    Children: {[child.name for child in li.children if hasattr(child, 'name')]}")
                break

        # Look for the specific number "26.5" (Jason Crowe's PPG)
        print(f"\n[6] Searching for stat value '26.5':")
        ppg_elements = soup.find_all(string=lambda x: x and '26.5' in str(x))
        print(f"  Found in {len(ppg_elements)} elements")
        for elem in ppg_elements[:3]:
            parent = elem.parent
            print(f"  - Parent: {parent.name}, class={parent.get('class')}")
            print(f"    Text: {parent.get_text(strip=True)}")

        # Dump a section of HTML around player data
        print(f"\n[7] HTML snippet with 'Jason Crowe Jr':")
        print("=" * 80)
        # Find the position in HTML
        jason_pos = html.find('Jason Crowe Jr')
        if jason_pos > 0:
            snippet = html[max(0, jason_pos-500):jason_pos+1000]
            print(snippet)
        print("=" * 80)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_stats_structure())
