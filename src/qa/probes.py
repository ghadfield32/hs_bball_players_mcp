"""
QA Probes - Lightweight Endpoint Verification

Fast health checks for data sources to verify endpoints are accessible
before running expensive backfills.
"""

import asyncio
from typing import Optional

import httpx

from ..config import get_settings
from ..services.aggregator import get_aggregator, load_from_registry
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def probe_source(source_id: str, timeout: float = 10.0) -> tuple[str, bool, str]:
    """
    Light-weight probe for a single source.

    Args:
        source_id: Source identifier (e.g., "eybl", "psal")
        timeout: Request timeout in seconds

    Returns:
        Tuple of (source_id, success, note)
    """
    try:
        # Try to load the source from registry
        source_classes = load_from_registry()
        if source_id not in source_classes:
            return (source_id, False, "Source not found in registry")

        # Instantiate the source
        source_class = source_classes[source_id]
        source = source_class()

        # Perform health check
        is_healthy = await source.health_check()
        await source.close()

        if is_healthy:
            return (source_id, True, "OK")
        else:
            return (source_id, False, "Health check failed")

    except Exception as e:
        return (source_id, False, f"Error: {str(e)[:100]}")


async def probe_all_sources(
    source_ids: Optional[list[str]] = None,
    max_concurrency: int = 10,
) -> dict[str, tuple[bool, str]]:
    """
    Probe all sources (or subset) in parallel.

    Args:
        source_ids: List of source IDs to probe (None = all active sources)
        max_concurrency: Max concurrent probes

    Returns:
        Dictionary mapping source_id to (success, note)
    """
    # Determine which sources to probe
    if source_ids is None:
        # Load all active sources from registry
        source_classes = load_from_registry()
        source_ids = list(source_classes.keys())

    logger.info(f"Probing {len(source_ids)} sources...")

    # Create probe tasks with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded_probe(src_id: str):
        async with semaphore:
            return await probe_source(src_id)

    tasks = [bounded_probe(src_id) for src_id in source_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build result dictionary
    probe_results = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Probe task failed: {result}")
            continue

        src_id, success, note = result
        probe_results[src_id] = (success, note)

    # Log summary
    successful = sum(1 for ok, _ in probe_results.values() if ok)
    failed = len(probe_results) - successful

    logger.info(
        f"Probe complete: {successful} OK, {failed} failed",
        total=len(probe_results),
    )

    return probe_results


def print_probe_results(results: dict[str, tuple[bool, str]]) -> None:
    """
    Print probe results in a readable format.

    Args:
        results: Dictionary from probe_all_sources()
    """
    print()
    print("=" * 70)
    print("QA PROBE RESULTS")
    print("=" * 70)
    print()

    # Sort by source_id
    sorted_results = sorted(results.items())

    for source_id, (success, note) in sorted_results:
        status = "✅" if success else "❌"
        print(f"  {status} {source_id:25} {note}")

    print()
    print("-" * 70)

    successful = sum(1 for ok, _ in results.values() if ok)
    failed = len(results) - successful

    print(f"Total: {len(results)} sources")
    print(f"  ✅ OK: {successful}")
    print(f"  ❌ Failed: {failed}")
    print()


async def run_probes_cli(
    source_ids: Optional[list[str]] = None,
    max_concurrency: int = 10,
) -> int:
    """
    CLI entry point for running probes.

    Args:
        source_ids: List of source IDs to probe (None = all)
        max_concurrency: Max concurrent probes

    Returns:
        Exit code (0 = all passed, 1 = some failed)
    """
    results = await probe_all_sources(source_ids, max_concurrency)
    print_probe_results(results)

    # Return error code if any failed
    failed_count = sum(1 for ok, _ in results.values() if not ok)
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(run_probes_cli())
    sys.exit(exit_code)
