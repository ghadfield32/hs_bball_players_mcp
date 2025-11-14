"""Fetch a specific Michigan bracket group to see actual game data"""
import asyncio
import httpx

async def fetch_mi_bracket_group():
    # Try BracketGroup/1 from the image map
    url = "https://my.mhsaa.com/Sports/MHSAA-Tournament-Brackets/BracketGroup/1/SportSeasonId/424465/Classification/DIVISION%201"

    print(f"Fetching: {url}\n")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)

        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Actual content size: {len(response.content)} bytes")
        print(f"\nFirst 3000 chars of HTML:")
        print(response.text[:3000])

        # Save to file
        with open("data/debug/html/mi_bracketgroup1.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"\n\n[SAVED] HTML saved to data/debug/html/mi_bracketgroup1.html")

if __name__ == "__main__":
    asyncio.run(fetch_mi_bracket_group())
