"""
Recruiting API Routes

RESTful API endpoints for college basketball recruiting data.
Provides access to rankings, offers, and predictions from recruiting services.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from ..models import (
    CollegeOffer,
    RecruitingPrediction,
    RecruitingProfile,
    RecruitingRank,
)
from ..services.aggregator import get_aggregator
from ..services.duckdb_storage import get_duckdb_storage
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/recruiting", tags=["recruiting"])


# Response models


class RankingsResponse(BaseModel):
    """Rankings response model."""

    total: int
    class_year: int
    rankings: list[RecruitingRank]
    sources_queried: list[str]


class OffersResponse(BaseModel):
    """Offers response model."""

    total: int
    player_id: str
    player_name: str
    offers: list[CollegeOffer]
    sources_queried: list[str]


class PredictionsResponse(BaseModel):
    """Predictions response model."""

    total: int
    player_id: str
    player_name: str
    predictions: list[RecruitingPrediction]
    sources_queried: list[str]


class ProfileResponse(BaseModel):
    """Complete recruiting profile response."""

    player_id: str
    player_name: str
    profile: Optional[RecruitingProfile]
    sources_queried: list[str]


class RecruitingSourcesResponse(BaseModel):
    """Available recruiting sources response."""

    sources: list[str]
    source_info: dict[str, dict]


# Rankings Endpoints


@router.get(
    "/rankings",
    response_model=RankingsResponse,
    summary="Get Recruiting Rankings",
)
async def get_rankings(
    class_year: int = Query(..., ge=2020, le=2035, description="Graduation year (e.g., 2025)"),
    position: Optional[str] = Query(None, description="Filter by position (PG, SG, SF, PF, C)"),
    state: Optional[str] = Query(None, description="Filter by state (2-letter code)"),
    sources: Optional[str] = Query(
        None, description="Comma-separated recruiting sources (e.g., '247sports,espn')"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    persist: bool = Query(
        False, description="If true, persist rankings to DuckDB for analytics"
    ),
):
    """
    Get recruiting rankings for a class year.

    Queries recruiting services (247Sports, ESPN, Rivals, On3) for player rankings.
    Returns composite rankings with stars, ratings, and commitment data.

    **IMPORTANT - LEGAL COMPLIANCE**:
    - Most recruiting services prohibit automated scraping
    - Use only with explicit permission or commercial data license
    - All recruiting sources disabled by default in configuration

    ### Query Parameters:
    - **class_year**: Graduation year (2020-2035)
    - **position**: Filter by position (PG, SG, SF, PF, C, optional)
    - **state**: Filter by state (2-letter code, optional)
    - **sources**: Specific recruiting sources to query (optional)
    - **limit**: Maximum number of results (1-500, default: 100)
    - **persist**: Auto-persist results to DuckDB (default: false)

    ### Returns:
    - List of RecruitingRank objects with rankings, stars, ratings, commitments
    - Total count of results
    - Sources that were queried

    ### Example:
    ```
    GET /api/v1/recruiting/rankings?class_year=2025&position=PG&limit=50
    ```
    """
    try:
        # Parse sources
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Get rankings from recruiting sources
        rankings = await aggregator.get_rankings_all_sources(
            class_year=class_year,
            position=position,
            state=state,
            sources=source_list,
            total_limit=limit,
        )

        # Get sources that were queried
        sources_queried = source_list if source_list else aggregator.get_recruiting_sources()

        logger.info(
            f"Rankings query returned {len(rankings)} results",
            class_year=class_year,
            position=position,
            state=state,
        )

        # Optional: manually persist to DuckDB if requested
        if persist and rankings:
            duckdb = get_duckdb_storage()
            if duckdb:
                try:
                    await duckdb.store_recruiting_ranks(rankings)
                    logger.info(f"Persisted {len(rankings)} rankings to DuckDB")
                except Exception as e:
                    logger.error("Failed to persist rankings", error=str(e))

        return {
            "total": len(rankings),
            "class_year": class_year,
            "rankings": rankings,
            "sources_queried": sources_queried,
        }

    except ValueError as e:
        # Class year validation error
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Rankings query failed", class_year=class_year, error=str(e))
        raise HTTPException(status_code=500, detail=f"Rankings query failed: {str(e)}")


@router.get(
    "/rankings/{player_id}",
    response_model=list[RecruitingRank],
    summary="Get Player Rankings",
)
async def get_player_rankings(
    player_id: str = Path(..., description="Player ID from recruiting service"),
    sources: Optional[str] = Query(None, description="Comma-separated recruiting sources"),
):
    """
    Get all rankings for a specific player across recruiting services.

    Retrieves rankings from multiple services (247Sports, ESPN, Rivals, On3)
    to show how different services rank the same player.

    ### Path Parameters:
    - **player_id**: Player identifier from recruiting service

    ### Query Parameters:
    - **sources**: Specific recruiting sources (optional)

    ### Returns:
    - List of RecruitingRank objects from different services

    ### Example:
    ```
    GET /api/v1/recruiting/rankings/247_12345
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Get player rankings from all recruiting sources
        # This uses the player's recruiting profile which includes all rankings
        profile = await aggregator.get_player_recruiting_profile_all_sources(
            player_id=player_id,
            sources=source_list,
        )

        if not profile or not profile.rankings:
            raise HTTPException(
                status_code=404,
                detail=f"No rankings found for player: {player_id}",
            )

        return profile.rankings

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player rankings failed", player_id=player_id, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get player rankings: {str(e)}"
        )


# Offers Endpoints


@router.get(
    "/offers/{player_id}",
    response_model=OffersResponse,
    summary="Get College Offers",
)
async def get_player_offers(
    player_id: str = Path(..., description="Player ID from recruiting service"),
    sources: Optional[str] = Query(None, description="Comma-separated recruiting sources"),
    status: Optional[str] = Query(
        None, description="Filter by offer status (OFFERED, COMMITTED, DECOMMITTED)"
    ),
    persist: bool = Query(False, description="If true, persist offers to DuckDB"),
):
    """
    Get college offers for a player.

    Retrieves scholarship offers from recruiting services, including
    offer dates, commitment status, and recruiting details.

    ### Path Parameters:
    - **player_id**: Player identifier from recruiting service

    ### Query Parameters:
    - **sources**: Specific recruiting sources (optional)
    - **status**: Filter by offer status (optional)
    - **persist**: Auto-persist results to DuckDB (default: false)

    ### Returns:
    - List of CollegeOffer objects with offer details
    - Player information
    - Total count of offers

    ### Example:
    ```
    GET /api/v1/recruiting/offers/247_12345?status=COMMITTED
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Get offers from recruiting sources
        offers = await aggregator.get_player_offers_all_sources(
            player_id=player_id,
            sources=source_list,
        )

        if not offers:
            raise HTTPException(
                status_code=404,
                detail=f"No offers found for player: {player_id}",
            )

        # Filter by status if provided
        if status:
            offers = [o for o in offers if o.status.value.upper() == status.upper()]

        # Extract player info from first offer
        player_name = offers[0].player_name if offers else "Unknown"

        # Get sources that were queried
        sources_queried = source_list if source_list else aggregator.get_recruiting_sources()

        logger.info(
            f"Offers query returned {len(offers)} results",
            player_id=player_id,
            status=status,
        )

        # Optional: manually persist to DuckDB if requested
        if persist and offers:
            duckdb = get_duckdb_storage()
            if duckdb:
                try:
                    await duckdb.store_college_offers(offers)
                    logger.info(f"Persisted {len(offers)} offers to DuckDB")
                except Exception as e:
                    logger.error("Failed to persist offers", error=str(e))

        return {
            "total": len(offers),
            "player_id": player_id,
            "player_name": player_name,
            "offers": offers,
            "sources_queried": sources_queried,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player offers failed", player_id=player_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get offers: {str(e)}")


