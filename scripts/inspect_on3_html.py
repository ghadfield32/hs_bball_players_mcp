"""
Inspect On3/Rivals HTML Structure for Industry Rankings

This script fetches the On3/Rivals Industry rankings page and analyzes
the HTML structure to identify correct selectors for data extraction.

Target URL: https://www.on3.com/rivals/rankings/industry-player/basketball/2025/

Purpose:
1. Test if browser can load the page (bot detection check)
2. Identify HTML structure for rankings data
3. Find correct CSS selectors for player elements
4. Determine data fields available

Usage:
    python scripts/inspect_on3_html.py

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import logging
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser_client import BrowserClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def inspect_on3_html():
    """Inspect On3/Rivals HTML structure for Industry rankings."""

    logger.info("="*60)
    logger.info("On3/Rivals HTML Structure Inspector")
    logger.info("="*60)
    logger.info("")

    # Target URL for Industry composite rankings
    url = "https://www.on3.com/rivals/rankings/industry-player/basketball/2025/"
    logger.info(f"Target URL: {url}")
    logger.info("")

    browser_client = BrowserClient()

    try:
        logger.info("Step 1: Testing browser access and bot detection...")
        logger.info("-" * 60)

        # Try different wait strategies to see which works
        wait_strategies = [
            {"selector": "div.player-card", "timeout": 30000, "name": "Player Cards"},
            {"selector": "table", "timeout": 30000, "name": "Table"},
            {"selector": "ul.rankings-list", "timeout": 30000, "name": "Rankings List"},
            {"selector": "div.ranking-item", "timeout": 30000, "name": "Ranking Items"},
        ]

        html = None
        successful_selector = None

        for strategy in wait_strategies:
            try:
                logger.info(f"Trying selector: {strategy['selector']} ({strategy['name']})...")

                html = await browser_client.get_rendered_html(
                    url=url,
                    wait_for=strategy['selector'],
                    wait_timeout=strategy['timeout'],
                    wait_for_network_idle=False,
                )

                if html and len(html) > 10000:  # Reasonable page size
                    logger.info(f"✅ SUCCESS with selector: {strategy['selector']}")
                    logger.info(f"   Page size: {len(html):,} bytes")
                    successful_selector = strategy['selector']
                    break

            except Exception as e:
                logger.warning(f"❌ Failed with selector '{strategy['selector']}': {str(e)[:100]}")
                continue

        if not html:
            logger.error("❌ FAILED: Could not load page with any selector")
            logger.error("   This suggests On3 also has bot detection")
            return False

        logger.info("")
        logger.info("Step 2: Analyzing HTML structure...")
        logger.info("-" * 60)

        # Save HTML for inspection
        output_file = Path("data/debug/on3_rankings.html")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html, encoding='utf-8')
        logger.info(f"Saved HTML to: {output_file}")
        logger.info("")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Look for common ranking patterns
        logger.info("Step 3: Searching for ranking elements...")
        logger.info("-" * 60)

        # Pattern 1: Table-based rankings
        tables = soup.find_all("table")
        logger.info(f"Found {len(tables)} <table> elements")
        for i, table in enumerate(tables[:3], 1):
            class_str = str(table.get('class', []))
            logger.info(f"  Table {i}: class={class_str[:50]}")

        # Pattern 2: List-based rankings (like 247Sports)
        ul_elements = soup.find_all("ul")
        logger.info(f"Found {len(ul_elements)} <ul> elements")
        for ul in ul_elements[:5]:
            class_str = str(ul.get('class', []))
            if any(keyword in class_str.lower() for keyword in ['rank', 'player', 'list']):
                logger.info(f"  Relevant <ul>: class={class_str}")
                # Show first few <li> items
                li_items = ul.find_all("li", limit=2)
                logger.info(f"    Contains {len(li_items)} <li> items")

        # Pattern 3: Div-based cards
        div_patterns = [
            "player-card",
            "ranking-item",
            "recruit-item",
            "player-row",
            "roster-item",
        ]

        for pattern in div_patterns:
            divs = soup.find_all("div", class_=lambda x: x and pattern in str(x).lower())
            if divs:
                logger.info(f"Found {len(divs)} divs matching '{pattern}'")
                if divs:
                    first_div = divs[0]
                    logger.info(f"  First div class: {first_div.get('class', [])}")
                    # Show structure
                    inner_divs = first_div.find_all("div", limit=5)
                    logger.info(f"  Contains {len(inner_divs)} inner divs")

        logger.info("")
        logger.info("Step 4: Looking for player data patterns...")
        logger.info("-" * 60)

        # Search for player names (common anchor pattern)
        player_links = soup.find_all("a", href=lambda x: x and "player" in str(x).lower())
        logger.info(f"Found {len(player_links)} links with 'player' in href")

        if player_links:
            logger.info("First 5 player links:")
            for i, link in enumerate(player_links[:5], 1):
                name = link.text.strip()
                href = link.get('href', '')
                if name and len(name) > 2:  # Filter out empty/short text
                    logger.info(f"  {i}. {name} -> {href[:50]}")

        # Search for ranking numbers
        rank_elements = soup.find_all(class_=lambda x: x and 'rank' in str(x).lower())
        logger.info(f"Found {len(rank_elements)} elements with 'rank' in class")

        logger.info("")
        logger.info("Step 5: Extracting sample player data...")
        logger.info("-" * 60)

        # Try to extract first player as example
        # This will vary based on actual HTML structure

        if successful_selector == "table" and tables:
            logger.info("Attempting table-based extraction...")
            first_table = tables[0]
            rows = first_table.find_all("tr")
            logger.info(f"Table has {len(rows)} rows")

            if len(rows) > 1:
                # Show first data row
                first_row = rows[1]  # Skip header
                cells = first_row.find_all(['td', 'th'])
                logger.info(f"First row has {len(cells)} cells:")
                for i, cell in enumerate(cells[:8], 1):
                    text = cell.text.strip()[:30]
                    logger.info(f"  Cell {i}: {text}")

        logger.info("")
        logger.info("="*60)
        logger.info("INSPECTION COMPLETE")
        logger.info("="*60)
        logger.info("")
        logger.info(f"✅ Bot Detection: PASSED (loaded with selector: {successful_selector})")
        logger.info(f"✅ Page Size: {len(html):,} bytes")
        logger.info(f"✅ HTML saved: {output_file}")
        logger.info("")
        logger.info("Next Steps:")
        logger.info("1. Review saved HTML file for exact structure")
        logger.info("2. Identify correct selectors for player elements")
        logger.info("3. Map data fields to RecruitingRank model")
        logger.info("4. Implement On3DataSource adapter")

        return True

    except Exception as e:
        logger.error("="*60)
        logger.error("❌ INSPECTION FAILED")
        logger.error("="*60)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        # BrowserClient uses singleton pattern - no explicit close needed
        pass


async def main():
    """Main entry point."""
    success = await inspect_on3_html()

    if success:
        logger.info("")
        logger.info("🎉 Inspection successful - Ready to implement On3 adapter")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("❌ Inspection failed - May need alternative approach")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
