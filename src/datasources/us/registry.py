"""
US Datasource Adapter Registry

Lazy-loading registry for all US high school basketball datasource adapters.
This architecture prevents import failures in one adapter from breaking others.

Design Benefits:
- Only imports adapters that are actually used (1 module vs 44 modules)
- Isolates import failures to specific adapters (missing bs4 in bound.py doesn't break wisconsin_wiaa.py)
- Provides clear error messages with full tracebacks
- Maintains backwards compatibility with existing import patterns

Usage:
    # Direct import (recommended, fastest)
    from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource

    # Lazy import via registry (good for dynamic loading)
    from src.datasources.us.registry import get_adapter_class
    WisconsinWiaaDataSource = get_adapter_class("WisconsinWiaaDataSource")

    # Bulk import (backwards compatible, uses __getattr__)
    from src.datasources.us import WisconsinWiaaDataSource, BoundDataSource
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Type

# Master registry: Maps adapter class names to "module_path:ClassName"
# This is the SINGLE source of truth for all US datasource adapters
ADAPTERS: Dict[str, str] = {
    # National circuits (11 adapters)
    "BoundDataSource": "src.datasources.us.bound:BoundDataSource",
    "EYBLDataSource": "src.datasources.us.eybl:EYBLDataSource",
    "EYBLGirlsDataSource": "src.datasources.us.eybl_girls:EYBLGirlsDataSource",
    "GrindSessionDataSource": "src.datasources.us.grind_session:GrindSessionDataSource",
    "OTEDataSource": "src.datasources.us.ote:OTEDataSource",
    "RankOneDataSource": "src.datasources.us.rankone:RankOneDataSource",
    "SBLiveDataSource": "src.datasources.us.sblive:SBLiveDataSource",
    "ThreeSSBDataSource": "src.datasources.us.three_ssb:ThreeSSBDataSource",
    "ThreeSSBGirlsDataSource": "src.datasources.us.three_ssb_girls:ThreeSSBGirlsDataSource",
    "UAADataSource": "src.datasources.us.uaa:UAADataSource",
    "UAAGirlsDataSource": "src.datasources.us.uaa_girls:UAAGirlsDataSource",
    # Regional/State platforms (5 adapters)
    "FHSAADataSource": "src.datasources.us.fhsaa:FHSAADataSource",
    "HHSAADataSource": "src.datasources.us.hhsaa:HHSAADataSource",
    "MNHubDataSource": "src.datasources.us.mn_hub:MNHubDataSource",
    "PSALDataSource": "src.datasources.us.psal:PSALDataSource",
    "WSNDataSource": "src.datasources.us.wsn:WSNDataSource",
    # State associations - Southeast (11 adapters)
    "AlabamaAhsaaDataSource": "src.datasources.us.alabama_ahsaa:AlabamaAhsaaDataSource",
    "ArkansasAaaDataSource": "src.datasources.us.arkansas_aaa:ArkansasAaaDataSource",
    "GeorgiaGhsaDataSource": "src.datasources.us.georgia_ghsa:GeorgiaGhsaDataSource",
    "KentuckyKhsaaDataSource": "src.datasources.us.kentucky_khsaa:KentuckyKhsaaDataSource",
    "LouisianaLhsaaDataSource": "src.datasources.us.louisiana_lhsaa:LouisianaLhsaaDataSource",
    "MississippiMhsaaDataSource": "src.datasources.us.mississippi_mhsaa:MississippiMhsaaDataSource",
    "NCHSAADataSource": "src.datasources.us.nchsaa:NCHSAADataSource",
    "SouthCarolinaSchslDataSource": "src.datasources.us.south_carolina_schsl:SouthCarolinaSchslDataSource",
    "TennesseeTssaaDataSource": "src.datasources.us.tennessee_tssaa:TennesseeTssaaDataSource",
    "VirginiaVhslDataSource": "src.datasources.us.virginia_vhsl:VirginiaVhslDataSource",
    "WestVirginiaWvssacDataSource": "src.datasources.us.west_virginia_wvssac:WestVirginiaWvssacDataSource",
    # State associations - Northeast (11 adapters)
    "ConnecticutCiacDataSource": "src.datasources.us.connecticut_ciac:ConnecticutCiacDataSource",
    "DelawareDiaaDataSource": "src.datasources.us.delaware_diaa:DelawareDiaaDataSource",
    "MaineMpaDataSource": "src.datasources.us.maine_mpa:MaineMpaDataSource",
    "MarylandMpssaaDataSource": "src.datasources.us.maryland_mpssaa:MarylandMpssaaDataSource",
    "MassachusettsMiaaDataSource": "src.datasources.us.massachusetts_miaa:MassachusettsMiaaDataSource",
    "NEPSACDataSource": "src.datasources.us.nepsac:NEPSACDataSource",
    "NewHampshireNhiaaDataSource": "src.datasources.us.new_hampshire_nhiaa:NewHampshireNhiaaDataSource",
    "NewJerseyNjsiaaDataSource": "src.datasources.us.new_jersey_njsiaa:NewJerseyNjsiaaDataSource",
    "PennsylvaniaPiaaDataSource": "src.datasources.us.pennsylvania_piaa:PennsylvaniaPiaaDataSource",
    "RhodeIslandRiilDataSource": "src.datasources.us.rhode_island_riil:RhodeIslandRiilDataSource",
    "VermontVpaDataSource": "src.datasources.us.vermont_vpa:VermontVpaDataSource",
    # State associations - Midwest (7 adapters)
    "IndianaIhsaaDataSource": "src.datasources.us.indiana_ihsaa:IndianaIhsaaDataSource",
    "KansasKshsaaDataSource": "src.datasources.us.kansas_kshsaa:KansasKshsaaDataSource",
    "MichiganMhsaaDataSource": "src.datasources.us.michigan_mhsaa:MichiganMhsaaDataSource",
    "MissouriMshsaaDataSource": "src.datasources.us.missouri_mshsaa:MissouriMshsaaDataSource",
    "NebraskaNsaaDataSource": "src.datasources.us.nebraska_nsaa:NebraskaNsaaDataSource",
    "NorthDakotaNdhsaaDataSource": "src.datasources.us.north_dakota_ndhsaa:NorthDakotaNdhsaaDataSource",
    "OhioOhsaaDataSource": "src.datasources.us.ohio_ohsaa:OhioOhsaaDataSource",
    "WisconsinWiaaDataSource": "src.datasources.us.wisconsin_wiaa:WisconsinWiaaDataSource",
    # State associations - Southwest/West (8 adapters)
    "AlaskaAsaaDataSource": "src.datasources.us.alaska_asaa:AlaskaAsaaDataSource",
    "ColoradoChsaaDataSource": "src.datasources.us.colorado_chsaa:ColoradoChsaaDataSource",
    "DcDciaaDataSource": "src.datasources.us.dc_dciaa:DcDciaaDataSource",
    "MontanaMhsaDataSource": "src.datasources.us.montana_mhsa:MontanaMhsaDataSource",
    "NewMexicoNmaaDataSource": "src.datasources.us.new_mexico_nmaa:NewMexicoNmaaDataSource",
    "OklahomaOssaaDataSource": "src.datasources.us.oklahoma_ossaa:OklahomaOssaaDataSource",
    "UtahUhsaaDataSource": "src.datasources.us.utah_uhsaa:UtahUhsaaDataSource",
    "WyomingWhsaaDataSource": "src.datasources.us.wyoming_whsaa:WyomingWhsaaDataSource",
}

# State code to adapter name mapping (for convenience)
STATE_TO_ADAPTER: Dict[str, str] = {
    "AL": "AlabamaAhsaaDataSource",
    "AK": "AlaskaAsaaDataSource",
    "AR": "ArkansasAaaDataSource",
    "CO": "ColoradoChsaaDataSource",
    "CT": "ConnecticutCiacDataSource",
    "DC": "DcDciaaDataSource",
    "DE": "DelawareDiaaDataSource",
    "FL": "FHSAADataSource",
    "GA": "GeorgiaGhsaDataSource",
    "HI": "HHSAADataSource",
    "IN": "IndianaIhsaaDataSource",
    "KS": "KansasKshsaaDataSource",
    "KY": "KentuckyKhsaaDataSource",
    "LA": "LouisianaLhsaaDataSource",
    "ME": "MaineMpaDataSource",
    "MD": "MarylandMpssaaDataSource",
    "MA": "MassachusettsMiaaDataSource",
    "MI": "MichiganMhsaaDataSource",
    "MN": "MNHubDataSource",
    "MS": "MississippiMhsaaDataSource",
    "MO": "MissouriMshsaaDataSource",
    "MT": "MontanaMhsaDataSource",
    "NE": "NebraskaNsaaDataSource",
    "NH": "NewHampshireNhiaaDataSource",
    "NJ": "NewJerseyNjsiaaDataSource",
    "NM": "NewMexicoNmaaDataSource",
    "NY": "PSALDataSource",  # NYC only
    "NC": "NCHSAADataSource",
    "ND": "NorthDakotaNdhsaaDataSource",
    "OH": "OhioOhsaaDataSource",
    "OK": "OklahomaOssaaDataSource",
    "PA": "PennsylvaniaPiaaDataSource",
    "RI": "RhodeIslandRiilDataSource",
    "SC": "SouthCarolinaSchslDataSource",
    "TN": "TennesseeTssaaDataSource",
    "UT": "UtahUhsaaDataSource",
    "VT": "VermontVpaDataSource",
    "VA": "VirginiaVhslDataSource",
    "WV": "WestVirginiaWvssacDataSource",
    "WI": "WisconsinWiaaDataSource",
    "WY": "WyomingWhsaaDataSource",
}


def get_adapter_class(adapter_name: str) -> Type[Any]:
    """
    Lazily import and return an adapter class by name.

    This function only imports the specific adapter requested, not all 44 adapters.
    If the adapter has missing dependencies (e.g., bs4), the ImportError will be
    raised with a clear traceback showing exactly what's missing.

    Args:
        adapter_name: Name of the adapter class (e.g., "WisconsinWiaaDataSource")

    Returns:
        The adapter class (not an instance)

    Raises:
        KeyError: If adapter_name is not in the registry
        ImportError: If the adapter module cannot be imported (missing dependencies, syntax errors, etc.)
        AttributeError: If the class doesn't exist in the module

    Example:
        >>> cls = get_adapter_class("WisconsinWiaaDataSource")
        >>> source = cls()  # Create instance
        >>> await source.get_tournament_bracket(2024, "Boys", 1)
    """
    if adapter_name not in ADAPTERS:
        available = ", ".join(sorted(ADAPTERS.keys()))
        raise KeyError(
            f"Adapter '{adapter_name}' not found in registry. "
            f"Available adapters: {available}"
        )

    module_path, class_name = ADAPTERS[adapter_name].rsplit(":", 1)

    try:
        module = import_module(module_path)
    except ImportError as e:
        # Re-raise with helpful context about which adapter failed
        raise ImportError(
            f"Failed to import module for adapter '{adapter_name}' "
            f"from '{module_path}': {e}"
        ) from e

    try:
        cls = getattr(module, class_name)
    except AttributeError as e:
        raise AttributeError(
            f"Module '{module_path}' does not have class '{class_name}'. "
            f"Available: {dir(module)}"
        ) from e

    return cls


def get_state_adapter_class(state_code: str) -> Type[Any]:
    """
    Get adapter class by state code (e.g., "WI" -> WisconsinWiaaDataSource).

    Args:
        state_code: Two-letter state code (e.g., "WI", "AL")

    Returns:
        The adapter class

    Raises:
        KeyError: If state code is not supported
        ImportError: If adapter module cannot be imported

    Example:
        >>> cls = get_state_adapter_class("WI")
        >>> source = cls()
    """
    state_code = state_code.upper()
    if state_code not in STATE_TO_ADAPTER:
        available = ", ".join(sorted(STATE_TO_ADAPTER.keys()))
        raise KeyError(
            f"No adapter registered for state '{state_code}'. "
            f"Available states: {available}"
        )

    adapter_name = STATE_TO_ADAPTER[state_code]
    return get_adapter_class(adapter_name)


def create_adapter(adapter_name: str, **kwargs: Any) -> Any:
    """
    Convenience function to instantiate an adapter by name.

    Args:
        adapter_name: Name of the adapter class
        **kwargs: Arguments to pass to adapter constructor

    Returns:
        Instantiated adapter

    Example:
        >>> source = create_adapter("WisconsinWiaaDataSource")
        >>> await source.get_tournament_bracket(2024, "Boys", 1)
    """
    cls = get_adapter_class(adapter_name)
    return cls(**kwargs)


def create_state_adapter(state_code: str, **kwargs: Any) -> Any:
    """
    Convenience function to instantiate an adapter by state code.

    Args:
        state_code: Two-letter state code
        **kwargs: Arguments to pass to adapter constructor

    Returns:
        Instantiated adapter

    Example:
        >>> source = create_state_adapter("WI")
        >>> await source.get_tournament_bracket(2024, "Boys", 1)
    """
    cls = get_state_adapter_class(state_code)
    return cls(**kwargs)


def list_adapters() -> list[str]:
    """
    Get list of all registered adapter names.

    Returns:
        Sorted list of adapter class names
    """
    return sorted(ADAPTERS.keys())


def list_states() -> list[str]:
    """
    Get list of all supported state codes.

    Returns:
        Sorted list of two-letter state codes
    """
    return sorted(STATE_TO_ADAPTER.keys())
