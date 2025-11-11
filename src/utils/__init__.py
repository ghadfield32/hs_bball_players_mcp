"""
Utility Functions and Helpers

Common utilities for HTTP, parsing, logging, and scraping.
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
from .scraping_helpers import (
    build_leaderboard_entry,
    extract_links_from_table,
    find_stat_table,
    parse_grad_year,
    parse_player_from_row,
    parse_season_stats_from_row,
    standardize_stat_columns,
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
    # Scraping helpers
    "find_stat_table",
    "parse_player_from_row",
    "parse_season_stats_from_row",
    "parse_grad_year",
    "standardize_stat_columns",
    "build_leaderboard_entry",
    "extract_links_from_table",
]
