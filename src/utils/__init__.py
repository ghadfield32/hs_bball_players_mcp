"""
Utility Functions and Helpers

Common utilities for HTTP, parsing, and logging.
"""

from .http_client import HTTPClient, create_http_client
from .logger import (
    RequestMetrics,
    StructuredLogger,
    get_logger,
    get_metrics,
    setup_logging,
)
from .parser import (
    clean_player_name,
    extract_table_data,
    get_attr_or_none,
    get_text_or_none,
    parse_float,
    parse_height_to_inches,
    parse_html,
    parse_int,
    parse_record,
    parse_stat,
)

__all__ = [
    # HTTP client
    "HTTPClient",
    "create_http_client",
    # Logger
    "StructuredLogger",
    "RequestMetrics",
    "get_logger",
    "get_metrics",
    "setup_logging",
    # Parser
    "parse_html",
    "get_text_or_none",
    "get_attr_or_none",
    "parse_int",
    "parse_float",
    "parse_stat",
    "parse_height_to_inches",
    "parse_record",
    "clean_player_name",
    "extract_table_data",
]
