"""
Simple test of On3 data source.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource


async def main():
    print("Testing On3DataSource...")

    on3 = On3DataSource()

    try:
        print("Fetching 2025 rankings (limit=10)...")
        rankings = await on3.get_rankings(class_year=2025, limit=10)

        print(f"SUCCESS: Got {len(rankings)} rankings")

        if rankings:
            print(f"  Top player: {rankings[0].player_name}")
            print(f"  Rank: #{rankings[0].rank_national}")
            print(f"  Stars: {rankings[0].stars}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(on3, 'browser_client') and on3.browser_client:
            try:
                await on3.browser_client.close()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
