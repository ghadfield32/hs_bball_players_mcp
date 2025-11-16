"""
247Sports API Endpoint Discovery Script

Systematically tests various API endpoint patterns to discover the correct
API structure for retrieving recruiting rankings.

This script tests:
1. Common REST API patterns
2. Different year formats (2025, 25, etc.)
3. Various query parameter combinations
4. Different base paths

Usage:
    python scripts/discover_247_api.py
    python scripts/discover_247_api.py --year 2025

Author: Claude Code
Date: 2025-11-15
Phase: 15 - API Discovery for Recruiting Data
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project HTTP client
from src.utils.http_client import HTTPClient


class API247Discoverer:
    """
    Discovers the correct API endpoint structure for 247Sports rankings.

    Tests various endpoint patterns systematically to find working APIs.
    """

    def __init__(self, class_year: int = 2025):
        """
        Initialize API discoverer.

        Args:
            class_year: Graduation year to test with
        """
        self.class_year = class_year
        self.base_url = "https://ipa.247sports.com"

        # Initialize HTTP client
        self.http_client = HTTPClient(source="247sports_api_discovery")

        # Common headers that might be needed
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://247sports.com/',
            'Origin': 'https://247sports.com'
        }

        self.successful_endpoints = []

    def generate_endpoint_patterns(self) -> List[Dict[str, Any]]:
        """
        Generate list of possible API endpoint patterns to test.

        Returns:
            List of endpoint configuration dictionaries
        """
        year_short = str(self.class_year)[-2:]  # Last 2 digits (e.g., "25")
        year_full = str(self.class_year)  # Full year (e.g., "2025")

        patterns = []

        # Pattern 1: RESTful /api/rankings/...
        patterns.extend([
            {
                'name': 'RESTful - Full Year',
                'url': f'{self.base_url}/api/rankings/basketball/{year_full}',
                'params': {}
            },
            {
                'name': 'RESTful - Full Year with Type',
                'url': f'{self.base_url}/api/rankings/basketball/{year_full}/composite',
                'params': {}
            },
            {
                'name': 'RESTful - Short Year',
                'url': f'{self.base_url}/api/rankings/basketball/{year_short}',
                'params': {}
            },
        ])

        # Pattern 2: /season/... path
        patterns.extend([
            {
                'name': 'Season Path - Full Year',
                'url': f'{self.base_url}/season/{year_full}/basketball/rankings',
                'params': {}
            },
            {
                'name': 'Season Path - Full Year with Composite',
                'url': f'{self.base_url}/season/{year_full}/basketball/composite',
                'params': {}
            },
        ])

        # Pattern 3: Query parameters
        patterns.extend([
            {
                'name': 'Query Params - rankings endpoint',
                'url': f'{self.base_url}/rankings',
                'params': {
                    'year': year_full,
                    'sport': 'basketball',
                    'type': 'composite'
                }
            },
            {
                'name': 'Query Params - api/rankings',
                'url': f'{self.base_url}/api/rankings',
                'params': {
                    'year': year_full,
                    'sport': 'basketball',
                    'rankingType': 'composite'
                }
            },
            {
                'name': 'Query Params - classYear',
                'url': f'{self.base_url}/api/rankings',
                'params': {
                    'classYear': year_full,
                    'sport': 'basketball'
                }
            },
        ])

        # Pattern 4: Composite specific
        patterns.extend([
            {
                'name': 'Composite - Direct Path',
                'url': f'{self.base_url}/composite/{year_full}/basketball',
                'params': {}
            },
            {
                'name': 'Composite - With Recruits',
                'url': f'{self.base_url}/recruits/composite/{year_full}/basketball',
                'params': {}
            },
        ])

        # Pattern 5: Player search/list endpoints
        patterns.extend([
            {
                'name': 'Players - List Endpoint',
                'url': f'{self.base_url}/api/players',
                'params': {
                    'year': year_full,
                    'sport': 'basketball',
                    'ranked': 'true'
                }
            },
            {
                'name': 'Recruits - List Endpoint',
                'url': f'{self.base_url}/api/recruits',
                'params': {
                    'classYear': year_full,
                    'sport': 'basketball'
                }
            },
        ])

        # Pattern 6: Data/feed endpoints
        patterns.extend([
            {
                'name': 'Data Feed - Rankings',
                'url': f'{self.base_url}/data/rankings/{year_full}/basketball',
                'params': {}
            },
            {
                'name': 'Feed - Rankings JSON',
                'url': f'{self.base_url}/feed/rankings',
                'params': {
                    'year': year_full,
                    'sport': 'basketball'
                }
            },
        ])

        return patterns

    async def test_endpoint(
        self,
        pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a single API endpoint pattern.

        Args:
            pattern: Endpoint configuration dictionary

        Returns:
            Result dictionary with test outcome
        """
        name = pattern['name']
        url = pattern['url']
        params = pattern.get('params', {})

        result = {
            'name': name,
            'url': url,
            'params': params,
            'success': False,
            'status_code': None,
            'content_type': None,
            'response_size': 0,
            'has_json': False,
            'has_rankings_data': False,
            'sample_data': None,
            'error': None
        }

        try:
            logger.info(f"Testing: {name}")
            logger.debug(f"  URL: {url}")
            if params:
                logger.debug(f"  Params: {params}")

            # Make request using HTTP client
            response = await self.http_client.get(
                url,
                params=params,
                headers=self.headers
            )

            result['status_code'] = response.status_code
            result['content_type'] = response.headers.get('Content-Type', '')

            # Get response body
            try:
                text = response.text
                result['response_size'] = len(text)

                # Try to parse as JSON
                if 'application/json' in result['content_type'] or text.startswith('{') or text.startswith('['):
                    try:
                        data = json.loads(text)
                        result['has_json'] = True

                        # Check if it looks like rankings data
                        result['has_rankings_data'] = self._looks_like_rankings(data)

                        if result['has_rankings_data']:
                            result['sample_data'] = self._extract_sample(data)
                            result['success'] = True
                            logger.info(f"  ✓ SUCCESS! Found rankings data")
                            self.successful_endpoints.append(result)
                        else:
                            logger.info(f"  ~ JSON response but no rankings data")
                    except json.JSONDecodeError:
                        logger.info(f"  ~ Not valid JSON")
                else:
                    logger.info(f"  ~ Non-JSON response")

            except Exception as e:
                result['error'] = f"Response parse error: {str(e)}"
                logger.info(f"  ✗ Error: {str(e)}")

            if response.status_code == 200:
                logger.info(f"  Status: 200 OK ({result['response_size']} bytes)")
            else:
                logger.info(f"  Status: {response.status_code}")

        except asyncio.TimeoutError:
            result['error'] = "Request timeout"
            logger.info(f"  ✗ Timeout")
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            logger.info(f"  ✗ {str(e)}")

        return result

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
            ranking_keys = ['rankings', 'recruits', 'players', 'results', 'data']
            for key in ranking_keys:
                if key in data:
                    potential_rankings = data[key]
                    if isinstance(potential_rankings, list) and len(potential_rankings) > 0:
                        # Check first item has ranking-like fields
                        first_item = potential_rankings[0]
                        if isinstance(first_item, dict):
                            ranking_fields = ['rank', 'rating', 'stars', 'name', 'position']
                            if any(field in first_item for field in ranking_fields):
                                return True

            # Check if data itself is a list of rankings
            if all(isinstance(data.get(k), (int, str, float, type(None))) for k in list(data.keys())[:5]):
                # Looks like a single player object
                ranking_fields = ['rank', 'rating', 'stars', 'name', 'position']
                if any(field in data for field in ranking_fields):
                    return True

        elif isinstance(data, list) and len(data) > 0:
            # Check if list items look like player rankings
            first_item = data[0]
            if isinstance(first_item, dict):
                ranking_fields = ['rank', 'rating', 'stars', 'name', 'position']
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
            for key in ['rankings', 'recruits', 'players', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    return {
                        'type': 'nested_list',
                        'key': key,
                        'total_count': len(data[key]),
                        'sample': data[key][:limit]
                    }
            # Return first few keys of dict
            return {
                'type': 'dict',
                'keys': list(data.keys())[:10],
                'sample': {k: data[k] for k in list(data.keys())[:limit] if k in data}
            }
        elif isinstance(data, list):
            return {
                'type': 'list',
                'total_count': len(data),
                'sample': data[:limit]
            }
        else:
            return {'type': 'other', 'sample': str(data)[:200]}

    async def run_discovery(self) -> List[Dict[str, Any]]:
        """
        Run full API endpoint discovery process.

        Returns:
            List of all test results
        """
        logger.info("="*60)
        logger.info(f"247Sports API Discovery - Class Year {self.class_year}")
        logger.info("="*60)
        logger.info("")

        # Generate patterns to test
        patterns = self.generate_endpoint_patterns()
        logger.info(f"Generated {len(patterns)} endpoint patterns to test")
        logger.info("")

        # Run tests
        results = []
        for i, pattern in enumerate(patterns, 1):
            logger.info(f"[{i}/{len(patterns)}] {pattern['name']}")
            result = await self.test_endpoint(pattern)
            results.append(result)
            logger.info("")

            # Small delay between requests to be polite
            await asyncio.sleep(0.5)

        # Close HTTP client
        await self.http_client.close()

        return results

    def print_summary(self, results: List[Dict[str, Any]]):
        """
        Print summary of discovery results.

        Args:
            results: List of test results
        """
        logger.info("="*60)
        logger.info("DISCOVERY SUMMARY")
        logger.info("="*60)
        logger.info("")

        successful = [r for r in results if r['success']]
        json_responses = [r for r in results if r['has_json']]
        errors_200 = [r for r in results if r['status_code'] == 200 and not r['success']]

        logger.info(f"Total endpoints tested: {len(results)}")
        logger.info(f"Successful (found rankings): {len(successful)}")
        logger.info(f"JSON responses: {len(json_responses)}")
        logger.info(f"200 OK (no rankings): {len(errors_200)}")
        logger.info("")

        if successful:
            logger.info("✓ SUCCESSFUL ENDPOINTS:")
            logger.info("")
            for result in successful:
                logger.info(f"  Name: {result['name']}")
                logger.info(f"  URL: {result['url']}")
                if result['params']:
                    logger.info(f"  Params: {result['params']}")
                logger.info(f"  Response size: {result['response_size']} bytes")
                logger.info(f"  Sample data:")
                logger.info(f"    {json.dumps(result['sample_data'], indent=4)[:500]}")
                logger.info("")
        else:
            logger.info("✗ No successful endpoints found")
            logger.info("")
            logger.info("This could mean:")
            logger.info("  1. API requires authentication")
            logger.info("  2. API uses different URL structure than tested")
            logger.info("  3. API is not publicly accessible")
            logger.info("  4. Need to analyze browser network requests directly")
            logger.info("")

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """
        Save results to JSON file.

        Args:
            results: List of test results
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump({
                'class_year': self.class_year,
                'total_tested': len(results),
                'successful': len(self.successful_endpoints),
                'results': results
            }, f, indent=2)

        logger.info(f"Results saved to: {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Discover 247Sports API endpoints")

    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Class year to test with (default: 2025)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='data/debug/api_discovery_results.json',
        help='Output JSON file for results'
    )

    args = parser.parse_args()

    # Run discovery
    discoverer = API247Discoverer(class_year=args.year)
    results = await discoverer.run_discovery()

    # Print summary
    discoverer.print_summary(results)

    # Save results
    discoverer.save_results(results, args.output)


if __name__ == '__main__':
    asyncio.run(main())
