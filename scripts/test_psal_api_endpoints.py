"""
Test PSAL Basketball API Endpoints

Tests the discovered PSAL API endpoints for basketball stats.

Usage:
    python scripts/test_psal_api_endpoints.py

Author: Claude Code
Date: 2025-11-16
"""

import asyncio
import json

import httpx


async def test_psal_basketball_api():
    """Test PSAL basketball API endpoints."""
    print("TESTING PSAL BASKETBALL API")
    print("=" * 80 + "\n")

    base_url = "https://www.psal.org/SportDisplay.svc"
    sport_code = "001"  # Basketball
    season = "2025"  # Current season (2024-25)

    # Test different league values
    leagues_to_test = ["''", "'1'", "'2'", "'A'", "'AA'", "'AAA'"]

    for league in leagues_to_test:
        print(f"\nTesting with league={league}...")

        # Test order=1 (Top Scorers)
        url = f"{base_url}/GetBskBallStats1?order=1&csports='{sport_code}'&season={season}&league={league}"

        print(f"URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"Content-Type: {content_type}")

                    if 'json' in content_type:
                        data = response.json()

                        if 'd' in data and len(data['d']) > 0:
                            print(f"[SUCCESS] Found {len(data['d'])} players!")

                            # Display first 3 players
                            print("\nTop 3 Scorers:")
                            for i, player in enumerate(data['d'][:3], 1):
                                print(f"\n{i}. {player.get('player', 'N/A')}")
                                print(f"   School: {player.get('school', 'N/A')}")
                                print(f"   Grade: {player.get('grade', 'N/A')}")
                                print(f"   Points: {player.get('points', 'N/A')}")
                                print(f"   Games: {player.get('nogames', 'N/A')}")

                            # Save the full response
                            clean_league = league.replace("'", "")
                            filename = f"psal_api_league_{clean_league}_stats.json"
                            with open(f"data/debug/{filename}", "w") as f:
                                json.dump(data, f, indent=2)
                            print(f"\nSaved full response to: data/debug/{filename}")

                            print(f"\n[WORKING] League {league} returns data!")
                            return True  # Found working league
                        else:
                            print(f"[EMPTY] No data returned for league {league}")
                    else:
                        print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(0.5)  # Be polite

    return False


async def test_all_stat_categories():
    """Test all basketball stat categories."""
    print("\n" + "=" * 80)
    print("TESTING ALL STAT CATEGORIES")
    print("=" * 80 + "\n")

    base_url = "https://www.psal.org/SportDisplay.svc"
    sport_code = "001"
    season = "2025"
    league = "''"  # Empty league (all divisions)

    categories = {
        1: "Top Scorers",
        2: "Top Assists",
        3: "Top Rebounds",
        4: "Top Free Throw %",
        5: "Top Points Per Game",
        6: "Top Assists Per Game",
        7: "Top Rebounds Per Game",
    }

    for order, category_name in categories.items():
        url = f"{base_url}/GetBskBallStats{order}?order={order}&csports='{sport_code}'&season={season}&league={league}"

        print(f"\n{category_name} (order={order}):")
        print(f"URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)

                if response.status_code == 200 and 'json' in response.headers.get('content-type', ''):
                    data = response.json()

                    if 'd' in data and len(data['d']) > 0:
                        print(f"[OK] Found {len(data['d'])} players")

                        # Show top player
                        top_player = data['d'][0]
                        print(f"Top: {top_player.get('player', 'N/A')} - {top_player.get('school', 'N/A')}")
                    else:
                        print(f"[EMPTY] No data")
                else:
                    print(f"[FAIL] Status {response.status_code}")

        except Exception as e:
            print(f"[ERROR] {e}")

        await asyncio.sleep(0.5)


async def main():
    """Main function."""
    # Test to find working league parameter
    working = await test_psal_basketball_api()

    if working:
        # Test all stat categories
        await test_all_stat_categories()

        print("\n" + "=" * 80)
        print("SUCCESS - PSAL API IS WORKING!")
        print("=" * 80)
        print("\nAPI Base URL: https://www.psal.org/SportDisplay.svc")
        print("Endpoints: /GetBskBallStats1 through /GetBskBallStats7")
        print("\nParameters:")
        print("  - order: 1-7 (stat category)")
        print("  - csports: '001' (basketball)")
        print("  - season: 2025 (for 2024-25)")
        print("  - league: '' (empty for all divisions)")
        print("\nReady to implement PSAL adapter using API!")
    else:
        print("\n" + "=" * 80)
        print("API NOT WORKING - WILL USE BROWSER AUTOMATION")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
