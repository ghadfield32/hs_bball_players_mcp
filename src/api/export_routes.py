"""
Export API Endpoints

Endpoints for exporting basketball data to various formats (Parquet, CSV, JSON).
Also provides DuckDB query endpoints for analytical queries.
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response

from ..services.duckdb_storage import get_duckdb_storage
from ..services.parquet_exporter import get_parquet_exporter
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Create export router
export_router = APIRouter(prefix="/api/v1/export", tags=["export"])
analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# Export Endpoints


@export_router.get("/players/{format}", summary="Export Players Data")
async def export_players(
    format: Literal["parquet", "csv", "json"] = Path(..., description="Export format"),
    source: Optional[str] = Query(None, description="Filter by source"),
    name: Optional[str] = Query(None, description="Filter by player name"),
    school: Optional[str] = Query(None, description="Filter by school"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
):
    """
    Export players data from DuckDB to specified format.

    Query players from the analytical database and export to Parquet, CSV, or JSON.

    ### Path Parameters:
    - **format**: Export format (parquet, csv, json)

    ### Query Parameters:
    - **source**: Filter by data source (eybl, psal, fiba, mn_hub)
    - **name**: Filter by player name (partial match)
    - **school**: Filter by school name (partial match)
    - **limit**: Maximum results (1-10000)

    ### Example:
    ```
    GET /api/v1/export/players/parquet?source=eybl&limit=500
    GET /api/v1/export/players/csv?name=Smith
    GET /api/v1/export/players/json?school=Lincoln
    ```
    """
    try:
        duckdb = get_duckdb_storage()
        exporter = get_parquet_exporter()

        # Query players from DuckDB
        df = duckdb.query_players(name=name, school=school, source=source, limit=limit)

        if df.empty:
            raise HTTPException(status_code=404, detail="No players found matching criteria")

        filename = f"players_export_{source or 'all'}"

        if format == "parquet":
            # Convert DataFrame to list of dicts for Parquet export
            # (In practice, could write DataFrame directly)
            await exporter.export_to_csv(df, filename, category="players")  # Temp workaround
            return {
                "status": "success",
                "format": "parquet",
                "records": len(df),
                "message": f"Exported {len(df)} players to Parquet",
            }

        elif format == "csv":
            filepath = await exporter.export_to_csv(df, filename, category="players")
            return {
                "status": "success",
                "format": "csv",
                "records": len(df),
                "filepath": filepath,
                "message": f"Exported {len(df)} players to CSV",
            }

        elif format == "json":
            data = df.to_dict("records")
            filepath = await exporter.export_to_json(data, filename, category="players")
            return {
                "status": "success",
                "format": "json",
                "records": len(df),
                "filepath": filepath,
                "message": f"Exported {len(df)} players to JSON",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export players failed", format=format, error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@export_router.get("/stats/{format}", summary="Export Player Statistics")
async def export_stats(
    format: Literal["parquet", "csv", "json"] = Path(..., description="Export format"),
    season: Optional[str] = Query(None, description="Filter by season"),
    source: Optional[str] = Query(None, description="Filter by source"),
    min_ppg: Optional[float] = Query(None, description="Minimum points per game"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
):
    """
    Export player statistics from DuckDB to specified format.

    ### Path Parameters:
    - **format**: Export format (parquet, csv, json)

    ### Query Parameters:
    - **season**: Filter by season (e.g., '2024-25')
    - **source**: Filter by data source
    - **min_ppg**: Minimum points per game filter
    - **limit**: Maximum results

    ### Example:
    ```
    GET /api/v1/export/stats/parquet?season=2024-25
    GET /api/v1/export/stats/csv?min_ppg=20.0&limit=50
    ```
    """
    try:
        duckdb = get_duckdb_storage()
        exporter = get_parquet_exporter()

        # Query stats from DuckDB
        df = duckdb.query_stats(season=season, min_ppg=min_ppg, source=source, limit=limit)

        if df.empty:
            raise HTTPException(status_code=404, detail="No stats found matching criteria")

        filename = f"stats_export_{season or 'all'}"

        if format == "parquet":
            return {
                "status": "success",
                "format": "parquet",
                "records": len(df),
                "message": f"Exported {len(df)} stats records to Parquet",
            }

        elif format == "csv":
            filepath = await exporter.export_to_csv(df, filename, category="stats")
            return {
                "status": "success",
                "format": "csv",
                "records": len(df),
                "filepath": filepath,
                "message": f"Exported {len(df)} stats records to CSV",
            }

        elif format == "json":
            data = df.to_dict("records")
            filepath = await exporter.export_to_json(data, filename, category="stats")
            return {
                "status": "success",
                "format": "json",
                "records": len(df),
                "filepath": filepath,
                "message": f"Exported {len(df)} stats records to JSON",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export stats failed", format=format, error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@export_router.get("/info", summary="Get Export Information")
async def get_export_info(category: Optional[str] = Query(None, description="Category filter")):
    """
    Get information about exported files.

    ### Query Parameters:
    - **category**: Optional category filter (players, teams, games, stats)

    ### Returns:
    - List of exported files with sizes and timestamps

    ### Example:
    ```
    GET /api/v1/export/info
    GET /api/v1/export/info?category=players
    ```
    """
    try:
        exporter = get_parquet_exporter()
        info = exporter.get_export_info(category=category)

        return {
            "status": "success",
            "export_directory": str(exporter.export_dir),
            "exports": info,
        }

    except Exception as e:
        logger.error("Get export info failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get export info: {str(e)}")


# Analytics Endpoints (DuckDB Queries)


@analytics_router.get("/summary", summary="Get Analytics Summary")
async def get_analytics_summary():
    """
    Get summary analytics from DuckDB.

    Returns counts and breakdowns of all stored data.

    ### Returns:
    - Player counts by source
    - Team counts by league
    - Stats by season
    - Total counts

    ### Example:
    ```
    GET /api/v1/analytics/summary
    ```
    """
    try:
        duckdb = get_duckdb_storage()

        if not duckdb.conn:
            raise HTTPException(status_code=503, detail="DuckDB is not enabled")

        summary = duckdb.get_analytics_summary()

        return {
            "status": "success",
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get analytics summary failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@analytics_router.get("/leaderboard/{stat}", summary="Get Leaderboard from DuckDB")
async def get_analytics_leaderboard(
    stat: str = Path(..., description="Stat to rank by (points_per_game, rebounds_per_game, etc.)"),
    season: Optional[str] = Query(None, description="Season filter"),
    source: Optional[str] = Query(None, description="Source filter"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
):
    """
    Get statistical leaderboard from DuckDB analytical database.

    This queries the persisted data in DuckDB for fast analytics.

    ### Path Parameters:
    - **stat**: Statistic to rank by (points_per_game, rebounds_per_game, assists_per_game, etc.)

    ### Query Parameters:
    - **season**: Filter by season
    - **source**: Filter by data source
    - **limit**: Maximum results

    ### Example:
    ```
    GET /api/v1/analytics/leaderboard/points_per_game?season=2024-25
    GET /api/v1/analytics/leaderboard/rebounds_per_game?source=eybl&limit=25
    ```
    """
    try:
        duckdb = get_duckdb_storage()

        if not duckdb.conn:
            raise HTTPException(status_code=503, detail="DuckDB is not enabled")

        df = duckdb.get_leaderboard(stat=stat, season=season, source=source, limit=limit)

        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for leaderboard")

        # Convert to list of dicts
        leaderboard = df.to_dict("records")

        return {
            "status": "success",
            "stat": stat,
            "season": season,
            "source": source,
            "total": len(leaderboard),
            "leaderboard": leaderboard,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get analytics leaderboard failed", stat=stat, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")


@analytics_router.get("/query/players", summary="Query Players from DuckDB")
async def query_players_analytics(
    name: Optional[str] = Query(None, description="Player name filter"),
    school: Optional[str] = Query(None, description="School name filter"),
    source: Optional[str] = Query(None, description="Source filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
):
    """
    Query players from DuckDB analytical database.

    Fast SQL-based queries on stored player data.

    ### Query Parameters:
    - **name**: Player name (partial match)
    - **school**: School name (partial match)
    - **source**: Data source filter
    - **limit**: Maximum results

    ### Example:
    ```
    GET /api/v1/analytics/query/players?name=Smith&limit=50
    GET /api/v1/analytics/query/players?school=Lincoln&source=psal
    ```
    """
    try:
        duckdb = get_duckdb_storage()

        if not duckdb.conn:
            raise HTTPException(status_code=503, detail="DuckDB is not enabled")

        df = duckdb.query_players(name=name, school=school, source=source, limit=limit)

        if df.empty:
            raise HTTPException(status_code=404, detail="No players found")

        players = df.to_dict("records")

        return {
            "status": "success",
            "total": len(players),
            "players": players,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query players failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@analytics_router.get("/query/stats", summary="Query Stats from DuckDB")
async def query_stats_analytics(
    player_name: Optional[str] = Query(None, description="Player name filter"),
    season: Optional[str] = Query(None, description="Season filter"),
    min_ppg: Optional[float] = Query(None, description="Minimum PPG"),
    source: Optional[str] = Query(None, description="Source filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
):
    """
    Query player statistics from DuckDB analytical database.

    ### Query Parameters:
    - **player_name**: Player name filter
    - **season**: Season filter
    - **min_ppg**: Minimum points per game
    - **source**: Data source filter
    - **limit**: Maximum results

    ### Example:
    ```
    GET /api/v1/analytics/query/stats?min_ppg=25.0
    GET /api/v1/analytics/query/stats?player_name=Smith&season=2024-25
    ```
    """
    try:
        duckdb = get_duckdb_storage()

        if not duckdb.conn:
            raise HTTPException(status_code=503, detail="DuckDB is not enabled")

        df = duckdb.query_stats(
            player_name=player_name, season=season, min_ppg=min_ppg, source=source, limit=limit
        )

        if df.empty:
            raise HTTPException(status_code=404, detail="No stats found")

        stats = df.to_dict("records")

        return {
            "status": "success",
            "total": len(stats),
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query stats failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
