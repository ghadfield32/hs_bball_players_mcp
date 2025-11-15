"""
Forecasting Data Aggregation Service

Aggregates ALL available data from all sources to create comprehensive
player profiles for forecasting high school and young European players.

This service maximizes data extraction for ML forecasting by pulling:
- **Stats**: Season stats, advanced metrics, per-40 stats
- **Recruiting**: Rankings (247/ESPN/Rivals/On3), offers, predictions
- **Bio**: Birth date, height, weight, position, age-for-grade
- **Performance**: Multiple seasons, circuits, tournaments
- **Context**: Competition level, conference, school quality

**CRITICAL FORECASTING METRICS** (in order of importance):
1. 247Sports Composite Rating (15% importance)
2. Star Rating (12%)
3. Power 6 Offer Count (10%)
4. **Age-for-Grade** (8-10%) - NEWLY ADDED
5. True Shooting % (8%)
6. Effective FG% (7%)
7. Assist/Turnover Ratio (6%)
8. Multiple-season performance trend
9. Competition level (circuit vs state)
10. Physical measurements (height, weight, wingspan)

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..models import (
    CollegeOffer,
    Player,
    PlayerSeasonStats,
    RecruitingPrediction,
    RecruitingProfile,
    RecruitingRank,
)
from ..utils.logger import get_logger
from .aggregator import DataSourceAggregator

logger = get_logger(__name__)


class ForecastingDataAggregator:
    """
    Comprehensive forecasting data aggregator.

    Pulls ALL available data from all sources to maximize forecasting accuracy
    for high school and young European players.
    """

    def __init__(self, aggregator: Optional[DataSourceAggregator] = None):
        """
        Initialize forecasting aggregator.

        Args:
            aggregator: Optional DataSourceAggregator instance (creates new if None)
        """
        self.aggregator = aggregator or DataSourceAggregator()
        self.logger = logger

    async def get_comprehensive_player_profile(
        self,
        player_name: str,
        grad_year: Optional[int] = None,
        state: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Get comprehensive player profile from ALL available sources.

        **THIS IS THE KEY FORECASTING METHOD** - pulls everything:
        - Season stats from all circuits/states
        - Advanced metrics (TS%, eFG%, A/TO, etc.)
        - Recruiting rankings (all services)
        - College offers (Power 6 count)
        - Crystal Ball predictions
        - Birth date and age-for-grade
        - Physical measurements
        - Multiple season trends

        Args:
            player_name: Player name to search
            grad_year: Graduation year filter
            state: State filter (for US players)
            **kwargs: Additional search parameters

        Returns:
            Dictionary with comprehensive profile data

        Example:
            >>> forecasting_agg = ForecastingDataAggregator()
            >>> profile = await forecasting_agg.get_comprehensive_player_profile(
            ...     player_name="Cooper Flagg",
            ...     grad_year=2025,
            ...     state="ME"
            ... )
            >>> print(f"Age advantage: {profile['age_for_grade']}")
            >>> print(f"Power 6 offers: {profile['power_6_offer_count']}")
            >>> print(f"True Shooting %: {profile['best_ts_pct']}")
        """
        self.logger.info(
            "Fetching comprehensive forecasting profile",
            player_name=player_name,
            grad_year=grad_year,
            state=state
        )

        # Initialize comprehensive profile
        profile = {
            # Identity
            "player_name": player_name,
            "grad_year": grad_year,
            "state": state,
            "player_uid": None,

            # Bio & Physical (CRITICAL for forecasting)
            "birth_date": None,
            "age_for_grade": None,
            "age_for_grade_category": None,
            "height": None,
            "weight": None,
            "position": None,
            "school": None,
            "city": None,

            # Recruiting Metrics (TOP FORECASTING PREDICTORS)
            "composite_247_rating": None,
            "composite_247_rank": None,
            "stars_247": None,
            "espn_rank": None,
            "rivals_rank": None,
            "on3_rank": None,
            "best_national_rank": None,
            "power_6_offer_count": 0,
            "total_offer_count": 0,
            "is_committed": False,
            "committed_to": None,
            "prediction_consensus": None,
            "prediction_confidence": None,

            # Performance Stats (aggregated across all sources)
            "total_seasons": 0,
            "total_games_played": 0,
            "career_ppg": None,
            "career_rpg": None,
            "career_apg": None,
            "career_spg": None,
            "career_bpg": None,

            # Advanced Metrics (CRITICAL for forecasting)
            "best_ts_pct": None,
            "best_efg_pct": None,
            "best_ato_ratio": None,
            "best_two_pt_pct": None,
            "best_three_pt_pct": None,
            "best_ft_pct": None,
            "best_per_40_ppg": None,
            "best_per_40_rpg": None,

            # Competition Context
            "highest_competition_level": None,
            "circuits_played": [],
            "states_played": [],
            "countries_played": [],

            # Trend Analysis
            "seasons": [],  # List of season stats for trend analysis
            "performance_trend": None,  # "improving", "declining", "stable"

            # Raw Data (for ML feature engineering)
            "raw_players": [],
            "raw_stats": [],
            "raw_recruiting_ranks": [],
            "raw_offers": [],
            "raw_predictions": [],
        }

        try:
            # ================================================================
            # PHASE 1: Get Stats Data from ALL Sources
            # ================================================================
            self.logger.info("Phase 1: Fetching stats from all sources", player_name=player_name)

            players = await self.aggregator.get_players(
                name=player_name,
                state=state,
                grad_year=grad_year,
                **kwargs
            )

            if players:
                self.logger.info(f"Found {len(players)} player records", player_name=player_name)
                profile["raw_players"] = players

                # Use first player for bio data
                primary_player = players[0]
                profile["player_uid"] = primary_player.player_uid
                profile["birth_date"] = primary_player.birth_date
                profile["height"] = primary_player.height
                profile["weight"] = primary_player.weight
                profile["position"] = str(primary_player.position) if primary_player.position else None
                profile["school"] = primary_player.school
                profile["city"] = primary_player.city
                profile["state"] = primary_player.state or state

                # Calculate age-for-grade if we have birth_date
                if primary_player.birth_date and grad_year:
                    from ..models.player import Player
                    temp_player = Player(
                        player_id=primary_player.player_id,
                        first_name=primary_player.first_name,
                        last_name=primary_player.last_name,
                        birth_date=primary_player.birth_date,
                        grad_year=grad_year,
                    )
                    profile["age_for_grade"] = temp_player.age_for_grade
                    profile["age_for_grade_category"] = temp_player.age_for_grade_category

                    self.logger.info(
                        "Calculated age-for-grade",
                        player_name=player_name,
                        age_advantage=profile["age_for_grade"],
                        category=profile["age_for_grade_category"]
                    )

            # ================================================================
            # PHASE 2: Get Season Stats from ALL Sources
            # ================================================================
            self.logger.info("Phase 2: Fetching season stats from all sources", player_name=player_name)

            stats = await self.aggregator.get_player_stats(
                name=player_name,
                state=state,
                grad_year=grad_year,
                **kwargs
            )

            if stats:
                self.logger.info(f"Found {len(stats)} season stat records", player_name=player_name)
                profile["raw_stats"] = stats
                profile["total_seasons"] = len(stats)

                # Aggregate across all seasons
                total_games = 0
                total_points = 0
                total_rebounds = 0
                total_assists = 0
                total_steals = 0
                total_blocks = 0

                best_ts = 0
                best_efg = 0
                best_ato = 0
                best_2pt = 0
                best_3pt = 0
                best_ft = 0
                best_per40_ppg = 0
                best_per40_rpg = 0

                circuits = set()
                states_set = set()
                countries = set()

                season_summaries = []

                for stat in stats:
                    # Aggregate totals
                    if stat.games_played:
                        total_games += stat.games_played
                    if stat.points and stat.games_played:
                        total_points += stat.points
                    if stat.rebounds and stat.games_played:
                        total_rebounds += stat.rebounds
                    if stat.assists and stat.games_played:
                        total_assists += stat.assists
                    if stat.steals and stat.games_played:
                        total_steals += stat.steals
                    if stat.blocks and stat.games_played:
                        total_blocks += stat.blocks

                    # Track best advanced metrics
                    if stat.true_shooting_pct and stat.true_shooting_pct > best_ts:
                        best_ts = stat.true_shooting_pct
                    if stat.effective_fg_pct and stat.effective_fg_pct > best_efg:
                        best_efg = stat.effective_fg_pct
                    if stat.assist_to_turnover_ratio and stat.assist_to_turnover_ratio > best_ato:
                        best_ato = stat.assist_to_turnover_ratio
                    if stat.two_point_pct and stat.two_point_pct > best_2pt:
                        best_2pt = stat.two_point_pct
                    if stat.three_point_pct and stat.three_point_pct > best_3pt:
                        best_3pt = stat.three_point_pct
                    if stat.free_throw_pct and stat.free_throw_pct > best_ft:
                        best_ft = stat.free_throw_pct
                    if stat.points_per_40 and stat.points_per_40 > best_per40_ppg:
                        best_per40_ppg = stat.points_per_40
                    if stat.rebounds_per_40 and stat.rebounds_per_40 > best_per40_rpg:
                        best_per40_rpg = stat.rebounds_per_40

                    # Track competition
                    if stat.league:
                        league_upper = stat.league.upper()
                        if any(circuit in league_upper for circuit in ["EYBL", "UAA", "3SSB", "PEACH JAM"]):
                            circuits.add(stat.league)

                    if stat.data_source and stat.data_source.region:
                        region_str = str(stat.data_source.region)
                        if "US" in region_str and state:
                            states_set.add(state)
                        elif "EUROPE" in region_str:
                            countries.add(region_str)

                    # Season summary for trend analysis
                    season_summaries.append({
                        "season": stat.season,
                        "league": stat.league,
                        "games_played": stat.games_played,
                        "ppg": stat.points_per_game,
                        "rpg": stat.rebounds_per_game,
                        "apg": stat.assists_per_game,
                        "ts_pct": stat.true_shooting_pct,
                        "efg_pct": stat.effective_fg_pct,
                    })

                # Calculate career averages
                profile["total_games_played"] = total_games
                if total_games > 0:
                    profile["career_ppg"] = round(total_points / total_games, 1)
                    profile["career_rpg"] = round(total_rebounds / total_games, 1)
                    profile["career_apg"] = round(total_assists / total_games, 1)
                    profile["career_spg"] = round(total_steals / total_games, 1) if total_steals else None
                    profile["career_bpg"] = round(total_blocks / total_games, 1) if total_blocks else None

                # Store best metrics
                profile["best_ts_pct"] = round(best_ts, 3) if best_ts > 0 else None
                profile["best_efg_pct"] = round(best_efg, 3) if best_efg > 0 else None
                profile["best_ato_ratio"] = round(best_ato, 2) if best_ato > 0 else None
                profile["best_two_pt_pct"] = round(best_2pt, 3) if best_2pt > 0 else None
                profile["best_three_pt_pct"] = round(best_3pt, 3) if best_3pt > 0 else None
                profile["best_ft_pct"] = round(best_ft, 3) if best_ft > 0 else None
                profile["best_per_40_ppg"] = round(best_per40_ppg, 1) if best_per40_ppg > 0 else None
                profile["best_per_40_rpg"] = round(best_per40_rpg, 1) if best_per40_rpg > 0 else None

                # Store competition context
                profile["circuits_played"] = list(circuits)
                profile["states_played"] = list(states_set)
                profile["countries_played"] = list(countries)
                profile["highest_competition_level"] = "National Circuit" if circuits else "State/Regional"

                # Store seasons for trend analysis
                profile["seasons"] = sorted(season_summaries, key=lambda x: x["season"])

                # Calculate performance trend (simple version)
                if len(season_summaries) >= 2:
                    recent_ppg = season_summaries[-1]["ppg"]
                    prev_ppg = season_summaries[-2]["ppg"]
                    if recent_ppg and prev_ppg:
                        improvement = ((recent_ppg - prev_ppg) / prev_ppg) * 100
                        if improvement > 10:
                            profile["performance_trend"] = "improving"
                        elif improvement < -10:
                            profile["performance_trend"] = "declining"
                        else:
                            profile["performance_trend"] = "stable"

            # ================================================================
            # PHASE 3: Get Recruiting Data (247Sports, ESPN, Rivals, On3)
            # ================================================================
            self.logger.info("Phase 3: Fetching recruiting data", player_name=player_name)

            # Try to get recruiting profile from 247Sports
            if "247" in self.aggregator.recruiting_sources:
                sports_247 = self.aggregator.recruiting_sources["247"]

                # Search for player in rankings
                rankings = await sports_247.search_players(
                    name=player_name,
                    class_year=grad_year,
                    limit=5
                )

                if rankings:
                    self.logger.info(f"Found {len(rankings)} recruiting ranks", player_name=player_name)
                    profile["raw_recruiting_ranks"] = rankings

                    # Extract recruiting metrics from rankings
                    for rank in rankings:
                        if rank.service.value == "247sports":
                            profile["stars_247"] = rank.stars
                        elif rank.service.value == "composite":
                            profile["composite_247_rating"] = rank.rating
                            profile["composite_247_rank"] = rank.rank_national
                            profile["stars_247"] = rank.stars  # Use composite stars if available
                        elif rank.service.value == "espn":
                            profile["espn_rank"] = rank.rank_national
                        elif rank.service.value == "rivals":
                            profile["rivals_rank"] = rank.rank_national
                        elif rank.service.value == "on3":
                            profile["on3_rank"] = rank.rank_national

                    # Calculate best national rank
                    national_ranks = [r.rank_national for r in rankings if r.rank_national]
                    if national_ranks:
                        profile["best_national_rank"] = min(national_ranks)

                    # Try to get full profile (with offers and predictions)
                    primary_rank = rankings[0]
                    if primary_rank.player_id and primary_rank.player_name:
                        recruiting_profile = await sports_247.get_player_recruiting_profile(
                            player_id=primary_rank.player_id,
                            player_name=primary_rank.player_name,
                            class_year=grad_year
                        )

                        if recruiting_profile:
                            self.logger.info("Retrieved full recruiting profile", player_name=player_name)

                            # Extract offers data
                            if recruiting_profile.offers:
                                profile["raw_offers"] = recruiting_profile.offers
                                profile["total_offer_count"] = recruiting_profile.offer_count
                                profile["power_6_offer_count"] = recruiting_profile.power_6_offers

                            # Extract commitment status
                            profile["is_committed"] = recruiting_profile.is_committed
                            profile["committed_to"] = recruiting_profile.committed_to

                            # Extract predictions
                            if recruiting_profile.predictions:
                                profile["raw_predictions"] = recruiting_profile.predictions
                                profile["prediction_consensus"] = recruiting_profile.prediction_consensus
                                profile["prediction_confidence"] = recruiting_profile.prediction_confidence

                            # Update birth date if found in profile
                            # (247Sports profile bio extraction from Enhancement 2)
                            # Birth date is extracted in _parse_player_bio()

                            self.logger.info(
                                "Recruiting profile complete",
                                player_name=player_name,
                                offers=profile["total_offer_count"],
                                power_6_offers=profile["power_6_offer_count"],
                                is_committed=profile["is_committed"]
                            )

            # ================================================================
            # PHASE 4: Calculate Forecasting Score (Simple Weighted)
            # ================================================================
            self.logger.info("Phase 4: Calculating forecasting metrics", player_name=player_name)

            profile["forecasting_score"] = self._calculate_forecasting_score(profile)
            profile["data_completeness"] = self._calculate_data_completeness(profile)

            self.logger.info(
                "Comprehensive profile complete",
                player_name=player_name,
                forecasting_score=profile["forecasting_score"],
                data_completeness=profile["data_completeness"],
                age_for_grade=profile["age_for_grade"],
                power_6_offers=profile["power_6_offer_count"],
                best_ts_pct=profile["best_ts_pct"]
            )

            return profile

        except Exception as e:
            self.logger.error(
                "Failed to build comprehensive profile",
                player_name=player_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return profile

    def _calculate_forecasting_score(self, profile: Dict) -> Optional[float]:
        """
        Calculate simple forecasting score based on available data.

        **WEIGHTED BY IMPORTANCE**:
        - 247 Composite Rating: 15%
        - Stars: 12%
        - Power 6 Offers: 10%
        - Age-for-Grade: 9%
        - True Shooting %: 8%
        - eFG%: 7%
        - A/TO Ratio: 6%
        - Career PPG: 5%
        - etc.

        Returns:
            Score from 0-100 or None if insufficient data
        """
        score = 0
        weights_used = 0

        # 247 Composite Rating (15% weight, normalized to 0-100)
        if profile["composite_247_rating"]:
            # 247 ratings are 0.8000-1.0000 scale
            rating = profile["composite_247_rating"]
            normalized = (rating - 0.8) / 0.2 * 100  # Convert to 0-100
            score += normalized * 0.15
            weights_used += 0.15

        # Stars (12% weight)
        if profile["stars_247"]:
            stars = profile["stars_247"]
            normalized = (stars / 5.0) * 100  # 5-star = 100
            score += normalized * 0.12
            weights_used += 0.12

        # Power 6 Offers (10% weight)
        if profile["power_6_offer_count"]:
            # Cap at 20 offers
            offers = min(profile["power_6_offer_count"], 20)
            normalized = (offers / 20.0) * 100
            score += normalized * 0.10
            weights_used += 0.10

        # Age-for-Grade (9% weight)
        if profile["age_for_grade"] is not None:
            age_adv = profile["age_for_grade"]
            # +1.5 years younger = 100, -1.5 years older = 0
            normalized = ((age_adv + 1.5) / 3.0) * 100
            normalized = max(0, min(100, normalized))  # Clamp to 0-100
            score += normalized * 0.09
            weights_used += 0.09

        # True Shooting % (8% weight)
        if profile["best_ts_pct"]:
            ts_pct = profile["best_ts_pct"]
            # 70% TS = 100, 40% TS = 0
            normalized = ((ts_pct - 0.40) / 0.30) * 100
            normalized = max(0, min(100, normalized))
            score += normalized * 0.08
            weights_used += 0.08

        # eFG% (7% weight)
        if profile["best_efg_pct"]:
            efg_pct = profile["best_efg_pct"]
            # 65% eFG = 100, 35% eFG = 0
            normalized = ((efg_pct - 0.35) / 0.30) * 100
            normalized = max(0, min(100, normalized))
            score += normalized * 0.07
            weights_used += 0.07

        # A/TO Ratio (6% weight)
        if profile["best_ato_ratio"]:
            ato = profile["best_ato_ratio"]
            # 4.0 A/TO = 100, 0.5 A/TO = 0
            normalized = ((ato - 0.5) / 3.5) * 100
            normalized = max(0, min(100, normalized))
            score += normalized * 0.06
            weights_used += 0.06

        # Career PPG (5% weight)
        if profile["career_ppg"]:
            ppg = profile["career_ppg"]
            # 30 PPG = 100, 5 PPG = 0
            normalized = ((ppg - 5) / 25.0) * 100
            normalized = max(0, min(100, normalized))
            score += normalized * 0.05
            weights_used += 0.05

        # If we have some data, normalize by weights used
        if weights_used > 0:
            return round(score / weights_used, 1)

        return None

    def _calculate_data_completeness(self, profile: Dict) -> float:
        """
        Calculate what % of critical data fields are populated.

        Returns:
            Percentage from 0-100
        """
        critical_fields = [
            "birth_date",
            "age_for_grade",
            "height",
            "weight",
            "position",
            "composite_247_rating",
            "stars_247",
            "power_6_offer_count",
            "best_ts_pct",
            "best_efg_pct",
            "best_ato_ratio",
            "career_ppg",
            "career_rpg",
            "career_apg",
            "total_seasons",
        ]

        populated = sum(1 for field in critical_fields if profile.get(field) is not None)
        return round((populated / len(critical_fields)) * 100, 1)


async def get_forecasting_data_for_player(
    player_name: str,
    grad_year: Optional[int] = None,
    state: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    Convenience function to get comprehensive forecasting data for a player.

    **USE THIS FOR REAL TESTING AND FORECASTING**

    Args:
        player_name: Player name
        grad_year: Graduation year
        state: State code
        **kwargs: Additional filters

    Returns:
        Comprehensive forecasting profile dictionary
    """
    agg = ForecastingDataAggregator()
    return await agg.get_comprehensive_player_profile(
        player_name=player_name,
        grad_year=grad_year,
        state=state,
        **kwargs
    )
