"""
Global Datasource Adapters

Adapters for international/global basketball data sources.
"""

from .fiba_livestats import FIBALiveStatsDataSource

__all__ = [
    "FIBALiveStatsDataSource",
]
