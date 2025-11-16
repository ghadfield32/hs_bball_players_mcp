"""
Datasource Registry

Central registry for all datasources with filtering by category.
Prevents accidentally using wrong datasource types in pipelines.

Added: Phase HS-1 (2025-11-16)
Purpose: Enforce datasource category separation (PLAYER_STATS vs RECRUITING vs BRACKETS)

Author: Claude Code
"""

from typing import Dict, List, Optional, Type

from ..models import DataSourceCategory, DataSourceType
from ..utils import get_logger

logger = get_logger(__name__)


class DatasourceRegistry:
    """
    Central registry for datasources with category filtering.

    Prevents mixing datasource types:
    - PLAYER_STATS sources (GoBound, EYBL, MaxPreps) for season statistics
    - RECRUITING sources (On3, 247Sports, Rivals) for rankings and offers
    - BRACKETS sources (State associations) for tournament brackets
    - SCHEDULES sources (RankOne) for schedules/fixtures only

    Usage:
        registry = DatasourceRegistry()
        stats_sources = registry.get_by_category(DataSourceCategory.PLAYER_STATS)
        recruiting_sources = registry.get_by_category(DataSourceCategory.RECRUITING)
    """

    def __init__(self):
        """Initialize datasource registry."""
        self._datasources: Dict[DataSourceType, Type] = {}
        self._categories: Dict[DataSourceType, DataSourceCategory] = {}
        self._initialized = False
        logger.info("Datasource registry initialized")

    def register(
        self,
        source_type: DataSourceType,
        datasource_class: Type,
        category: Optional[DataSourceCategory] = None
    ):
        """
        Register a datasource class.

        Args:
            source_type: DataSourceType enum value
            datasource_class: Datasource class (must have CATEGORY attribute)
            category: Optional category override (uses datasource_class.CATEGORY if not provided)

        Raises:
            ValueError: If datasource class doesn't have CATEGORY attribute
        """
        # Get category from class or use override
        if category is None:
            if not hasattr(datasource_class, 'CATEGORY'):
                raise ValueError(
                    f"{datasource_class.__name__} must have CATEGORY attribute. "
                    f"Add: CATEGORY = DataSourceCategory.PLAYER_STATS (or RECRUITING/BRACKETS/SCHEDULES)"
                )
            category = datasource_class.CATEGORY

        self._datasources[source_type] = datasource_class
        self._categories[source_type] = category

        logger.debug(
            "Datasource registered",
            source_type=source_type.value,
            class_name=datasource_class.__name__,
            category=category.value
        )

    def get(self, source_type: DataSourceType) -> Optional[Type]:
        """
        Get datasource class by type.

        Args:
            source_type: DataSourceType enum value

        Returns:
            Datasource class or None if not registered
        """
        return self._datasources.get(source_type)

    def get_by_category(self, category: DataSourceCategory) -> Dict[DataSourceType, Type]:
        """
        Get all datasources of a specific category.

        Args:
            category: DataSourceCategory to filter by

        Returns:
            Dictionary mapping source_type -> datasource_class for matching category

        Example:
            # Get only player statistics sources
            stats_sources = registry.get_by_category(DataSourceCategory.PLAYER_STATS)
            # Returns: {DataSourceType.BOUND: BoundDataSource, DataSourceType.EYBL: EYBLDataSource, ...}
        """
        filtered = {
            source_type: datasource_class
            for source_type, datasource_class in self._datasources.items()
            if self._categories.get(source_type) == category
        }

        logger.debug(
            "Filtered datasources by category",
            category=category.value,
            count=len(filtered),
            sources=[st.value for st in filtered.keys()]
        )

        return filtered

    def get_category(self, source_type: DataSourceType) -> Optional[DataSourceCategory]:
        """
        Get category for a specific datasource type.

        Args:
            source_type: DataSourceType enum value

        Returns:
            DataSourceCategory or None if not registered
        """
        return self._categories.get(source_type)

    def list_all(self) -> Dict[DataSourceCategory, List[DataSourceType]]:
        """
        List all registered datasources grouped by category.

        Returns:
            Dictionary mapping category -> list of source types

        Example:
            {
                DataSourceCategory.PLAYER_STATS: [DataSourceType.BOUND, DataSourceType.EYBL],
                DataSourceCategory.RECRUITING: [DataSourceType.ON3, DataSourceType.SPORTS_247],
                DataSourceCategory.BRACKETS: [DataSourceType.GHSA, DataSourceType.FHSAA],
                DataSourceCategory.SCHEDULES: [DataSourceType.RANKONE]
            }
        """
        grouped: Dict[DataSourceCategory, List[DataSourceType]] = {}

        for source_type, category in self._categories.items():
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(source_type)

        return grouped

    def validate_for_pipeline(
        self,
        source_types: List[DataSourceType],
        expected_category: DataSourceCategory
    ) -> bool:
        """
        Validate that all source types match expected category.

        Useful for ensuring a pipeline only uses appropriate datasources.

        Args:
            source_types: List of DataSourceType enum values to validate
            expected_category: Expected category for all sources

        Returns:
            True if all sources match expected category, False otherwise

        Example:
            # Validate that a player stats pipeline only uses PLAYER_STATS sources
            sources = [DataSourceType.BOUND, DataSourceType.EYBL]
            is_valid = registry.validate_for_pipeline(sources, DataSourceCategory.PLAYER_STATS)
        """
        for source_type in source_types:
            category = self.get_category(source_type)
            if category != expected_category:
                logger.warning(
                    "Datasource category mismatch in pipeline validation",
                    source_type=source_type.value,
                    expected_category=expected_category.value,
                    actual_category=category.value if category else "unregistered"
                )
                return False

        return True


