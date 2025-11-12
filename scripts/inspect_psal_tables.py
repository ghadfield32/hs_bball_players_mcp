"""
Inspect PSAL Tables in Detail

The debug script found 5 tables with 15 rows, but the adapter returns no data.
This script inspects each table's columns to understand what data exists.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup
from src.utils.http_client import HTTPClient
from src.utils import extract_table_data


async def inspect_psal_tables():
    """Inspect PSAL tables to see what columns/data exist."""
    print("=" * 80)
    print("INSPECTING: PSAL Tables - Column Analysis")
    print("=" * 80)

    url = "https://www.psal.org/sports/top-player.aspx?spCode=001"

    try:
        client = HTTPClient(source="psal_inspector")
        html = await client.get_text(url, use_cache=False)
        soup = BeautifulSoup(html, "html.parser")

        print(f"\n[1] Fetched HTML ({len(html)} characters)")
        print(f"    URL: {url}")

        # Get all tables
        tables = soup.find_all("table")
        print(f"\n[2] Found {len(tables)} tables total")

        for idx, table in enumerate(tables, 1):
            print(f"\n{'='*70}")
            print(f"TABLE #{idx}")
            print(f"{'='*70}")

            # Table attributes
            table_class = table.get("class", [])
            table_id = table.get("id", "")
            print(f"   Classes: {table_class if table_class else 'NONE'}")
            print(f"   ID: {table_id if table_id else 'NONE'}")

            # Try extract_table_data
            try:
                rows = extract_table_data(table)
                print(f"   Rows extracted: {len(rows)}")

                if rows:
                    print(f"\n   COLUMNS IN TABLE #{idx}:")
                    first_row = rows[0]
                    for col_name, col_value in first_row.items():
                        print(f"      - {col_name}: {col_value[:50] if col_value and len(col_value) > 50 else col_value}")

                    if len(rows) > 1:
                        print(f"\n   SAMPLE ROW (row #2):")
                        second_row = rows[1]
                        for col_name, col_value in second_row.items():
                            print(f"      - {col_name}: {col_value[:50] if col_value and len(col_value) > 50 else col_value}")
                else:
                    print(f"   No rows extracted (empty table)")

            except Exception as e:
                print(f"   [ERROR] Failed to extract table data: {e}")

            # Check if this looks like a feedback form
            if any("feed" in str(c).lower() for c in table_class):
                print(f"\n   [NOTE] This appears to be a FEEDBACK FORM, not stats data")

        print(f"\n{'='*80}")
        print(f"ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"\nLooking for columns like: 'Player', 'Name', 'PLAYER NAME', 'School', 'Team'")
        print(f"If none found, then page has no player stats tables (likely off-season)")

        await client.close()

    except Exception as e:
        print(f"[ERROR] Failed to inspect tables: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(inspect_psal_tables())
