"""
Base Recruiting DataSource Adapter

Abstract base class for all recruiting data source adapters.
Recruiting sources have different interface than stats sources (no games/teams).

Author: Claude Code
Date: 2025-11-14
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from pydantic import ValidationError

from ...config import get_settings
from ...models import (
    CollegeOffer,
    DataQualityFlag,
    DataSource,
    DataSourceRegion,
    DataSourceType,
    RecruitingPrediction,
    RecruitingProfile,
    RecruitingRank,
)
from ...utils import get_logger
from ...utils.http_client import create_http_client

logger = get_logger(__name__)


class BaseRecruitingSource(ABC):
    """
    Abstract base class for recruiting data source adapters.

    All recruiting datasource adapters must inherit from this class
    and implement the abstract methods.

    **Key Differences from BaseDataSource**:
    - Focus on player rankings and recruiting (not game stats)
    - Methods for rankings, offers, commitments, predictions
    - No game/team stats methods

    **Common Pattern**:
    - get_rankings() - List of ranked players
    - get_player_profile() - Individual player recruiting profile
    - search_players() - Search by name/location/class
    - get_offers() - College offers for player(s)
    - get_predictions() - Crystal Ball style predictions
    """

    # Class attributes to be set by subclasses
    source_type: DataSourceType
    source_name: str
    base_url: str
    region: DataSourceRegion

    def __init__(self):
        """Initialize base recruiting datasource."""
        self.settings = get_settings()
        self.http_client = create_http_client(self.source_type.value)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Verify subclass set required attributes
        if not hasattr(self, "source_type"):
            raise NotImplementedError("Subclass must set 'source_type' attribute")
        if not hasattr(self, "source_name"):
            raise NotImplementedError("Subclass must set 'source_name' attribute")
        if not hasattr(self, "base_url"):
            raise NotImplementedError("Subclass must set 'base_url' attribute")
        if not hasattr(self, "region"):
            raise NotImplementedError("Subclass must set 'region' attribute")

        self.logger.info(
            f"Recruiting datasource initialized",
            source=self.source_name,
            type=self.source_type.value,
            region=self.region.value,
        )

    def create_data_source_metadata(
        self,
        url: Optional[str] = None,
        quality_flag: DataQualityFlag = DataQualityFlag.UNVERIFIED,
        notes: Optional[str] = None,
    ) -> DataSource:
        """
        Create DataSource metadata object.

        Args:
            url: Source URL
            quality_flag: Data quality assessment
            notes: Additional notes

        Returns:
            DataSource metadata
        """
        return DataSource(
            source_type=self.source_type,
            source_name=self.source_name,
            source_url=url,
            region=self.region,
            retrieved_at=datetime.utcnow(),
            quality_flag=quality_flag,
            notes=notes,
        )

    def validate_and_log_data(
        self,
        model_class: type,
        data: dict,
        context: str = "data",
    ) -> Optional[any]:
        """
        Validate data against Pydantic model and log errors.

        Args:
            model_class: Pydantic model class
            data: Data dictionary to validate
            context: Context string for logging

        Returns:
            Validated model instance or None if validation fails
        """
        try:
            instance = model_class(**data)
            self.logger.debug(f"Validated {context}", model=model_class.__name__)
            return instance

        except ValidationError as e:
            self.logger.error(
                f"Validation failed for {context}",
                model=model_class.__name__,
                errors=e.errors(),
            )
            return None

        except Exception as e:
            self.logger.error(
                f"Unexpected error validating {context}",
                model=model_class.__name__,
                error=str(e),
            )
            return None

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self.http_client.close()
        self.logger.info(f"Recruiting datasource closed", source=self.source_name)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Abstract methods that subclasses must implement

    @abstractmethod
    async def get_rankings(
        self,
        class_year: int,
        limit: int = 100,
        position: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[RecruitingRank]:
        """
        Get recruiting rankings for a class year.

        Args:
            class_year: Graduation year (e.g., 2025, 2026)
            limit: Maximum number of results
            position: Filter by position (optional)
            state: Filter by state (optional)

        Returns:
            List of RecruitingRank objects
        """
        pass

    @abstractmethod
    async def get_player_recruiting_profile(
        self,
        player_id: str
    ) -> Optional[RecruitingProfile]:
        """
        Get comprehensive recruiting profile for a player.

        Args:
            player_id: Player identifier from recruiting service

        Returns:
            RecruitingProfile with rankings, offers, predictions
        """
        pass

    @abstractmethod
    async def search_players(
        self,
        name: Optional[str] = None,
        class_year: Optional[int] = None,
        state: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 50,
    ) -> List[RecruitingRank]:
        """
        Search for players in recruiting database.

        Args:
            name: Player name (partial match)
            class_year: Graduation year filter
            state: State filter
            position: Position filter
            limit: Maximum results

        Returns:
            List of RecruitingRank objects
        """
        pass

    # Optional methods (can be overridden if data available)

    async def get_offers(
        self,
        player_id: str
    ) -> List[CollegeOffer]:
        """
        Get college offers for a player.

        Args:
            player_id: Player identifier

        Returns:
            List of CollegeOffer objects

        Note: Override this method if offers data is available
        """
        self.logger.warning(
            f"get_offers not implemented for {self.source_name}",
            player_id=player_id
        )
        return []

    async def get_predictions(
        self,
        player_id: str
    ) -> List[RecruitingPrediction]:
        """
        Get recruiting predictions (Crystal Ball style) for a player.

        Args:
            player_id: Player identifier

        Returns:
            List of RecruitingPrediction objects

        Note: Override this method if prediction data is available
        """
        self.logger.warning(
            f"get_predictions not implemented for {self.source_name}",
            player_id=player_id
        )
        return []

    async def health_check(self) -> bool:
        """
        Check if recruiting datasource is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.http_client.get(
                self.base_url,
                use_cache=False,
            )
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Health check failed", error=str(e))
            return False

    def is_enabled(self) -> bool:
        """
        Check if recruiting datasource is enabled in configuration.

        Returns:
            True if enabled, False otherwise
        """
        return self.settings.is_datasource_enabled(self.source_type.value)
