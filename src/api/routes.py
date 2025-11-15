"""
API Routes

RESTful API endpoints for basketball player statistics.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from ..models import Player, PlayerSeasonStats, Team
from ..services.aggregator import get_aggregator
from ..services.duckdb_storage import get_duckdb_storage
from ..services.parquet_exporter import get_parquet_exporter
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1", tags=["api"])


# Response models
class PlayerResponse(BaseModel):
    """Player response model."""

    player_id: str
    full_name: str
    school_name: Optional[str]
    team_name: Optional[str]
    position: Optional[str]
    height_inches: Optional[int]
    grad_year: Optional[int]
    source: str

    class Config:
        from_attributes = True


class PlayersSearchResponse(BaseModel):
    """Players search response."""

    total: int
    players: list[Player]
    sources_queried: list[str]


class StatsResponse(BaseModel):
    """Stats response model."""

    player_id: str
    player_name: str
    season: str
    league: Optional[str]
    games_played: int
    points_per_game: Optional[float]
    rebounds_per_game: Optional[float]
    assists_per_game: Optional[float]
    source: str


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    total: int
    stat: str
    entries: list[dict]


class SourcesResponse(BaseModel):
    """Available sources response."""

    sources: list[str]
    source_info: dict[str, dict]


# Player Endpoints


@router.get("/players/search", response_model=PlayersSearchResponse, summary="Search Players")
async def search_players(
    name: Optional[str] = Query(None, description="Player name (partial match)"),
    team: Optional[str] = Query(None, description="Team/school name (partial match)"),
    season: Optional[str] = Query(None, description="Season filter (e.g., '2024-25')"),
    sources: Optional[str] = Query(
        None, description="Comma-separated list of sources (e.g., 'eybl,psal')"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
):
    """
    Search for players across multiple data sources.

    Queries enabled data sources in parallel and aggregates results.
    Uses identity resolution for intelligent deduplication across sources.
    Automatically persists results to DuckDB if enabled.

    ### Query Parameters:
    - **name**: Filter by player name (case-insensitive partial match)
    - **team**: Filter by team or school name (case-insensitive partial match)
    - **season**: Filter by season (e.g., "2024-25")
    - **sources**: Limit search to specific sources (comma-separated: "eybl,psal,fiba")
    - **limit**: Maximum number of results (1-200, default: 50)

    ### Returns:
    - List of Player objects matching criteria with stable player_uid for cross-source matching
    - Total count of results
    - Sources that were queried

    ### Example:
    ```
    GET /api/v1/players/search?name=Smith&team=Lincoln&limit=10
    ```
    """
    try:
        # Parse sources
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Search players (automatically uses identity resolution)
        players = await aggregator.search_players_all_sources(
            name=name,
            team=team,
            season=season,
            sources=source_list,
            total_limit=limit,
        )

        # Get sources that were queried
        sources_queried = source_list if source_list else aggregator.get_available_sources()

        logger.info(f"Player search returned {len(players)} results", name=name, team=team)

        return {
            "total": len(players),
            "players": players,
            "sources_queried": sources_queried,
        }

    except Exception as e:
        logger.error("Player search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/players/{source}/{player_id}",
    response_model=Player,
    summary="Get Player by ID",
)
async def get_player(
    source: str = Path(..., description="Data source (e.g., 'eybl', 'psal')"),
    player_id: str = Path(..., description="Player ID within the source"),
):
    """
    Get detailed player information from a specific source.

    ### Path Parameters:
    - **source**: Data source identifier (eybl, psal, fiba, mn_hub)
    - **player_id**: Player ID within that source

    ### Returns:
    - Complete Player object with all available details

    ### Example:
    ```
    GET /api/v1/players/eybl/eybl_john_smith
    ```
    """
    try:
        aggregator = get_aggregator()

        player = await aggregator.get_player_from_source(source, player_id)

        if not player:
            raise HTTPException(
                status_code=404, detail=f"Player {player_id} not found in source {source}"
            )

        return player

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player failed", source=source, player_id=player_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get player: {str(e)}")


@router.get(
    "/players/{player_name}/stats",
    response_model=list[PlayerSeasonStats],
    summary="Get Player Season Stats",
)
async def get_player_stats(
    player_name: str = Path(..., description="Player name"),
    season: Optional[str] = Query(None, description="Season (e.g., '2024-25')"),
    sources: Optional[str] = Query(None, description="Comma-separated source list"),
    persist: bool = Query(
        False, description="If true, persist stats to DuckDB for analytics"
    ),
):
    """
    Get player season statistics from multiple sources.

    Searches for the player across sources and retrieves their season stats.
    Returns stats from each source where the player is found.

    **ADVANCED METRICS**: All stats are automatically enriched with calculated advanced metrics:
    - `true_shooting_pct`: True Shooting % - Best overall shooting efficiency measure
    - `effective_fg_pct`: Effective FG% - Adjusts for 3-point value
    - `assist_to_turnover_ratio`: Assist-to-Turnover ratio - Decision making quality
    - `two_point_pct`: 2-Point FG% - Inside scoring efficiency
    - `three_point_attempt_rate`: 3PA Rate - 3-point shot selection frequency
    - `free_throw_rate`: FT Rate - Ability to get to the free throw line
    - `points_per_shot_attempt`: Points per Shot Attempt - Scoring efficiency
    - `rebounds_per_40`: Rebounds per 40 minutes - Rebounding rate normalized
    - `points_per_40`: Points per 40 minutes - Scoring rate normalized

    ### Parameters:
    - **player_name**: Player's full or partial name
    - **season**: Season filter (optional, defaults to current season)
    - **sources**: Limit to specific sources (optional)
    - **persist**: If true, automatically persist results to DuckDB (default: false)

    ### Returns:
    - List of PlayerSeasonStats objects with basic stats + advanced metrics

    ### Example:
    ```
    GET /api/v1/players/John Smith/stats?season=2024-25&persist=true
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        stats = await aggregator.get_player_season_stats_all_sources(
            player_name=player_name,
            season=season,
            sources=source_list,
        )

        if not stats:
            raise HTTPException(
                status_code=404, detail=f"No stats found for player: {player_name}"
            )

        # Optional: manually persist to DuckDB if requested
        if persist and stats:
            duckdb = get_duckdb_storage()
            if duckdb:
                try:
                    await duckdb.store_player_stats(stats)
                    logger.info(
                        f"Manually persisted {len(stats)} stats records to DuckDB"
                    )
                except Exception as e:
                    logger.error("Failed to persist stats", error=str(e))

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player stats failed", player_name=player_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Team Endpoints


@router.get("/teams/search", summary="Search Teams")
async def search_teams(
    name: Optional[str] = Query(None, description="Team name (partial match)"),
    league: Optional[str] = Query(None, description="League filter"),
    season: Optional[str] = Query(None, description="Season filter"),
    sources: Optional[str] = Query(None, description="Comma-separated source list"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
):
    """
    Search for teams across multiple data sources.

    ### Query Parameters:
    - **name**: Filter by team name (case-insensitive partial match)
    - **league**: Filter by league (e.g., "PSAL", "EYBL")
    - **season**: Filter by season
    - **sources**: Limit search to specific sources
    - **limit**: Maximum results

    ### Example:
    ```
    GET /api/v1/teams/search?name=Lincoln&league=PSAL
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        teams = await aggregator.search_teams_all_sources(
            name=name,
            league=league,
            season=season,
            sources=source_list,
            total_limit=limit,
        )

        return {"total": len(teams), "teams": teams}

    except Exception as e:
        logger.error("Team search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Leaderboard Endpoints


@router.get(
    "/leaderboards/{stat}",
    response_model=LeaderboardResponse,
    summary="Get Statistical Leaderboard",
)
async def get_leaderboard(
    stat: str = Path(
        ...,
        description="Stat category (points, rebounds, assists, steals, blocks)",
    ),
    season: Optional[str] = Query(None, description="Season filter"),
    sources: Optional[str] = Query(None, description="Comma-separated source list"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
):
    """
    Get statistical leaderboard across multiple sources.

    Aggregates leaderboards from multiple sources and ranks players
    by the specified statistic.

    ### Path Parameters:
    - **stat**: Statistic to rank by (points, rebounds, assists, steals, blocks, etc.)

    ### Query Parameters:
    - **season**: Filter by season
    - **sources**: Limit to specific sources
    - **limit**: Maximum results

    ### Returns:
    - Aggregated leaderboard with players ranked by stat value
    - Each entry includes player name, team, stat value, and source

    ### Example:
    ```
    GET /api/v1/leaderboards/points?season=2024-25&limit=25
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        entries = await aggregator.get_leaderboard_all_sources(
            stat=stat,
            season=season,
            sources=source_list,
            total_limit=limit,
        )

        return {"total": len(entries), "stat": stat, "entries": entries}

    except Exception as e:
        logger.error("Get leaderboard failed", stat=stat, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")


# Data Source Endpoints


@router.get("/sources", response_model=SourcesResponse, summary="Get Available Sources")
async def get_sources():
    """
    Get information about available data sources.

    ### Returns:
    - List of available source keys
    - Detailed information about each source (name, region, URL, status)

    ### Example:
    ```
    GET /api/v1/sources
    ```
    """
    try:
        aggregator = get_aggregator()

        sources = aggregator.get_available_sources()
        source_info = aggregator.get_source_info()

        return {"sources": sources, "source_info": source_info}

    except Exception as e:
        logger.error("Get sources failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get sources: {str(e)}")


@router.get("/sources/health", summary="Check Source Health")
async def check_source_health():
    """
    Check health status of all data sources.

    Performs health checks on all enabled sources in parallel.

    ### Returns:
    - Dictionary mapping each source to its health status (true/false)

    ### Example:
    ```
    GET /api/v1/sources/health
    ```
    """
    try:
        aggregator = get_aggregator()

        health_status = await aggregator.health_check_all_sources()

        # Count healthy sources
        healthy_count = sum(1 for status in health_status.values() if status)
        total_count = len(health_status)

        return {
            "healthy": healthy_count,
            "total": total_count,
            "sources": health_status,
        }

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
