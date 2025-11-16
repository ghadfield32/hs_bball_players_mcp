"""
Browser Crash Debugging Script

Systematically tests different browser configurations to identify
why 247Sports page crashes.

DO NOT FIX ANYTHING - ONLY OBSERVE AND LOG

Phase 1: Test different browser settings
Phase 2: Test different URLs (control vs 247Sports)
Phase 3: Identify exact crash point

Usage:
    python scripts/debug_browser_crash.py

Author: Claude Code
Date: 2025-11-15
Purpose: Systematic debugging of browser crash issue
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BrowserCrashDebugger:
    """
    Systematically tests browser configurations to identify crash cause.
    """

    def __init__(self):
        """Initialize debugger."""
        self.test_results = []
        self.control_url = "https://example.com"  # Simple page that should work
        self.target_url = "https://247sports.com/season/2025-basketball/compositerecruitrankings/"

    async def test_scenario(
        self,
        scenario_name: str,
        browser_type: str = "chromium",
        headless: bool = True,
        extra_args: list = None,
        url: str = None
    ) -> Dict[str, Any]:
        """
        Test a specific browser configuration scenario.

        Args:
            scenario_name: Description of test scenario
            browser_type: Browser to use
            headless: Headless mode
            extra_args: Additional browser arguments
            url: URL to test (defaults to target_url)

        Returns:
            Test result dictionary
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

        url = url or self.target_url
        extra_args = extra_args or []

        logger.info("="*60)
        logger.info(f"TEST SCENARIO: {scenario_name}")
        logger.info(f"  Browser: {browser_type}")
        logger.info(f"  Headless: {headless}")
        logger.info(f"  Extra args: {extra_args}")
        logger.info(f"  URL: {url}")
        logger.info("="*60)

        result = {
            'scenario': scenario_name,
            'browser_type': browser_type,
            'headless': headless,
            'extra_args': extra_args,
            'url': url,
            'success': False,
            'error': None,
            'error_type': None,
            'html_length': 0,
            'crash_point': None
        }

        playwright = None
        browser = None
        context = None
        page = None

        try:
            # PHASE 1: Initialize Playwright
            logger.info("[PHASE 1] Initializing Playwright...")
            playwright = await async_playwright().start()
            logger.info("[PHASE 1] ✓ Playwright initialized")
            result['crash_point'] = 'after_playwright_init'

            # PHASE 2: Launch browser
            logger.info(f"[PHASE 2] Launching {browser_type} browser...")
            browser_launcher = getattr(playwright, browser_type)

            # Build args list
            args = []
            if browser_type == "chromium":
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                ]
                args.extend(extra_args)
                logger.info(f"[PHASE 2] Chromium args: {args}")

            browser = await browser_launcher.launch(
                headless=headless,
                args=args if browser_type == "chromium" else []
            )
            logger.info("[PHASE 2] ✓ Browser launched")
            result['crash_point'] = 'after_browser_launch'

            # PHASE 3: Create context
            logger.info("[PHASE 3] Creating browser context...")
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ignore_https_errors=True,
            )
            logger.info("[PHASE 3] ✓ Context created")
            result['crash_point'] = 'after_context_creation'

            # PHASE 4: Create page
            logger.info("[PHASE 4] Creating page...")
            page = await context.new_page()
            logger.info("[PHASE 4] ✓ Page created")
            result['crash_point'] = 'after_page_creation'

            # PHASE 5: Navigate to URL
            logger.info(f"[PHASE 5] Navigating to URL: {url}")
            logger.info("[PHASE 5] Starting page.goto()...")

            # Try navigation with detailed error catching
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                logger.info(f"[PHASE 5] ✓ Navigation completed: status={response.status}")
                result['crash_point'] = 'after_navigation'
                result['response_status'] = response.status

            except PlaywrightTimeoutError as e:
                logger.error(f"[PHASE 5] ✗ TIMEOUT during navigation: {str(e)}")
                result['error'] = f"Timeout: {str(e)}"
                result['error_type'] = 'PlaywrightTimeoutError'
                result['crash_point'] = 'during_navigation_timeout'
                return result

            except Exception as e:
                logger.error(f"[PHASE 5] ✗ CRASH during navigation: {str(e)}")
                logger.error(f"[PHASE 5]    Error type: {type(e).__name__}")
                result['error'] = str(e)
                result['error_type'] = type(e).__name__
                result['crash_point'] = 'during_navigation_crash'

                # Check if it's the "page crashed" error
                if "page crashed" in str(e).lower():
                    logger.error("[PHASE 5]    ⚠️  PAGE CRASH CONFIRMED")
                    logger.error("[PHASE 5]    This indicates anti-bot detection or browser incompatibility")

                return result

            # PHASE 6: Wait for network idle
            logger.info("[PHASE 6] Waiting for network idle...")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("[PHASE 6] ✓ Network idle achieved")
                result['crash_point'] = 'after_network_idle'
            except PlaywrightTimeoutError:
                logger.warning("[PHASE 6] ⚠️  Network idle timeout (continuing)")
                result['crash_point'] = 'network_idle_timeout'

            # PHASE 7: Get page content
            logger.info("[PHASE 7] Getting page content...")
            html = await page.content()
            html_length = len(html)
            logger.info(f"[PHASE 7] ✓ Got HTML content: {html_length} bytes")
            result['html_length'] = html_length
            result['crash_point'] = 'after_content_extraction'

            # PHASE 8: Check for table element (247Sports specific)
            logger.info("[PHASE 8] Checking for table element...")
            try:
                table = await page.wait_for_selector("table", timeout=5000)
                if table:
                    logger.info("[PHASE 8] ✓ Table element found")
                    result['table_found'] = True
            except PlaywrightTimeoutError:
                logger.warning("[PHASE 8] ⚠️  No table found within timeout")
                result['table_found'] = False

            # SUCCESS
            logger.info("="*60)
            logger.info(f"✅ SCENARIO PASSED: {scenario_name}")
            logger.info(f"   HTML size: {html_length} bytes")
            logger.info("="*60)

            result['success'] = True
            return result

        except Exception as e:
            logger.error("="*60)
            logger.error(f"❌ SCENARIO FAILED: {scenario_name}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Crash point: {result['crash_point']}")
            logger.error("="*60)

            result['error'] = str(e)
            result['error_type'] = type(e).__name__
            return result

        finally:
            # Cleanup
            logger.info("[CLEANUP] Starting cleanup...")
            if page:
                try:
                    await page.close()
                    logger.info("[CLEANUP] ✓ Page closed")
                except:
                    logger.warning("[CLEANUP] ⚠️  Failed to close page")

            if context:
                try:
                    await context.close()
                    logger.info("[CLEANUP] ✓ Context closed")
                except:
                    logger.warning("[CLEANUP] ⚠️  Failed to close context")

            if browser:
                try:
                    await browser.close()
                    logger.info("[CLEANUP] ✓ Browser closed")
                except:
                    logger.warning("[CLEANUP] ⚠️  Failed to close browser")

            if playwright:
                try:
                    await playwright.stop()
                    logger.info("[CLEANUP] ✓ Playwright stopped")
                except:
                    logger.warning("[CLEANUP] ⚠️  Failed to stop Playwright")

    async def run_all_tests(self):
        """Run all test scenarios."""
        logger.info("\n" + "="*80)
        logger.info("BROWSER CRASH DEBUGGING SESSION")
        logger.info("="*80 + "\n")

        # TEST 1: Control test - Simple page, headless Chromium
        logger.info("\n" + "-"*80)
        logger.info("TEST 1: Control Test (example.com, headless)")
        logger.info("-"*80)
        result1 = await self.test_scenario(
            scenario_name="Control: example.com with headless Chromium",
            browser_type="chromium",
            headless=True,
            url=self.control_url
        )
        self.test_results.append(result1)
        await asyncio.sleep(2)

        # TEST 2: 247Sports with headless Chromium (expected to fail)
        logger.info("\n" + "-"*80)
        logger.info("TEST 2: 247Sports with headless Chromium (BASELINE)")
        logger.info("-"*80)
        result2 = await self.test_scenario(
            scenario_name="247Sports with headless Chromium (baseline)",
            browser_type="chromium",
            headless=True,
            url=self.target_url
        )
        self.test_results.append(result2)
        await asyncio.sleep(2)

        # TEST 3: 247Sports with NON-headless Chromium
        logger.info("\n" + "-"*80)
        logger.info("TEST 3: 247Sports with visible Chromium (headless=False)")
        logger.info("-"*80)
        result3 = await self.test_scenario(
            scenario_name="247Sports with visible Chromium",
            browser_type="chromium",
            headless=False,
            url=self.target_url
        )
        self.test_results.append(result3)
        await asyncio.sleep(2)

        # TEST 4: 247Sports with additional anti-detection flags
        logger.info("\n" + "-"*80)
        logger.info("TEST 4: 247Sports with enhanced anti-detection flags")
        logger.info("-"*80)
        result4 = await self.test_scenario(
            scenario_name="247Sports with enhanced anti-detection",
            browser_type="chromium",
            headless=True,
            extra_args=[
                "--window-size=1920,1080",
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ],
            url=self.target_url
        )
        self.test_results.append(result4)
        await asyncio.sleep(2)

        # TEST 5: 247Sports with Firefox
        logger.info("\n" + "-"*80)
        logger.info("TEST 5: 247Sports with Firefox")
        logger.info("-"*80)
        result5 = await self.test_scenario(
            scenario_name="247Sports with Firefox (headless)",
            browser_type="firefox",
            headless=True,
            url=self.target_url
        )
        self.test_results.append(result5)
        await asyncio.sleep(2)

        # Print summary
        await self.print_summary()

    async def print_summary(self):
        """Print test results summary."""
        logger.info("\n" + "="*80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*80 + "\n")

        passed = [r for r in self.test_results if r['success']]
        failed = [r for r in self.test_results if not r['success']]

        logger.info(f"Total tests: {len(self.test_results)}")
        logger.info(f"Passed: {len(passed)} ✅")
        logger.info(f"Failed: {len(failed)} ❌")
        logger.info("")

        if failed:
            logger.info("Failed scenarios:")
            for result in failed:
                logger.info(f"  ❌ {result['scenario']}")
                logger.info(f"     Error: {result['error_type']} - {result['error']}")
                logger.info(f"     Crash point: {result['crash_point']}")
                logger.info("")

        if passed:
            logger.info("Passed scenarios:")
            for result in passed:
                logger.info(f"  ✅ {result['scenario']}")
                logger.info(f"     HTML size: {result['html_length']} bytes")
                logger.info("")

        logger.info("="*80)
        logger.info("DEBUGGING CONCLUSIONS:")
        logger.info("="*80)

        # Analyze patterns
        if all(r['success'] for r in self.test_results if r['url'] == self.control_url):
            logger.info("✓ Control test passed - browser is working correctly")

        if all(not r['success'] for r in self.test_results if r['url'] == self.target_url and r['headless']):
            logger.info("✗ ALL headless 247Sports tests failed - likely anti-bot detection")

        if any(r['success'] for r in self.test_results if r['url'] == self.target_url and not r['headless']):
            logger.info("✓ Non-headless succeeded - CONFIRMS anti-bot detection")
            logger.info("  → 247Sports detects and blocks headless browsers")

        if all("page crashed" in str(r['error']).lower() for r in failed if r['url'] == self.target_url):
            logger.info("✗ Consistent 'page crashed' error - browser incompatibility or deliberate crash")

        logger.info("\nRECOMMENDED NEXT STEPS:")
        logger.info("1. If non-headless works: Consider using visible browser or different approach")
        logger.info("2. If all Chromium fails but Firefox works: Switch to Firefox")
        logger.info("3. If all browsers fail: 247Sports has strong anti-bot, consider alternatives:")
        logger.info("   - Use HTTP client if possible (check if API exists)")
        logger.info("   - Use different recruiting service (On3, Rivals)")
        logger.info("   - Manual data import from CSV/Excel")
        logger.info("="*80)


async def main():
    """Main entry point."""
    debugger = BrowserCrashDebugger()
    await debugger.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())
