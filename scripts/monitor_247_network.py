"""
247Sports Network Traffic Monitor

Uses Playwright to monitor actual network requests made by the 247Sports
rankings page to discover the real API endpoints.

This script:
1. Launches browser with network monitoring
2. Navigates to 247Sports rankings page
3. Captures all XHR/Fetch requests
4. Filters for JSON responses containing rankings data
5. Documents the actual API structure

Usage:
    python scripts/monitor_247_network.py
    python scripts/monitor_247_network.py --year 2025 --duration 30

Author: Claude Code
Date: 2025-11-15
Phase: 15 - API Discovery via Network Monitoring
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class NetworkMonitor:
    """
    Monitors network traffic on 247Sports page to discover API endpoints.
    """

    def __init__(self, class_year: int = 2025, monitor_duration: int = 30):
        """
        Initialize network monitor.

        Args:
            class_year: Graduation year to monitor
            monitor_duration: How long to monitor network traffic (seconds)
        """
        self.class_year = class_year
        self.monitor_duration = monitor_duration
        self.captured_requests = []
        self.api_requests = []

    async def monitor_page(self):
        """
        Monitor network traffic on 247Sports rankings page.

        Returns:
            List of captured API requests
        """
        from playwright.async_api import async_playwright

        url = f"https://247sports.com/season/{self.class_year}-basketball/compositerecruitrankings/"

        logger.info("="*60)
        logger.info(f"247Sports Network Traffic Monitor - Class {self.class_year}")
        logger.info("="*60)
        logger.info(f"Target URL: {url}")
        logger.info(f"Monitor duration: {self.monitor_duration} seconds")
        logger.info("")

        playwright = None
        browser = None
        context = None
        page = None

        try:
            # Launch browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Setup network request listener
            async def handle_request(request):
                """Capture all requests."""
                self.captured_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'headers': dict(request.headers) if request.headers else {}
                })

            async def handle_response(response):
                """Capture API responses."""
                # Filter for XHR/Fetch requests
                if response.request.resource_type in ['xhr', 'fetch']:
                    try:
                        url = response.url
                        status = response.status
                        content_type = response.headers.get('content-type', '')

                        logger.info(f"[API] {response.request.method} {url}")
                        logger.info(f"      Status: {status}, Type: {content_type}")

                        # Try to get response body
                        if status == 200:
                            try:
                                # Check if JSON
                                if 'application/json' in content_type:
                                    body = await response.json()

                                    # Check if it looks like rankings data
                                    if self._looks_like_rankings(body):
                                        logger.info(f"      ✓ RANKINGS DATA FOUND!")

                                        api_info = {
                                            'url': url,
                                            'method': response.request.method,
                                            'status': status,
                                            'content_type': content_type,
                                            'headers': dict(response.request.headers) if response.request.headers else {},
                                            'response_sample': self._extract_sample(body),
                                            'parsed_url': self._parse_url(url)
                                        }
                                        self.api_requests.append(api_info)

                                        # Save full response for analysis
                                        self._save_response(url, body)
                                    else:
                                        logger.info(f"      ~ JSON but no rankings data")
                                else:
                                    text_preview = await response.text()
                                    logger.info(f"      ~ Non-JSON: {text_preview[:100]}...")
                            except Exception as e:
                                logger.debug(f"      Error reading response: {str(e)}")
                    except Exception as e:
                        logger.debug(f"Error handling response: {str(e)}")

            # Register listeners
            page.on("request", handle_request)
            page.on("response", handle_response)

            # Navigate to page
            logger.info("Navigating to rankings page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for network activity
            logger.info(f"Monitoring network traffic for {self.monitor_duration} seconds...")
            logger.info("")
            await asyncio.sleep(self.monitor_duration)

            logger.info("")
            logger.info("Network monitoring complete")

        finally:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

        return self.api_requests

    def _looks_like_rankings(self, data: Any) -> bool:
        """
        Check if JSON data looks like recruiting rankings.

        Args:
            data: Parsed JSON data

        Returns:
            True if data appears to be rankings
        """
        # Check for common ranking data patterns
        if isinstance(data, dict):
            # Check for keys that indicate rankings
            ranking_keys = ['rankings', 'recruits', 'players', 'results', 'data', 'items']
            for key in ranking_keys:
                if key in data:
                    potential_rankings = data[key]
                    if isinstance(potential_rankings, list) and len(potential_rankings) > 0:
                        # Check first item has ranking-like fields
                        first_item = potential_rankings[0]
                        if isinstance(first_item, dict):
                            ranking_fields = ['rank', 'rating', 'stars', 'name', 'position', 'player']
                            if any(field in first_item for field in ranking_fields):
                                return True

        elif isinstance(data, list) and len(data) > 0:
            # Check if list items look like player rankings
            first_item = data[0]
            if isinstance(first_item, dict):
                ranking_fields = ['rank', 'rating', 'stars', 'name', 'position', 'player']
                if any(field in first_item for field in ranking_fields):
                    return True

        return False

    def _extract_sample(self, data: Any, limit: int = 3) -> Any:
        """
        Extract a small sample of the rankings data.

        Args:
            data: Full JSON data
            limit: Number of items to include in sample

        Returns:
            Sample of the data
        """
        if isinstance(data, dict):
            # Find the rankings list
            for key in ['rankings', 'recruits', 'players', 'results', 'data', 'items']:
                if key in data and isinstance(data[key], list):
                    return {
                        'structure': 'nested_dict',
                        'key': key,
                        'total_count': len(data[key]),
                        'sample_items': data[key][:limit],
                        'all_keys': list(data.keys())
                    }
            # Return structure info
            return {
                'structure': 'dict',
                'keys': list(data.keys())[:10],
                'sample': {k: str(data[k])[:100] for k in list(data.keys())[:limit] if k in data}
            }
        elif isinstance(data, list):
            return {
                'structure': 'list',
                'total_count': len(data),
                'sample_items': data[:limit]
            }
        else:
            return {'structure': 'other', 'sample': str(data)[:200]}

    def _parse_url(self, url: str) -> Dict[str, Any]:
        """
        Parse URL to extract structure information.

        Args:
            url: Full URL

        Returns:
            Dictionary with URL components
        """
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        return {
            'scheme': parsed.scheme,
            'domain': parsed.netloc,
            'path': parsed.path,
            'query_params': query_params,
            'fragment': parsed.fragment
        }

    def _save_response(self, url: str, data: Any):
        """
        Save API response to file for detailed analysis.

        Args:
            url: Request URL
            data: Response data
        """
        # Create safe filename from URL
        safe_name = url.replace('https://', '').replace('http://', '')
        safe_name = safe_name.replace('/', '_').replace('?', '_').replace('&', '_')
        safe_name = safe_name[:100]  # Limit length

        output_path = Path(f"data/debug/api_response_{safe_name}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"      Response saved to: {output_path.name}")

    def print_summary(self, api_requests: List[Dict[str, Any]]):
        """
        Print summary of discovered API endpoints.

        Args:
            api_requests: List of captured API requests
        """
        logger.info("")
        logger.info("="*60)
        logger.info("NETWORK MONITORING SUMMARY")
        logger.info("="*60)
        logger.info("")
        logger.info(f"Total requests captured: {len(self.captured_requests)}")
        logger.info(f"API requests with rankings data: {len(api_requests)}")
        logger.info("")

        if api_requests:
            logger.info("✓ DISCOVERED API ENDPOINTS:")
            logger.info("")
            for i, req in enumerate(api_requests, 1):
                logger.info(f"{i}. {req['method']} {req['url']}")
                logger.info(f"   Status: {req['status']}")
                logger.info(f"   Content-Type: {req['content_type']}")
                logger.info("")
                logger.info(f"   URL Structure:")
                logger.info(f"     Domain: {req['parsed_url']['domain']}")
                logger.info(f"     Path: {req['parsed_url']['path']}")
                if req['parsed_url']['query_params']:
                    logger.info(f"     Query Params: {req['parsed_url']['query_params']}")
                logger.info("")
                logger.info(f"   Response Structure:")
                sample = req['response_sample']
                logger.info(f"     Type: {sample.get('structure', 'unknown')}")
                if 'key' in sample:
                    logger.info(f"     Data Key: {sample['key']}")
                if 'total_count' in sample:
                    logger.info(f"     Items: {sample['total_count']}")
                logger.info("")
        else:
            logger.info("✗ No API endpoints with rankings data found")
            logger.info("")
            logger.info("This could mean:")
            logger.info("  1. Rankings loaded via different mechanism (WebSocket, etc.)")
            logger.info("  2. Need longer monitoring duration")
            logger.info("  3. Data embedded in page HTML/JavaScript")
            logger.info("  4. API requires specific user interactions to trigger")

    def save_results(self, output_path: str):
        """
        Save monitoring results to JSON file.

        Args:
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'class_year': self.class_year,
                'monitor_duration': self.monitor_duration,
                'total_requests': len(self.captured_requests),
                'api_requests_found': len(self.api_requests),
                'discovered_endpoints': self.api_requests,
                'all_requests': self.captured_requests[:100]  # Limit to first 100
            }, f, indent=2)

        logger.info(f"Results saved to: {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor 247Sports network traffic")

    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Class year to monitor (default: 2025)'
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Monitoring duration in seconds (default: 30)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='data/debug/network_monitor_results.json',
        help='Output JSON file for results'
    )

    args = parser.parse_args()

    # Run monitoring
    monitor = NetworkMonitor(class_year=args.year, monitor_duration=args.duration)
    api_requests = await monitor.monitor_page()

    # Print summary
    monitor.print_summary(api_requests)

    # Save results
    monitor.save_results(args.output)


if __name__ == '__main__':
    asyncio.run(main())
