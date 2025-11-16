"""
Investigate ANGT (EuroLeague Next Generation) website structure.

This script inspects the ANGT/EuroLeague website to identify:
1. JSON API endpoints (EuroLeague uses JSON APIs)
2. Available data structures
3. Tournament/competition IDs
4. Player and team data availability
"""

import asyncio
import httpx
import json
from bs4 import BeautifulSoup


async def investigate_angt():
    """Investigate ANGT website structure."""
    print("=" * 80)
    print("ANGT (EuroLeague Next Generation) Investigation")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        # Test 1: Main ANGT page
        print("\n[1] Testing main ANGT page...")
        try:
            url = "https://www.euroleaguebasketball.net/next-generation"
            response = await client.get(url)
            print(f"URL: {url}")
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"Content Length: {len(response.text)} chars")

            # Check for JSON in response
            if 'json' in response.headers.get('content-type', '').lower():
                data = response.json()
                print(f"JSON keys: {list(data.keys())[:10]}")

            # Check HTML for API endpoints
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script', src=True)
            print(f"Script tags found: {len(scripts)}")

            # Look for data in inline scripts
            inline_scripts = soup.find_all('script', src=False)
            for script in inline_scripts[:5]:
                if 'api' in script.string.lower() if script.string else False:
                    print(f"Found API reference in script")
                    break

        except Exception as e:
            print(f"Error: {e}")

        # Test 2: EuroLeague API patterns (common endpoints)
        print("\n[2] Testing EuroLeague API endpoints...")
        api_patterns = [
            "https://live.euroleague.net/api/Competition?seasonCode=U2024",
            "https://live.euroleague.net/api/Seasons",
            "https://www.euroleague.net/api/SeasonPhases",
            "https://live.euroleaguebasketball.net/api/Competitions",
        ]

        for api_url in api_patterns:
            try:
                response = await client.get(api_url, headers={'Accept': 'application/json'})
                print(f"\nAPI: {api_url}")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"SUCCESS! JSON keys: {list(data.keys()) if isinstance(data, dict) else f'Array length: {len(data)}'}")
                        print(f"Sample: {json.dumps(data, indent=2)[:500]}")
                    except:
                        print(f"Response (first 300 chars): {response.text[:300]}")
            except Exception as e:
                print(f"Error: {e}")

        # Test 3: Look for Next Gen specific endpoints
        print("\n[3] Testing Next Generation specific endpoints...")
        nextgen_patterns = [
            "https://www.euroleaguebasketball.net/api/next-generation",
            "https://www.euroleague.net/next-generation/api",
            "https://live.euroleague.net/api/NextGeneration",
        ]

        for ng_url in nextgen_patterns:
            try:
                response = await client.get(ng_url, headers={'Accept': 'application/json'})
                print(f"\nNext Gen API: {ng_url}")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"SUCCESS! Content length: {len(response.text)}")
                    print(f"First 300 chars: {response.text[:300]}")
            except Exception as e:
                print(f"Error: {e}")

        # Test 4: Try competition/stats pages
        print("\n[4] Testing stats/competition pages...")
        stats_patterns = [
            "https://www.euroleaguebasketball.net/next-generation/stats",
            "https://www.euroleaguebasketball.net/next-generation/2024-25",
            "https://www.euroleaguebasketball.net/next-generation/competition",
        ]

        for stats_url in stats_patterns:
            try:
                response = await client.get(stats_url)
                print(f"\nStats URL: {stats_url}")
                print(f"Status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

                if response.status_code == 200:
                    # Check for tables
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    print(f"Tables found: {len(tables)}")

                    # Check for React app indicators
                    react_indicators = ['react', 'redux', '__NEXT_DATA__', 'webpack']
                    for indicator in react_indicators:
                        if indicator in response.text.lower():
                            print(f"Found React indicator: {indicator}")
                            break

            except Exception as e:
                print(f"Error: {e}")

        # Test 5: Try direct API endpoint patterns from EuroLeague
        print("\n[5] Testing EuroLeague player/game API patterns...")
        # EuroLeague typically uses patterns like:
        # /api/Header
        # /api/Player?competitionId=X&playerId=Y
        # /api/Stats?competitionId=X

        api_base = "https://www.euroleague.net/api"
        endpoints = [
            f"{api_base}/Header",
            f"{api_base}/Seasons",
            f"{api_base}/CompetitionPlayerStats?SeasonCode=U2024",
        ]

        for endpoint in endpoints:
            try:
                response = await client.get(endpoint, headers={'Accept': 'application/json'})
                print(f"\nEuroLeague API: {endpoint}")
                print(f"Status: {response.status_code}")
                if response.status_code == 200 and 'json' in response.headers.get('content-type', ''):
                    data = response.json()
                    print(f"SUCCESS! Type: {type(data)}, Keys/Length: {list(data.keys()) if isinstance(data, dict) else len(data)}")
            except Exception as e:
                print(f"Error: {e}")

    print("\n" + "=" * 80)
    print("Investigation complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(investigate_angt())
