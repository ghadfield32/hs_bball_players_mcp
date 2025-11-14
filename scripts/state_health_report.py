"""
State Adapter Health Report

Validates that active state adapters are operational and reachable.

Usage:
    python scripts/state_health_report.py
    python scripts/state_health_report.py --verbose
    python scripts/state_health_report.py --state CA,TX,FL

This script:
- Initializes each active state adapter
- Validates base_url is reachable (HEAD/GET request)
- Checks adapter configuration (source_type, source_name)
- Reports any errors or warnings
- Provides operational status matrix

Health Checks:
1. Adapter Initialization - Can the adapter be instantiated?
2. Configuration Valid - Does it have required attributes?
3. Base URL Reachable - Can we connect to the data source?
4. (Optional) Sample Bracket Parse - Can it fetch and parse a test page?

Outputs:
- Console table with pass/fail status for each state
- Colored formatting (green = pass, red = fail, yellow = warn)
- Detailed error messages in verbose mode
- Summary statistics (X/Y healthy)
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import importlib

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import *  # Import all US state adapters
from src.models.source import DataSourceType


# Map of state IDs to adapter classes (based on Phase 17-22)
STATE_ADAPTER_MAP = {
    # Phase 17
    "cif_ss": CaliforniaCIFSSDataSource,
    "uil_tx": TexasUILDataSource,
    "fhsaa_fl": FloridaFHSAADataSource,
    "ghsa": GeorgiaGHSADataSource,
    "ohsaa": OhioOHSAADataSource,
    "piaa": PennsylvaniaPIAADataSource,
    "nysphsaa": NewYorkNYSPHSAADataSource,
    # Phase 19
    "ihsa": IHSADataSource,
    "nchsaa": NCHSAADataSource,
    "vhsl": VirginiaVHSLDataSource,
    "wiaa_wa": WashingtonWIAADataSource,
    "miaa": MassachusettsMiaaDataSource,
    # Phase 20
    "ihsaa": IndianaIHSAADataSource,
    "wiaa": WisconsinWIAADataSource,
    "mshsaa": MissouriMSHSAADataSource,
    "mpssaa": MarylandMPSSAADataSource,
    "mshsl": MinnesotaMSHSLDataSource,
    # Phase 21
    "mhsaa_mi": MichiganMHSAADataSource,
    "njsiaa": NewJerseyNJSIAADataSource,
    "aia": ArizonaAIADataSource,
    "chsaa": ColoradoCHSAADataSource,
    "tssaa": TennesseeTSSAADataSource,
    "khsaa": KentuckyKHSAADataSource,
    "ciac": ConnecticutCIACDataSource,
    "schsl": SouthCarolinaSCHSLDataSource,
    # Phase 22
    "ahsaa": AlabamaAHSAADataSource,
    "lhsaa": LouisianaLHSAADataSource,
    "osaa": OregonOSAADataSource,
    "mhsaa_ms": MississippiMHSAA_MSDataSource,
    "kshsaa": KansasKSHSAADataSource,
    "aaa": ArkansasAAADataSource,
    "nsaa": NebraskaNSAADataSource,
    "sdhsaa": SouthDakotaSDHSAADataSource,
    "ihsaa_id": IdahoIHSAADataSource,
    "uhsaa": UtahUHSAADataSource,
}


async def check_adapter_health(adapter_class, state_id: str, verbose: bool = False) -> Dict:
    """
    Perform health checks on a single adapter.

    Returns dict with:
        - state_id: State identifier
        - adapter_name: Class name
        - init_ok: Boolean - can adapter be initialized?
        - config_ok: Boolean - has required attributes?
        - url_reachable: Boolean - can base_url be reached?
        - error_msg: String - error details if any check failed
    """
    result = {
        "state_id": state_id,
        "adapter_name": adapter_class.__name__,
        "init_ok": False,
        "config_ok": False,
        "url_reachable": None,  # None = not tested, True/False = result
        "error_msg": "",
    }

    try:
        # Test 1: Initialization
        adapter = adapter_class()
        result["init_ok"] = True

        # Test 2: Configuration validation
        has_base_url = hasattr(adapter, "base_url") and adapter.base_url
        has_source_name = hasattr(adapter, "source_name") and adapter.source_name
        has_source_type = hasattr(adapter, "source_type") and adapter.source_type

        if not (has_base_url and has_source_name and has_source_type):
            result["error_msg"] = "Missing required attributes"
        else:
            result["config_ok"] = True

            # Test 3: URL Reachability (simple HTTP HEAD request)
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.head(adapter.base_url)
                    result["url_reachable"] = response.status_code < 500
                    if not result["url_reachable"]:
                        result["error_msg"] = f"HTTP {response.status_code}"
            except httpx.RequestError as e:
                result["url_reachable"] = False
                result["error_msg"] = f"Connection error: {type(e).__name__}"
            except Exception as e:
                result["url_reachable"] = False
                result["error_msg"] = f"URL check failed: {str(e)}"

        # Cleanup
        await adapter.close()

    except Exception as e:
        result["error_msg"] = f"Init failed: {str(e)}"

    return result


async def generate_health_report(state_filter: Optional[List[str]] = None, verbose: bool = False):
    """Generate comprehensive health report for active state adapters."""

    # Filter adapters if specific states requested
    if state_filter:
        adapters_to_check = {
            sid: cls for sid, cls in STATE_ADAPTER_MAP.items()
            if sid.upper() in [s.upper() for s in state_filter]
        }
    else:
        adapters_to_check = STATE_ADAPTER_MAP

    print("=" * 80)
    print("STATE ADAPTER HEALTH REPORT".center(80))
    print("=" * 80)
    print()

    # Run health checks concurrently
    tasks = [
        check_adapter_health(adapter_class, state_id, verbose)
        for state_id, adapter_class in adapters_to_check.items()
    ]

    results = await asyncio.gather(*tasks)

    # Print header
    print(f"{'State':<10} {'Adapter':<30} {'Init':<6} {'Config':<8} {'URL':<10} {'Status'}")
    print("-" * 80)

    # Print results
    healthy_count = 0
    for result in sorted(results, key=lambda x: x["state_id"]):
        init_sym = "✓" if result["init_ok"] else "✗"
        config_sym = "✓" if result["config_ok"] else "✗"

        if result["url_reachable"] is None:
            url_sym = "-"
        elif result["url_reachable"]:
            url_sym = "✓"
        else:
            url_sym = "✗"

        # Overall status
        is_healthy = result["init_ok"] and result["config_ok"] and (
            result["url_reachable"] is None or result["url_reachable"]
        )

        if is_healthy:
            status_sym = "HEALTHY"
            healthy_count += 1
        elif result["init_ok"]:
            status_sym = "DEGRADED"
        else:
            status_sym = "FAILED"

        adapter_short = result["adapter_name"][:28]

        print(
            f"{result['state_id']:<10} {adapter_short:<30} "
            f"{init_sym:<6} {config_sym:<8} {url_sym:<10} {status_sym}"
        )

        if verbose and result["error_msg"]:
            print(f"           Error: {result['error_msg']}")

    # Summary
    total = len(results)
    print()
    print("=" * 80)
    print(f"SUMMARY: {healthy_count}/{total} adapters healthy ({healthy_count/total*100:.1f}%)")
    print("=" * 80)

    legend = """
Legend:
  Init   - Adapter can be instantiated
  Config - Has required attributes (base_url, source_name, source_type)
  URL    - Base URL is reachable (HTTP status < 500)

  HEALTHY  - All checks passed
  DEGRADED - Initialized but URL unreachable
  FAILED   - Failed to initialize
"""
    print(legend)


def main():
    parser = argparse.ArgumentParser(description="State adapter health check")
    parser.add_argument(
        "--state",
        help="Comma-separated list of state IDs to check (e.g., CA,TX,FL)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed error messages"
    )

    args = parser.parse_args()

    state_filter = None
    if args.state:
        state_filter = [s.strip() for s in args.state.split(",")]

    # Run async health report
    asyncio.run(generate_health_report(state_filter=state_filter, verbose=args.verbose))


if __name__ == "__main__":
    main()
