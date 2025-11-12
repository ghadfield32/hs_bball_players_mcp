"""
Test Sample of State Association Adapters

Tests a representative sample of newly unblocked state adapters to determine:
- Which adapters work out-of-box
- Common failure patterns
- Which need URL/parsing fixes
- Which have off-season data issues

Sample Selection:
- 2-3 adapters per region (Southeast, Northeast, Midwest, Southwest/West)
- Mix of basketball hotbed states and smaller states
- Total: 10 adapters tested
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import (
    GeorgiaGhsaDataSource,           # Southeast - Basketball hotbed
    VirginiaVhslDataSource,          # Southeast - High priority
    AlabamaAhsaaDataSource,          # Southeast - Medium state
    PennsylvaniaPiaaDataSource,      # Northeast - Basketball hotbed
    NewJerseyNjsiaaDataSource,       # Northeast - High priority
    MassachusettsMiaaDataSource,     # Northeast - Prep basketball
    OhioOhsaaDataSource,             # Midwest - Basketball hotbed
    IndianaIhsaaDataSource,          # Midwest - Basketball tradition
    ColoradoChsaaDataSource,         # Southwest/West - Mountain state
    UtahUhsaaDataSource,             # Southwest/West - Growing market
)


# Test configuration
SAMPLE_ADAPTERS = [
    # Southeast (3)
    ("GeorgiaGhsaDataSource", GeorgiaGhsaDataSource, "GA", "Southeast"),
    ("VirginiaVhslDataSource", VirginiaVhslDataSource, "VA", "Southeast"),
    ("AlabamaAhsaaDataSource", AlabamaAhsaaDataSource, "AL", "Southeast"),

    # Northeast (3)
    ("PennsylvaniaPiaaDataSource", PennsylvaniaPiaaDataSource, "PA", "Northeast"),
    ("NewJerseyNjsiaaDataSource", NewJerseyNjsiaaDataSource, "NJ", "Northeast"),
    ("MassachusettsMiaaDataSource", MassachusettsMiaaDataSource, "MA", "Northeast"),

    # Midwest (2)
    ("OhioOhsaaDataSource", OhioOhsaaDataSource, "OH", "Midwest"),
    ("IndianaIhsaaDataSource", IndianaIhsaaDataSource, "IN", "Midwest"),

    # Southwest/West (2)
    ("ColoradoChsaaDataSource", ColoradoChsaaDataSource, "CO", "Southwest/West"),
    ("UtahUhsaaDataSource", UtahUhsaaDataSource, "UT", "Southwest/West"),
]

# Result categories
RESULTS = {
    "works": [],           # Returns data successfully
    "no_data": [],         # No errors but no data (off-season likely)
    "url_error": [],       # URL issues (404, timeout, connection)
    "parse_error": [],     # Parsing issues (selector not found, table missing)
    "json_needed": [],     # HTML only, needs JSON endpoint discovery
    "other_error": [],     # Other issues
}


async def test_adapter(name: str, adapter_class, state: str, region: str):
    """Test a single state adapter."""
    print(f"\n{'='*80}")
    print(f"TESTING: {name} ({state} - {region})")
    print(f"{'='*80}\n")

    result = {
        "name": name,
        "state": state,
        "region": region,
        "base_url": None,
        "health_check": None,
        "search_test": None,
        "error_type": None,
        "error_msg": None,
        "recommendation": None,
    }

    adapter = None
    try:
        # Initialize adapter
        adapter = adapter_class()
        result["base_url"] = adapter.base_url
        print(f"[OK] Adapter initialized")
        print(f"     Base URL: {adapter.base_url}")
        print(f"     Source Type: {adapter.source_type}")

        # Test health check
        print(f"\n[TEST] Health check...")
        health = await adapter.health_check()
        result["health_check"] = health

        if health:
            print(f"[OK] Health check passed")
        else:
            print(f"[WARN] Health check failed - site may be down")
            result["error_type"] = "health_check_failed"
            result["recommendation"] = "Site unreachable - check URL or wait for site recovery"

        # Test player search
        print(f"\n[TEST] Searching for players...")
        players = await adapter.search_players(limit=10)

        if players and len(players) > 0:
            print(f"[SUCCESS] Found {len(players)} players!")
            print(f"[SAMPLE] First player: {players[0].name}")
            result["search_test"] = "success"
            result["recommendation"] = "WORKS OUT-OF-BOX - Adapter ready for production"
            RESULTS["works"].append(result)
        else:
            print(f"[WARN] No players found")
            result["search_test"] = "no_data"
            result["recommendation"] = "Off-season or no data published - re-test during season (December+)"
            RESULTS["no_data"].append(result)

    except Exception as e:
        error_msg = str(e)
        result["error_msg"] = error_msg

        print(f"[ERROR] {error_msg}")

        # Categorize error
        if "404" in error_msg or "Not Found" in error_msg:
            result["error_type"] = "url_404"
            result["recommendation"] = "Update URL paths - association website structure changed"
            RESULTS["url_error"].append(result)
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            result["error_type"] = "timeout"
            result["recommendation"] = "Site slow or blocking - increase timeout or check anti-bot"
            RESULTS["url_error"].append(result)
        elif "connection" in error_msg.lower() or "unreachable" in error_msg.lower():
            result["error_type"] = "connection"
            result["recommendation"] = "Site unreachable - verify domain and URL structure"
            RESULTS["url_error"].append(result)
        elif "selector" in error_msg.lower() or "not found" in error_msg.lower():
            result["error_type"] = "parse"
            result["recommendation"] = "Update HTML selectors - website structure changed"
            RESULTS["parse_error"].append(result)
        elif "json" in error_msg.lower():
            result["error_type"] = "json"
            result["recommendation"] = "Implement JSON endpoint discovery"
            RESULTS["json_needed"].append(result)
        else:
            result["error_type"] = "other"
            result["recommendation"] = "Investigate error details"
            RESULTS["other_error"].append(result)

    finally:
        if adapter:
            await adapter.close()
            print(f"\n[OK] Adapter closed")

    return result


async def main():
    """Run all adapter tests."""
    print(f"\n{'#'*80}")
    print(f"# STATE ADAPTER SAMPLE TEST SUITE")
    print(f"# Testing {len(SAMPLE_ADAPTERS)} adapters across 4 regions")
    print(f"{'#'*80}\n")

    # Test all adapters sequentially
    all_results = []
    for name, adapter_class, state, region in SAMPLE_ADAPTERS:
        result = await test_adapter(name, adapter_class, state, region)
        all_results.append(result)

        # Brief pause between tests
        await asyncio.sleep(2)

    # Print summary
    print(f"\n\n{'#'*80}")
    print(f"# TEST SUMMARY")
    print(f"{'#'*80}\n")

    print(f"Total Adapters Tested: {len(all_results)}")
    print(f"  [OK] Works Out-of-Box:  {len(RESULTS['works'])}")
    print(f"  [WARN] No Data (likely off-season): {len(RESULTS['no_data'])}")
    print(f"  [FIX] URL Errors:        {len(RESULTS['url_error'])}")
    print(f"  [FIX] Parse Errors:      {len(RESULTS['parse_error'])}")
    print(f"  [FIX] JSON Needed:       {len(RESULTS['json_needed'])}")
    print(f"  [ERROR] Other Errors:    {len(RESULTS['other_error'])}")
    print()

    # Detailed results by category
    if RESULTS["works"]:
        print(f"\n{'='*80}")
        print(f"[OK] WORKING ADAPTERS ({len(RESULTS['works'])})")
        print(f"{'='*80}")
        for r in RESULTS["works"]:
            print(f"  * {r['state']:2} - {r['name']:30} - {r['base_url']}")
        print()

    if RESULTS["no_data"]:
        print(f"\n{'='*80}")
        print(f"[WARN] NO DATA (Off-Season) ({len(RESULTS['no_data'])})")
        print(f"{'='*80}")
        for r in RESULTS["no_data"]:
            print(f"  * {r['state']:2} - {r['name']:30} - {r['base_url']}")
        print(f"\nRecommendation: Re-test these adapters during active season (December 2025+)")
        print()

    if RESULTS["url_error"]:
        print(f"\n{'='*80}")
        print(f"[FIX] URL ERRORS ({len(RESULTS['url_error'])})")
        print(f"{'='*80}")
        for r in RESULTS["url_error"]:
            print(f"  * {r['state']:2} - {r['name']:30}")
            print(f"       URL: {r['base_url']}")
            print(f"       Error: {r['error_type']} - {r['error_msg'][:80]}")
            print(f"       Fix: {r['recommendation']}")
            print()

    if RESULTS["parse_error"]:
        print(f"\n{'='*80}")
        print(f"[FIX] PARSE ERRORS ({len(RESULTS['parse_error'])})")
        print(f"{'='*80}")
        for r in RESULTS["parse_error"]:
            print(f"  * {r['state']:2} - {r['name']:30}")
            print(f"       URL: {r['base_url']}")
            print(f"       Error: {r['error_msg'][:80]}")
            print(f"       Fix: {r['recommendation']}")
            print()

    if RESULTS["json_needed"]:
        print(f"\n{'='*80}")
        print(f"[FIX] JSON DISCOVERY NEEDED ({len(RESULTS['json_needed'])})")
        print(f"{'='*80}")
        for r in RESULTS["json_needed"]:
            print(f"  * {r['state']:2} - {r['name']:30} - {r['base_url']}")
        print()

    if RESULTS["other_error"]:
        print(f"\n{'='*80}")
        print(f"[ERROR] OTHER ERRORS ({len(RESULTS['other_error'])})")
        print(f"{'='*80}")
        for r in RESULTS["other_error"]:
            print(f"  * {r['state']:2} - {r['name']:30}")
            print(f"       Error: {r['error_msg'][:80]}")
            print()

    # Regional breakdown
    print(f"\n{'='*80}")
    print(f"REGIONAL BREAKDOWN")
    print(f"{'='*80}")

    regions = {}
    for r in all_results:
        region = r["region"]
        if region not in regions:
            regions[region] = {"total": 0, "works": 0, "no_data": 0, "errors": 0}

        regions[region]["total"] += 1
        if r["search_test"] == "success":
            regions[region]["works"] += 1
        elif r["search_test"] == "no_data":
            regions[region]["no_data"] += 1
        else:
            regions[region]["errors"] += 1

    for region, stats in sorted(regions.items()):
        print(f"\n{region}:")
        print(f"  Total Tested: {stats['total']}")
        print(f"  Works:        {stats['works']} ({stats['works']/stats['total']*100:.0f}%)")
        print(f"  No Data:      {stats['no_data']} ({stats['no_data']/stats['total']*100:.0f}%)")
        print(f"  Errors:       {stats['errors']} ({stats['errors']/stats['total']*100:.0f}%)")

    # Recommendations
    print(f"\n\n{'='*80}")
    print(f"RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if len(RESULTS["works"]) > 0:
        success_rate = len(RESULTS["works"]) / len(all_results) * 100
        print(f"1. SUCCESS RATE: {success_rate:.0f}% of tested adapters work out-of-box")
        print(f"   - These {len(RESULTS['works'])} adapters are production-ready")
        print(f"   - Extrapolate: ~{int(success_rate * 37 / 100)} of 37 total state adapters may work")
        print()

    if len(RESULTS["no_data"]) > 0:
        print(f"2. OFF-SEASON: {len(RESULTS['no_data'])} adapters returned no data")
        print(f"   - Likely due to November off-season timing")
        print(f"   - Re-test all adapters during active season (December 2025+)")
        print()

    if len(RESULTS["url_error"]) > 0:
        print(f"3. URL FIXES NEEDED: {len(RESULTS['url_error'])} adapters have connection issues")
        print(f"   - Investigate each URL manually")
        print(f"   - Update base_url in adapter files")
        print(f"   - Check for domain changes or rebranding")
        print()

    if len(RESULTS["parse_error"]) > 0:
        print(f"4. PARSER FIXES NEEDED: {len(RESULTS['parse_error'])} adapters have HTML parsing issues")
        print(f"   - Inspect current website HTML structure")
        print(f"   - Update CSS selectors in _parse_html_data() methods")
        print(f"   - Test JSON endpoint discovery as alternative")
        print()

    print(f"5. NEXT ACTIONS:")
    print(f"   a) Fix URL issues for adapters with connection errors")
    print(f"   b) Update parsers for adapters with selector issues")
    print(f"   c) Test remaining 27 state adapters (same sampling approach)")
    print(f"   d) Re-test all adapters during season (December+)")
    print(f"   e) Focus on Priority 2 fixes (3SSB, MN Hub, PSAL) based on learnings")
    print()


if __name__ == "__main__":
    asyncio.run(main())
