"""
Debug GoBound stats aggregation to see why only points are showing.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.bound import BoundDataSource
from src.utils.parser import parse_html


async def main():
    """Debug stats aggregation."""
    print("Debugging GoBound Stats Aggregation")
    print("="*60)

    bound = BoundDataSource()

    # Fetch Iowa leaders page
    url = bound._get_state_url("IA", "leaders")
    html = await bound.http_client.get_text(url, cache_ttl=3600)
    soup = parse_html(html)

    # Extract tables
    tables = bound._extract_gobound_tables(soup)
    print(f"Found {len(tables)} tables\n")

    # Search for Mason Bechen in all tables
    target_player = "Mason Bechen"
    print(f"Searching for '{target_player}' in all tables:\n")

    for i, table in enumerate(tables, 1):
        category = table.get("stat_category", "unknown")
        print(f"Table {i} - {category}:")

        found_in_table = False
        for row in table["rows"]:
            player_info = bound._parse_gobound_player_info(row["player_info"])
            player_name = player_info.get("name", "")

            # Check if this is our player
            if target_player.lower() in player_name.lower():
                found_in_table = True
                stat_value = row.get("stat_value", "")
                print(f"  FOUND: {player_name} = {stat_value}")
                break

        if not found_in_table:
            print(f"  NOT FOUND")

    await bound.close()


if __name__ == '__main__':
    asyncio.run(main())
