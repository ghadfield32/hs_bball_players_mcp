"""
Debug GoBound parsing to see raw data.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from src.datasources.us.bound import BoundDataSource
from src.utils.parser import parse_html


async def main():
    """Debug GoBound parsing."""
    print("Debugging GoBound Parsing")
    print("="*60)

    bound = BoundDataSource()

    # Fetch Iowa leaders page
    url = bound._get_state_url("IA", "leaders")
    print(f"\nFetching: {url}\n")

    html = await bound.http_client.get_text(url, cache_ttl=3600)
    soup = parse_html(html)

    # Extract tables
    tables = bound._extract_gobound_tables(soup)
    print(f"Found {len(tables)} GoBound tables\n")

    # Show first few rows from first table
    if tables and tables[0]["rows"]:
        first_table = tables[0]
        print(f"TABLE 1 - Category: {first_table.get('stat_category')}")
        print("="*60)

        for i, row in enumerate(first_table["rows"][:5], 1):
            print(f"\nRow {i}:")
            print(f"  Rank: {row['rank']}")
            print(f"  Player Info (raw): {repr(row['player_info'])}")
            print(f"  Stat Value: {row['stat_value']}")

            # Parse player info
            parsed = bound._parse_gobound_player_info(row['player_info'])
            print(f"  Parsed:")
            for key, val in parsed.items():
                print(f"    {key}: {val}")

    # Check other tables
    print(f"\n\nALL TABLES:")
    print("="*60)
    for i, table in enumerate(tables, 1):
        row_count = len(table["rows"])
        category = table.get("stat_category", "unknown")
        print(f"{i:2d}. {category:20s} - {row_count} rows")

    await bound.close()


if __name__ == '__main__':
    asyncio.run(main())
