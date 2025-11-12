"""
Diagnose Rate Limiting Configuration

Analyzes rate limit configuration to identify which datasources are:
1. Properly configured with dedicated rate limits
2. Falling back to shared "default" bucket (PROBLEM!)
3. Missing from configuration entirely

This script does NOT modify any code - it only inspects and reports.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Settings
from src.models import DataSourceType


def diagnose_rate_limits():
    """Diagnose rate limit configuration issues."""
    print("=" * 80)
    print("RATE LIMITING CONFIGURATION DIAGNOSIS")
    print("=" * 80)

    settings = Settings()

    # Get all configured sources in rate_limiter._setup_buckets()
    configured_in_rate_limiter = {
        DataSourceType.EYBL,
        DataSourceType.FIBA,
        DataSourceType.PSAL,
        DataSourceType.MN_HUB,
        DataSourceType.GRIND_SESSION,
        DataSourceType.OTE,
        DataSourceType.ANGT,
        DataSourceType.OSBA,
        DataSourceType.PLAYHQ,
        # Stats Adapters (High Priority)
        DataSourceType.BOUND,
        DataSourceType.SBLIVE,
        DataSourceType.THREE_SSB,
        DataSourceType.WSN,
        # Fixtures Adapters
        DataSourceType.RANKONE,
        DataSourceType.FHSAA,
        DataSourceType.HHSAA,
    }

    # Get all data source types
    all_sources = set(DataSourceType)

    # Identify sources NOT configured
    unconfigured_sources = all_sources - configured_in_rate_limiter - {DataSourceType.UNKNOWN}

    print(f"\n[1] CONFIGURED SOURCES (Dedicated Rate Limits)")
    print(f"=" * 80)
    print(f"These sources have dedicated token buckets:\n")
    for source in sorted(configured_in_rate_limiter, key=lambda x: x.value):
        limit = getattr(settings, f"rate_limit_{source.value.lower()}", None)
        if limit:
            print(f"  - {source.value:20} -> {limit:3} req/min")
        else:
            print(f"  - {source.value:20} -> [ERROR: Config missing!]")

    print(f"\n[2] UNCONFIGURED SOURCES (Using Shared 'Default' Bucket)")
    print(f"=" * 80)
    print(f"[WARNING] PROBLEM: These {len(unconfigured_sources)} sources share a single bucket!")
    print(f"Default limit: {settings.rate_limit_default} req/min (shared across ALL)\n")

    # Group by category
    stats_sources = []
    fixtures_sources = []
    other_sources = []

    for source in sorted(unconfigured_sources, key=lambda x: x.value):
        if source.value in ["bound", "sblive", "three_ssb", "wsn"]:
            stats_sources.append(source)
        elif source.value in ["rankone", "fhsaa", "hhsaa"]:
            fixtures_sources.append(source)
        else:
            other_sources.append(source)

    if stats_sources:
        print(f"  HIGH-PRIORITY Stats Adapters (competing for same 10 req/min):")
        for source in stats_sources:
            print(f"    - {source.value}")

    if fixtures_sources:
        print(f"\n  Fixtures Adapters (also sharing default):")
        for source in fixtures_sources:
            print(f"    - {source.value}")

    if other_sources:
        print(f"\n  State Associations & Others ({len(other_sources)} sources):")
        for source in sorted(other_sources[:5], key=lambda x: x.value):  # Show first 5
            print(f"    - {source.value}")
        if len(other_sources) > 5:
            print(f"    ... and {len(other_sources) - 5} more")

    print(f"\n[3] IMPACT ANALYSIS")
    print(f"=" * 80)
    print(f"Current Situation:")
    print(f"  - Configured sources: {len(configured_in_rate_limiter)}")
    print(f"  - Unconfigured sources: {len(unconfigured_sources)}")
    print(f"  - Default bucket limit: {settings.rate_limit_default} req/min")
    print(f"\n[WARNING] If Bound, SBLive, 3SSB, and WSN all make requests:")
    print(f"     They compete for just {settings.rate_limit_default} req/min TOTAL!")
    print(f"     Expected per-source: ~{settings.rate_limit_default / 4:.1f} req/min each")
    print(f"     This can cause:")
    print(f"       - Severe throttling")
    print(f"       - Request timeouts")
    print(f"       - Failed data extraction")

    print(f"\n[4] RECOMMENDED FIXES")
    print(f"=" * 80)
    print(f"Add to src/config.py:")
    print(f"  rate_limit_bound: int = Field(default=20, ge=1)")
    print(f"  rate_limit_sblive: int = Field(default=15, ge=1)")
    print(f"  rate_limit_three_ssb: int = Field(default=20, ge=1)")
    print(f"  rate_limit_wsn: int = Field(default=15, ge=1)")
    print(f"  rate_limit_rankone: int = Field(default=20, ge=1)")
    print(f"  rate_limit_fhsaa: int = Field(default=15, ge=1)")
    print(f"  rate_limit_hhsaa: int = Field(default=15, ge=1)")
    print(f"\nAdd to src/services/rate_limiter.py _setup_buckets():")
    print(f"  DataSourceType.BOUND: self.settings.rate_limit_bound,")
    print(f"  DataSourceType.SBLIVE: self.settings.rate_limit_sblive,")
    print(f"  DataSourceType.THREE_SSB: self.settings.rate_limit_three_ssb,")
    print(f"  DataSourceType.WSN: self.settings.rate_limit_wsn,")
    print(f"  DataSourceType.RANKONE: self.settings.rate_limit_rankone,")
    print(f"  DataSourceType.FHSAA: self.settings.rate_limit_fhsaa,")
    print(f"  DataSourceType.HHSAA: self.settings.rate_limit_hhsaa,")

    print(f"\n" + "=" * 80)
    print(f"DIAGNOSIS COMPLETE")
    print(f"=" * 80)


if __name__ == "__main__":
    diagnose_rate_limits()
