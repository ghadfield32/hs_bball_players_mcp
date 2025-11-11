"""
Logging and Monitoring Utilities

Provides structured logging with context and request tracking.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import get_settings


class StructuredLogger:
    """
    Structured logger with context support.

    Provides consistent logging format across the application with
    automatic context (source, request_id, etc.) injection.
    """

    def __init__(self, name: str):
        """
        Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
        """
        self.logger = logging.getLogger(name)
        self.context: dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        """
        Set context values that will be included in all log messages.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context values."""
        self.context.clear()

    def _format_message(self, message: str, extra: Optional[dict[str, Any]] = None) -> str:
        """
        Format message with context.

        Args:
            message: Log message
            extra: Additional context for this message only

        Returns:
            Formatted message string
        """
        parts = [message]

        # Add context
        all_context = {**self.context}
        if extra:
            all_context.update(extra)

        if all_context:
            context_str = " | ".join(f"{k}={v}" for k, v in all_context.items())
            parts.append(f"[{context_str}]")

        return " ".join(parts)

    def debug(self, message: str, **extra: Any) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(message, extra))

    def info(self, message: str, **extra: Any) -> None:
        """Log info message."""
        self.logger.info(self._format_message(message, extra))

    def warning(self, message: str, **extra: Any) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(message, extra))

    def error(self, message: str, **extra: Any) -> None:
        """Log error message."""
        self.logger.error(self._format_message(message, extra))

    def critical(self, message: str, **extra: Any) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message(message, extra))

    def exception(self, message: str, **extra: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message, extra))


def setup_logging() -> None:
    """
    Set up application logging configuration.

    Configures logging handlers, formatters, and log levels based on settings.
    Should be called once at application startup.
    """
    settings = get_settings()

    # Create logs directory if it doesn't exist
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    all_log_file = log_dir / "app.log"
    file_handler = logging.FileHandler(all_log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG and above to file
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # File handler for errors only
    error_log_file = log_dir / "error.log"
    error_handler = logging.FileHandler(error_log_file, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # File handler for datasource requests
    if settings.enable_request_logging:
        datasource_log_file = log_dir / "datasource_requests.log"
        datasource_handler = logging.FileHandler(datasource_log_file, encoding="utf-8")
        datasource_handler.setLevel(logging.INFO)
        datasource_handler.addFilter(DataSourceRequestFilter())
        datasource_handler.setFormatter(file_formatter)
        root_logger.addHandler(datasource_handler)

    # Set third-party library log levels to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    root_logger.info(
        f"Logging initialized | level={settings.log_level} | "
        f"log_dir={log_dir.absolute()} | "
        f"request_logging={settings.enable_request_logging}"
    )


class DataSourceRequestFilter(logging.Filter):
    """Filter to capture only datasource request logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if record should be logged.

        Args:
            record: Log record

        Returns:
            True if record is from datasource, False otherwise
        """
        return "datasource" in record.name.lower() or "request" in record.getMessage().lower()


class RequestMetrics:
    """
    Track request metrics for monitoring.

    Collects statistics about API requests and datasource calls.
    """

    def __init__(self):
        """Initialize metrics storage."""
        self.metrics: dict[str, dict[str, Any]] = {
            "api_requests": {"total": 0, "success": 0, "error": 0},
            "datasource_requests": {},
            "cache_stats": {"hits": 0, "misses": 0},
            "rate_limit_hits": 0,
        }
        self.start_time = datetime.utcnow()

    def record_api_request(self, success: bool = True) -> None:
        """
        Record an API request.

        Args:
            success: Whether request was successful
        """
        self.metrics["api_requests"]["total"] += 1
        if success:
            self.metrics["api_requests"]["success"] += 1
        else:
            self.metrics["api_requests"]["error"] += 1

    def record_datasource_request(self, source: str, success: bool = True) -> None:
        """
        Record a datasource request.

        Args:
            source: Data source name
            success: Whether request was successful
        """
        if source not in self.metrics["datasource_requests"]:
            self.metrics["datasource_requests"][source] = {"total": 0, "success": 0, "error": 0}

        self.metrics["datasource_requests"][source]["total"] += 1
        if success:
            self.metrics["datasource_requests"][source]["success"] += 1
        else:
            self.metrics["datasource_requests"][source]["error"] += 1

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.metrics["cache_stats"]["hits"] += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.metrics["cache_stats"]["misses"] += 1

    def record_rate_limit_hit(self) -> None:
        """Record a rate limit hit."""
        self.metrics["rate_limit_hits"] += 1

    def get_summary(self) -> dict[str, Any]:
        """
        Get metrics summary.

        Returns:
            Dictionary of metrics with calculated rates
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        cache_total = self.metrics["cache_stats"]["hits"] + self.metrics["cache_stats"]["misses"]
        cache_hit_rate = (
            (self.metrics["cache_stats"]["hits"] / cache_total * 100) if cache_total > 0 else 0
        )

        return {
            "uptime_seconds": uptime,
            "api_requests": self.metrics["api_requests"],
            "datasource_requests": self.metrics["datasource_requests"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cache_stats": self.metrics["cache_stats"],
            "rate_limit_hits": self.metrics["rate_limit_hits"],
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.__init__()


# Global metrics instance
_metrics_instance: Optional[RequestMetrics] = None


def get_metrics() -> RequestMetrics:
    """
    Get global metrics instance.

    Returns:
        RequestMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = RequestMetrics()
    return _metrics_instance


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
