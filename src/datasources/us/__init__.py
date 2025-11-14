"""
US DataSource Adapters

This module uses lazy loading to avoid importing all 44 adapters at once.
Import failures in one adapter (e.g., missing bs4 in bound.py) do NOT break other adapters.

Recommended Usage (fastest, most explicit):
    from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource

Registry Usage (dynamic loading):
    from src.datasources.us.registry import get_adapter_class, create_state_adapter
    WisconsinWiaaDataSource = get_adapter_class("WisconsinWiaaDataSource")
    source = create_state_adapter("WI")

Backwards Compatible (lazy via __getattr__):
    from src.datasources.us import WisconsinWiaaDataSource, BoundDataSource

Design Benefits:
- Only imports adapters you actually use (1 module vs 44 modules)
- Clear error messages with full tracebacks when imports fail
- Isolated failures (broken adapter doesn't break others)
- Backwards compatible with existing code
"""

from typing import Any

from .registry import ADAPTERS, get_adapter_class

# Export registry functions for convenience
from .registry import (  # noqa: F401
    STATE_TO_ADAPTER,
    create_adapter,
    create_state_adapter,
    get_state_adapter_class,
    list_adapters,
    list_states,
)

# __all__ maintained for IDE autocomplete and explicit exports
# Note: These are lazily loaded via __getattr__ below, NOT eagerly imported
__all__ = [
    # Registry functions
    "ADAPTERS",
    "STATE_TO_ADAPTER",
    "get_adapter_class",
    "get_state_adapter_class",
    "create_adapter",
    "create_state_adapter",
    "list_adapters",
    "list_states",
    # National circuits (11 adapters)
    "BoundDataSource",
    "EYBLDataSource",
    "EYBLGirlsDataSource",
    "GrindSessionDataSource",
    "OTEDataSource",
    "RankOneDataSource",
    "SBLiveDataSource",
    "ThreeSSBDataSource",
    "ThreeSSBGirlsDataSource",
    "UAADataSource",
    "UAAGirlsDataSource",
    # Regional/State platforms (5 adapters)
    "FHSAADataSource",
    "HHSAADataSource",
    "MNHubDataSource",
    "PSALDataSource",
    "WSNDataSource",
    # State associations - Southeast (11 adapters)
    "AlabamaAhsaaDataSource",
    "ArkansasAaaDataSource",
    "GeorgiaGhsaDataSource",
    "KentuckyKhsaaDataSource",
    "LouisianaLhsaaDataSource",
    "MississippiMhsaaDataSource",
    "NCHSAADataSource",
    "SouthCarolinaSchslDataSource",
    "TennesseeTssaaDataSource",
    "VirginiaVhslDataSource",
    "WestVirginiaWvssacDataSource",
    # State associations - Northeast (11 adapters)
    "ConnecticutCiacDataSource",
    "DelawareDiaaDataSource",
    "MaineMpaDataSource",
    "MarylandMpssaaDataSource",
    "MassachusettsMiaaDataSource",
    "NEPSACDataSource",
    "NewHampshireNhiaaDataSource",
    "NewJerseyNjsiaaDataSource",
    "PennsylvaniaPiaaDataSource",
    "RhodeIslandRiilDataSource",
    "VermontVpaDataSource",
    # State associations - Midwest (8 adapters)
    "IndianaIhsaaDataSource",
    "KansasKshsaaDataSource",
    "MichiganMhsaaDataSource",
    "MissouriMshsaaDataSource",
    "NebraskaNsaaDataSource",
    "NorthDakotaNdhsaaDataSource",
    "OhioOhsaaDataSource",
    "WisconsinWiaaDataSource",
    # State associations - Southwest/West (8 adapters)
    "AlaskaAsaaDataSource",
    "ColoradoChsaaDataSource",
    "DcDciaaDataSource",
    "MontanaMhsaDataSource",
    "NewMexicoNmaaDataSource",
    "OklahomaOssaaDataSource",
    "UtahUhsaaDataSource",
    "WyomingWhsaaDataSource",
]


def __getattr__(name: str) -> Any:
    """
    Lazy import mechanism for backwards compatibility.

    When you do: from src.datasources.us import WisconsinWiaaDataSource
    Python calls: __getattr__("WisconsinWiaaDataSource")

    This function then imports ONLY that adapter (not all 44).

    Benefits:
    - Backwards compatible with existing code
    - Only imports what you use
    - Clear error messages if adapter fails to import

    Args:
        name: Adapter class name being requested

    Returns:
        The adapter class

    Raises:
        AttributeError: If adapter not in registry
        ImportError: If adapter module cannot be imported
    """
    if name in ADAPTERS:
        try:
            return get_adapter_class(name)
        except (ImportError, AttributeError) as e:
            # Re-raise with context that this came from lazy loading
            raise ImportError(
                f"Failed to lazy-load adapter '{name}' from src.datasources.us. "
                f"Original error: {e}"
            ) from e

    # Standard behavior for unknown attributes
    raise AttributeError(f"module 'src.datasources.us' has no attribute '{name}'")


def __dir__() -> list[str]:
    """
    Custom dir() for better IDE autocomplete.

    Returns all available adapter names plus registry functions.
    """
    return __all__
