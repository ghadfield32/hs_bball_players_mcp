"""
Performance Benchmarking Script for All Adapters

Measures and compares adapter performance across:
- Response times (search, stats, leaderboards)
- Cache effectiveness
- Data quality metrics
- Resource usage
- Method-level performance

Creates detailed performance reports for optimization.

Usage:
    python scripts/benchmark_adapters.py                    # Benchmark all adapters
    python scripts/benchmark_adapters.py --adapter sblive   # Benchmark specific adapter
    python scripts/benchmark_adapters.py --output report.json  # Save to file
"""

import asyncio
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import tracemalloc

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.sblive import SBLiveDataSource
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.rankone import RankOneDataSource
from src.datasources.us.three_ssb import ThreeSSBDataSource
from src.datasources.us.wsn import WSNDataSource
from src.datasources.us.fhsaa import FHSAADataSource
from src.datasources.us.hhsaa import HHSAADataSource
from src.datasources.us.mn_hub import MNHubDataSource
from src.datasources.us.psal import PSALDataSource


class PerformanceBenchmark:
    """Performance benchmarking for basketball data adapters."""

    def __init__(self):
        """Initialize benchmark runner."""
        self.results = {}

    async def benchmark_adapter(
        self,
        adapter_class,
        adapter_name: str,
        test_state: Optional[str] = None,
    ) -> Dict:
        """
        Benchmark a single adapter across all methods.

        Args:
            adapter_class: Adapter class to benchmark
            adapter_name: Human-readable adapter name
            test_state: State to test (for multi-state adapters)

        Returns:
            Dictionary with benchmark results
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARKING: {adapter_name}")
        print(f"{'='*70}")

        results = {
            "adapter": adapter_name,
            "adapter_class": adapter_class.__name__,
            "test_state": test_state,
            "timestamp": datetime.now().isoformat(),
            "methods": {},
            "cache_metrics": {},
            "data_quality": {},
            "resource_usage": {},
            "errors": [],
        }

        try:
            # Start memory tracking
            tracemalloc.start()
            mem_start = tracemalloc.get_traced_memory()[0]

            adapter = adapter_class()
            print(f"[OK] Adapter initialized")

            # Determine if multi-state adapter
            is_multi_state = hasattr(adapter_class, 'SUPPORTED_STATES')
            if is_multi_state and not test_state:
                test_state = adapter_class.SUPPORTED_STATES[0]
                print(f"[INFO] Using state: {test_state}")

            # Benchmark: health_check
            await self._benchmark_method(
                adapter=adapter,
                method_name="health_check",
                method_kwargs={},
                results=results,
            )

            # Benchmark: search_players
            search_kwargs = {"limit": 10}
            if is_multi_state:
                search_kwargs["state"] = test_state

            players = await self._benchmark_method(
                adapter=adapter,
                method_name="search_players",
                method_kwargs=search_kwargs,
                results=results,
            )

            # Benchmark: get_player_season_stats (if players found)
            if players and len(players) > 0:
                player_id = players[0].player_id
                await self._benchmark_method(
                    adapter=adapter,
                    method_name="get_player_season_stats",
                    method_kwargs={"player_id": player_id},
                    results=results,
                )

                # Benchmark: get_player (if available)
                await self._benchmark_method(
                    adapter=adapter,
                    method_name="get_player",
                    method_kwargs={"player_id": player_id},
                    results=results,
                )

            # Benchmark: get_leaderboard
            leaderboard_kwargs = {"stat": "points", "limit": 10}
            if is_multi_state:
                leaderboard_kwargs["state"] = test_state

            await self._benchmark_method(
                adapter=adapter,
                method_name="get_leaderboard",
                method_kwargs=leaderboard_kwargs,
                results=results,
            )

            # Test cache effectiveness (run search_players again)
            print(f"\n[INFO] Testing cache effectiveness...")
            first_run = results["methods"]["search_players"]["response_time"]

            # Second run (should hit cache)
            start = time.time()
            await adapter.search_players(**search_kwargs)
            second_run = time.time() - start

            results["cache_metrics"]["first_run_time"] = first_run
            results["cache_metrics"]["second_run_time"] = second_run
            results["cache_metrics"]["cache_speedup"] = (
                first_run / second_run if second_run > 0 else 0
            )
            results["cache_metrics"]["cache_effective"] = second_run < first_run

            print(f"  First run:  {first_run*1000:.2f}ms")
            print(f"  Second run: {second_run*1000:.2f}ms")
            print(f"  Speedup:    {results['cache_metrics']['cache_speedup']:.2f}x")

            # Calculate data quality metrics
            self._calculate_data_quality(results)

            # Memory usage
            mem_end = tracemalloc.get_traced_memory()[0]
            mem_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()

            results["resource_usage"]["memory_used_mb"] = (mem_end - mem_start) / 1024 / 1024
            results["resource_usage"]["memory_peak_mb"] = mem_peak / 1024 / 1024

            # Cleanup
            await adapter.close()
            print(f"\n[OK] Adapter closed")

            # Print summary
            self._print_adapter_summary(results)

        except Exception as e:
            print(f"\n[FAIL] Benchmark failed: {str(e)}")
            results["errors"].append({
                "message": str(e),
                "traceback": str(e.__traceback__)
            })

        return results

    async def _benchmark_method(
        self,
        adapter,
        method_name: str,
        method_kwargs: Dict[str, Any],
        results: Dict,
        runs: int = 3,
    ) -> Any:
        """
        Benchmark a single adapter method.

        Args:
            adapter: Adapter instance
            method_name: Method name to benchmark
            method_kwargs: Method arguments
            results: Results dictionary to update
            runs: Number of benchmark runs

        Returns:
            Method return value from last run
        """
        print(f"\n[BENCHMARK] {method_name}()")

        method = getattr(adapter, method_name)
        times = []
        return_value = None
        error = None

        for run in range(runs):
            try:
                start = time.time()
                return_value = await method(**method_kwargs)
                elapsed = time.time() - start
                times.append(elapsed)

                print(f"  Run {run + 1}: {elapsed*1000:.2f}ms")

            except Exception as e:
                error = str(e)
                print(f"  Run {run + 1}: FAILED - {error}")
                break

        # Calculate statistics
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            results["methods"][method_name] = {
                "response_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "runs": len(times),
                "success": error is None,
                "return_count": len(return_value) if isinstance(return_value, list) else (1 if return_value else 0),
            }

            if error:
                results["methods"][method_name]["error"] = error

            print(f"  Average: {avg_time*1000:.2f}ms")
        else:
            results["methods"][method_name] = {
                "response_time": 0,
                "runs": 0,
                "success": False,
                "error": error or "No successful runs",
            }

        return return_value

    def _calculate_data_quality(self, results: Dict):
        """Calculate data quality metrics."""
        methods = results["methods"]

        # Check which methods returned data
        data_availability = {
            "search_players": methods.get("search_players", {}).get("return_count", 0) > 0,
            "get_leaderboard": methods.get("get_leaderboard", {}).get("return_count", 0) > 0,
            "get_player_season_stats": methods.get("get_player_season_stats", {}).get("success", False),
        }

        results["data_quality"] = {
            "has_players": data_availability["search_players"],
            "has_leaderboard": data_availability["get_leaderboard"],
            "has_stats": data_availability["get_player_season_stats"],
            "completeness_score": sum(data_availability.values()) / len(data_availability) * 100,
        }

    def _print_adapter_summary(self, results: Dict):
        """Print summary for a single adapter."""
        print(f"\n{'='*70}")
        print(f"BENCHMARK RESULTS: {results['adapter']}")
        print(f"{'='*70}")

        # Method performance
        print(f"\nMethod Performance:")
        for method_name, metrics in results["methods"].items():
            status = "[OK]" if metrics["success"] else "[FAIL]"
            time_ms = metrics["response_time"] * 1000
            count = metrics.get("return_count", 0)

            print(f"  {status} {method_name:30} {time_ms:8.2f}ms  (returned {count} items)")

        # Cache metrics
        if results["cache_metrics"]:
            print(f"\nCache Effectiveness:")
            cache = results["cache_metrics"]
            print(f"  First run:      {cache['first_run_time']*1000:.2f}ms")
            print(f"  Cached run:     {cache['second_run_time']*1000:.2f}ms")
            print(f"  Speedup:        {cache['cache_speedup']:.2f}x")
            print(f"  Cache working:  {'YES' if cache['cache_effective'] else 'NO'}")

        # Data quality
        if results["data_quality"]:
            quality = results["data_quality"]
            print(f"\nData Quality:")
            print(f"  Has Players:    {'YES' if quality['has_players'] else 'NO'}")
            print(f"  Has Leaderboard:{'YES' if quality['has_leaderboard'] else 'NO'}")
            print(f"  Has Stats:      {'YES' if quality['has_stats'] else 'NO'}")
            print(f"  Completeness:   {quality['completeness_score']:.1f}%")

        # Resource usage
        if results["resource_usage"]:
            memory = results["resource_usage"]
            print(f"\nResource Usage:")
            print(f"  Memory Used:    {memory['memory_used_mb']:.2f} MB")
            print(f"  Memory Peak:    {memory['memory_peak_mb']:.2f} MB")

    async def run_all_benchmarks(
        self,
        specific_adapter: Optional[str] = None,
        output_file: Optional[str] = None,
    ):
        """Run benchmarks on all adapters."""
        print("="*70)
        print("ADAPTER PERFORMANCE BENCHMARK SUITE")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # All adapters with test states (for multi-state)
        adapters = [
            (SBLiveDataSource, "SBLive Sports", "WA"),
            (BoundDataSource, "Bound", "IA"),
            (RankOneDataSource, "RankOne Sport", "TX"),
            (ThreeSSBDataSource, "Adidas 3SSB", None),
            (WSNDataSource, "Wisconsin Sports Network", None),
            (FHSAADataSource, "Florida HSAA", None),
            (HHSAADataSource, "Hawaii HSAA", None),
            (MNHubDataSource, "Minnesota Basketball Hub", None),
            (PSALDataSource, "PSAL NYC", None),
        ]

        # Filter if specific adapter requested
        if specific_adapter:
            adapters = [
                (cls, name, state)
                for cls, name, state in adapters
                if specific_adapter.lower() in name.lower()
            ]

        for adapter_class, adapter_name, test_state in adapters:
            result = await self.benchmark_adapter(adapter_class, adapter_name, test_state)
            self.results[adapter_name] = result

        # Print overall summary
        self._print_overall_summary()

        # Save to file if requested
        if output_file:
            self._save_results(output_file)

    def _print_overall_summary(self):
        """Print overall summary across all adapters."""
        print(f"\n\n{'='*70}")
        print("OVERALL BENCHMARK SUMMARY")
        print(f"{'='*70}")

        # Performance ranking
        print(f"\nAdapter Performance Ranking (by avg search_players time):")
        ranked = sorted(
            [
                (name, r["methods"].get("search_players", {}).get("response_time", 999))
                for name, r in self.results.items()
                if r["methods"].get("search_players", {}).get("success", False)
            ],
            key=lambda x: x[1]
        )

        for rank, (adapter_name, response_time) in enumerate(ranked, 1):
            print(f"  {rank}. {adapter_name:40} {response_time*1000:8.2f}ms")

        # Data quality ranking
        print(f"\nData Completeness Ranking:")
        quality_ranked = sorted(
            [
                (name, r["data_quality"].get("completeness_score", 0))
                for name, r in self.results.items()
            ],
            key=lambda x: x[1],
            reverse=True
        )

        for rank, (adapter_name, score) in enumerate(quality_ranked, 1):
            print(f"  {rank}. {adapter_name:40} {score:5.1f}%")

        print(f"\n{'='*70}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

    def _save_results(self, output_file: str):
        """Save benchmark results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[OK] Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark basketball data adapters")
    parser.add_argument("--adapter", help="Benchmark specific adapter (e.g., 'sblive', 'bound')")
    parser.add_argument("--output", help="Save results to JSON file")
    args = parser.parse_args()

    benchmark = PerformanceBenchmark()
    asyncio.run(benchmark.run_all_benchmarks(args.adapter, args.output))


if __name__ == "__main__":
    main()
