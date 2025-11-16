"""Test calling On3 twice in sequence."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.recruiting.on3 import On3DataSource


async def test_once(year):
    print(f"\nTesting {year}...")
    on3 = On3DataSource()

    try:
        rankings = await on3.get_rankings(class_year=year, limit=5)
        print(f"  SUCCESS: Got {len(rankings)} rankings")
        if rankings:
            print(f"  Top: {rankings[0].player_name}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    finally:
        try:
            if hasattr(on3, 'browser_client'):
                await on3.browser_client.close()
        except:
            pass


async def main():
    print("=" * 50)
    print("Testing On3 twice in sequence")
    print("=" * 50)

    result1 = await test_once(2025)
    await asyncio.sleep(2)  # Wait between calls

    result2 = await test_once(2024)

    print(f"\nResults: 2025={result1}, 2024={result2}")


if __name__ == "__main__":
    asyncio.run(main())
