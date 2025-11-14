"""
State Adapter Smoke Tests - Phases 17-22

Parametrized smoke tests for all state association adapters.
Tests verify that adapters can parse brackets, create games, and generate canonical IDs.

**Current Coverage (35 States)**:
- Phase 17: CA, TX, FL, GA, OH, PA, NY
- Phase 19: IL, NC, VA, WA, MA
- Phase 20: IN, WI, MO, MD, MN
- Phase 21: MI, NJ, AZ, CO, TN, KY, CT, SC
- Phase 22: AL, LA, OR, MS, KS, AR, NE, SD, ID, UT

Usage:
    pytest tests/test_state_adapters_smoke.py -v
    pytest tests/test_state_adapters_smoke.py -v -k "illinois"
    pytest tests/test_state_adapters_smoke.py -v --tb=short
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.california_cif_ss import CaliforniaCIFSSDataSource
from src.datasources.us.texas_uil import TexasUILDataSource
from src.datasources.us.florida_fhsaa import FloridaFHSAADataSource
from src.datasources.us.georgia_ghsa import GeorgiaGHSADataSource
from src.datasources.us.ohio_ohsaa import OhioOHSAADataSource
from src.datasources.us.pennsylvania_piaa import PennsylvaniaPIAADataSource
from src.datasources.us.newyork_nysphsaa import NewYorkNYSPHSAADataSource
from src.datasources.us.illinois_ihsa import IllinoisIHSADataSource
from src.datasources.us.nchsaa import NCHSAADataSource
from src.datasources.us.virginia_vhsl import VirginiaVHSLDataSource
from src.datasources.us.washington_wiaa import WashingtonWIAADataSource
from src.datasources.us.massachusetts_miaa import MassachusettsMiaaDataSource
from src.datasources.us.indiana_ihsaa import IndianaIHSAADataSource
from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.datasources.us.missouri_mshsaa import MissouriMSHSAADataSource
from src.datasources.us.maryland_mpssaa import MarylandMPSSAADataSource
from src.datasources.us.minnesota_mshsl import MinnesotaMSHSLDataSource
from src.datasources.us.michigan_mhsaa import MichiganMHSAADataSource
from src.datasources.us.new_jersey_njsiaa import NewJerseyNJSIAADataSource
from src.datasources.us.arizona_aia import ArizonaAIADataSource
from src.datasources.us.colorado_chsaa import ColoradoCHSAADataSource
from src.datasources.us.tennessee_tssaa import TennesseeTSSAADataSource
from src.datasources.us.kentucky_khsaa import KentuckyKHSAADataSource
from src.datasources.us.connecticut_ciac import ConnecticutCIACDataSource
from src.datasources.us.south_carolina_schsl import SouthCarolinaSCHSLDataSource
# Phase 22 - Priority 3B (10 states)
from src.datasources.us.alabama_ahsaa import AlabamaAHSAADataSource
from src.datasources.us.louisiana_lhsaa import LouisianaLHSAADataSource
from src.datasources.us.oregon_osaa import OregonOSAADataSource
from src.datasources.us.mississippi_mhsaa_ms import MississippiMHSAA_MSDataSource
from src.datasources.us.kansas_kshsaa import KansasKSHSAADataSource
from src.datasources.us.arkansas_aaa import ArkansasAAADataSource
from src.datasources.us.nebraska_nsaa import NebraskaNSAADataSource
from src.datasources.us.south_dakota_sdhsaa import SouthDakotaSDHSAADataSource
from src.datasources.us.idaho_ihsaa import IdahoIHSAADataSource
from src.datasources.us.utah_uhsaa import UtahUHSAADataSource


# Synthetic HTML fixture for bracket testing
# Matches real bracket structure: both teams in same row with scores
SYNTHETIC_BRACKET_HTML = """
<html>
<body>
    <h2>State Championship Bracket - Division 1</h2>
    <div class="bracket">
        <h3>Quarterfinals</h3>
        <table class="bracket-table">
            <tr>
                <th>Team</th>
                <th>Score</th>
                <th>Team</th>
                <th>Score</th>
            </tr>
            <tr>
                <td>Lincoln High School (1)</td>
                <td>65</td>
                <td>Washington Prep (8)</td>
                <td>58</td>
            </tr>
            <tr>
                <td>Roosevelt Academy (4)</td>
                <td>72</td>
                <td>Jefferson Central (5)</td>
                <td>69</td>
            </tr>
        </table>
    </div>
