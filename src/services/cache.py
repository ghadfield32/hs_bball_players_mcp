"""
Caching Service

Provides file-based and Redis caching with configurable TTLs.
Reduces load on data sources and improves response times.
"""

import asyncio
import hashlib
import json
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Callable, TypeVar

import aiofiles

from ..config import get_settings
from ..utils.logger import get_logger, get_metrics

logger = get_logger(__name__)

T = TypeVar('T')


async def retry_on_file_lock(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 0.1,
    **kwargs
) -> T:
    """
    Retry a file operation on Windows file locking errors.

    Windows [WinError 32] occurs when multiple processes/tasks access the same file.
    This helper retries with exponential backoff to handle concurrent access gracefully.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (exponentially increases)
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except (OSError, PermissionError) as e:
            last_exception = e
            # Check if it's a file locking error (Windows Error 32)
            if attempt < max_retries and (
                'WinError 32' in str(e) or
                'being used by another process' in str(e) or
                'Permission denied' in str(e)
            ):
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.debug(
                    f"File lock detected, retrying in {delay}s",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )
                await asyncio.sleep(delay)
            else:
                raise

    # All retries exhausted
    raise last_exception


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

    async def _read_metadata(self, meta_path: Path) -> Optional[dict]:
        """Read metadata file with retry logic."""
        async def _read():
            async with aiofiles.open(meta_path, "r") as f:
                return json.loads(await f.read())

        try:
            return await retry_on_file_lock(_read)
        except Exception as e:
            logger.warning(f"Failed to read metadata", path=str(meta_path), error=str(e))
            return None

    async def _read_cache_value(self, cache_path: Path) -> Optional[Any]:
        """Read cache value file with retry logic."""
        async def _read():
            async with aiofiles.open(cache_path, "rb") as f:
                return pickle.loads(await f.read())

        try:
            return await retry_on_file_lock(_read)
        except Exception as e:
            logger.warning(f"Failed to read cache value", path=str(cache_path), error=str(e))
            return None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        if not cache_path.exists():
            get_metrics().record_cache_miss()
            return None

        # Check TTL from metadata
        if meta_path.exists():
            metadata = await self._read_metadata(meta_path)
            if metadata is None:
                await self.delete(key)
                get_metrics().record_cache_miss()
                return None

            try:
                expires_at = datetime.fromisoformat(metadata["expires_at"])

                if datetime.utcnow() > expires_at:
                    # Expired, delete and return None
                    logger.debug(f"Cache expired for key: {key}")
                    await self.delete(key)
                    get_metrics().record_cache_miss()
                    return None
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid cache metadata for key: {key}", error=str(e))
                await self.delete(key)
                get_metrics().record_cache_miss()
                return None

        # Read cached value
        value = await self._read_cache_value(cache_path)
        if value is None:
            await self.delete(key)
            get_metrics().record_cache_miss()
            return None

        logger.debug(f"Cache hit for key: {key}")
        get_metrics().record_cache_hit()
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        try:
            # Write value with retry logic
            async def _write_value():
                async with aiofiles.open(cache_path, "wb") as f:
                    await f.write(pickle.dumps(value))

            await retry_on_file_lock(_write_value)

            # Write metadata with TTL and retry logic
            expires_at = datetime.utcnow() + timedelta(seconds=ttl if ttl else 3600)
            metadata = {
                "key": key,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "ttl": ttl,
            }

            async def _write_metadata():
                async with aiofiles.open(meta_path, "w") as f:
                    await f.write(json.dumps(metadata))

            await retry_on_file_lock(_write_metadata)

            logger.debug(f"Cache set for key: {key}", ttl=ttl)
            return True

        except (pickle.PickleError, OSError) as e:
            logger.error(f"Failed to write cache for key: {key}", error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache with retry logic for file locking."""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        async def _delete_file(path: Path) -> bool:
            """Delete a single file with proper existence check."""
            if path.exists():
                path.unlink()
                return True
            return False

        deleted = False
        try:
            if cache_path.exists():
                await retry_on_file_lock(_delete_file, cache_path)
                deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete cache file", path=str(cache_path), error=str(e))

        try:
            if meta_path.exists():
                await retry_on_file_lock(_delete_file, meta_path)
                deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete metadata file", path=str(meta_path), error=str(e))

        if deleted:
            logger.debug(f"Cache deleted for key: {key}")

        return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache entries with retry logic for file locking."""
        async def _delete_file(path: Path) -> None:
            """Delete a single file."""
            path.unlink()

        errors = []
        try:
            # Delete cache files with retry
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    await retry_on_file_lock(_delete_file, cache_file)
                except Exception as e:
                    errors.append(f"Failed to delete {cache_file.name}: {str(e)}")

            # Delete metadata files with retry
            for meta_file in self.cache_dir.glob("*.meta"):
                try:
                    await retry_on_file_lock(_delete_file, meta_file)
                except Exception as e:
                    errors.append(f"Failed to delete {meta_file.name}: {str(e)}")

            if errors:
                logger.warning(f"Cache cleared with {len(errors)} errors", errors=errors[:5])
            else:
                logger.info("Cache cleared successfully")

            return len(errors) == 0

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
