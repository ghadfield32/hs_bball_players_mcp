"""
Stress Test Script for Multi-State Adapters

Tests multi-state adapters under high concurrent load to validate:
- Rate limiting behavior
- Concurrent request handling
- Error recovery
- Cache effectiveness
- Response times under stress

Usage:
    python scripts/stress_test_adapters.py              # Test all multi-state adapters
    python scripts/stress_test_adapters.py --adapter sblive  # Test specific adapter
    python scripts/stress_test_adapters.py --requests 50    # Custom request count
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.sblive import SBLiveDataSource
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.rankone import RankOneDataSource


class StressTestRunner:
    """Runs stress tests on multi-state adapters."""

    def __init__(self, requests_per_adapter: int = 100, concurrency: int = 10):
        """
        Initialize stress test runner.

        Args:
            requests_per_adapter: Total requests to send to each adapter
            concurrency: Number of concurrent requests to send
        """
        self.requests_per_adapter = requests_per_adapter
        self.concurrency = concurrency
        self.results = {}

    async def stress_test_adapter(
        self,
        adapter_class,
        adapter_name: str,
        states: List[str],
    ) -> Dict:
        """
        Stress test a single multi-state adapter.

        Args:
            adapter_class: Adapter class to test
            adapter_name: Human-readable adapter name
            states: List of states supported by adapter

        Returns:
            Dictionary with stress test results
        """
        print(f"\n{'='*70}")
        print(f"STRESS TESTING: {adapter_name}")
        print(f"{'='*70}")
        print(f"States: {', '.join(states)}")
        print(f"Total requests: {self.requests_per_adapter}")
        print(f"Concurrency: {self.concurrency}")

        results = {
            "adapter": adapter_name,
            "states": states,
            "total_requests": self.requests_per_adapter,
            "concurrency": self.concurrency,
            "successful_requests": 0,
            "failed_requests": 0,
            "timeouts": 0,
            "rate_limit_hits": 0,
            "response_times": [],
            "errors_by_type": defaultdict(int),
            "requests_by_state": defaultdict(int),
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
        }

        try:
            adapter = adapter_class()
            print(f"\n[OK] Adapter initialized")

            results["start_time"] = datetime.now()
            start_timestamp = time.time()

            # Create task queue
            tasks = []
            for i in range(self.requests_per_adapter):
                # Distribute requests across states
                state = states[i % len(states)]
                task = self._make_request(
                    adapter=adapter,
                    state=state,
                    request_id=i,
                    results=results,
                )
                tasks.append(task)

            print(f"\n[INFO] Executing {len(tasks)} concurrent requests...")

            # Execute requests in batches (respecting concurrency limit)
            for i in range(0, len(tasks), self.concurrency):
                batch = tasks[i:i + self.concurrency]
                await asyncio.gather(*batch, return_exceptions=True)

                # Progress indicator
                completed = min(i + self.concurrency, len(tasks))
                progress = (completed / len(tasks)) * 100
                print(f"  Progress: {completed}/{len(tasks)} requests ({progress:.1f}%)")

            results["end_time"] = datetime.now()
            results["duration_seconds"] = time.time() - start_timestamp

            # Calculate statistics
            if results["response_times"]:
                times = results["response_times"]
                results["avg_response_time"] = sum(times) / len(times)
                results["min_response_time"] = min(times)
                results["max_response_time"] = max(times)
                results["p50_response_time"] = self._percentile(times, 50)
                results["p95_response_time"] = self._percentile(times, 95)
                results["p99_response_time"] = self._percentile(times, 99)
            else:
                results["avg_response_time"] = 0
                results["min_response_time"] = 0
                results["max_response_time"] = 0

            # Calculate requests per second
            if results["duration_seconds"] > 0:
                results["requests_per_second"] = (
                    results["successful_requests"] / results["duration_seconds"]
                )
            else:
                results["requests_per_second"] = 0

            # Cleanup
            await adapter.close()
            print(f"\n[OK] Adapter closed")

            # Print summary
            self._print_adapter_summary(results)

        except Exception as e:
            print(f"\n[CRITICAL FAIL] Stress test failed: {str(e)}")
            results["critical_error"] = str(e)

        return results

    async def _make_request(
        self,
        adapter,
        state: str,
        request_id: int,
        results: Dict,
    ):
        """
        Make a single request and record results.

        Args:
            adapter: Adapter instance
            state: State to query
            request_id: Unique request identifier
            results: Results dictionary to update
        """
        start_time = time.time()

        try:
            # Make request (search_players with small limit for speed)
            players = await adapter.search_players(state=state, limit=5)

            # Record success
            response_time = time.time() - start_time
            results["successful_requests"] += 1
            results["response_times"].append(response_time)
            results["requests_by_state"][state] += 1

        except asyncio.TimeoutError:
            results["failed_requests"] += 1
            results["timeouts"] += 1
            results["errors_by_type"]["TimeoutError"] += 1

        except Exception as e:
            results["failed_requests"] += 1
            error_type = type(e).__name__

            # Check for rate limiting
            if "rate limit" in str(e).lower() or "429" in str(e):
                results["rate_limit_hits"] += 1
                error_type = "RateLimitError"

            results["errors_by_type"][error_type] += 1

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _print_adapter_summary(self, results: Dict):
        """Print summary for a single adapter."""
        print(f"\n{'='*70}")
        print(f"STRESS TEST RESULTS: {results['adapter']}")
        print(f"{'='*70}")

        # Request statistics
        print(f"\nRequest Statistics:")
        print(f"  Total Requests:      {results['total_requests']}")
        print(f"  Successful:          {results['successful_requests']} ({results['successful_requests']/results['total_requests']*100:.1f}%)")
        print(f"  Failed:              {results['failed_requests']} ({results['failed_requests']/results['total_requests']*100:.1f}%)")
        print(f"  Timeouts:            {results['timeouts']}")
        print(f"  Rate Limit Hits:     {results['rate_limit_hits']}")

        # Performance statistics
        print(f"\nPerformance:")
        print(f"  Duration:            {results['duration_seconds']:.2f}s")
        print(f"  Requests/Second:     {results['requests_per_second']:.2f}")
        print(f"  Avg Response Time:   {results['avg_response_time']*1000:.2f}ms")
        print(f"  Min Response Time:   {results['min_response_time']*1000:.2f}ms")
        print(f"  Max Response Time:   {results['max_response_time']*1000:.2f}ms")
        print(f"  P50 Response Time:   {results.get('p50_response_time', 0)*1000:.2f}ms")
        print(f"  P95 Response Time:   {results.get('p95_response_time', 0)*1000:.2f}ms")
        print(f"  P99 Response Time:   {results.get('p99_response_time', 0)*1000:.2f}ms")

        # Requests by state
        print(f"\nRequests by State:")
        for state, count in sorted(results['requests_by_state'].items()):
            print(f"  {state}: {count}")

        # Errors by type
        if results['errors_by_type']:
            print(f"\nErrors by Type:")
            for error_type, count in sorted(results['errors_by_type'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {error_type}: {count}")

    async def run_all_tests(
        self,
        specific_adapter: Optional[str] = None,
    ):
        """Run stress tests on all multi-state adapters."""
        print("="*70)
        print("MULTI-STATE ADAPTER STRESS TEST SUITE")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Requests per adapter: {self.requests_per_adapter}")
        print(f"Concurrency: {self.concurrency}")

        # Multi-state adapters with their supported states
        adapters = [
            (SBLiveDataSource, "SBLive Sports", ["WA", "OR", "CA", "AZ", "ID", "NV"]),
            (BoundDataSource, "Bound", ["IA", "SD", "IL", "MN"]),
            (RankOneDataSource, "RankOne Sport", ["TX", "KY", "IN", "OH", "TN"]),
        ]

        # Filter if specific adapter requested
        if specific_adapter:
            adapters = [
                (cls, name, states)
                for cls, name, states in adapters
                if specific_adapter.lower() in name.lower()
            ]

        for adapter_class, adapter_name, states in adapters:
            result = await self.stress_test_adapter(adapter_class, adapter_name, states)
            self.results[adapter_name] = result

        # Print overall summary
        self._print_overall_summary()

    def _print_overall_summary(self):
        """Print overall summary across all adapters."""
        print(f"\n\n{'='*70}")
        print("OVERALL STRESS TEST SUMMARY")
        print(f"{'='*70}")

        total_requests = sum(r['total_requests'] for r in self.results.values())
        total_successful = sum(r['successful_requests'] for r in self.results.values())
        total_failed = sum(r['failed_requests'] for r in self.results.values())
        total_rate_limits = sum(r['rate_limit_hits'] for r in self.results.values())

        print(f"\nAggregate Statistics:")
        print(f"  Adapters Tested:     {len(self.results)}")
        print(f"  Total Requests:      {total_requests}")
        print(f"  Total Successful:    {total_successful} ({total_successful/total_requests*100:.1f}%)")
        print(f"  Total Failed:        {total_failed} ({total_failed/total_requests*100:.1f}%)")
        print(f"  Total Rate Limits:   {total_rate_limits}")

        print(f"\nAdapter Performance Ranking:")
        # Sort by requests per second
        ranked = sorted(
            self.results.items(),
            key=lambda x: x[1].get('requests_per_second', 0),
            reverse=True
        )

        for rank, (adapter_name, result) in enumerate(ranked, 1):
            rps = result.get('requests_per_second', 0)
            success_rate = result['successful_requests'] / result['total_requests'] * 100
            avg_response = result.get('avg_response_time', 0) * 1000

            print(f"  {rank}. {adapter_name}:")
            print(f"     RPS: {rps:.2f} | Success: {success_rate:.1f}% | Avg Response: {avg_response:.2f}ms")

        print(f"\n{'='*70}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Stress test multi-state basketball adapters")
    parser.add_argument("--adapter", help="Test specific adapter (e.g., 'sblive', 'bound')")
    parser.add_argument("--requests", type=int, default=100, help="Total requests per adapter (default: 100)")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests (default: 10)")
    args = parser.parse_args()

    runner = StressTestRunner(
        requests_per_adapter=args.requests,
        concurrency=args.concurrency,
    )

    asyncio.run(runner.run_all_tests(args.adapter))


if __name__ == "__main__":
    main()
