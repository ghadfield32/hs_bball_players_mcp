"""
Test Priority Adapters - SBLive, Bound, WSN

Systematic investigation of the 3 remaining priority adapters:
1. SBLive: Network timeout / anti-bot blocking
2. Bound: Domain unreachability / "All connection attempts failed"
3. WSN: Defunct website investigation

Following debugging methodology:
- Don't fill in missing values or cover up problems
- Dissect the problem, add debugs
- Examine expected vs actual behavior
- Review error messages in detail
- Trace code execution step by step
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import BoundDataSource, SBLiveDataSource, WSNDataSource
from src.services.rate_limiter import get_rate_limiter


async def test_rate_limiter_config():
    """First, verify rate limiter has correct configs for our 3 sources."""
    print("=" * 80)
    print("STEP 1: VERIFY RATE LIMITER CONFIGURATION")
    print("=" * 80)
    print("Expected: SBLive, Bound, WSN should have dedicated token buckets")
    print("Previous issue: Sources were falling back to shared default bucket\n")

    rate_limiter = get_rate_limiter()

    sources_to_check = {
        "sblive": 15,
        "bound": 20,
        "wsn": 15,
    }

    all_configured = True
    for source_key, expected_limit in sources_to_check.items():
        if source_key in rate_limiter.buckets:
            bucket = rate_limiter.buckets[source_key]
            actual_capacity = bucket.capacity
            print(f"  [OK] {source_key:10} -> Dedicated bucket with {int(actual_capacity):2} req/min capacity")

            if actual_capacity != expected_limit:
                print(f"       [WARN] Expected {expected_limit}, got {int(actual_capacity)}")
        else:
            print(f"  [FAIL] {source_key:10} -> No dedicated bucket found!")
            all_configured = False

    if all_configured:
        print(f"\n  [SUCCESS] All 3 sources have dedicated token buckets!")
    else:
        print(f"\n  [FAIL] Rate limiter configuration incomplete!")

    print("")
    return all_configured


async def test_sblive():
    """Test SBLive adapter - investigate anti-bot blocking."""
    print("=" * 80)
    print("STEP 2: INVESTIGATE SBLIVE ANTI-BOT BLOCKING")
    print("=" * 80)
    print("Error from stress test:")
    print("  'Network/timeout error: GET https://www.sblive.com/wa/basketball/stats [source=sblive | error=]'")
    print("  Empty error message suggests connection closed/reset without details")
    print("  Strong anti-bot protection suspected\n")

    adapter = None
    try:
        print("[1] Initializing SBLive adapter...")
        adapter = SBLiveDataSource()
        print(f"    Base URL: {adapter.base_url}")
        print(f"    HTTP Client: {adapter.http_client}")
        print(f"    States covered: {len(adapter.states)}")

        # Try Washington state first
        test_state = "WA"
        test_url = f"{adapter.base_url}/{test_state.lower()}/basketball/stats"
        print(f"\n[2] Testing HTTP request to: {test_url}")

        try:
            # This should trigger the same error we saw in stress test
            html = await adapter.http_client.get_text(test_url, use_cache=False)
            print(f"    [UNEXPECTED] Request succeeded! Got {len(html)} characters")
            print(f"    This suggests the website is accessible now")
        except Exception as e:
            print(f"    [EXPECTED ERROR] Request failed: {type(e).__name__}")
            print(f"    Error message: {str(e) if str(e) else '<empty>'}")
            print(f"\n    Analysis:")
            print(f"      - Empty error message = connection reset by server")
            print(f"      - Likely causes:")
            print(f"        1. Anti-bot protection (Cloudflare, Akamai, etc.)")
            print(f"        2. IP-based blocking")
            print(f"        3. User-Agent filtering")
            print(f"        4. TLS fingerprinting")

        print(f"\n[3] Checking if browser automation would help...")
        print(f"    Browser enabled: {adapter.browser_client is not None}")
        if adapter.browser_client:
            print(f"    Browser type: chromium (Playwright)")
            print(f"    Headless: True")
            print(f"\n    Recommendation: Try browser automation with:")
            print(f"      - Proper user-agent and headers")
            print(f"      - JavaScript execution")
            print(f"      - Cookie handling")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if adapter:
            await adapter.close()

    print("")


async def test_bound():
    """Test Bound adapter - investigate domain unreachability."""
    print("=" * 80)
    print("STEP 3: INVESTIGATE BOUND DOMAIN UNREACHABILITY")
    print("=" * 80)
    print("Error from stress test:")
    print("  'Network/timeout error: GET https://www.ia.bound.com/basketball/stats [source=bound | error=All connection attempts failed]'")
    print("  'All connection attempts failed' suggests domain doesn't exist or wrong URL pattern\n")

    adapter = None
    try:
        print("[1] Analyzing current Bound adapter configuration...")
        adapter = BoundDataSource()
        print(f"    Base URL: {adapter.base_url}")
        print(f"    HTTP Client: {adapter.http_client}")
        print(f"    States covered: {len(adapter.states)}")

        # Check URL pattern
        test_state = "IA"
        test_url = adapter._get_state_url(test_state, "/basketball/stats")
        print(f"\n[2] Current URL pattern: {test_url}")

        # Parse URL pattern
        from urllib.parse import urlparse
        parsed = urlparse(test_url)
        print(f"    Scheme: {parsed.scheme}")
        print(f"    Subdomain: {parsed.hostname}")
        print(f"    Path: {parsed.path}")

        print(f"\n[3] Problem identified:")
        print(f"    URL pattern www.{test_state.lower()}.bound.com may be incorrect")
        print(f"\n    Possible alternatives:")
        print(f"      1. bound.com/{test_state.lower()}/...")
        print(f"      2. {test_state.lower()}.bound.com/... (no www)")
        print(f"      3. varsitybound.com/... (old branding)")
        print(f"      4. Bound may have rebranded or been acquired")

        print(f"\n[4] Testing domain reachability...")
        test_domains = [
            f"https://www.{test_state.lower()}.bound.com",
            f"https://{test_state.lower()}.bound.com",
            "https://www.bound.com",
            "https://bound.com",
            "https://www.varsitybound.com",
            "https://varsitybound.com",
        ]

        for domain in test_domains:
            try:
                print(f"    Testing: {domain}...", end=" ")
                html = await adapter.http_client.get_text(domain, use_cache=False, timeout=10)
                print(f"[OK] Reachable! ({len(html)} chars)")
                break
            except Exception as e:
                error_msg = str(e) if str(e) else type(e).__name__
                print(f"[FAIL] {error_msg}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if adapter:
            await adapter.close()

    print("")


async def test_wsn():
    """Test WSN adapter - investigate defunct website."""
    print("=" * 80)
    print("STEP 4: INVESTIGATE WSN (WISCONSIN SPORTS NETWORK)")
    print("=" * 80)
    print("Known issue: WSN website may be defunct (merged with MaxPreps)")
    print("Need to find alternative Wisconsin high school stats source\n")

    adapter = None
    try:
        print("[1] Testing current WSN configuration...")
        adapter = WSNDataSource()
        print(f"    Base URL: {adapter.base_url}")
        print(f"    HTTP Client: {adapter.http_client}")

        print(f"\n[2] Testing website reachability...")
        try:
            html = await adapter.http_client.get_text(adapter.base_url, use_cache=False, timeout=10)
            print(f"    [UNEXPECTED] Website reachable! ({len(html)} chars)")
            print(f"    May need to investigate parsing logic instead")
        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            print(f"    [EXPECTED] Website unreachable: {error_msg}")

            print(f"\n[3] Searching for Wisconsin alternatives...")
            print(f"    Potential replacements:")
            print(f"      1. MaxPreps (maxpreps.com/wi/) - General coverage")
            print(f"      2. WIAA (wiaawi.org) - Official state association")
            print(f"      3. Wisconsin Basketball Yearbook")
            print(f"      4. SBLive Wisconsin (if available)")
            print(f"\n    Action needed: Research and implement alternative adapter")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if adapter:
            await adapter.close()

    print("")


async def main():
    """Run all diagnostic tests."""
    print("\n")
    print("=" * 80)
    print("PRIORITY ADAPTERS DIAGNOSTIC SUITE")
    print("=" * 80)
    print("Systematic investigation of SBLive, Bound, and WSN adapters")
    print("Following evidence-based debugging methodology")
    print("=" * 80)
    print("\n")

    # Step 1: Verify rate limiter configuration
    rate_limiter_ok = await test_rate_limiter_config()

    if not rate_limiter_ok:
        print("[CRITICAL] Rate limiter configuration incomplete!")
        print("Fix rate limiter before proceeding with network diagnostics")
        return

    # Step 2: Investigate SBLive anti-bot
    await test_sblive()

    # Step 3: Investigate Bound domain
    await test_bound()

    # Step 4: Investigate WSN replacement
    await test_wsn()

    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Fix any rate limiter issues found")
    print("  2. Research SBLive anti-bot bypass strategies")
    print("  3. Investigate Bound domain/branding changes")
    print("  4. Find WSN replacement for Wisconsin coverage")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
