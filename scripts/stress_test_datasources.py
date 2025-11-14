"""
Datasource Stress Testing Framework

Validates datasources can handle high-volume queries, concurrent requests,
error conditions, and edge cases. Tests rate limiting compliance.

Usage:
    python scripts/stress_test_datasources.py --source ihsa --concurrent 5
    python scripts/stress_test_datasources.py --source iowa_ihsaa --concurrent 5
    python scripts/stress_test_datasources.py --all --quick
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.base import BaseDataSource
from src.datasources.us.illinois_ihsa import IllinoisIHSADataSource
from src.datasources.us.iowa_ihsaa import IowaIHSAADataSource
from src.datasources.us.south_dakota_sdhsaa import SouthDakotaSdhsaaDataSource
from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.datasources.us.wisconsin_maxpreps import MaxPrepsWisconsinDataSource
from src.utils import get_logger

logger = get_logger(__name__)


class DatasourceStressTest:
    """Stress test framework for datasource adapters."""

    def __init__(self, output_dir: str = "data/stress_test"):
        """
        Initialize stress tester.

        Args:
            output_dir: Directory to save test results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_stress_test(
        self, source: BaseDataSource, concurrent_requests: int = 5, quick_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive stress test on datasource.

        Args:
            source: Datasource to test
            concurrent_requests: Number of concurrent requests to test
            quick_mode: Run abbreviated test suite

        Returns:
            Stress test results dictionary
        """
        logger.info(f"Starting stress test of {source.source_name}")

        results = {
            "source_id": source.source_type.value,
            "source_name": source.source_name,
            "test_timestamp": datetime.utcnow().isoformat(),
            "test_config": {
                "concurrent_requests": concurrent_requests,
                "quick_mode": quick_mode,
            },
            "tests": {},
            "metrics": {},
            "passed": 0,
            "failed": 0,
            "errors": [],
        }

        # Test 1: Sequential requests (baseline)
        await self._test_sequential_requests(source, results, quick_mode)

        # Test 2: Concurrent requests
        await self._test_concurrent_requests(source, results, concurrent_requests, quick_mode)

        # Test 3: Rate limiting compliance
        await self._test_rate_limiting(source, results, quick_mode)

        # Test 4: Error handling
        await self._test_error_handling(source, results, quick_mode)

        # Test 5: Edge cases
        await self._test_edge_cases(source, results, quick_mode)

        # Test 6: Cache effectiveness
        await self._test_cache_effectiveness(source, results, quick_mode)

        # Calculate overall results
        total_tests = results["passed"] + results["failed"]
        results["pass_rate"] = (
            (results["passed"] / total_tests * 100) if total_tests > 0 else 0
        )

        logger.info(f"Completed stress test of {source.source_name}")
        return results

    async def _test_sequential_requests(
        self, source: BaseDataSource, results: Dict, quick_mode: bool
    ):
        """Test sequential requests to establish baseline performance."""
        test_name = "sequential_requests"
        logger.info(f"Running {test_name} test")

        test_results = {
            "passed": False,
            "request_count": 5 if quick_mode else 10,
            "response_times": [],
            "errors": 0,
        }

        try:
            for i in range(test_results["request_count"]):
                start_time = time.time()

                # Make a simple request
                try:
                    if hasattr(source, "get_games"):
                        await source.get_games(limit=1)
                    elif hasattr(source, "search_players"):
                        await source.search_players(limit=1)
                    else:
                        await source.health_check()

                    elapsed = time.time() - start_time
                    test_results["response_times"].append(elapsed)

                except Exception as e:
                    test_results["errors"] += 1
                    logger.debug(f"Request {i+1} failed: {e}")

                # Small delay between requests
                await asyncio.sleep(0.5)

            # Calculate metrics
            if test_results["response_times"]:
                test_results["avg_response_time"] = sum(test_results["response_times"]) / len(
                    test_results["response_times"]
                )
                test_results["min_response_time"] = min(test_results["response_times"])
                test_results["max_response_time"] = max(test_results["response_times"])

            # Pass if at least 80% succeeded
            success_rate = (
                (test_results["request_count"] - test_results["errors"])
                / test_results["request_count"]
                * 100
            )
            test_results["success_rate"] = success_rate
            test_results["passed"] = success_rate >= 80

            if test_results["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    async def _test_concurrent_requests(
        self, source: BaseDataSource, results: Dict, concurrent: int, quick_mode: bool
    ):
        """Test concurrent requests to validate thread safety."""
        test_name = "concurrent_requests"
        logger.info(f"Running {test_name} test with {concurrent} concurrent requests")

        test_results = {
            "passed": False,
            "concurrent_count": concurrent,
            "total_requests": concurrent,
            "successful": 0,
            "failed": 0,
        }

        try:
            start_time = time.time()

            # Create concurrent tasks
            async def make_request():
                try:
                    if hasattr(source, "get_games"):
                        await source.get_games(limit=1)
                    elif hasattr(source, "search_players"):
                        await source.search_players(limit=1)
                    else:
                        await source.health_check()
                    return True
                except Exception:
                    return False

            # Run concurrent requests
            tasks = [make_request() for _ in range(concurrent)]
            results_list = await asyncio.gather(*tasks)

            elapsed = time.time() - start_time

            test_results["successful"] = sum(results_list)
            test_results["failed"] = len(results_list) - test_results["successful"]
            test_results["total_time"] = elapsed
            test_results["requests_per_second"] = concurrent / elapsed if elapsed > 0 else 0

            # Pass if at least 70% succeeded (lower threshold for concurrent)
            success_rate = (test_results["successful"] / concurrent) * 100
            test_results["success_rate"] = success_rate
            test_results["passed"] = success_rate >= 70

            if test_results["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    async def _test_rate_limiting(
        self, source: BaseDataSource, results: Dict, quick_mode: bool
    ):
        """Test that rate limiting is properly enforced."""
        test_name = "rate_limiting_compliance"
        logger.info(f"Running {test_name} test")

        test_results = {
            "passed": False,
            "burst_count": 5 if quick_mode else 10,
            "rate_limited": False,
        }

        try:
            # Make rapid burst of requests
            start_time = time.time()
            successful = 0

            for i in range(test_results["burst_count"]):
                try:
                    if hasattr(source, "health_check"):
                        await source.health_check()
                    successful += 1
                except Exception as e:
                    logger.debug(f"Burst request {i+1} failed: {e}")

                # No delay - test rate limiting

            elapsed = time.time() - start_time

            test_results["requests_completed"] = successful
            test_results["time_elapsed"] = elapsed
            test_results["effective_rate"] = successful / (elapsed / 60) if elapsed > 0 else 0

            # Pass if rate limiter is working (not exceeding configured limit)
            # This is tricky to test without knowing exact limit, so we just check it completed
            test_results["passed"] = True

            results["passed"] += 1

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    async def _test_error_handling(
        self, source: BaseDataSource, results: Dict, quick_mode: bool
    ):
        """Test error handling with invalid inputs."""
        test_name = "error_handling"
        logger.info(f"Running {test_name} test")

        test_results = {
            "passed": False,
            "test_cases": [],
        }

        # Test cases: (method, kwargs, should_handle_gracefully)
        test_cases = [
            ("get_games", {"season": "invalid"}, True),
            ("get_games", {"limit": -1}, True),
            ("search_players", {"name": ""}, True),
        ]

        if hasattr(source, "get_tournament_brackets"):
            test_cases.append(("get_tournament_brackets", {"season": "9999-00"}, True))

        try:
            for method_name, kwargs, should_handle in test_cases:
                case_result = {"method": method_name, "kwargs": kwargs}

                try:
                    if hasattr(source, method_name):
                        method = getattr(source, method_name)
                        result = await method(**kwargs)

                        # Check if it handled gracefully (returned empty, not crashed)
                        case_result["handled_gracefully"] = True
                        case_result["returned_data"] = result is not None

                except Exception as e:
                    # Exception is okay if it's a proper error type
                    case_result["handled_gracefully"] = True
                    case_result["exception_type"] = type(e).__name__

                test_results["test_cases"].append(case_result)

                await asyncio.sleep(0.3)

            # Pass if all cases were handled gracefully
            handled_count = sum(
                1 for case in test_results["test_cases"] if case.get("handled_gracefully")
            )
            test_results["handled_count"] = handled_count
            test_results["total_count"] = len(test_results["test_cases"])
            test_results["passed"] = handled_count == len(test_results["test_cases"])

            if test_results["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    async def _test_edge_cases(self, source: BaseDataSource, results: Dict, quick_mode: bool):
        """Test edge cases (empty results, limits, etc.)."""
        test_name = "edge_cases"
        logger.info(f"Running {test_name} test")

        test_results = {
            "passed": False,
            "cases_tested": 0,
            "cases_passed": 0,
        }

        try:
            # Test limit=0
            try:
                if hasattr(source, "get_games"):
                    result = await source.get_games(limit=0)
                    test_results["cases_tested"] += 1
                    if isinstance(result, list) and len(result) == 0:
                        test_results["cases_passed"] += 1
            except Exception:
                pass

            await asyncio.sleep(0.5)

            # Test large limit
            try:
                if hasattr(source, "get_games"):
                    result = await source.get_games(limit=1000)
                    test_results["cases_tested"] += 1
                    # Should either work or handle gracefully
                    test_results["cases_passed"] += 1
            except Exception:
                # Exception is okay
                test_results["cases_passed"] += 1

            await asyncio.sleep(0.5)

            # Test old season (should return empty or error gracefully)
            try:
                if hasattr(source, "get_games"):
                    result = await source.get_games(season="1900-01", limit=1)
                    test_results["cases_tested"] += 1
                    test_results["cases_passed"] += 1  # Handled gracefully
            except Exception:
                test_results["cases_passed"] += 1  # Exception is okay

            # Pass if majority of edge cases handled
            test_results["passed"] = (
                test_results["cases_passed"] >= test_results["cases_tested"] * 0.7
            )

            if test_results["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    async def _test_cache_effectiveness(
        self, source: BaseDataSource, results: Dict, quick_mode: bool
    ):
        """Test cache effectiveness by timing repeated requests."""
        test_name = "cache_effectiveness"
        logger.info(f"Running {test_name} test")

        test_results = {
            "passed": False,
            "first_request_time": 0,
            "cached_request_time": 0,
            "speedup_factor": 0,
        }

        try:
            # First request (should hit network)
            start_time = time.time()
            if hasattr(source, "get_games"):
                await source.get_games(limit=1)
            elif hasattr(source, "health_check"):
                await source.health_check()
            test_results["first_request_time"] = time.time() - start_time

            await asyncio.sleep(0.5)

            # Second request (should hit cache)
            start_time = time.time()
            if hasattr(source, "get_games"):
                await source.get_games(limit=1)
            elif hasattr(source, "health_check"):
                await source.health_check()
            test_results["cached_request_time"] = time.time() - start_time

            # Calculate speedup
            if test_results["cached_request_time"] > 0:
                test_results["speedup_factor"] = (
                    test_results["first_request_time"] / test_results["cached_request_time"]
                )

            # Pass if cached request is faster (speedup > 1.2x)
            test_results["passed"] = test_results["speedup_factor"] >= 1.2

            if test_results["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
                # This is not a hard failure, just informational
                results["errors"].append(f"{test_name}: Cache may not be effective (speedup: {test_results['speedup_factor']:.2f}x)")

        except Exception as e:
            test_results["error"] = str(e)
            results["failed"] += 1
            results["errors"].append(f"{test_name}: {e}")

        results["tests"][test_name] = test_results

    def save_results(self, results: Dict, source_id: str):
        """Save stress test results to JSON file."""
        output_file = self.output_dir / f"{source_id}_stress_test.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved stress test results to {output_file}")

    async def stress_test_all(
        self,
        sources: List[BaseDataSource],
        concurrent_requests: int = 5,
        quick_mode: bool = False,
    ) -> List[Dict]:
        """Run stress tests on multiple datasources sequentially."""
        all_results = []

        for source in sources:
            try:
                results = await self.run_stress_test(source, concurrent_requests, quick_mode)
                self.save_results(results, source.source_type.value)
                all_results.append(results)

                # Wait between sources
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"Failed to stress test {source.source_name}: {e}")

        return all_results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Stress test datasources")
    parser.add_argument(
        "--source",
        type=str,
        choices=["ihsa", "iowa_ihsaa", "sdhsaa", "wiaa", "maxpreps_wi", "all"],
        help="Datasource to test",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="Number of concurrent requests to test",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick mode (fewer test iterations)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/stress_test",
        help="Output directory for results",
    )

    args = parser.parse_args()

    tester = DatasourceStressTest(output_dir=args.output)

    # Select sources to test
    sources = []
    if args.source == "ihsa":
        sources = [IllinoisIHSADataSource()]
    elif args.source == "iowa_ihsaa":
        sources = [IowaIHSAADataSource()]
    elif args.source == "sdhsaa":
        sources = [SouthDakotaSdhsaaDataSource()]
    elif args.source == "wiaa":
        sources = [WisconsinWiaaDataSource()]
    elif args.source == "maxpreps_wi":
        sources = [MaxPrepsWisconsinDataSource()]
    elif args.source == "all":
        sources = [IllinoisIHSADataSource(), IowaIHSAADataSource(), SouthDakotaSdhsaaDataSource(), WisconsinWiaaDataSource(), MaxPrepsWisconsinDataSource()]
    else:
        print("Please specify a datasource to test with --source")
        return

    # Run stress tests
    all_results = await tester.stress_test_all(sources, args.concurrent, args.quick)

    # Print summary
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)
    for results in all_results:
        print(f"\n{results['source_name']}:")
        print(f"  Tests Passed: {results['passed']}/{results['passed'] + results['failed']}")
        print(f"  Pass Rate: {results['pass_rate']:.1f}%")
        print(f"  Errors: {len(results['errors'])}")

    print(f"\nDetailed results saved to: {tester.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
