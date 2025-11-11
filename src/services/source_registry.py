"""
Source Registry Service

Manages datasource metadata from sources.yaml registry.
Provides auto-routing, capability checking, and source discovery.
"""

import importlib
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SourceCapabilities(BaseModel):
    """Capabilities a datasource can provide."""

    player_search: bool = False
    player_profiles: bool = False
    season_stats: bool = False
    game_stats: bool = False
    box_scores: bool = False
    leaderboards: bool = False
    team_stats: bool = False
    schedules: bool = False
    standings: bool = False


class SourceDataQuality(BaseModel):
    """Data quality indicators for a source."""

    has_player_stats: bool = False
    has_box_scores: bool = False
    stat_completeness: str = "low"  # low, medium, high


class SourceRateLimit(BaseModel):
    """Rate limiting configuration for a source."""

    requests_per_minute: int = 10
    burst_capacity: int = 5
    safety_margin: float = 0.5


class SourceCacheTTL(BaseModel):
    """Cache TTL values for different data types."""

    players: int = 3600
    stats: int = 3600
    games: int = 1800
    standings: int = 7200


class SourceMetadata(BaseModel):
    """Complete metadata for a datasource."""

    id: str
    name: str
    full_name: str
    region: str
    type: str
    status: str
    url: str
    adapter_class: str
    adapter_module: str
    capabilities: SourceCapabilities
    data_quality: SourceDataQuality
    rate_limit: SourceRateLimit
    cache_ttl: SourceCacheTTL
    robots_policy: str = "check"
    url_patterns: dict[str, str] = Field(default_factory=dict)
    states: list[str] = Field(default_factory=list)
    notes: str = ""


