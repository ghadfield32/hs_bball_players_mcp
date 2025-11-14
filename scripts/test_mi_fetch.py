"""Direct fetch of Michigan MHSAA bracket to inspect raw HTML"""
import asyncio
import httpx

async def fetch_mi_bracket():
    url = "https://my.mhsaa.com/Sports/MHSAA-Tournament-Brackets/BracketGroup/9/SportSeasonId/424465/Classification/Division 1"

    print(f"Fetching: {url}\n")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)

        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Encoding: {response.headers.get('content-encoding', 'none')}")
        print(f"Content-Length: {response.headers.get('content-length', 'unknown')}")
        print(f"Actual content size: {len(response.content)} bytes")
        print(f"\nFirst 2000 chars of HTML:")
        print(response.text[:2000])

        # Save to file
        with open("data/debug/html/mi_direct_fetch.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"\n\n[SAVED] HTML saved to data/debug/html/mi_direct_fetch.html")

if __name__ == "__main__":
    asyncio.run(fetch_mi_bracket())
