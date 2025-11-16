"""
Debug Script: Test SBLive and Bound Website Accessibility

Systematically tests actual website URLs to diagnose adapter issues.
NO assumptions - pure diagnostic testing.

Author: Debugging Session
Date: 2025-11-15
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_url_with_playwright(url: str, headless: bool = True) -> dict:
    """
    Test URL accessibility with Playwright browser automation.

    Returns diagnostic information without assumptions.
    """
    result = {
        'url': url,
        'accessible': False,
        'status_code': None,
        'final_url': None,
        'error': None,
        'page_title': None,
        'cloudflare_detected': False,
        'content_sample': None
    }

    try:
        async with async_playwright() as p:
            logger.info(f"Testing URL: {url}")
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            # Set realistic user agent
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                result['accessible'] = True
                result['status_code'] = response.status if response else None
                result['final_url'] = page.url
                result['page_title'] = await page.title()

                # Check for Cloudflare
                page_content = await page.content()
                if 'cloudflare' in page_content.lower() or 'cf-browser-verification' in page_content.lower():
                    result['cloudflare_detected'] = True

                # Get content sample
                result['content_sample'] = page_content[:500]

                logger.info(f"✓ SUCCESS: {url}")
                logger.info(f"  Status: {result['status_code']}")
                logger.info(f"  Title: {result['page_title']}")
                logger.info(f"  Cloudflare: {result['cloudflare_detected']}")

            except Exception as e:
                result['error'] = str(e)
                logger.error(f"✗ FAILED: {url}")
                logger.error(f"  Error: {str(e)}")

            finally:
                await browser.close()

    except Exception as e:
        result['error'] = f"Browser launch failed: {str(e)}"
        logger.error(f"✗ BROWSER FAILED: {url}")
        logger.error(f"  Error: {str(e)}")

    return result


async def main():
    """Run diagnostic tests on both SBLive and Bound URLs."""

    logger.info("=" * 80)
    logger.info("ADAPTER WEBSITE DIAGNOSTIC TEST")
    logger.info("=" * 80)

    # Test URLs
    test_cases = [
        # SBLive Tests
        ("SBLive WA (stats page)", "https://www.sblive.com/wa/basketball/stats"),
        ("SBLive WA (main)", "https://www.sblive.com/wa/basketball"),
        ("SBLive CA (stats page)", "https://www.sblive.com/ca/basketball/stats"),

        # Bound Tests - Test different URL patterns
        ("Bound IA (subdomain pattern)", "https://www.ia.bound.com/basketball"),
        ("Bound main site", "https://www.bound.com"),
        ("Bound IA (path pattern)", "https://www.bound.com/ia/basketball"),
        ("Bound IA (varsitybound)", "https://www.varsitybound.com/ia/basketball"),

        # Alternative Bound patterns
        ("Bound IA (iabound.com)", "https://www.iabound.com"),
        ("Bound IA (bound.com/iowa)", "https://www.bound.com/iowa/basketball"),
    ]

    results = []

    for name, url in test_cases:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {name}")
        logger.info(f"{'='*80}")

        result = await test_url_with_playwright(url, headless=True)
        result['test_name'] = name
        results.append(result)

        # Small delay between tests
        await asyncio.sleep(2)

    # Summary Report
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 80)

    accessible_urls = [r for r in results if r['accessible']]
    failed_urls = [r for r in results if not r['accessible']]

    logger.info(f"\n✓ Accessible URLs: {len(accessible_urls)}/{len(results)}")
    for r in accessible_urls:
        logger.info(f"  - {r['test_name']}")
        logger.info(f"    URL: {r['url']}")
        logger.info(f"    Title: {r['page_title']}")
        if r['cloudflare_detected']:
            logger.warning(f"    WARNING: Cloudflare detected!")

    logger.info(f"\n✗ Failed URLs: {len(failed_urls)}/{len(results)}")
    for r in failed_urls:
        logger.info(f"  - {r['test_name']}")
        logger.info(f"    URL: {r['url']}")
        logger.info(f"    Error: {r['error']}")

    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 80)

    # Generate recommendations based on results
    sblive_accessible = any('sblive.com' in r['url'] and r['accessible'] for r in results)
    bound_accessible = any('bound' in r['url'].lower() and r['accessible'] for r in results)

    if sblive_accessible:
        logger.info("\n✓ SBLive: Website accessible")
        cloudflare_found = any('sblive.com' in r['url'] and r['cloudflare_detected'] for r in results)
        if cloudflare_found:
            logger.info("  - ACTION: Implement Cloudflare bypass (stealth mode, delays)")
    else:
        logger.warning("\n✗ SBLive: Website NOT accessible")
        logger.warning("  - ACTION: Verify domain, check network, or find alternative source")

    if bound_accessible:
        logger.info("\n✓ Bound: Website accessible")
        working_url = next((r['url'] for r in results if 'bound' in r['url'].lower() and r['accessible']), None)
        logger.info(f"  - Working URL pattern: {working_url}")
    else:
        logger.warning("\n✗ Bound: No accessible URLs found")
        logger.warning("  - ACTION: Research actual Bound/VarsityBound domain")
        logger.warning("  - POSSIBILITY: Service may be renamed, moved, or discontinued")

    logger.info("\n" + "=" * 80)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nTest failed: {str(e)}", exc_info=True)
