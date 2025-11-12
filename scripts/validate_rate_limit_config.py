"""
Validate Rate Limiting Configuration

Checks that all priority datasources have dedicated rate limit configurations
in config.py without instantiating the rate limiter (avoids circular imports).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Settings


def validate_config():
    """Validate rate limit configuration exists for priority sources."""
    print("=" * 80)
    print("RATE LIMIT CONFIGURATION VALIDATION")
    print("=" * 80)

    settings = Settings()

    # Priority sources that should have dedicated rate limits
    priority_sources = {
        # Original 9 sources
        "eybl": ("EYBL", 30),
        "fiba": ("FIBA", 20),
        "psal": ("PSAL", 15),
        "mn_hub": ("MN Hub", 20),
        "grind_session": ("Grind Session", 15),
        "ote": ("OTE", 25),
        "angt": ("ANGT", 20),
        "osba": ("OSBA", 15),
        "playhq": ("PlayHQ", 25),
        # Stats Adapters (High Priority)
        "bound": ("Bound", 20),
        "sblive": ("SBLive", 15),
        "three_ssb": ("3SSB", 20),
        "wsn": ("WSN", 15),
        # Fixtures Adapters
        "rankone": ("RankOne", 20),
        "fhsaa": ("FHSAA", 15),
        "hhsaa": ("HHSAA", 15),
    }

    print(f"\n[1] Validating Config Fields")
    print("=" * 80)

    all_configured = True
    for source_key, (display_name, expected_default) in sorted(priority_sources.items()):
        config_attr = f"rate_limit_{source_key}"

        if hasattr(settings, config_attr):
            actual_value = getattr(settings, config_attr)
            print(f"  [OK] {display_name:20} -> {actual_value:3} req/min (config: {config_attr})")

            if actual_value != expected_default:
                print(f"       [INFO] Using custom value (default: {expected_default})")
        else:
            print(f"  [FAIL] {display_name:20} -> Config field '{config_attr}' NOT FOUND")
            all_configured = False

    print(f"\n[2] Checking Helper Methods")
    print("=" * 80)

    # Test get_datasource_rate_limit method
    test_sources = ["eybl", "bound", "sblive", "rankone"]
    for source in test_sources:
        limit = settings.get_datasource_rate_limit(source)
        print(f"  get_datasource_rate_limit('{source}') -> {limit} req/min")

    print(f"\n[3] Summary")
    print("=" * 80)
    print(f"  Priority sources checked: {len(priority_sources)}")
    print(f"  Default rate limit: {settings.rate_limit_default} req/min")

    if all_configured:
        print(f"\n  [SUCCESS] All {len(priority_sources)} priority sources have config fields!")
        print(f"\n  Configuration is ready for rate_limiter.py _setup_buckets()")
        print(f"  Each priority adapter will get its own dedicated token bucket")
        print(f"  State associations will use default bucket ({settings.rate_limit_default} req/min)")
    else:
        print(f"\n  [FAIL] Some config fields are missing!")

    print(f"\n{'=' * 80}")
    print(f"VALIDATION COMPLETE")
    print(f"{'=' * 80}")

    return all_configured


if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
