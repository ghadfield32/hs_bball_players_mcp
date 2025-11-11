"""
Caching Service

Provides file-based and Redis caching with configurable TTLs.
Reduces load on data sources and improves response times.
"""

import hashlib
import json
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiofiles

from ..config import get_settings
from ..utils.logger import get_logger, get_metrics

logger = get_logger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class FileCacheBackend(CacheBackend):
    """
    File-based cache backend.

    Stores cache entries as files on disk with metadata for TTL.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File cache initialized", cache_dir=str(self.cache_dir.absolute()))

    def _get_cache_path(self, key: str) -> Path:
        """Get path to cache file for key."""
        # Hash key to create safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _get_metadata_path(self, key: str) -> Path:
        """Get path to metadata file for key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        if not cache_path.exists():
            get_metrics().record_cache_miss()
            return None

        # Check TTL from metadata
        if meta_path.exists():
            try:
                async with aiofiles.open(meta_path, "r") as f:
                    metadata = json.loads(await f.read())
                    expires_at = datetime.fromisoformat(metadata["expires_at"])

                    if datetime.utcnow() > expires_at:
                        # Expired, delete and return None
                        logger.debug(f"Cache expired for key: {key}")
                        await self.delete(key)
                        get_metrics().record_cache_miss()
                        return None
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Invalid cache metadata for key: {key}", error=str(e))
                await self.delete(key)
                get_metrics().record_cache_miss()
                return None

        # Read cached value
        try:
            async with aiofiles.open(cache_path, "rb") as f:
                value = pickle.loads(await f.read())
                logger.debug(f"Cache hit for key: {key}")
                get_metrics().record_cache_hit()
                return value
        except (pickle.PickleError, EOFError) as e:
            logger.warning(f"Failed to read cache for key: {key}", error=str(e))
            await self.delete(key)
            get_metrics().record_cache_miss()
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        try:
            # Write value
            async with aiofiles.open(cache_path, "wb") as f:
                await f.write(pickle.dumps(value))

            # Write metadata with TTL
            expires_at = datetime.utcnow() + timedelta(seconds=ttl if ttl else 3600)
            metadata = {
                "key": key,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "ttl": ttl,
            }

            async with aiofiles.open(meta_path, "w") as f:
                await f.write(json.dumps(metadata))

            logger.debug(f"Cache set for key: {key}", ttl=ttl)
            return True

        except (pickle.PickleError, OSError) as e:
            logger.error(f"Failed to write cache for key: {key}", error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        deleted = False
        if cache_path.exists():
            cache_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        if deleted:
            logger.debug(f"Cache deleted for key: {key}")

        return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            for meta_file in self.cache_dir.glob("*.meta"):
                meta_file.unlink()
            logger.info("Cache cleared")
            return True
        except OSError as e:
            logger.error("Failed to clear cache", error=str(e))
            return False


class CacheService:
    """
    High-level caching service with automatic backend selection.

    Provides simple interface for caching with TTL management.
    """

    def __init__(self):
        """Initialize cache service."""
        self.settings = get_settings()
        self.backend = self._create_backend()
        logger.info(
            "Cache service initialized",
            enabled=self.settings.cache_enabled,
            backend=self.settings.cache_type,
        )

    def _create_backend(self) -> CacheBackend:
        """Create cache backend based on configuration."""
        if not self.settings.cache_enabled:
            # Return a no-op backend
            return NullCacheBackend()

        if self.settings.cache_type == "file":
            return FileCacheBackend()
        elif self.settings.cache_type == "redis":
            # Redis implementation would go here
            # For now, fall back to file cache
            logger.warning("Redis cache not yet implemented, using file cache")
            return FileCacheBackend()
        elif self.settings.cache_type == "memory":
            # In-memory cache implementation would go here
            logger.warning("Memory cache not yet implemented, using file cache")
            return FileCacheBackend()
        else:
            logger.warning(f"Unknown cache type: {self.settings.cache_type}, using file cache")
            return FileCacheBackend()

    async def get_player(self, key: str) -> Optional[Any]:
        """Get player data from cache."""
        return await self.backend.get(f"player:{key}")

    async def set_player(self, key: str, value: Any) -> bool:
        """Set player data in cache."""
        return await self.backend.set(
            f"player:{key}", value, ttl=self.settings.cache_ttl_players
        )

    async def get_game(self, key: str) -> Optional[Any]:
        """Get game data from cache."""
        return await self.backend.get(f"game:{key}")

    async def set_game(self, key: str, value: Any) -> bool:
        """Set game data in cache."""
        return await self.backend.set(f"game:{key}", value, ttl=self.settings.cache_ttl_games)

    async def get_stats(self, key: str) -> Optional[Any]:
        """Get stats data from cache."""
        return await self.backend.get(f"stats:{key}")

    async def set_stats(self, key: str, value: Any) -> bool:
        """Set stats data in cache."""
        return await self.backend.set(f"stats:{key}", value, ttl=self.settings.cache_ttl_stats)

    async def get_schedule(self, key: str) -> Optional[Any]:
        """Get schedule data from cache."""
        return await self.backend.get(f"schedule:{key}")

    async def set_schedule(self, key: str, value: Any) -> bool:
        """Set schedule data in cache."""
        return await self.backend.set(
            f"schedule:{key}", value, ttl=self.settings.cache_ttl_schedules
        )

    async def get_raw_html(self, url: str) -> Optional[str]:
        """Get raw HTML from cache."""
        return await self.backend.get(f"html:{url}")

    async def set_raw_html(self, url: str, html: str, ttl: int = 3600) -> bool:
        """Set raw HTML in cache."""
        return await self.backend.set(f"html:{url}", html, ttl=ttl)

    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        return await self.backend.clear()


class NullCacheBackend(CacheBackend):
    """No-op cache backend when caching is disabled."""

    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return True

    async def delete(self, key: str) -> bool:
        return True

    async def exists(self, key: str) -> bool:
        return False

    async def clear(self) -> bool:
        return True


# Global cache service instance
_cache_service_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get global cache service instance.

    Returns:
        CacheService instance
    """
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService()
    return _cache_service_instance