# Global registry instance
_registry = DatasourceRegistry()


def get_registry() -> DatasourceRegistry:
    """
    Get the global datasource registry.

    Returns:
        Global DatasourceRegistry instance
    """
    return _registry


def auto_register_datasources():
    """
    Auto-register all available datasources.

    This function imports and registers datasources from known modules.
    Call this once at application startup.

    Note: Only imports datasources that are known to be stable/working.
    """
    registry = get_registry()

    # Import datasource classes
    # Note: Only import working datasources to avoid initialization errors
    try:
        from .us.bound import BoundDataSource
        registry.register(DataSourceType.BOUND, BoundDataSource)
    except ImportError as e:
        logger.debug(f"Could not import BoundDataSource: {e}")

    try:
        from .us.eybl import EYBLDataSource
        registry.register(DataSourceType.EYBL, EYBLDataSource)
    except ImportError as e:
        logger.debug(f"Could not import EYBLDataSource: {e}")

    try:
        from .us.maxpreps import MaxPrepsDataSource
        registry.register(DataSourceType.MAXPREPS, MaxPrepsDataSource)
    except ImportError as e:
        logger.debug(f"Could not import MaxPrepsDataSource: {e}")

    try:
        from .us.rankone import RankOneDataSource
        registry.register(DataSourceType.RANKONE, RankOneDataSource)
    except ImportError as e:
        logger.debug(f"Could not import RankOneDataSource: {e}")

    try:
        from .recruiting.on3 import On3DataSource
        registry.register(DataSourceType.ON3, On3DataSource)
    except ImportError as e:
        logger.debug(f"Could not import On3DataSource: {e}")

    try:
        from .recruiting.sports_247 import Sports247DataSource
        registry.register(DataSourceType.SPORTS_247, Sports247DataSource)
    except ImportError as e:
        logger.debug(f"Could not import Sports247DataSource: {e}")

    # Add more datasources as they become stable

    logger.info(
        "Datasources auto-registered",
        total=len(registry._datasources),
        by_category=registry.list_all()
    )

    return registry
