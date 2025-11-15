#!/usr/bin/env python3
"""
Test MN Hub Season Fallback Logic
"""

import asyncio
import sys
sys.path.insert(0, 'c:\\docker_projects\\betts_basketball\\hs_bball_players_mcp')

from src.datasources.us.mn_hub import MNHubDataSource


async def test_season_fallback():
    """Test MN Hub season fallback detection."""

    print("[...] Initializing MN Hub datasource")
    datasource = MNHubDataSource()

    print(f"[INFO] Current season year calculated: {datasource.current_season_year}")
    print(f"[INFO] Season before detection: {datasource.season}")
    print(f"[INFO] URL before detection: {datasource.leaderboards_url}")

    print("\n[...] Testing season detection...")
    found = await datasource._find_available_season()

    if found:
        print(f"[OK] ✓ Season detected successfully!")
        print(f"      Season: {datasource.season}")
        print(f"      URL: {datasource.leaderboards_url}")
    else:
        print(f"[X] ✗ No season found")
        return

    print("\n[...] Testing search_players() with auto-detection...")
    players = await datasource.search_players(limit=5)

    print(f"[OK] Found {len(players)} players:")
    for i, player in enumerate(players[:5], 1):
        print(f"  {i}. {player.full_name} - {player.team_name}")

    # Close datasource
    await datasource.close()
    print("\n[OK] Test complete!")


if __name__ == "__main__":
    asyncio.run(test_season_fallback())
