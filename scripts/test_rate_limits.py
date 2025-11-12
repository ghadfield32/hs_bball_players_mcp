"""
Test Rate Limiting Configuration at Runtime

Validates that the rate limiter properly instantiates token buckets
for all 16 configured datasources with correct rate limits.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.rate_limiter import get_rate_limiter
from src.models import DataSourceType


async def test_rate_limiter():
    """Test rate limiter has correct buckets configured."""
    print("=" * 80)
    print("RATE LIMITER RUNTIME VALIDATION")
    print("=" * 80)

    rate_limiter = get_rate_limiter()

    # Expected configured sources (should have dedicated buckets)
    expected_configured = {
        DataSourceType.EYBL: 30,
        DataSourceType.FIBA: 20,
        DataSourceType.PSAL: 15,
        DataSourceType.MN_HUB: 20,
        DataSourceType.GRIND_SESSION: 15,
        DataSourceType.OTE: 25,
        DataSourceType.ANGT: 20,
        DataSourceType.OSBA: 15,
        DataSourceType.PLAYHQ: 25,
        # Stats Adapters (High Priority)
        DataSourceType.BOUND: 20,
        DataSourceType.SBLIVE: 15,
        DataSourceType.THREE_SSB: 20,
        DataSourceType.WSN: 15,
        # Fixtures Adapters
        DataSourceType.RANKONE: 20,
        DataSourceType.FHSAA: 15,
        DataSourceType.HHSAA: 15,
    }

    print(f"\n[1] Checking Configured Token Buckets")
    print("=" * 80)

    all_passed = True
    for source_type, expected_limit in sorted(expected_configured.items(), key=lambda x: x[0].value):
        bucket_key = source_type.value

        if bucket_key in rate_limiter.buckets:
            bucket = rate_limiter.buckets[bucket_key]
            actual_capacity = bucket.capacity
            actual_refill = bucket.refill_rate * 60  # Convert back to per-minute

            # Check if capacity matches expected limit
            if actual_capacity == expected_limit:
                print(f"  [OK] {source_type.value:20} -> {int(actual_capacity):3} req/min (capacity={int(actual_capacity)}, refill={actual_refill:.2f}/min)")
            else:
                print(f"  [FAIL] {source_type.value:20} -> Expected {expected_limit}, got {int(actual_capacity)}")
                all_passed = False
        else:
            print(f"  [FAIL] {source_type.value:20} -> Bucket not found!")
            all_passed = False

    print(f"\n[2] Checking Default Bucket Behavior")
    print("=" * 80)

    # Test a state association (should fall back to default)
    test_state = DataSourceType.AHSAA  # Alabama High School Athletic Association

    status = await rate_limiter.get_rate_limit_status(test_state)
    print(f"  State Association Test: {test_state.value}")
    print(f"    Requests allowed: {status['requests_allowed']} req/min")
    print(f"    Expected: {rate_limiter.settings.rate_limit_default} req/min (default)")

    if status['requests_allowed'] == rate_limiter.settings.rate_limit_default:
        print(f"  [OK] State associations correctly using default bucket")
    else:
        print(f"  [WARN] Unexpected rate limit for state association")

    print(f"\n[3] Summary")
    print("=" * 80)
    print(f"  Total buckets instantiated: {len(rate_limiter.buckets)}")
    print(f"  Configured sources tested: {len(expected_configured)}")
    print(f"  Default rate limit: {rate_limiter.settings.rate_limit_default} req/min")

    if all_passed:
        print(f"\n  [SUCCESS] All 16 priority sources have dedicated token buckets!")
        print(f"  Stats adapters (Bound, SBLive, 3SSB, WSN) no longer compete")
        print(f"  Fixtures adapters (RankOne, FHSAA, HHSAA) have dedicated buckets")
    else:
        print(f"\n  [FAIL] Some sources are not properly configured!")

    print(f"\n{'=' * 80}")
    print(f"VALIDATION COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_rate_limiter())
