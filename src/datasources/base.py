"""
Base DataSource Adapter

Abstract base class for all data source adapters.
Provides common interface and shared functionality.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

from ..config import get_settings
from ..models import (
    DataQualityFlag,
    DataSource,
    DataSourceCategory,
    DataSourceRegion,
    DataSourceType,
    Game,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Team,
)
from ..utils import get_logger
from ..utils.http_client import create_http_client

logger = get_logger(__name__)

# Global per-domain semaphores for rate limiting
_domain_semaphores: dict[str, asyncio.Semaphore] = {}
_semaphore_lock = asyncio.Lock()

# Simple in-memory cache for ETag/IMS caching
_http_cache: dict[str, dict] = {}


class BaseDataSource(ABC):
    """
    Abstract base class for data source adapters.

    All datasource adapters must inherit from this class and implement
    the abstract methods.

    Added Phase HS-1 (2025-11-16):
    - CATEGORY: Explicitly marks this as a PLAYER_STATS datasource
    - This prevents accidentally using recruiting/bracket sources for player statistics
    """

    # Class attributes to be set by subclasses
    source_type: DataSourceType
    source_name: str
    base_url: str
    region: DataSourceRegion

    # Datasource category - marks what type of data this source provides
    # Must be set by subclasses, defaults to PLAYER_STATS for BaseDataSource
    CATEGORY: DataSourceCategory = DataSourceCategory.PLAYER_STATS

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

    async def _get_domain_semaphore(self, url: str, max_concurrent: int = 5) -> asyncio.Semaphore:
        """
        Get or create a semaphore for the domain of the given URL.
        Prevents overwhelming servers with concurrent requests.

        Args:
            url: URL to extract domain from
            max_concurrent: Max concurrent requests per domain

        Returns:
            Semaphore for the domain
        """
        domain = urlparse(url).netloc
        async with _semaphore_lock:
            if domain not in _domain_semaphores:
                _domain_semaphores[domain] = asyncio.Semaphore(max_concurrent)
            return _domain_semaphores[domain]

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def http_get(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: float = 20.0,
        use_cache: bool = True,
    ) -> tuple[int, bytes, dict]:
        """
        Centralized HTTP GET with ETag/If-Modified-Since caching, retry, and concurrency control.

        Args:
            url: URL to fetch
            headers: Additional headers
            timeout: Request timeout in seconds
            use_cache: Whether to use ETag/IMS caching

        Returns:
            Tuple of (status_code, content, response_headers)
            - status_code 304 means cached content is still valid (content will be from cache)
            - status_code 200 means new content fetched
        """
        # Get per-domain semaphore for rate limiting
        semaphore = await self._get_domain_semaphore(url)

        # Prepare headers
        request_headers = headers or {}

        # Add ETag/If-Modified-Since from cache if available
        if use_cache and url in _http_cache:
            cached = _http_cache[url]
            if "etag" in cached:
                request_headers["If-None-Match"] = cached["etag"]
            if "last_modified" in cached:
                request_headers["If-Modified-Since"] = cached["last_modified"]

        # Acquire semaphore to limit concurrent requests per domain
        async with semaphore:
            try:
                response = await self.http_client.get(
                    url,
                    headers=request_headers,
                    timeout=timeout,
                )

                status = response.status_code
                response_headers = dict(response.headers)

                # Handle 304 Not Modified - return cached content
                if status == 304 and url in _http_cache:
                    self.logger.debug(f"Cache hit (304): {url}")
                    cached = _http_cache[url]
                    return (304, cached["content"], cached["headers"])

                # Handle 200 OK - cache and return new content
                if status == 200:
                    content = response.content

                    # Update cache with new ETag/Last-Modified
                    if use_cache:
                        cache_entry = {
                            "content": content,
                            "headers": response_headers,
                        }
                        if "etag" in response_headers:
                            cache_entry["etag"] = response_headers["etag"]
                        if "last-modified" in response_headers:
                            cache_entry["last_modified"] = response_headers["last-modified"]

                        _http_cache[url] = cache_entry
                        self.logger.debug(f"Cached: {url}")

                    return (status, content, response_headers)

                # Other status codes - return as-is
                return (status, response.content, response_headers)

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                self.logger.warning(f"HTTP request failed (will retry): {url}", error=str(e))
                raise  # Let tenacity retry
            except Exception as e:
                self.logger.error(f"HTTP request failed: {url}", error=str(e))
                # Return error status
                return (500, b"", {})

    def create_data_source_metadata(
        self,
        url: Optional[str] = None,
        quality_flag: DataQualityFlag = DataQualityFlag.UNVERIFIED,
        notes: Optional[str] = None,
        **extra_kwargs,
    ) -> DataSource:
        """
        Create DataSource metadata object in a forward-compatible way.

        Args:
            url: Source URL
            quality_flag: Data quality assessment
            notes: Additional notes
            **extra_kwargs: Additional fields for future compatibility (e.g., 'extra' for Phase 18 metadata)

        Returns:
            DataSource metadata

        Note:
            Phase 18+ adapters may pass 'extra' dict with round/venue/tipoff metadata.
            This method accepts but currently ignores these fields to maintain backward compatibility.
            Future DataSource model updates can consume these fields without breaking existing adapters.
        """
        # Extract known extra fields (Phase 18+)
        extra_metadata = extra_kwargs.pop("extra", None)

        # Ignore any remaining unknown kwargs for forward compatibility
        # (allows adapters to pass new fields without breaking)

        return DataSource(
            source_type=self.source_type,
            source_name=self.source_name,
            source_url=url,
            region=self.region,
            retrieved_at=datetime.utcnow(),
            quality_flag=quality_flag,
            notes=notes,
            # Future: attach extra_metadata when DataSource model supports it
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