class SourceRegistry:
    """
    Source Registry for managing datasource metadata.

    Loads sources.yaml and provides:
    - Source discovery by region, type, capability
    - Auto-routing to appropriate adapters
    - Dynamic adapter loading
    - Capability checking
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize source registry.

        Args:
            registry_path: Path to sources.yaml (default: config/sources.yaml)
        """
        if registry_path is None:
            # Default to config/sources.yaml in project root
            project_root = Path(__file__).parent.parent.parent
            registry_path = project_root / "config" / "sources.yaml"

        self.registry_path = registry_path
        self.sources: dict[str, SourceMetadata] = {}
        self.events: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}

        self._load_registry()

    def _load_registry(self) -> None:
        """Load sources from YAML registry."""
        try:
            with open(self.registry_path) as f:
                data = yaml.safe_load(f)

            # Load sources
            for source_data in data.get("sources", []):
                try:
                    source = SourceMetadata(**source_data)
                    self.sources[source.id] = source
                except Exception as e:
                    logger.error(f"Failed to parse source {source_data.get('id')}: {e}")

            # Load events
            self.events = data.get("events", [])

            # Load metadata
            self.metadata = data.get("metadata", {})

            logger.info(
                f"Loaded {len(self.sources)} sources from registry",
                active=len(self.get_sources_by_status("active")),
                planned=len(self.get_sources_by_status("planned")),
                template=len(self.get_sources_by_status("template")),
            )

        except FileNotFoundError:
            logger.error(f"Registry file not found: {self.registry_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            raise

    def get_source(self, source_id: str) -> Optional[SourceMetadata]:
        """
        Get source metadata by ID.

        Args:
            source_id: Source identifier (e.g., 'eybl', 'psal')

        Returns:
            SourceMetadata or None
        """
        return self.sources.get(source_id)

    def get_sources_by_status(self, status: str) -> list[SourceMetadata]:
        """
        Get all sources with given status.

        Args:
            status: 'active', 'planned', or 'template'

        Returns:
            List of matching sources
        """
        return [s for s in self.sources.values() if s.status == status]

    def get_sources_by_region(self, region: str) -> list[SourceMetadata]:
        """
        Get all sources for a region.

        Args:
            region: Region code (e.g., 'US', 'EUROPE', 'US-CA')

        Returns:
            List of matching sources
        """
        return [s for s in self.sources.values() if s.region.startswith(region)]

    def get_sources_by_capability(
        self, capability: str, required: bool = True
    ) -> list[SourceMetadata]:
        """
        Get sources that have a specific capability.

        Args:
            capability: Capability name (e.g., 'player_search', 'box_scores')
            required: If True, capability must be True

        Returns:
            List of sources with the capability
        """
        result = []
        for source in self.sources.values():
            cap_value = getattr(source.capabilities, capability, None)
            if cap_value is not None:
                if (required and cap_value) or (not required):
                    result.append(source)
        return result

    def get_sources_by_type(self, source_type: str) -> list[SourceMetadata]:
        """
        Get sources by type.

        Args:
            source_type: 'state', 'circuit', 'tournament', 'platform', etc.

        Returns:
            List of matching sources
        """
        return [s for s in self.sources.values() if s.type == source_type]

    def get_active_sources(self) -> list[SourceMetadata]:
        """Get all active (working) sources."""
        return self.get_sources_by_status("active")

    def get_sources_for_query(
        self,
        region: Optional[str] = None,
        capability: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> list[SourceMetadata]:
        """
        Get sources matching query filters.

        Args:
            region: Filter by region
            capability: Filter by capability
            status: Filter by status (default: 'active')

        Returns:
            List of matching sources
        """
        sources = list(self.sources.values())

        if status:
            sources = [s for s in sources if s.status == status]

        if region:
            sources = [s for s in sources if s.region.startswith(region)]

        if capability:
            sources = [
                s
                for s in sources
                if getattr(s.capabilities, capability, False)
            ]

        return sources

    def load_adapter(self, source_id: str):
        """
        Dynamically load adapter class for a source.

        Args:
            source_id: Source identifier

        Returns:
            Adapter class instance or None

        Example:
            registry = SourceRegistry()
            eybl = registry.load_adapter('eybl')
            players = await eybl.search_players(limit=10)
        """
        source = self.get_source(source_id)
        if not source:
            logger.error(f"Source not found: {source_id}")
            return None

        try:
            # Import module
            module = importlib.import_module(source.adapter_module)

            # Get class
            adapter_class = getattr(module, source.adapter_class)

            # Instantiate
            adapter = adapter_class()

            logger.info(f"Loaded adapter for {source_id}", adapter=source.adapter_class)
            return adapter

        except ImportError as e:
            logger.error(
                f"Failed to import adapter module",
                source_id=source_id,
                module=source.adapter_module,
                error=str(e),
            )
            return None
        except AttributeError as e:
            logger.error(
                f"Adapter class not found in module",
                source_id=source_id,
                class_name=source.adapter_class,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load adapter", source_id=source_id, error=str(e))
            return None

    def get_source_ids(self, status: Optional[str] = None) -> list[str]:
        """
        Get list of source IDs, optionally filtered by status.

        Args:
            status: Filter by status (None = all)

        Returns:
            List of source IDs
        """
        if status:
            return [s.id for s in self.sources.values() if s.status == status]
        return list(self.sources.keys())

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of registry contents.

        Returns:
            Dictionary with counts and stats
        """
        return {
            "total_sources": len(self.sources),
            "active": len(self.get_sources_by_status("active")),
            "planned": len(self.get_sources_by_status("planned")),
            "template": len(self.get_sources_by_status("template")),
            "by_region": self.metadata.get("by_region", {}),
            "capabilities": {
                "player_search": len(self.get_sources_by_capability("player_search")),
                "season_stats": len(self.get_sources_by_capability("season_stats")),
                "box_scores": len(self.get_sources_by_capability("box_scores")),
                "leaderboards": len(self.get_sources_by_capability("leaderboards")),
            },
            "events": len(self.events),
        }

    def validate_source(self, source_id: str) -> dict[str, Any]:
        """
        Validate a source configuration.

        Args:
            source_id: Source to validate

        Returns:
            Validation results
        """
        source = self.get_source(source_id)
        if not source:
            return {"valid": False, "error": "Source not found"}

        issues = []

        # Check if adapter module exists
        try:
            importlib.import_module(source.adapter_module)
        except ImportError:
            issues.append(f"Adapter module not found: {source.adapter_module}")

        # Check rate limit sanity
        if source.rate_limit.requests_per_minute < 1:
            issues.append("Rate limit too low (< 1 req/min)")

        # Check cache TTLs
        if any(ttl < 0 for ttl in [source.cache_ttl.players, source.cache_ttl.stats]):
            issues.append("Negative cache TTL values")

        return {
            "valid": len(issues) == 0,
            "source_id": source_id,
            "status": source.status,
            "issues": issues,
        }


# Singleton instance
_registry: Optional[SourceRegistry] = None


def get_source_registry() -> SourceRegistry:
    """
    Get singleton source registry instance.

    Returns:
        SourceRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = SourceRegistry()
    return _registry


def list_sources(status: Optional[str] = None, region: Optional[str] = None) -> None:
    """
    Print list of available sources.

    Args:
        status: Filter by status
        region: Filter by region
    """
    registry = get_source_registry()
    sources = list(registry.sources.values())

    if status:
        sources = [s for s in sources if s.status == status]
    if region:
        sources = [s for s in sources if s.region.startswith(region)]

    print(f"\nAvailable Sources ({len(sources)}):\n")
    print(f"{'ID':<20} {'Name':<30} {'Region':<15} {'Status':<10} {'Stats'}")
    print("=" * 95)

    for source in sorted(sources, key=lambda x: (x.region, x.name)):
        stats_marker = "✓" if source.data_quality.has_player_stats else "○"
        box_marker = "✓" if source.data_quality.has_box_scores else "○"

        print(
            f"{source.id:<20} {source.name:<30} {source.region:<15} "
            f"{source.status:<10} {stats_marker} Stats, {box_marker} Box"
        )

    print()


# CLI helper
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            status = sys.argv[2] if len(sys.argv) > 2 else None
            list_sources(status=status)
        elif command == "summary":
            registry = get_source_registry()
            summary = registry.get_summary()
            print("\nSource Registry Summary:\n")
            for key, value in summary.items():
                print(f"{key}: {value}")
        elif command == "validate":
            source_id = sys.argv[2] if len(sys.argv) > 2 else None
            if source_id:
                registry = get_source_registry()
                result = registry.validate_source(source_id)
                print(f"\nValidation for {source_id}:")
                print(f"Valid: {result['valid']}")
                if result.get("issues"):
                    print("Issues:")
                    for issue in result["issues"]:
                        print(f"  - {issue}")
    else:
        list_sources(status="active")
