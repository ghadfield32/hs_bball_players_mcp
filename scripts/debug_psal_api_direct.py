#!/usr/bin/env python3
"""
PSAL SportDisplay.svc API Direct Call Test
Try calling the WCF service directly to find player stats endpoints
"""

import asyncio
import httpx


async def test_psal_api():
    """Test PSAL Sport Display.svc API endpoints."""

    base_url = "https://www.psal.org/SportDisplay.svc"

    # Try various endpoint patterns
    endpoints_to_try = [
        # OData metadata
        "$metadata",
        # Based on observed calls
        "vw_Schools",
        "GetSchoolList?type='list_mdl_schls_teams'",
        # Guessing at player/stat endpoints
        "vw_Players",
        "vw_PlayerStats",
        "vw_StatLeaders",
        "vw_TopPlayers",
        "GetStatLeaders",
        "GetTopPlayers",
        "GetPlayerStats",
        # Try with basketball sport code
        "vw_StatLeaders?spCode=001",
        "GetStatLeaders?spCode=001",
        # Try with season
        "vw_StatLeaders?spCode=001&season=2024",
    ]

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for endpoint in endpoints_to_try:
            url = f"{base_url}/{endpoint}"
            print(f"\n[...] Trying: {url}")

            try:
                response = await client.get(url)
                print(f"[{response.status_code}] Status: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"     Content-Type: {content_type}")

                    # Show response (first 1000 chars)
                    text = response.text
                    print(f"     Length: {len(text)} chars")
                    print(f"     Response (first 1000 chars):")
                    print("     " + "=" * 70)
                    print("     " + text[:1000].replace("\n", "\n     "))
                    print("     " + "=" * 70)

                    # If JSON, try to parse
                    if 'json' in content_type.lower():
                        try:
                            data = response.json()
                            print(f"     JSON keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                        except:
                            pass

                elif response.status_code == 404:
                    print(f"     Endpoint not found")
                elif response.status_code == 500:
                    print(f"     Server error")
                else:
                    print(f"     Response: {response.text[:200]}")

            except httpx.HTTPError as e:
                print(f"[X] HTTP Error: {e}")
            except Exception as e:
                print(f"[X] Error: {e}")

        # Try the metadata endpoint to see all available endpoints
        print(f"\n\n[INFO] Checking OData $metadata for all available endpoints...")
        try:
            response = await client.get(f"{base_url}/$metadata")
            if response.status_code == 200:
                text = response.text
                # Extract EntitySet names (available OData collections)
                import re
                entity_sets = re.findall(r'<EntitySet\s+Name="(\w+)"', text)
                if entity_sets:
                    print(f"[OK] Found {len(entity_sets)} EntitySets:")
                    for entity_set in entity_sets:
                        print(f"     - {entity_set}")
                else:
                    # Try FunctionImport (service operations)
                    functions = re.findall(r'<FunctionImport\s+Name="(\w+)"', text)
                    if functions:
                        print(f"[OK] Found {len(functions)} FunctionImports:")
                        for func in functions:
                            print(f"     - {func}")
        except Exception as e:
            print(f"[X] Could not read metadata: {e}")


if __name__ == "__main__":
    asyncio.run(test_psal_api())
