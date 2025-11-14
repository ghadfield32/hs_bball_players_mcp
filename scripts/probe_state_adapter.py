"""
State Adapter Real-Data Probe Utility

Tests individual state adapters against live endpoints to verify:
- HTTP connectivity and status codes
- HTML parsing correctness
- Bracket/game data extraction
- Data quality and completeness

Usage:
    python scripts/probe_state_adapter.py --state al --year 2024
    python scripts/probe_state_adapter.py --state or --year 2025 --classification 6A
    python scripts/probe_state_adapter.py --all --year 2024
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Type, Optional, Any
import httpx
import ssl

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.us import (
    # Phase 17 - High Impact
    CaliforniaCIFSSDataSource,
    TexasUILDataSource,
    FloridaFHSAADataSource,
    GeorgiaGHSADataSource,
    OhioOHSAADataSource,
    PennsylvaniaPIAADataSource,
    NewYorkNYSPHSAADataSource,
    # Phase 19
    IHSADataSource,
    NCHSAADataSource,
    VirginiaVHSLDataSource,
    WashingtonWIAADataSource,
    MassachusettsMiaaDataSource,
    # Phase 20
    IndianaIHSAADataSource,
    WisconsinWIAADataSource,
    MissouriMSHSAADataSource,
    MarylandMPSSAADataSource,
    MinnesotaMSHSLDataSource,
    # Phase 21
    MichiganMHSAADataSource,
    NewJerseyNJSIAADataSource,
    ArizonaAIADataSource,
    ColoradoCHSAADataSource,
    TennesseeTSSAADataSource,
    KentuckyKHSAADataSource,
    ConnecticutCIACDataSource,
    SouthCarolinaSCHSLDataSource,
    # Phase 22
    AlabamaAHSAADataSource,
    LouisianaLHSAADataSource,
    OregonOSAADataSource,
    MississippiMHSAA_MSDataSource,
    KansasKSHSAADataSource,
    ArkansasAAADataSource,
    NebraskaNSAADataSource,
    SouthDakotaSDHSAADataSource,
    IdahoIHSAADataSource,
    UtahUHSAADataSource,
)

# Validation framework for automated QA and health scoring
from src.utils.validation import validate_games, format_validation_report

# State adapter registry
ADAPTERS: Dict[str, Type] = {
    # Phase 17
    "ca": CaliforniaCIFSSDataSource,
    "tx": TexasUILDataSource,
    "fl": FloridaFHSAADataSource,
    "ga": GeorgiaGHSADataSource,
    "oh": OhioOHSAADataSource,
    "pa": PennsylvaniaPIAADataSource,
    "ny": NewYorkNYSPHSAADataSource,
    # Phase 19
    "il": IHSADataSource,
    "nc": NCHSAADataSource,
    "va": VirginiaVHSLDataSource,
    "wa": WashingtonWIAADataSource,
    "ma": MassachusettsMiaaDataSource,
    # Phase 20
    "in": IndianaIHSAADataSource,
    "wi": WisconsinWIAADataSource,
    "mo": MissouriMSHSAADataSource,
    "md": MarylandMPSSAADataSource,
    "mn": MinnesotaMSHSLDataSource,
    # Phase 21
    "mi": MichiganMHSAADataSource,
    "nj": NewJerseyNJSIAADataSource,
    "az": ArizonaAIADataSource,
    "co": ColoradoCHSAADataSource,
    "tn": TennesseeTSSAADataSource,
    "ky": KentuckyKHSAADataSource,
    "ct": ConnecticutCIACDataSource,
    "sc": SouthCarolinaSCHSLDataSource,
    # Phase 22
    "al": AlabamaAHSAADataSource,
    "la": LouisianaLHSAADataSource,
    "or": OregonOSAADataSource,
    "ms": MississippiMHSAA_MSDataSource,
    "ks": KansasKSHSAADataSource,
    "ar": ArkansasAAADataSource,
    "ne": NebraskaNSAADataSource,
    "sd": SouthDakotaSDHSAADataSource,
    "id": IdahoIHSAADataSource,
    "ut": UtahUHSAADataSource,
}


def classify_probe_result(result: Dict, error: Optional[Exception] = None) -> str:
    """
    Classify probe result into standardized status categories.

    Status Categories (Session 8 - Phase 24):
    - OK_REAL_DATA: Success with games_found > 0 (real bracket data extracted)
    - DISCOVERY_FAIL: Index fetched but no bracket URLs found (discovery pattern failed)
    - NO_GAMES: Success but games_found = 0 (parsing issue or legitimately no games)
    - HTTP_404: Not Found - wrong URL pattern
    - HTTP_403: Forbidden - access blocked/auth required/anti-bot
    - HTTP_500: Internal Server Error - website issue
    - SSL_ERROR: SSL/TLS certificate verification failed
    - NETWORK_ERROR: Connection timeout, refused, DNS failure
    - OTHER: Unknown error

    Args:
        result: Probe result dict with success, games_found, error_msg
        error: Optional exception that was caught

    Returns:
        Status string for categorization
    """
    # Success cases
    if result.get("success"):
        if result.get("games_found", 0) > 0:
            return "OK_REAL_DATA"

        # Check if this is a discovery failure vs legitimately no games
        # Discovery failure indicators:
        # 1. Error message mentions discovery issues
        # 2. Metadata contains discovery-related errors
        error_msg = result.get("error_msg", "").lower()

        discovery_keywords = [
            "no bracket urls",
            "discovery failed",
            "no brackets found",
            "could not discover",
            "failed to discover",
            "no urls discovered",
        ]

        if any(keyword in error_msg for keyword in discovery_keywords):
            return "DISCOVERY_FAIL"

        # Check metadata for discovery issues (used by some adapters)
        metadata = result.get("metadata", {})
        if metadata:
            metadata_error = str(metadata.get("error", "")).lower()
            if any(keyword in metadata_error for keyword in discovery_keywords):
                return "DISCOVERY_FAIL"

        # Default to NO_GAMES for successful fetch with no games
        return "NO_GAMES"

    # Error cases - analyze error message
    error_msg = result.get("error_msg", "").lower()

    # HTTP status code errors
    if "404" in error_msg or "not found" in error_msg:
        return "HTTP_404"
    if "403" in error_msg or "forbidden" in error_msg or "access denied" in error_msg:
        return "HTTP_403"
    if "500" in error_msg or "internal server error" in error_msg:
        return "HTTP_500"

    # SSL/TLS errors
    if any(ssl_keyword in error_msg for ssl_keyword in [
        "ssl", "certificate", "tlsv1", "verify failed", "cert"
    ]):
        return "SSL_ERROR"

    # Network errors
    if any(net_keyword in error_msg for net_keyword in [
        "timeout", "timed out", "connection refused", "connection reset",
        "connection error", "network", "dns", "unreachable"
    ]):
        return "NETWORK_ERROR"

    # Default to OTHER for unknown errors
    return "OTHER"


async def probe_adapter(
    state_code: str,
    year: Optional[int] = None,
    classification: Optional[str] = None,
    gender: str = "Boys",
    verbose: bool = False,
    dump_html: bool = False
) -> Dict:
    """
    Probe a single state adapter with real HTTP requests.

    Args:
        state_code: Two-letter state code (e.g., "al", "mi")
        year: Tournament year (default: current year)
        classification: Specific classification to test
        gender: "Boys" or "Girls"
        verbose: Show detailed output
        dump_html: Save fetched HTML to data/debug/html/ for inspection

    Returns dict with:
        - state: State code
        - adapter: Adapter class name
        - success: Boolean - did probe succeed?
        - games_found: Number of games extracted
        - teams_found: Number of teams extracted
        - error_msg: Error message if failed
        - http_status: HTTP status code from bracket fetch
        - url_tested: URL that was tested
        - html_saved_to: Path to saved HTML file (if dump_html=True)
    """
    result = {
        "state": state_code.upper(),
        "adapter": None,
        "success": False,
        "status": None,  # Will be set by classify_probe_result
        "error_type": None,  # Deprecated - use status instead
        "games_found": 0,
        "teams_found": 0,
        "error_msg": "",
        "http_status": None,
        "url_tested": None,
        # Validation metrics (Session A - Phase 24)
        "health_score": 0.0,
        "errors_count": 0,
        "warnings_count": 0,
        "validation_errors": [],
        "validation_warnings": [],
    }

    caught_exception = None

    try:
        adapter_cls = ADAPTERS.get(state_code.lower())
        if not adapter_cls:
            result["error_msg"] = f"Unknown state code: {state_code}"
            return result

        result["adapter"] = adapter_cls.__name__
        adapter = adapter_cls()

        # Build season string
        if year is None:
            year = datetime.now().year
        season = f"{year-1}-{str(year)[2:]}"

        if verbose:
            print(f"\n[{state_code.upper()}] Testing {adapter.source_name} ({adapter.base_url})")
            print(f"  Season: {season}, Gender: {gender}")
            if classification:
                print(f"  Classification: {classification}")

        # Call get_tournament_brackets which will make real HTTP requests
        # Try classification first (Phase 22), fall back to division (Phase 17)
        try:
            brackets_data = await adapter.get_tournament_brackets(
                season=season,
                classification=classification,
                gender=gender
            )
        except TypeError:
            # Adapter uses 'division' instead of 'classification'
            brackets_data = await adapter.get_tournament_brackets(
                season=season,
                division=classification,
                gender=gender
            )

        # Extract results
        games = brackets_data.get("games", [])
        teams = brackets_data.get("teams", [])
        metadata = brackets_data.get("metadata", {})

        result["success"] = True
        result["games_found"] = len(games)
        result["teams_found"] = len(teams)
        result["http_status"] = 200  # If we got here, HTTP was successful
        result["metadata"] = metadata  # Capture adapter metadata for classification

        # Check for discovery errors in metadata (Session 8 - Phase 24)
        if metadata and metadata.get("error"):
            result["error_msg"] = metadata.get("error")

        # Run validation for QA and health scoring
        validation_report = validate_games(
            games=games,
            teams=teams,
            state=state_code.upper(),
            year=year or datetime.now().year
        )

        # Add validation metrics to result
        result["health_score"] = validation_report.health_score
        result["errors_count"] = len(validation_report.errors)
        result["warnings_count"] = len(validation_report.warnings)
        result["validation_errors"] = validation_report.errors[:10]  # Limit to first 10
        result["validation_warnings"] = validation_report.warnings[:5]  # Limit to first 5

        if verbose:
            print(f"  [SUCCESS] {len(games)} games, {len(teams)} teams")
            print(f"  [HEALTH] Score: {validation_report.health_score:.2f} | Errors: {len(validation_report.errors)} | Warnings: {len(validation_report.warnings)}")
            if games:
                sample_game = games[0]
                print(f"  Sample: {sample_game.home_team_name} vs {sample_game.away_team_name}")

        # Dump HTML for inspection if requested
        if dump_html:
            try:
                # Get bracket URL from adapter
                url = None
                if hasattr(adapter, '_build_bracket_url'):
                    # Try to call with classification if provided
                    if classification:
                        try:
                            url = adapter._build_bracket_url(classification, gender, year)
                        except TypeError:
                            # Adapter might use different signature
                            url = adapter._build_bracket_url(gender=gender, year=year)
                    else:
                        # Try with default classification or just gender/year
                        try:
                            # Some adapters like Michigan require classification
                            # Try a common default like "Division 1" or "1"
                            url = adapter._build_bracket_url("Division 1", gender, year)
                        except TypeError:
                            # Fall back to gender/year only
                            url = adapter._build_bracket_url(gender=gender, year=year)

                if url:
                    # Fetch HTML
                    status, content, headers = await adapter.http_get(url, timeout=30.0)

                    if status == 200:
                        # Create debug directory
                        debug_dir = Path("data/debug/html")
                        debug_dir.mkdir(parents=True, exist_ok=True)

                        # Save HTML
                        html_file = debug_dir / f"{state_code.lower()}_{year or datetime.now().year}.html"
                        html_file.write_bytes(content)
                        result["html_saved_to"] = str(html_file)

                        # Save metadata JSON with validation metrics
                        metadata_file = debug_dir / f"{state_code.lower()}_{year or datetime.now().year}_meta.json"
                        metadata = {
                            "state": state_code.upper(),
                            "adapter": result.get("adapter"),
                            "year": year or datetime.now().year,
                            "url": url,
                            "status": status,
                            "content_type": headers.get("content-type", "unknown"),
                            "content_length": len(content),
                            "fetched_at": datetime.utcnow().isoformat() + "Z",
                            "gender": gender,
                            "classification": classification,
                            # Validation metrics (Session A - Phase 24)
                            "games_found": result.get("games_found", 0),
                            "teams_found": result.get("teams_found", 0),
                            "health_score": result.get("health_score", 0.0),
                            "errors_count": result.get("errors_count", 0),
                            "warnings_count": result.get("warnings_count", 0),
                            "validation_errors": result.get("validation_errors", []),
                            "validation_warnings": result.get("validation_warnings", []),
                        }
                        metadata_file.write_text(json.dumps(metadata, indent=2))

                        if verbose:
                            print(f"  [SAVED] HTML dumped to: {html_file}")
                            print(f"  [SAVED] Metadata saved to: {metadata_file}")
                    else:
                        if verbose:
                            print(f"  [WARN] Failed to dump HTML: HTTP {status}")
                else:
                    if verbose:
                        print(f"  [WARN] Adapter doesn't support HTML dumping")
            except Exception as e:
                if verbose:
                    print(f"  [WARN] Failed to dump HTML: {e}")

        # Cleanup
        await adapter.close()

    except Exception as e:
        caught_exception = e
        result["error_msg"] = f"{type(e).__name__}: {str(e)}"
        if verbose:
            print(f"  [FAILED] {result['error_msg']}")

    # Classify the result into standardized status categories
    result["status"] = classify_probe_result(result, caught_exception)
    result["error_type"] = result["status"]  # Backwards compat

    return result


async def probe_all_adapters(
    year: Optional[int] = None,
    verbose: bool = False,
    validate: bool = False
) -> Dict[str, Dict]:
    """Probe all registered state adapters with optional validation output."""
    print(f"{'='*80}")
    print(f"PROBING ALL {len(ADAPTERS)} STATE ADAPTERS")
    print(f"{'='*80}\n")

    results = {}
    for state_code in sorted(ADAPTERS.keys()):
        result = await probe_adapter(state_code, year=year, verbose=verbose)
        results[state_code.upper()] = result

        # Print summary line with status classification (Windows-compatible ASCII)
        # Session 8 - Phase 24: Added DISCOVERY_FAIL as distinct category
        if result["status"] == "OK_REAL_DATA":
            status_icon = "[OK]"
        elif result["status"] == "DISCOVERY_FAIL":
            status_icon = "[DF]"  # DF = Discovery Fail (ASCII-safe)
        elif result["status"] == "NO_GAMES":
            status_icon = "[NO]"
        else:
            status_icon = "[XX]"

        status_label = f"[{result['status']:<15}]"
        # Session 8 - Phase 24: Encode to ASCII to prevent Windows console errors
        safe_line = f"{status_icon} {status_label} {result['state']:<3} {result['adapter']:<35} Games: {result['games_found']:<4}"
        print(safe_line.encode('ascii', 'replace').decode('ascii'))

        # Print validation health score if --validate flag is set
        if validate:
            health = result.get("health_score", 0.0)
            errors = result.get("errors_count", 0)
            warnings = result.get("warnings_count", 0)
            health_label = "HEALTHY" if health >= 0.7 else "UNHEALTHY"
            print(f"     Health: {health:.2f} [{health_label}] | Errors: {errors} | Warnings: {warnings}")

        if result["status"] != "OK_REAL_DATA":
            print(f"     -> {result['error_msg'][:75]}" if result['error_msg'] else "     -> No games found")

    # Summary statistics by status category (Session 8 - Phase 24)
    total = len(results)
    ok_real_data = sum(1 for r in results.values() if r["status"] == "OK_REAL_DATA")
    discovery_fail = sum(1 for r in results.values() if r["status"] == "DISCOVERY_FAIL")
    no_games = sum(1 for r in results.values() if r["status"] == "NO_GAMES")
    http_404 = sum(1 for r in results.values() if r["status"] == "HTTP_404")
    http_403 = sum(1 for r in results.values() if r["status"] == "HTTP_403")
    http_500 = sum(1 for r in results.values() if r["status"] == "HTTP_500")
    ssl_error = sum(1 for r in results.values() if r["status"] == "SSL_ERROR")
    network_error = sum(1 for r in results.values() if r["status"] == "NETWORK_ERROR")
    other_error = sum(1 for r in results.values() if r["status"] == "OTHER")
    total_games = sum(r["games_found"] for r in results.values())
    total_teams = sum(r["teams_found"] for r in results.values())

    print(f"\n{'='*80}")
    print(f"PROBE SUMMARY: {ok_real_data}/{total} states with REAL DATA ({ok_real_data/total*100:.1f}%)")
    print(f"{'='*80}")
    print(f"  [OK] OK_REAL_DATA:    {ok_real_data:>3} states ({total_games} games, {total_teams} teams)")
    print(f"  [DF] DISCOVERY_FAIL:  {discovery_fail:>3} states (bracket URL discovery failed)")
    print(f"  [NO] NO_GAMES:        {no_games:>3} states (parser/URL issues)")
    print(f"  [XX] HTTP_404:        {http_404:>3} states (URL pattern wrong)")
    print(f"  [XX] HTTP_403:        {http_403:>3} states (access blocked/anti-bot)")
    print(f"  [XX] HTTP_500:        {http_500:>3} states (server error)")
    print(f"  [XX] SSL_ERROR:       {ssl_error:>3} states (certificate issues)")
    print(f"  [XX] NETWORK_ERROR:   {network_error:>3} states (timeout/connection)")
    print(f"  [XX] OTHER:           {other_error:>3} states (unknown error)")
    print(f"{'='*80}\n")

    return results


def save_probe_results(
    results: Dict[str, Dict[str, Any]],
    year: Optional[int] = None,
    output_path: Path = Path("state_adapter_health.json")
) -> None:
    """
    Persist probe results to JSON for real-data coverage tracking.

    Creates machine-readable artifact showing which states/seasons have
    verified real data. This supports historical coverage expansion.

    Enhanced Schema (Phase 24):
    {
      "generated_at": "2025-11-13T03:21:00Z",
      "probe_year": 2024,
      "states": [
        {
          "state": "AL",
          "adapter": "AlabamaAHSAADataSource",
          "success": true,
          "status": "OK_REAL_DATA",
          "games_found": 154,
          "teams_found": 43,
          "error_msg": ""
        },
        ...
      ],
      "summary": {
        "total_states": 35,
        "ok_real_data": 1,
        "no_games": 5,
        "http_404": 13,
        "http_403": 1,
        "http_500": 1,
        "ssl_error": 2,
        "network_error": 2,
        "other": 10,
        "total_games": 154,
        "total_teams": 43
      }
    }
    """
    # Calculate summary stats by status category
    total = len(results)
    ok_real_data = sum(1 for r in results.values() if r.get("status") == "OK_REAL_DATA")
    no_games = sum(1 for r in results.values() if r.get("status") == "NO_GAMES")
    http_404 = sum(1 for r in results.values() if r.get("status") == "HTTP_404")
    http_403 = sum(1 for r in results.values() if r.get("status") == "HTTP_403")
    http_500 = sum(1 for r in results.values() if r.get("status") == "HTTP_500")
    ssl_error = sum(1 for r in results.values() if r.get("status") == "SSL_ERROR")
    network_error = sum(1 for r in results.values() if r.get("status") == "NETWORK_ERROR")
    other_error = sum(1 for r in results.values() if r.get("status") == "OTHER")
    total_games = sum(r["games_found"] for r in results.values())
    total_teams = sum(r["teams_found"] for r in results.values())

    # Build payload
    payload = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "probe_year": year or datetime.now().year,
        "states": list(results.values()),
        "summary": {
            "total_states": total,
            "ok_real_data": ok_real_data,
            "no_games": no_games,
            "http_404": http_404,
            "http_403": http_403,
            "http_500": http_500,
            "ssl_error": ssl_error,
            "network_error": network_error,
            "other": other_error,
            "total_games": total_games,
            "total_teams": total_teams,
            "success_rate": round(ok_real_data / total * 100, 1) if total > 0 else 0.0
        }
    }

    # Write to file
    output_path.write_text(json.dumps(payload, indent=2))
    print(f"\n[SAVED] Probe results written to: {output_path}")
    print(f"  [OK] {ok_real_data}/{total} states verified with REAL DATA ({ok_real_data/total*100:.1f}%)")
    print(f"  [  ] {total_games} games, {total_teams} teams extracted")
    print(f"\n  Status Breakdown:")
    print(f"    OK_REAL_DATA: {ok_real_data}, NO_GAMES: {no_games}")
    print(f"    HTTP_404: {http_404}, HTTP_403: {http_403}, HTTP_500: {http_500}")
    print(f"    SSL_ERROR: {ssl_error}, NETWORK_ERROR: {network_error}, OTHER: {other_error}")


def main():
    parser = argparse.ArgumentParser(
        description="Probe state adapters with real HTTP requests"
    )
    parser.add_argument(
        "--state",
        help="State code (e.g., al, ca, tx). Use --all to test all states."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all registered state adapters"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--classification",
        help="Specific classification to test (e.g., 6A, Division 1)"
    )
    parser.add_argument(
        "--gender",
        default="Boys",
        help="Gender (Boys or Girls)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--dump-html",
        action="store_true",
        help="Save fetched HTML to data/debug/html/ for inspection"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation and show health scores for each state"
    )

    args = parser.parse_args()

    if not args.state and not args.all:
        parser.error("Must specify either --state or --all")

    # Run probes
    if args.all:
        results = asyncio.run(probe_all_adapters(
            year=args.year,
            verbose=args.verbose,
            validate=args.validate  # Pass validation flag
        ))
        # Persist real-data probe results to JSON
        save_probe_results(results, year=args.year)
    else:
        result = asyncio.run(probe_adapter(
            args.state,
            year=args.year,
            classification=args.classification,
            gender=args.gender,
            verbose=True,
            dump_html=args.dump_html
        ))

        # Print detailed result for single state
        print(f"\n{'='*80}")
        print(f"PROBE RESULT: {result['state']}")
        print(f"{'='*80}")
        print(f"Adapter: {result['adapter']}")
        print(f"Status: {result['status']}")  # Session 8 - Phase 24: Show classification
        print(f"Success: {result['success']}")
        print(f"Games Found: {result['games_found']}")
        print(f"Teams Found: {result['teams_found']}")

        # Print validation results if --validate flag is set or if verbose
        if args.validate or args.verbose:
            health = result.get("health_score", 0.0)
            errors = result.get("errors_count", 0)
            warnings = result.get("warnings_count", 0)
            health_label = "HEALTHY" if health >= 0.7 else "UNHEALTHY"
            print(f"Health Score: {health:.2f} [{health_label}]")
            print(f"Errors: {errors} | Warnings: {warnings}")

        if result['error_msg']:
            print(f"Error: {result['error_msg']}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
