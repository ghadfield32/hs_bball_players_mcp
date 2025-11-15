"""
Historical Trends Service

Analyzes player performance trends across multiple seasons to identify:
- Year-over-year growth rates
- Peak performance seasons
- Career trajectory (improving/stable/declining)
- Consistency metrics

This service is CRITICAL for forecasting as it provides:
- Progression data (20-30% importance in forecasting models)
- Peak potential identification
- Development curve analysis
- Consistency/reliability metrics

Author: Claude Code
Date: 2025-11-15
"""

from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

from ..models import PlayerSeasonStats
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HistoricalTrendsService:
    """
    Analyzes player performance trends across multiple seasons.

    Provides comprehensive longitudinal analysis including:
    - Multi-season stat aggregation
    - Growth rate calculations (YoY % change)
    - Peak performance identification
    - Career trajectory analysis
    - Consistency metrics (std dev, coefficient of variation)

    **USE CASES**:
    - Prospect evaluation (identify improving vs declining players)
    - Draft modeling (peak performance prediction)
    - Player development tracking
    - Scouting reports (career progression narratives)
    """

    def __init__(self):
        """Initialize historical trends service."""
        self.logger = logger

    async def get_player_historical_trends(
        self,
        seasons: List[PlayerSeasonStats],
        player_name: str
    ) -> Dict:
        """
        Get comprehensive historical trends for a player.

        Analyzes all available season data to produce:
        - Season-by-season breakdown
        - Growth rates for key metrics
        - Peak season identification
        - Career averages
        - Consistency scores
        - Trajectory classification

        Args:
            seasons: List of PlayerSeasonStats objects (sorted by season)
            player_name: Player name for logging

        Returns:
            Dictionary with comprehensive trend data:
            {
                "player_name": str,
                "seasons_analyzed": int,
                "season_by_season": List[Dict],  # Each season's key stats
                "growth_rates": Dict[str, float],  # YoY % change
                "peak_season": Dict,  # Best performing season
                "career_averages": Dict[str, float],  # Overall career stats
                "consistency_scores": Dict[str, float],  # Variance metrics
                "trajectory": str,  # RAPIDLY_IMPROVING | IMPROVING | STABLE | DECLINING
                "analysis_date": str
            }

        Example:
            >>> trends_service = HistoricalTrendsService()
            >>> seasons = [season_2023, season_2024, season_2025]
            >>> trends = await trends_service.get_player_historical_trends(
            ...     seasons=seasons,
            ...     player_name="Cooper Flagg"
            ... )
            >>> print(trends["trajectory"])  # "RAPIDLY_IMPROVING"
            >>> print(trends["growth_rates"]["ppg"])  # 15.3 (% increase YoY)
        """
        if not seasons:
            self.logger.warning(
                "No seasons provided for trend analysis",
                player_name=player_name
            )
            return {
                "player_name": player_name,
                "seasons_analyzed": 0,
                "error": "No season data available"
            }

        # Sort seasons chronologically
        sorted_seasons = sorted(seasons, key=lambda s: s.season)

        self.logger.info(
            "Analyzing historical trends",
            player_name=player_name,
            seasons_count=len(sorted_seasons),
            seasons=[s.season for s in sorted_seasons]
        )

        # Extract season-by-season breakdown
        season_breakdown = self._extract_season_breakdown(sorted_seasons)

        # Calculate growth rates (YoY % change)
        growth_rates = self.calculate_growth_rates(sorted_seasons)

        # Identify peak season
        peak_season, peak_score = self.identify_peak_season(sorted_seasons)

        # Calculate career averages
        career_averages = self._calculate_career_averages(sorted_seasons)

        # Calculate consistency metrics
        consistency_scores = self._calculate_consistency_metrics(sorted_seasons)

        # Determine trajectory
        trajectory = self.calculate_trajectory(growth_rates)

        result = {
            "player_name": player_name,
            "seasons_analyzed": len(sorted_seasons),
            "season_by_season": season_breakdown,
            "growth_rates": growth_rates,
            "peak_season": {
                "season": peak_season.season,
                "composite_score": round(peak_score, 2),
                "ppg": peak_season.points_per_game,
                "rpg": peak_season.rebounds_per_game,
                "apg": peak_season.assists_per_game,
                "ts_pct": peak_season.true_shooting_percentage,
                "efg_pct": peak_season.effective_field_goal_percentage,
            },
            "career_averages": career_averages,
            "consistency_scores": consistency_scores,
            "trajectory": trajectory,
            "analysis_date": datetime.now().isoformat()
        }

        self.logger.info(
            "Historical trends analysis complete",
            player_name=player_name,
            trajectory=trajectory,
            peak_season=peak_season.season,
            avg_growth_rate=round(mean(growth_rates.values()) if growth_rates else 0, 2)
        )

        return result

    def _extract_season_breakdown(
        self,
        seasons: List[PlayerSeasonStats]
    ) -> List[Dict]:
        """
        Extract key stats from each season for breakdown.

        Args:
            seasons: Sorted list of season stats

        Returns:
            List of dicts with key metrics per season
        """
        breakdown = []

        for season in seasons:
            breakdown.append({
                "season": season.season,
                "games_played": season.games_played,
                "ppg": season.points_per_game,
                "rpg": season.rebounds_per_game,
                "apg": season.assists_per_game,
                "spg": season.steals_per_game,
                "bpg": season.blocks_per_game,
                "fg_pct": season.field_goal_percentage,
                "three_pt_pct": season.three_point_percentage,
                "ft_pct": season.free_throw_percentage,
                "ts_pct": season.true_shooting_percentage,
                "efg_pct": season.effective_field_goal_percentage,
                "ato_ratio": season.assist_to_turnover_ratio,
                "team_name": season.team_name,
                "data_source": season.data_source.source_type if season.data_source else None
            })

        return breakdown

    def calculate_growth_rates(
        self,
        seasons: List[PlayerSeasonStats]
    ) -> Dict[str, float]:
        """
        Calculate year-over-year growth rates for key metrics.

        Growth rate = ((Current - Previous) / Previous) * 100

        Metrics analyzed:
        - PPG (points per game)
        - RPG (rebounds per game)
        - APG (assists per game)
        - TS% (true shooting percentage)
        - eFG% (effective field goal percentage)
        - A/TO (assist to turnover ratio)

        Args:
            seasons: Sorted list of season stats (chronological order)

        Returns:
            Dict of average YoY growth rates by metric
            Example: {"ppg": 15.3, "rpg": -2.1, "ts_pct": 8.7}

        Note:
            - Returns empty dict if < 2 seasons
            - Skips metrics with None values
            - Averages growth across all year-pairs
        """
        if len(seasons) < 2:
            self.logger.debug("Cannot calculate growth rates with < 2 seasons")
            return {}

        # Track growth rates for each metric across all year-pairs
        growth_by_metric = defaultdict(list)

        # Compare each consecutive season pair
        for i in range(1, len(seasons)):
            prev_season = seasons[i-1]
            curr_season = seasons[i]

            # PPG growth
            if prev_season.points_per_game and curr_season.points_per_game and prev_season.points_per_game > 0:
                ppg_growth = ((curr_season.points_per_game - prev_season.points_per_game) / prev_season.points_per_game) * 100
                growth_by_metric["ppg"].append(ppg_growth)

            # RPG growth
            if prev_season.rebounds_per_game and curr_season.rebounds_per_game and prev_season.rebounds_per_game > 0:
                rpg_growth = ((curr_season.rebounds_per_game - prev_season.rebounds_per_game) / prev_season.rebounds_per_game) * 100
                growth_by_metric["rpg"].append(rpg_growth)

            # APG growth
            if prev_season.assists_per_game and curr_season.assists_per_game and prev_season.assists_per_game > 0:
                apg_growth = ((curr_season.assists_per_game - prev_season.assists_per_game) / prev_season.assists_per_game) * 100
                growth_by_metric["apg"].append(apg_growth)

            # TS% growth
            if prev_season.true_shooting_percentage and curr_season.true_shooting_percentage and prev_season.true_shooting_percentage > 0:
                ts_growth = ((curr_season.true_shooting_percentage - prev_season.true_shooting_percentage) / prev_season.true_shooting_percentage) * 100
                growth_by_metric["ts_pct"].append(ts_growth)

            # eFG% growth
            if prev_season.effective_field_goal_percentage and curr_season.effective_field_goal_percentage and prev_season.effective_field_goal_percentage > 0:
                efg_growth = ((curr_season.effective_field_goal_percentage - prev_season.effective_field_goal_percentage) / prev_season.effective_field_goal_percentage) * 100
                growth_by_metric["efg_pct"].append(efg_growth)

            # A/TO growth
            if prev_season.assist_to_turnover_ratio and curr_season.assist_to_turnover_ratio and prev_season.assist_to_turnover_ratio > 0:
                ato_growth = ((curr_season.assist_to_turnover_ratio - prev_season.assist_to_turnover_ratio) / prev_season.assist_to_turnover_ratio) * 100
                growth_by_metric["ato_ratio"].append(ato_growth)

        # Calculate average growth rate per metric
        avg_growth_rates = {}
        for metric, growth_list in growth_by_metric.items():
            if growth_list:
                avg_growth_rates[metric] = round(mean(growth_list), 2)

        self.logger.debug(
            "Calculated growth rates",
            metrics=list(avg_growth_rates.keys()),
            sample_ppg_growth=avg_growth_rates.get("ppg")
        )

        return avg_growth_rates

    def identify_peak_season(
        self,
        seasons: List[PlayerSeasonStats]
    ) -> Tuple[PlayerSeasonStats, float]:
        """
        Identify best performing season using weighted composite score.

        Composite score formula (0-100 scale):
        - PPG: 30% weight (normalized to 0-50 points)
        - TS%: 25% weight (normalized to 0-100%)
        - RPG: 20% weight (normalized to 0-20 rebounds)
        - APG: 15% weight (normalized to 0-15 assists)
        - A/TO: 10% weight (normalized to 0-5 ratio)

        Args:
            seasons: List of season stats

        Returns:
            Tuple of (peak_season, composite_score)

        Example:
            >>> peak, score = identify_peak_season(seasons)
            >>> print(f"{peak.season}: {score:.1f}")
            "2024-25: 87.3"
        """
        if not seasons:
            raise ValueError("Cannot identify peak season with empty seasons list")

        best_season = None
        best_score = -1

        for season in seasons:
            # Calculate weighted composite score
            score = 0

            # PPG component (30%) - normalize to 0-50 scale
            if season.points_per_game:
                ppg_normalized = min(season.points_per_game / 50.0, 1.0)  # Max 50 PPG
                score += ppg_normalized * 30

            # TS% component (25%) - already 0-100 scale
            if season.true_shooting_percentage:
                ts_normalized = season.true_shooting_percentage / 100.0
                score += ts_normalized * 25

            # RPG component (20%) - normalize to 0-20 scale
            if season.rebounds_per_game:
                rpg_normalized = min(season.rebounds_per_game / 20.0, 1.0)  # Max 20 RPG
                score += rpg_normalized * 20

            # APG component (15%) - normalize to 0-15 scale
            if season.assists_per_game:
                apg_normalized = min(season.assists_per_game / 15.0, 1.0)  # Max 15 APG
                score += apg_normalized * 15

            # A/TO component (10%) - normalize to 0-5 scale
            if season.assist_to_turnover_ratio:
                ato_normalized = min(season.assist_to_turnover_ratio / 5.0, 1.0)  # Max 5.0 ratio
                score += ato_normalized * 10

            if score > best_score:
                best_score = score
                best_season = season

        self.logger.debug(
            "Peak season identified",
            season=best_season.season if best_season else None,
            score=round(best_score, 2)
        )

        return best_season, best_score

    def _calculate_career_averages(
        self,
        seasons: List[PlayerSeasonStats]
    ) -> Dict[str, float]:
        """
        Calculate career-wide averages across all seasons.

        Weighted by games played in each season.

        Args:
            seasons: List of season stats

        Returns:
            Dict of career averages
        """
        if not seasons:
            return {}

        # Collect all values for each metric
        total_games = sum(s.games_played or 0 for s in seasons)

        if total_games == 0:
            self.logger.warning("No games played data available for career averages")
            # Fall back to simple averaging
            ppg_vals = [s.points_per_game for s in seasons if s.points_per_game]
            rpg_vals = [s.rebounds_per_game for s in seasons if s.rebounds_per_game]
            apg_vals = [s.assists_per_game for s in seasons if s.assists_per_game]
            ts_vals = [s.true_shooting_percentage for s in seasons if s.true_shooting_percentage]
            efg_vals = [s.effective_field_goal_percentage for s in seasons if s.effective_field_goal_percentage]

            return {
                "ppg": round(mean(ppg_vals), 2) if ppg_vals else None,
                "rpg": round(mean(rpg_vals), 2) if rpg_vals else None,
                "apg": round(mean(apg_vals), 2) if apg_vals else None,
                "ts_pct": round(mean(ts_vals), 2) if ts_vals else None,
                "efg_pct": round(mean(efg_vals), 2) if efg_vals else None,
            }

        # Weight by games played
        weighted_ppg = sum((s.points_per_game or 0) * (s.games_played or 0) for s in seasons) / total_games
        weighted_rpg = sum((s.rebounds_per_game or 0) * (s.games_played or 0) for s in seasons) / total_games
        weighted_apg = sum((s.assists_per_game or 0) * (s.games_played or 0) for s in seasons) / total_games
        weighted_ts = sum((s.true_shooting_percentage or 0) * (s.games_played or 0) for s in seasons) / total_games
        weighted_efg = sum((s.effective_field_goal_percentage or 0) * (s.games_played or 0) for s in seasons) / total_games

        return {
            "ppg": round(weighted_ppg, 2),
            "rpg": round(weighted_rpg, 2),
            "apg": round(weighted_apg, 2),
            "ts_pct": round(weighted_ts, 2),
            "efg_pct": round(weighted_efg, 2),
            "games_played": total_games
        }

    def _calculate_consistency_metrics(
        self,
        seasons: List[PlayerSeasonStats]
    ) -> Dict[str, float]:
        """
        Calculate consistency/variance metrics across seasons.

        Metrics:
        - Standard deviation (absolute variance)
        - Coefficient of variation (relative variance, %)

        Lower values = more consistent performance

        Args:
            seasons: List of season stats

        Returns:
            Dict with std_dev and coef_variation for key metrics
        """
        if len(seasons) < 2:
            return {}

        consistency = {}

        # PPG consistency
        ppg_vals = [s.points_per_game for s in seasons if s.points_per_game]
        if len(ppg_vals) >= 2:
            ppg_mean = mean(ppg_vals)
            ppg_std = stdev(ppg_vals)
            consistency["ppg_std_dev"] = round(ppg_std, 2)
            consistency["ppg_coef_variation"] = round((ppg_std / ppg_mean * 100) if ppg_mean > 0 else 0, 2)

        # TS% consistency
        ts_vals = [s.true_shooting_percentage for s in seasons if s.true_shooting_percentage]
        if len(ts_vals) >= 2:
            ts_mean = mean(ts_vals)
            ts_std = stdev(ts_vals)
            consistency["ts_pct_std_dev"] = round(ts_std, 2)
            consistency["ts_pct_coef_variation"] = round((ts_std / ts_mean * 100) if ts_mean > 0 else 0, 2)

        return consistency

    def calculate_trajectory(
        self,
        growth_rates: Dict[str, float]
    ) -> str:
        """
        Determine career trajectory based on growth rates.

        Classifications:
        - RAPIDLY_IMPROVING: Avg growth > 15%
        - IMPROVING: Avg growth 5-15%
        - STABLE: Avg growth -5% to 5%
        - DECLINING: Avg growth < -5%

        Weighted average prioritizes:
        - PPG: 40%
        - TS%: 30%
        - APG: 20%
        - Other: 10%

        Args:
            growth_rates: Dict of YoY growth rates by metric

        Returns:
            Trajectory classification string

        Example:
            >>> calculate_trajectory({"ppg": 18.5, "ts_pct": 12.3, "apg": 8.1})
            "RAPIDLY_IMPROVING"
        """
        if not growth_rates:
            return "UNKNOWN"

        # Calculate weighted average growth
        weights = {
            "ppg": 0.40,
            "ts_pct": 0.30,
            "apg": 0.20,
            "efg_pct": 0.05,
            "rpg": 0.05
        }

        weighted_growth = 0
        total_weight = 0

        for metric, weight in weights.items():
            if metric in growth_rates:
                weighted_growth += growth_rates[metric] * weight
                total_weight += weight

        if total_weight == 0:
            # Fall back to simple average
            avg_growth = mean(growth_rates.values())
        else:
            avg_growth = weighted_growth / total_weight

        # Classify trajectory
        if avg_growth > 15:
            trajectory = "RAPIDLY_IMPROVING"
        elif avg_growth > 5:
            trajectory = "IMPROVING"
        elif avg_growth > -5:
            trajectory = "STABLE"
        else:
            trajectory = "DECLINING"

        self.logger.debug(
            "Trajectory calculated",
            avg_growth=round(avg_growth, 2),
            trajectory=trajectory
        )

        return trajectory