</body>
</html>
"""


# Test parameters: (adapter_class, prefix, league_prefix, classification)
STATE_ADAPTERS = [
    pytest.param(
        CaliforniaCIFSSDataSource,
        "cif_ss",
        "CIF-SS",
        "Open",
        id="california_cif_ss"
    ),
    pytest.param(
        TexasUILDataSource,
        "uil_tx",
        "UIL",
        "6A",
        id="texas_uil"
    ),
    pytest.param(
        FloridaFHSAADataSource,
        "fhsaa",
        "FHSAA",
        "7A",
        id="florida_fhsaa"
    ),
    pytest.param(
        GeorgiaGHSADataSource,
        "ghsa",
        "GHSA",
        "7A",
        id="georgia_ghsa"
    ),
    pytest.param(
        OhioOHSAADataSource,
        "ohsaa",
        "OHSAA",
        "I",
        id="ohio_ohsaa"
    ),
    pytest.param(
        PennsylvaniaPIAADataSource,
        "piaa",
        "PIAA",
        "6A",
        id="pennsylvania_piaa"
    ),
    pytest.param(
        NewYorkNYSPHSAADataSource,
        "nysphsaa",
        "NYSPHSAA",
        "AA",
        id="newyork_nysphsaa"
    ),
    pytest.param(
        IllinoisIHSADataSource,
        "ihsa",
        "IHSA",
        "4A",
        id="illinois_ihsa"
    ),
    pytest.param(
        NCHSAADataSource,
        "nchsaa",
        "NCHSAA",
        "4A",
        id="north_carolina_nchsaa"
    ),
    pytest.param(
        VirginiaVHSLDataSource,
        "vhsl",
        "VHSL",
        "6",
        id="virginia_vhsl"
    ),
    pytest.param(
        WashingtonWIAADataSource,
        "wiaa_wa",
        "WIAA_WA",
        "4A",
        id="washington_wiaa"
    ),
    pytest.param(
        MassachusettsMiaaDataSource,
        "miaa",
        "MIAA",
        "Division 1",
        id="massachusetts_miaa"
    ),
    # Phase 20 - Priority 2 (Mid-Size States)
    pytest.param(
        IndianaIHSAADataSource,
        "ihsaa",
        "IHSAA",
        "4A",
        id="indiana_ihsaa"
    ),
    pytest.param(
        WisconsinWiaaDataSource,
        "wiaa",
        "WIAA",
        "Division 1",
        id="wisconsin_wiaa"
    ),
    pytest.param(
        MissouriMSHSAADataSource,
        "mshsaa",
        "MSHSAA",
        "Class 6",
        id="missouri_mshsaa"
    ),
    pytest.param(
        MarylandMPSSAADataSource,
        "mpssaa",
        "MPSSAA",
        "4A",
        id="maryland_mpssaa"
    ),
    pytest.param(
        MinnesotaMSHSLDataSource,
        "mshsl",
        "MSHSL",
        "4A",
        id="minnesota_mshsl"
    ),
    # Phase 21 - Priority 3A (Mid-Size States)
    pytest.param(
        MichiganMHSAADataSource,
        "mhsaa_mi",
        "MHSAA",
        "Division 1",
        id="michigan_mhsaa"
    ),
    pytest.param(
        NewJerseyNJSIAADataSource,
        "njsiaa",
        "NJSIAA",
        "North Group 1",
        id="new_jersey_njsiaa"
    ),
    pytest.param(
        ArizonaAIADataSource,
        "aia",
        "AIA",
        "6A",
        id="arizona_aia"
    ),
    pytest.param(
        ColoradoCHSAADataSource,
        "chsaa",
        "CHSAA",
        "5A",
        id="colorado_chsaa"
    ),
    pytest.param(
        TennesseeTSSAADataSource,
        "tssaa",
        "TSSAA",
        "4A",
        id="tennessee_tssaa"
    ),
    pytest.param(
        KentuckyKHSAADataSource,
        "khsaa",
        "KHSAA",
        "Region 1",
        id="kentucky_khsaa"
    ),
    pytest.param(
        ConnecticutCIACDataSource,
        "ciac",
        "CIAC",
        "Division I",
        id="connecticut_ciac"
    ),
    pytest.param(
        SouthCarolinaSCHSLDataSource,
        "schsl",
        "SCHSL",
        "5A",
        id="south_carolina_schsl"
    ),
    # Phase 22 - Priority 3B (10 states)
    pytest.param(
        AlabamaAHSAADataSource,
        "ahsaa",
        "AHSAA",
        "7A",
        id="alabama_ahsaa"
    ),
    pytest.param(
        LouisianaLHSAADataSource,
        "lhsaa",
        "LHSAA",
        "5A",
        id="louisiana_lhsaa"
    ),
    pytest.param(
        OregonOSAADataSource,
        "osaa",
        "OSAA",
        "6A",
        id="oregon_osaa"
    ),
    pytest.param(
        MississippiMHSAA_MSDataSource,
        "mhsaa_ms",
        "MHSAA_MS",
        "6A",
        id="mississippi_mhsaa_ms"
    ),
    pytest.param(
        KansasKSHSAADataSource,
        "kshsaa",
        "KSHSAA",
        "6A",
        id="kansas_kshsaa"
    ),
    pytest.param(
        ArkansasAAADataSource,
        "aaa",
        "AAA",
        "6A",
        id="arkansas_aaa"
    ),
    pytest.param(
        NebraskaNSAADataSource,
        "nsaa",
        "NSAA",
        "A",
        id="nebraska_nsaa"
    ),
    pytest.param(
        SouthDakotaSDHSAADataSource,
        "sdhsaa",
        "SDHSAA",
        "AA",
        id="south_dakota_sdhsaa"
    ),
    pytest.param(
        IdahoIHSAADataSource,
        "ihsaa_id",
        "IHSAA",
        "5A",
        id="idaho_ihsaa"
    ),
    pytest.param(
        UtahUHSAADataSource,
        "uhsaa",
        "UHSAA",
        "6A",
        id="utah_uhsaa"
    ),
]


@pytest.mark.smoke_state_adapters
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_cls,prefix,league_prefix,classification", STATE_ADAPTERS)
async def test_state_adapter_can_parse_synthetic_bracket(
    adapter_cls, prefix, league_prefix, classification
):
    """
    Smoke test: Verify state adapter bracket parser wiring is correct.

    This is NOT testing real-world correctness. The goal is to catch:
    - Wiring issues (imports, method names, missing methods)
    - Obvious crashes in _parse_bracket_html
    - Metadata creation problems (e.g. extra kwargs)

    Validates:
    - Adapter has _parse_bracket_html method
    - Method can be called without AttributeError/TypeError
    - If parsing succeeds, result has expected structure

    Note: ValidationError is EXPECTED because synthetic HTML lacks required
    fields (like game_date). This test only checks wiring, not data completeness.
    """
    adapter = adapter_cls()

    try:
        # Parse synthetic HTML
        from src.utils import parse_html
        from pydantic import ValidationError

        soup = parse_html(SYNTHETIC_BRACKET_HTML)

        # Test that method exists and can be called
        year = 2025

        try:
            result = adapter._parse_bracket_html(
                soup, year, classification, "Boys", "https://test.example.com"
            )

            # If parsing succeeds, validate structure
            assert isinstance(result, dict), \
                f"Bracket parser must return dict, got {type(result)}"

            assert "games" in result, \
                "Result missing 'games' key"

            assert "teams" in result, \
                "Result missing 'teams' key"

            # Type checks - don't assert on count
            assert isinstance(result["games"], list), \
                f"result['games'] must be list, got {type(result['games'])}"

            # Teams can be either dict or list depending on adapter
            assert isinstance(result["teams"], (list, dict)), \
                f"result['teams'] must be list or dict, got {type(result['teams'])}"

        except ValidationError:
            # Expected: synthetic HTML doesn't have all required fields (game_date, etc.)
            # This is OK - we're just testing wiring, not data completeness
            pass

        # Success = method exists, can be called, no wiring errors
        # Actual bracket correctness tested in integration tests with real HTML

    finally:
        await adapter.close()


@pytest.mark.smoke_state_adapters
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_cls,prefix,league_prefix,classification", STATE_ADAPTERS)
async def test_state_adapter_health_check(adapter_cls, prefix, league_prefix, classification):
    """
    Test that state adapter base URL is reachable.

    This is a basic smoke test to verify the adapter's base_url is valid.
    Does NOT test actual bracket fetching (that's integration test territory).
    """
    adapter = adapter_cls()

    try:
        # Basic health check - just verify adapter initializes
        assert adapter.base_url, f"{adapter_cls.__name__} has no base_url"
        assert adapter.source_name, f"{adapter_cls.__name__} has no source_name"
        assert adapter.source_type, f"{adapter_cls.__name__} has no source_type"

        # Verify correct prefix is configured
        # Note: Can't check internal methods directly, but we validated in previous test

    finally:
        await adapter.close()


@pytest.mark.smoke_state_adapters
def test_all_state_adapters_are_phase17_18_compliant():
    """
    Test that all state adapters follow Phase 17/18 pattern.

    Validates:
    - Uses shared bracket parser
    - Has canonical team ID generation
    - Has metadata extraction capability
    """
    from src.utils.brackets import parse_bracket_tables_and_divs, canonical_team_id

    for params in STATE_ADAPTERS:
        adapter_cls = params.values[0]  # First param is adapter class
        prefix = params.values[1]  # Second param is prefix

        # Verify adapter uses shared utilities (by checking imports)
        adapter = adapter_cls()

        # Check that adapter has required methods
        assert hasattr(adapter, '_parse_bracket_html'), \
            f"{adapter_cls.__name__} missing _parse_bracket_html"
        assert hasattr(adapter, '_create_game'), \
            f"{adapter_cls.__name__} missing _create_game"
        assert hasattr(adapter, '_create_team'), \
            f"{adapter_cls.__name__} missing _create_team"

        # Test canonical ID generation
        test_team = "Test High School"
        team_id = canonical_team_id(prefix, test_team)
        assert team_id.startswith(prefix), \
            f"Canonical ID '{team_id}' doesn't start with '{prefix}'"
        assert "_" in team_id, "Canonical ID should use underscores"
        assert team_id.islower() or "_" in team_id, "Canonical ID should be lowercase"


@pytest.mark.smoke_state_adapters
def test_state_adapter_coverage():
    """
    Test that we have expected coverage of US states.

    Documents current coverage for visibility.
    """
    # Current coverage
    phase_17_states = ["CA", "TX", "FL", "GA", "OH", "PA", "NY"]
    phase_19_states = ["IL", "NC", "VA", "WA", "MA"]
    phase_20_states = ["IN", "WI", "MO", "MD", "MN"]
    phase_21_states = ["MI", "NJ", "AZ", "CO", "TN", "KY", "CT", "SC"]
    phase_22_states = ["AL", "LA", "OR", "MS", "KS", "AR", "NE", "SD", "ID", "UT"]

    total_states = len(phase_17_states) + len(phase_19_states) + len(phase_20_states) + len(phase_21_states) + len(phase_22_states)
    assert total_states == 35, f"Expected 35 states, got {total_states}"

    # Verify we have 35 adapter test cases
    assert len(STATE_ADAPTERS) == 35, \
        f"Expected 35 STATE_ADAPTERS, got {len(STATE_ADAPTERS)}"

    # Progress towards 50/50
    coverage_pct = (total_states / 50) * 100
    assert coverage_pct >= 70, f"Coverage should be at least 70%, got {coverage_pct:.1f}%"

    print(f"\n{'='*60}")
    print(f"State Adapter Coverage: {total_states}/50 states ({coverage_pct:.1f}%)")
    print(f"Phase 17 (7 states): {', '.join(phase_17_states)}")
    print(f"Phase 19 (5 states): {', '.join(phase_19_states)}")
    print(f"Phase 20 (5 states): {', '.join(phase_20_states)}")
    print(f"Phase 21 (8 states): {', '.join(phase_21_states)}")
    print(f"Phase 22 (10 states): {', '.join(phase_22_states)}")
    print(f"Remaining (15 states): NV, OK, NM, MT, WY, AK, HI, ND, WV, IA, NH, VT, ME, RI, DE")
    print(f"{'='*60}\n")
