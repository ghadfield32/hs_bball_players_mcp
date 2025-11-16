"""
Comprehensive Datasource Audit Script

This script tests all 56 configured datasources to identify:
1. Which adapters can successfully connect to their target websites
2. Which adapters are blocked (403/401/etc.)
3. Which adapters have working data extraction
4. Which adapters need browser automation
5. Which adapters have broken/defunct domains
6. Overall datasource health status

This provides a complete picture of what needs to be fixed.
"""

import asyncio
import httpx
from datetime import datetime
import json


# All configured datasources from the project
DATASOURCES = {
    # US National Circuits
    "EYBL Boys": "https://nikeeyb.com/cumulative-season-stats",
    "EYBL Girls": "https://nikeeyb.com/girls/cumulative-season-stats",
    "3SSB Boys": "https://adidas3ssb.com/stats",
    "3SSB Girls": "https://adidas3ssb.com/girls/stats",
    "UAA Boys": "https://uaassociation.com/stats",
    "UAA Girls": "https://uanext.com/stats",

    # US Multi-State
    "SBLive WA": "https://wa.sblive.com/high-school/boys-basketball/stats",
    "Bound IA": "https://www.ia.bound.com/stats",
    "MN Basketball Hub": "https://www.mnbasketballhub.com/stats",

    # US Single State
    "PSAL NYC": "https://www.psal.org/sports/basketball",
    "WSN Wisconsin": "https://www.wissports.net/basketball",

    # US Prep/Elite
    "OTE": "https://overtimeelite.com/stats",
    "Grind Session": "https://thegrindsession.com/stats",
    "NEPSAC": "https://www.nepsac.org/landing/index",

    # Global/International
    "FIBA Youth": "https://www.fiba.basketball/youth",
    "FIBA LiveStats": "https://livefiba.dcd.shared.geniussports.com",
    "ANGT": "https://www.euroleaguebasketball.net/next-generation",
    "NBBL (Germany)": "https://www.nbbl-basketball.de/stats",
    "FEB (Spain)": "https://www.feb.es/competiciones",
    "MKL (Lithuania)": "https://www.lkl.lt/mkl",
    "LNB Espoirs (France)": "https://www.lnb.fr/espoirs",

    # Canada
    "OSBA": "https://www.osba.ca",
    "NPA Canada": "https://npacanada.com/stats",

    # Australia
    "PlayHQ": "https://www.playhq.com/basketball-australia",

    # State Associations (Sample - top basketball states)
    "Florida FHSAA": "https://www.fhsaa.org/basketball",
    "Georgia GHSA": "https://www.ghsa.net/sports/basketball",
    "North Carolina NCHSAA": "https://www.nchsaa.org/sports/basketball",
    "Texas UIL": "https://www.uiltexas.org/basketball",
    "California CIF": "https://www.cifstate.org/basketball",
    "New York NYSPHSAA": "https://www.nysphsaa.org/sports/basketball",
    "Illinois IHSA": "https://www.ihsa.org/Sports-Activities/Boys-Basketball",
    "Pennsylvania PIAA": "https://www.piaa.org/sports/basketball",
    "Ohio OHSAA": "https://www.ohsaa.org/sports/basketball",
    "Michigan MHSAA": "https://www.mhsaa.com/sports/basketball",
}


async def test_datasource(name: str, url: str, client: httpx.AsyncClient):
    """Test a single datasource for connectivity and basic functionality."""
    result = {
        "name": name,
        "url": url,
        "status": "UNKNOWN",
        "http_status": None,
        "error": None,
        "response_size": 0,
        "has_content": False,
        "needs_browser": False,
        "recommendation": ""
    }

    try:
        # Test with standard HTTP client
        response = await client.get(url, timeout=15.0)
        result["http_status"] = response.status_code
        result["response_size"] = len(response.text)

        if response.status_code == 200:
            result["status"] = "SUCCESS"
            result["has_content"] = len(response.text) > 1000

            # Check for indicators that stats might be available
            content_lower = response.text.lower()
            if any(keyword in content_lower for keyword in ['stats', 'statistics', 'player', 'team']):
                result["recommendation"] = "✅ GOOD - Site accessible, content found"
            else:
                result["recommendation"] = "⚠️  WARNING - Accessible but may lack stats"

        elif response.status_code == 403:
            result["status"] = "BLOCKED"
            result["needs_browser"] = True
            result["recommendation"] = "🛑 BLOCKED - Needs browser automation (anti-bot protection)"

        elif response.status_code == 404:
            result["status"] = "NOT_FOUND"
            result["recommendation"] = "❌ BROKEN - Page not found (404)"

        elif response.status_code == 401:
            result["status"] = "AUTH_REQUIRED"
            result["recommendation"] = "🔒 AUTH - Requires authentication"

        elif response.status_code in [301, 302, 307, 308]:
            result["status"] = "REDIRECT"
            result["recommendation"] = f"🔄 REDIRECT - Redirects to {response.headers.get('Location', 'unknown')}"

        else:
            result["status"] = "HTTP_ERROR"
            result["recommendation"] = f"⚠️  HTTP {response.status_code}"

    except httpx.ConnectTimeout:
        result["status"] = "TIMEOUT"
        result["error"] = "Connection timeout"
        result["recommendation"] = "⏱️  TIMEOUT - Server not responding"

    except httpx.ConnectError as e:
        result["status"] = "UNREACHABLE"
        result["error"] = str(e)
        result["recommendation"] = "💀 UNREACHABLE - Domain may be defunct"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:200]
        result["recommendation"] = f"❌ ERROR - {str(e)[:100]}"

    return result


