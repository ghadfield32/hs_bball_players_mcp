"""
Base DataSource Adapter

Abstract base class for all data source adapters.
Provides common interface and shared functionality.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import ValidationError

from ..config import get_settings
from ..models import (
    DataQualityFlag,
    DataSource,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Team,
)
from ..utils import create_http_client, get_logger

logger = get_logger(__name__)


class BaseDataSource(ABC):
    """
    Abstract base class for data source adapters.

    All datasource adapters must inherit from this class and implement
    the abstract methods.
    """

    # Class attributes to be set by subclasses
    source_type: DataSourceType
    source_name: str
    base_url: str
    region: DataSourceRegion

    def __init__(self):
        """Initialize base datasource."""
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
            f"Datasource initialized",
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
        self.logger.info(f"Datasource closed", source=self.source_name)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Abstract methods that subclasses must implement

    @abstractmethod
    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
        pass

    @abstractmethod
    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season (e.g., '2024-25')
            limit: Maximum results

        Returns:
            List of Player objects
        """
        pass

    @abstractmethod
    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        Args:
            player_id: Player identifier
            season: Season (None = current season)

        Returns:
            PlayerSeasonStats or None
        """
        pass

    @abstractmethod
    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        pass

    @abstractmethod
    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        pass

    @abstractmethod
    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games with optional filters.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        pass

    @abstractmethod
    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category (e.g., 'points', 'rebounds', 'assists')
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        pass

    # Optional methods (can be overridden)

    async def health_check(self) -> bool:
        """
        Check if datasource is accessible.

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
        Check if datasource is enabled in configuration.

        Returns:
            True if enabled, False otherwise
        """
        return self.settings.is_datasource_enabled(self.source_type.value)
