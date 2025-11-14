"""Test FIBA API endpoint discovery."""
import asyncio
import httpx

async def test_fiba_api():
    """Test different FIBA API endpoints."""
    endpoints = [
        "https://digital-api.fiba.basketball/hapi",
        "https://digital-api.fiba.basketball/hapi/getcustomgateway",
        "https://account.fiba.basketball",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in endpoints:
            print(f"\nTesting: {endpoint}")
            try:
                response = await client.get(endpoint)
                print(f"  Status: {response.status_code}")
                print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
                if response.status_code == 200:
                    print(f"  Content preview: {response.text[:200]}")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_fiba_api())
