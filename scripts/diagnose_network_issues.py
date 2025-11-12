"""
Diagnose Network Issues - SBLive, Bound, WSN

Systematic investigation following debugging methodology:
1. Don't fill in missing values
2. Dissect the problem with debugs
3. Examine expected vs actual behavior
4. Review error messages in detail
5. Trace execution step by step
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.http_client import HTTPClient


async def diagnose_sblive():
    """Diagnose SBLive anti-bot blocking issue."""
    print("=" * 80)
    print("ISSUE 1: SBLIVE - ANTI-BOT BLOCKING")
    print("=" * 80)
    print("\n[EXPECTED BEHAVIOR]")
    print("  HTTP GET request should return HTML with player statistics tables")
    print("\n[ACTUAL BEHAVIOR - from stress test]")
    print("  'Network/timeout error: GET https://www.sblive.com/wa/basketball/stats")
    print("  [source=sblive | error=]'")
    print("  Empty error message = connection reset by server without details")
    print("\n[HYPOTHESIS]")
    print("  Strong anti-bot protection (Cloudflare, Akamai, or similar)")
    print("  Server detecting automated traffic and blocking requests")
    print("")

    client = HTTPClient(source="diagnose_sblive")
    test_states = ["wa", "ca", "az"]

    print("[STEP 1] Testing direct HTTP requests to SBLive...")
    for state in test_states:
        url = f"https://www.sblive.com/{state}/basketball/stats"
        print(f"\n  Testing: {url}")

        try:
            html = await client.get_text(url, use_cache=False, timeout=15)
            print(f"    [UNEXPECTED SUCCESS] Got {len(html)} chars")
            print(f"    Website is accessible - may need to check parsing logic")
            # If we get here, the issue might be intermittent or resolved
            break
        except asyncio.TimeoutError:
            print(f"    [ERROR] Timeout after 15 seconds")
            print(f"    Analysis: Request hanging, no response from server")
        except ConnectionResetError:
            print(f"    [ERROR] Connection reset by peer")
            print(f"    Analysis: Server actively rejecting connection")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "<empty>"
            print(f"    [ERROR] {error_type}: {error_msg}")

            # Detailed error analysis
            if not error_msg or error_msg == "<empty>":
                print(f"\n    [ANALYSIS] Empty error message indicates:")
                print(f"      - Connection closed by server before response")
                print(f"      - Likely anti-bot protection (Cloudflare, etc.)")
                print(f"      - Possible TLS fingerprinting detection")
            elif "SSL" in error_msg or "certificate" in error_msg.lower():
                print(f"\n    [ANALYSIS] SSL/TLS error indicates:")
                print(f"      - Certificate validation issue")
                print(f"      - Or TLS version mismatch")
            elif "ECONNREFUSED" in error_msg:
                print(f"\n    [ANALYSIS] Connection refused:")
                print(f"      - Server actively rejecting connections")
                print(f"      - Possible IP-based blocking")

    print(f"\n[STEP 2] Recommendations:")
    print(f"  1. Use browser automation (Playwright) instead of HTTP client")
    print(f"  2. Add realistic headers and user-agent")
    print(f"  3. Implement cookie persistence")
    print(f"  4. Add delays between requests")
    print(f"  5. Consider rotating user-agents")
    print("")

    await client.close()


async def diagnose_bound():
    """Diagnose Bound domain unreachability issue."""
    print("=" * 80)
    print("ISSUE 2: BOUND - DOMAIN UNREACHABILITY")
    print("=" * 80)
    print("\n[EXPECTED BEHAVIOR]")
    print("  HTTP GET request should return HTML from state-specific subdomain")
    print("\n[ACTUAL BEHAVIOR - from stress test]")
    print("  'Network/timeout error: GET https://www.ia.bound.com/basketball/stats")
    print("  [source=bound | error=All connection attempts failed]'")
    print("  All 30 requests failed with same error")
    print("\n[HYPOTHESIS]")
    print("  Domain doesn't exist or URL pattern is incorrect")
    print("  Possible causes:")
    print("    1. Bound rebranded/changed domains")
    print("    2. Subdomain pattern is wrong")
    print("    3. Company was acquired/shut down")
    print("")

    client = HTTPClient(source="diagnose_bound")

    print("[STEP 1] Testing Bound URL patterns...")

    # Test different URL patterns for Iowa (primary state)
    test_patterns = [
        ("Current pattern", "https://www.ia.bound.com"),
        ("No www", "https://ia.bound.com"),
        ("Path-based", "https://www.bound.com/ia"),
        ("Path-based no www", "https://bound.com/ia"),
        ("Main domain", "https://www.bound.com"),
        ("Main domain no www", "https://bound.com"),
        ("Old branding", "https://www.varsitybound.com"),
        ("Old branding no www", "https://varsitybound.com"),
    ]

    found_working = False
    for pattern_name, url in test_patterns:
        print(f"\n  {pattern_name}: {url}")

        try:
            html = await client.get_text(url, use_cache=False, timeout=10)
            print(f"    [SUCCESS] Reachable! ({len(html)} chars)")
            print(f"    Found working URL pattern!")
            found_working = True

            # Check if it looks like a basketball stats site
            if "basketball" in html.lower():
                print(f"    [CONFIRMED] Contains 'basketball' - likely correct site")
            else:
                print(f"    [WARN] No 'basketball' mention - may be wrong site")

            break  # Found working pattern, stop testing
        except asyncio.TimeoutError:
            print(f"    [FAIL] Timeout (10s)")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "<empty>"
            print(f"    [FAIL] {error_type}: {error_msg[:80]}")

    if not found_working:
        print(f"\n  [CRITICAL] No working URL pattern found!")
        print(f"\n  [STEP 2] Research needed:")
        print(f"    1. Google 'Bound high school basketball stats' ")
        print(f"    2. Check if company was acquired/rebranded")
        print(f"    3. Look for press releases about domain changes")
        print(f"    4. Check Iowa high school basketball forums")
        print(f"    5. Consider alternative Midwest stats sources")
    else:
        print(f"\n  [STEP 2] Update adapter with correct URL pattern")

    print("")
    await client.close()


async def diagnose_wsn():
    """Diagnose WSN (Wisconsin Sports Network) status."""
    print("=" * 80)
    print("ISSUE 3: WSN - WEBSITE STATUS CHECK")
    print("=" * 80)
    print("\n[EXPECTED BEHAVIOR]")
    print("  Website is defunct (merged with MaxPreps)")
    print("  Need to find alternative Wisconsin stats source")
    print("\n[ACTUAL TEST RESULT - from earlier diagnostic]")
    print("  Website reachable! (40,972 chars)")
    print("  This contradicts the 'defunct' hypothesis!")
    print("\n[NEW HYPOTHESIS]")
    print("  Website EXISTS but may have:")
    print("    1. Changed structure/format")
    print("    2. Moved stats to different pages")
    print("    3. No active basketball data")
    print("")

    client = HTTPClient(source="diagnose_wsn")

    print("[STEP 1] Testing WSN website and basketball pages...")

    test_urls = [
        ("Main site", "https://www.wissports.net"),
        ("Main no www", "https://wissports.net"),
        ("Basketball", "https://www.wissports.net/basketball"),
        ("Basketball stats", "https://www.wissports.net/basketball/stats"),
        ("Boys basketball", "https://www.wissports.net/boys-basketball"),
    ]

    for url_name, url in test_urls:
        print(f"\n  {url_name}: {url}")

        try:
            html = await client.get_text(url, use_cache=False, timeout=10)
            print(f"    [SUCCESS] Reachable ({len(html)} chars)")

            # Quick content analysis
            html_lower = html.lower()
            indicators = {
                "basketball": "basketball" in html_lower,
                "stats": "stats" in html_lower or "statistics" in html_lower,
                "player": "player" in html_lower,
                "team": "team" in html_lower,
                "schedule": "schedule" in html_lower or "scores" in html_lower,
            }

            found_any = sum(indicators.values())
            if found_any > 0:
                print(f"    [CONTENT] Found {found_any}/5 basketball indicators:")
                for key, value in indicators.items():
                    if value:
                        print(f"      ✓ {key}")
            else:
                print(f"    [WARN] No basketball-related content found")

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "<empty>"
            print(f"    [FAIL] {error_type}: {error_msg[:80]}")

    print(f"\n[STEP 2] Recommendations:")
    print(f"  If WSN has basketball content:")
    print(f"    1. Inspect HTML structure to update parsing logic")
    print(f"    2. Check if stats are behind login/paywall")
    print(f"  If WSN lacks basketball content:")
    print(f"    1. Research Wisconsin alternatives (WIAA, MaxPreps, etc.)")
    print(f"    2. Consider deprecating WSN adapter")
    print("")

    await client.close()


async def main():
    """Run all network diagnostics."""
    print("\n")
    print("=" * 80)
    print("NETWORK ISSUES DIAGNOSTIC")
    print("=" * 80)
    print("Systematic investigation of SBLive, Bound, and WSN network issues")
    print("=" * 80)
    print("\n")

    await diagnose_sblive()
    await diagnose_bound()
    await diagnose_wsn()

    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("")


if __name__ == "__main__":
    asyncio.run(main())