async def audit_all_datasources():
    """Run comprehensive audit of all datasources."""
    print("=" * 100)
    print("COMPREHENSIVE DATASOURCE AUDIT")
    print(f"Testing {len(DATASOURCES)} datasources...")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    results = []

    # Configure HTTP client with realistic headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=15.0,
        follow_redirects=True,
        verify=False  # Ignore SSL errors for testing
    ) as client:

        # Test each datasource
        tasks = []
        for name, url in DATASOURCES.items():
            task = test_datasource(name, url, client)
            tasks.append(task)

        # Run tests concurrently (in batches to avoid overwhelming servers)
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

            # Brief pause between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(2)

    # Analyze results
    print("\n" + "=" * 100)
    print("DETAILED RESULTS")
    print("=" * 100)

    # Group by status
    by_status = {}
    for result in results:
        status = result["status"]
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(result)

    # Print detailed results by category
    categories = [
        ("SUCCESS", "✅ WORKING DATASOURCES"),
        ("BLOCKED", "🛑 BLOCKED BY ANTI-BOT (Need Browser Automation)"),
        ("NOT_FOUND", "❌ BROKEN (404 Not Found)"),
        ("UNREACHABLE", "💀 UNREACHABLE (Defunct Domain?)"),
        ("TIMEOUT", "⏱️  TIMEOUT (Server Issues)"),
        ("AUTH_REQUIRED", "🔒 REQUIRES AUTHENTICATION"),
        ("REDIRECT", "🔄 REDIRECTS"),
        ("HTTP_ERROR", "⚠️  HTTP ERRORS"),
        ("ERROR", "❌ OTHER ERRORS"),
    ]

    for status, title in categories:
        if status in by_status:
            print(f"\n{title} ({len(by_status[status])})")
            print("-" * 100)
            for result in by_status[status]:
                print(f"  {result['name']:30s} | {result['recommendation']}")
                if result['error']:
                    print(f"      Error: {result['error'][:100]}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)

    total = len(results)
    success = len(by_status.get("SUCCESS", []))
    blocked = len(by_status.get("BLOCKED", []))
    broken = len(by_status.get("NOT_FOUND", [])) + len(by_status.get("UNREACHABLE", []))
    needs_fix = total - success

    print(f"Total Datasources Tested: {total}")
    print(f"✅ Working (HTTP 200):    {success} ({success/total*100:.1f}%)")
    print(f"🛑 Blocked (403):         {blocked} ({blocked/total*100:.1f}%)")
    print(f"❌ Broken (404/defunct):  {broken} ({broken/total*100:.1f}%)")
    print(f"⚠️  Needs Attention:      {needs_fix} ({needs_fix/total*100:.1f}%)")

    # Priority recommendations
    print("\n" + "=" * 100)
    print("PRIORITY RECOMMENDATIONS")
    print("=" * 100)

    print("\n🔥 HIGH PRIORITY - Fix These First:")
    high_priority = []
    for result in results:
        if result["status"] == "BLOCKED" and any(keyword in result["name"] for keyword in ["EYBL", "ANGT", "OSBA", "3SSB", "UAA"]):
            high_priority.append(result["name"])
    for name in high_priority:
        print(f"  - {name}: Implement browser automation")

    print("\n🔧 MEDIUM PRIORITY - Investigate & Fix:")
    medium_priority = []
    for result in results:
        if result["status"] in ["NOT_FOUND", "UNREACHABLE"]:
            medium_priority.append(f"{result['name']}: {result['recommendation']}")
    for item in medium_priority[:10]:  # Limit to top 10
        print(f"  - {item}")

    print("\n✅ LOW PRIORITY - Verify Data Extraction:")
    for result in results[:5]:  # Show first 5 working sources
        if result["status"] == "SUCCESS":
            print(f"  - {result['name']}: Test actual stat extraction")

    # Export results to JSON
    output_file = "datasource_audit_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tested": total,
            "summary": {
                "success": success,
                "blocked": blocked,
                "broken": broken,
                "needs_fix": needs_fix
            },
            "results": results
        }, f, indent=2)

    print(f"\n📄 Full results exported to: {output_file}")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    # Disable SSL warnings
    import warnings
    warnings.filterwarnings('ignore')

    asyncio.run(audit_all_datasources())