# Predictions Endpoints


@router.get(
    "/predictions/{player_id}",
    response_model=PredictionsResponse,
    summary="Get Recruiting Predictions",
)
async def get_player_predictions(
    player_id: str = Path(..., description="Player ID from recruiting service"),
    sources: Optional[str] = Query(None, description="Comma-separated recruiting sources"),
    persist: bool = Query(False, description="If true, persist predictions to DuckDB"),
):
    """
    Get recruiting predictions (Crystal Ball style) for a player.

    Retrieves expert predictions about where a player will commit,
    including confidence scores and prediction history.

    ### Path Parameters:
    - **player_id**: Player identifier from recruiting service

    ### Query Parameters:
    - **sources**: Specific recruiting sources (optional)
    - **persist**: Auto-persist results to DuckDB (default: false)

    ### Returns:
    - List of RecruitingPrediction objects with predictions and confidence
    - Player information
    - Total count of predictions

    ### Example:
    ```
    GET /api/v1/recruiting/predictions/247_12345
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Get predictions from recruiting sources
        predictions = await aggregator.get_player_predictions_all_sources(
            player_id=player_id,
            sources=source_list,
        )

        if not predictions:
            raise HTTPException(
                status_code=404,
                detail=f"No predictions found for player: {player_id}",
            )

        # Extract player info from first prediction
        player_name = predictions[0].player_name if predictions else "Unknown"

        # Get sources that were queried
        sources_queried = source_list if source_list else aggregator.get_recruiting_sources()

        logger.info(
            f"Predictions query returned {len(predictions)} results",
            player_id=player_id,
        )

        # Optional: manually persist to DuckDB if requested
        if persist and predictions:
            duckdb = get_duckdb_storage()
            if duckdb:
                try:
                    await duckdb.store_recruiting_predictions(predictions)
                    logger.info(f"Persisted {len(predictions)} predictions to DuckDB")
                except Exception as e:
                    logger.error("Failed to persist predictions", error=str(e))

        return {
            "total": len(predictions),
            "player_id": player_id,
            "player_name": player_name,
            "predictions": predictions,
            "sources_queried": sources_queried,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player predictions failed", player_id=player_id, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get predictions: {str(e)}"
        )


# Profile Endpoint


@router.get(
    "/profile/{player_id}",
    response_model=ProfileResponse,
    summary="Get Complete Recruiting Profile",
)
async def get_player_profile(
    player_id: str = Path(..., description="Player ID from recruiting service"),
    sources: Optional[str] = Query(None, description="Comma-separated recruiting sources"),
):
    """
    Get complete recruiting profile for a player.

    Aggregates all recruiting data: rankings, offers, predictions into
    a comprehensive RecruitingProfile object.

    ### Path Parameters:
    - **player_id**: Player identifier from recruiting service

    ### Query Parameters:
    - **sources**: Specific recruiting sources (optional)

    ### Returns:
    - RecruitingProfile with all rankings, offers, and predictions
    - Player information
    - Sources that were queried

    ### Example:
    ```
    GET /api/v1/recruiting/profile/247_12345
    ```
    """
    try:
        source_list = sources.split(",") if sources else None

        aggregator = get_aggregator()

        # Get complete recruiting profile
        profile = await aggregator.get_player_recruiting_profile_all_sources(
            player_id=player_id,
            sources=source_list,
        )

        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"No recruiting profile found for player: {player_id}",
            )

        # Get sources that were queried
        sources_queried = source_list if source_list else aggregator.get_recruiting_sources()

        logger.info(
            f"Profile query returned complete profile",
            player_id=player_id,
            rankings_count=len(profile.rankings) if profile.rankings else 0,
            offers_count=len(profile.offers) if profile.offers else 0,
            predictions_count=len(profile.predictions) if profile.predictions else 0,
        )

        return {
            "player_id": player_id,
            "player_name": profile.player_name,
            "profile": profile,
            "sources_queried": sources_queried,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get player profile failed", player_id=player_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


# Sources Endpoint


@router.get(
    "/sources",
    response_model=RecruitingSourcesResponse,
    summary="Get Available Recruiting Sources",
)
async def get_recruiting_sources():
    """
    Get information about available recruiting data sources.

    ### Returns:
    - List of available recruiting source keys
    - Detailed information about each recruiting source

    ### Example:
    ```
    GET /api/v1/recruiting/sources
    ```
    """
    try:
        aggregator = get_aggregator()

        sources = aggregator.get_recruiting_sources()
        source_info = aggregator.get_recruiting_source_info()

        return {"sources": sources, "source_info": source_info}

    except Exception as e:
        logger.error("Get recruiting sources failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get recruiting sources: {str(e)}"
        )
