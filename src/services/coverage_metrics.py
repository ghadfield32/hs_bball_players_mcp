"""
Coverage Metrics Service

Measures actual data coverage per player for forecasting pipelines.

Converts coverage from a "design score" to a "runtime metric" computed over real players.
Tracks which critical predictors are present/missing and generates weighted coverage scores.

Author: Claude Code
Date: 2025-11-15
Methodology: 8-Step Coverage Measurement Plan (Step 1)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class CoverageFlags:
    """
    Per-player coverage flags tracking presence of critical forecasting predictors.

    Coverage is organized by importance to forecasting model:
    - Tier 1 (Critical): 247 ratings, offers, advanced stats (60% weight)
    - Tier 2 (Important): Physical, age, multi-season (30% weight)
    - Tier 3 (Supplemental): Context, competition level (10% weight)

    Missing reasons track WHY data is unavailable (for imputation decisions).
    """

    # ===== TIER 1: CRITICAL FORECASTING PREDICTORS (60% weight) =====

    # Recruiting Metrics (TOP predictors: 37% combined)
    has_composite_247: bool = False  # 247Sports composite rating (15% importance)
    has_stars: bool = False  # Star rating (12% importance)
    has_power6_offers: bool = False  # Power 6 conference offer count (10% importance)

    # Advanced Efficiency Stats (23% combined)
    has_ts_pct: bool = False  # True shooting % (8% importance)
    has_efg_pct: bool = False  # Effective FG % (7% importance)
    has_ato_ratio: bool = False  # Assist-to-turnover ratio (6% importance)
    has_usage_rate: bool = False  # Usage rate (2% importance - calculated if have stats)

    # ===== TIER 2: IMPORTANT FEATURES (30% weight) =====

    # Development Context (15% combined)
    has_age_for_grade: bool = False  # Age-for-grade (maturity indicator) (10% importance)
    has_multi_season: bool = False  # Multiple seasons of data (progression) (5% importance)

    # Physical Measurements (10% combined)
    has_birth_date: bool = False  # Exact age calculation (5% importance)
    has_physical_measurements: bool = False  # Height + Weight (5% importance)

    # Competition Context (5%)
    has_maxpreps_stats: bool = False  # State-level stats (2% importance)
    has_recruiting_profile: bool = False  # Full recruiting write-up (3% importance)

    # ===== TIER 3: SUPPLEMENTAL CONTEXT (10% weight) =====

    # International Context (for Euro/World players)
    has_fiba_youth_or_angt: bool = False  # FIBA/ANGT stats (5% importance)
    has_eurobasket_profile: bool = False  # International profile (2% importance)

    # High School Context
    has_school_info: bool = False  # HS name, city, state (2% importance)
    has_position: bool = False  # Position (1% importance)

    # ===== MISSING REASONS (for imputation decisions) =====

    missing_247_profile: bool = False  # Not in 247Sports database
    missing_maxpreps_data: bool = False  # Not in state leaderboards
    missing_multi_season_data: bool = False  # Only one season available
    missing_recruiting_coverage: bool = False  # No recruiting services coverage
    missing_international_data: bool = False  # No FIBA/ANGT data
    missing_advanced_stats: bool = False  # No TS%, eFG%, A/TO, or usage rate

    # Player segment (for coverage reporting)
    player_segment: Optional[str] = None  # "US_HS" | "Europe" | "Canada" | "Other"

    # Raw counts (for debugging)
    total_stats_seasons: int = 0
    total_recruiting_sources: int = 0
    total_data_sources: int = 0


@dataclass
class CoverageScore:
    """
    Coverage score result with breakdown by tier and segment.

    overall_score: Weighted coverage (0-100)
    tier_scores: Breakdown by importance tier
    missing_critical: List of missing critical predictors
    coverage_level: Classification (EXCELLENT/GOOD/FAIR/POOR)
    """

    overall_score: float  # 0-100
    tier1_score: float  # Critical predictors (0-100)
    tier2_score: float  # Important features (0-100)
    tier3_score: float  # Supplemental context (0-100)

    missing_critical: List[str] = field(default_factory=list)  # Missing Tier 1 predictors
    missing_important: List[str] = field(default_factory=list)  # Missing Tier 2 features

    coverage_level: str = "UNKNOWN"  # EXCELLENT (>85) | GOOD (70-85) | FAIR (50-70) | POOR (<50)

    # Detailed breakdown
    recruiting_score: float = 0.0  # 247 + offers coverage
    efficiency_score: float = 0.0  # Advanced stats coverage
    development_score: float = 0.0  # Age + multi-season coverage
    physical_score: float = 0.0  # Bio measurements coverage
    competition_score: float = 0.0  # MaxPreps + recruiting profile coverage
    international_score: float = 0.0  # FIBA/ANGT coverage


def compute_coverage_score(flags: CoverageFlags) -> CoverageScore:
    """
    Compute weighted coverage score based on forecasting importance.

    Weights match actual ML model feature importance from forecasting research:
    - Tier 1 (Critical): 60% - Recruiting metrics (37%) + Advanced stats (23%)
    - Tier 2 (Important): 30% - Development context (15%) + Physical (10%) + Competition (5%)
    - Tier 3 (Supplemental): 10% - International (5%) + HS context (5%)

    Args:
        flags: CoverageFlags for a single player

    Returns:
        CoverageScore with overall score (0-100) and breakdowns
    """

    # ===== TIER 1: CRITICAL PREDICTORS (60% weight) =====

    # Recruiting Metrics (37% of total)
    recruiting_components = []
    recruiting_weights = []

    if flags.has_composite_247:
        recruiting_components.append(1.0)
    else:
        recruiting_components.append(0.0)
    recruiting_weights.append(15.0)  # 15% importance

    if flags.has_stars:
        recruiting_components.append(1.0)
    else:
        recruiting_components.append(0.0)
    recruiting_weights.append(12.0)  # 12% importance

    if flags.has_power6_offers:
        recruiting_components.append(1.0)
    else:
        recruiting_components.append(0.0)
    recruiting_weights.append(10.0)  # 10% importance

    recruiting_score = sum(c * w for c, w in zip(recruiting_components, recruiting_weights))
    recruiting_max = sum(recruiting_weights)
    recruiting_pct = (recruiting_score / recruiting_max * 100) if recruiting_max > 0 else 0.0

    # Advanced Efficiency Stats (23% of total)
    efficiency_components = []
    efficiency_weights = []

    if flags.has_ts_pct:
        efficiency_components.append(1.0)
    else:
        efficiency_components.append(0.0)
    efficiency_weights.append(8.0)  # 8% importance

    if flags.has_efg_pct:
        efficiency_components.append(1.0)
    else:
        efficiency_components.append(0.0)
    efficiency_weights.append(7.0)  # 7% importance

    if flags.has_ato_ratio:
        efficiency_components.append(1.0)
    else:
        efficiency_components.append(0.0)
    efficiency_weights.append(6.0)  # 6% importance

    if flags.has_usage_rate:
        efficiency_components.append(1.0)
    else:
        efficiency_components.append(0.0)
    efficiency_weights.append(2.0)  # 2% importance

    efficiency_score = sum(c * w for c, w in zip(efficiency_components, efficiency_weights))
    efficiency_max = sum(efficiency_weights)
    efficiency_pct = (efficiency_score / efficiency_max * 100) if efficiency_max > 0 else 0.0

    # Tier 1 Total (60% of overall)
    tier1_score = (recruiting_score + efficiency_score) / (recruiting_max + efficiency_max) * 100
    tier1_weight = 60.0

    # Track missing critical predictors
    missing_critical = []
    if not flags.has_composite_247:
        missing_critical.append("247_composite_rating")
    if not flags.has_stars:
        missing_critical.append("star_rating")
    if not flags.has_power6_offers:
        missing_critical.append("power6_offers")
    if not flags.has_ts_pct:
        missing_critical.append("true_shooting_pct")
    if not flags.has_efg_pct:
        missing_critical.append("effective_fg_pct")
    if not flags.has_ato_ratio:
        missing_critical.append("assist_to_turnover_ratio")

    # ===== TIER 2: IMPORTANT FEATURES (30% weight) =====

    # Development Context (15% of total)
    development_components = []
    development_weights = []

    if flags.has_age_for_grade:
        development_components.append(1.0)
    else:
        development_components.append(0.0)
    development_weights.append(10.0)  # 10% importance

    if flags.has_multi_season:
        development_components.append(1.0)
    else:
        development_components.append(0.0)
    development_weights.append(5.0)  # 5% importance

    development_score = sum(c * w for c, w in zip(development_components, development_weights))
    development_max = sum(development_weights)
    development_pct = (development_score / development_max * 100) if development_max > 0 else 0.0

    # Physical Measurements (10% of total)
    physical_components = []
    physical_weights = []

    if flags.has_birth_date:
        physical_components.append(1.0)
    else:
        physical_components.append(0.0)
    physical_weights.append(5.0)  # 5% importance

    if flags.has_physical_measurements:
        physical_components.append(1.0)
    else:
        physical_components.append(0.0)
    physical_weights.append(5.0)  # 5% importance

    physical_score = sum(c * w for c, w in zip(physical_components, physical_weights))
    physical_max = sum(physical_weights)
    physical_pct = (physical_score / physical_max * 100) if physical_max > 0 else 0.0

    # Competition Context (5% of total)
    competition_components = []
    competition_weights = []

    if flags.has_maxpreps_stats:
        competition_components.append(1.0)
    else:
        competition_components.append(0.0)
    competition_weights.append(2.0)  # 2% importance

    if flags.has_recruiting_profile:
        competition_components.append(1.0)
    else:
        competition_components.append(0.0)
    competition_weights.append(3.0)  # 3% importance

    competition_score = sum(c * w for c, w in zip(competition_components, competition_weights))
    competition_max = sum(competition_weights)
    competition_pct = (competition_score / competition_max * 100) if competition_max > 0 else 0.0

    # Tier 2 Total (30% of overall)
    tier2_score = (development_score + physical_score + competition_score) / \
                  (development_max + physical_max + competition_max) * 100
    tier2_weight = 30.0

    # Track missing important features
    missing_important = []
    if not flags.has_age_for_grade:
        missing_important.append("age_for_grade")
    if not flags.has_multi_season:
        missing_important.append("multi_season_data")
    if not flags.has_birth_date:
        missing_important.append("birth_date")
    if not flags.has_physical_measurements:
        missing_important.append("height_weight")

    # ===== TIER 3: SUPPLEMENTAL CONTEXT (10% weight) =====

    # International Context (5% of total)
    international_components = []
    international_weights = []

    if flags.has_fiba_youth_or_angt:
        international_components.append(1.0)
    else:
        international_components.append(0.0)
    international_weights.append(5.0)  # 5% importance

    if flags.has_eurobasket_profile:
        international_components.append(1.0)
    else:
        international_components.append(0.0)
    international_weights.append(2.0)  # 2% importance

    international_score = sum(c * w for c, w in zip(international_components, international_weights))
    international_max = sum(international_weights)
    international_pct = (international_score / international_max * 100) if international_max > 0 else 0.0

    # High School Context (5% of total)
    hs_context_components = []
    hs_context_weights = []

    if flags.has_school_info:
        hs_context_components.append(1.0)
    else:
        hs_context_components.append(0.0)
    hs_context_weights.append(2.0)  # 2% importance

    if flags.has_position:
        hs_context_components.append(1.0)
    else:
        hs_context_components.append(0.0)
    hs_context_weights.append(1.0)  # 1% importance

    hs_context_score = sum(c * w for c, w in zip(hs_context_components, hs_context_weights))
    hs_context_max = sum(hs_context_weights)

    # Tier 3 Total (10% of overall)
    tier3_score = (international_score + hs_context_score) / \
                  (international_max + hs_context_max) * 100
    tier3_weight = 10.0

    # ===== OVERALL WEIGHTED SCORE =====

    overall_score = (
        (tier1_score * tier1_weight / 100.0) +
        (tier2_score * tier2_weight / 100.0) +
        (tier3_score * tier3_weight / 100.0)
    )

    # Classify coverage level
    if overall_score >= 85:
        coverage_level = "EXCELLENT"
    elif overall_score >= 70:
        coverage_level = "GOOD"
    elif overall_score >= 50:
        coverage_level = "FAIR"
    else:
        coverage_level = "POOR"

    return CoverageScore(
        overall_score=round(overall_score, 2),
        tier1_score=round(tier1_score, 2),
        tier2_score=round(tier2_score, 2),
        tier3_score=round(tier3_score, 2),
        missing_critical=missing_critical,
        missing_important=missing_important,
        coverage_level=coverage_level,
        recruiting_score=round(recruiting_pct, 2),
        efficiency_score=round(efficiency_pct, 2),
        development_score=round(development_pct, 2),
        physical_score=round(physical_pct, 2),
        competition_score=round(competition_pct, 2),
        international_score=round(international_pct, 2),
    )


def extract_coverage_flags_from_profile(profile: Dict[str, Any]) -> CoverageFlags:
    """
    Extract CoverageFlags from a ForecastingDataAggregator profile.

    Args:
        profile: Profile dict from get_comprehensive_player_profile()

    Returns:
        CoverageFlags with presence/absence of each predictor
    """

    flags = CoverageFlags()

    # ===== TIER 1: CRITICAL PREDICTORS =====

    # Recruiting metrics
    flags.has_composite_247 = profile.get("composite_247_rating") is not None
    flags.has_stars = profile.get("stars_247") is not None and profile.get("stars_247", 0) > 0
    flags.has_power6_offers = profile.get("power_6_offer_count", 0) > 0

    # Advanced efficiency stats
    flags.has_ts_pct = profile.get("best_ts_pct") is not None
    flags.has_efg_pct = profile.get("best_efg_pct") is not None
    flags.has_ato_ratio = profile.get("best_ato_ratio") is not None
    flags.has_usage_rate = profile.get("best_usage_rate") is not None  # May be added later

    # ===== TIER 2: IMPORTANT FEATURES =====

    # Development context
    flags.has_age_for_grade = profile.get("age_for_grade") is not None

    # Multi-season: Check if we have stats from multiple years
    raw_stats = profile.get("raw_stats", [])
    unique_seasons = set()
    for stat in raw_stats:
        season = getattr(stat, 'season', None)
        if season:
            unique_seasons.add(season)
    flags.has_multi_season = len(unique_seasons) >= 2
    flags.total_stats_seasons = len(unique_seasons)

    # Physical measurements
    flags.has_birth_date = profile.get("birth_date") is not None
    has_height = profile.get("height") is not None
    has_weight = profile.get("weight") is not None
    flags.has_physical_measurements = has_height and has_weight

    # Competition context
    # MaxPreps stats: Check if any stats are from MaxPreps
    has_maxpreps = False
    for stat in raw_stats:
        data_source = getattr(stat, 'data_source', None)
        if data_source and 'maxpreps' in str(data_source).lower():
            has_maxpreps = True
            break
    flags.has_maxpreps_stats = has_maxpreps

    # Recruiting profile: Check if we have 247Sports profile data
    raw_players = profile.get("raw_players", [])
    has_recruiting_profile = False
    recruiting_sources = 0
    for player in raw_players:
        data_source = getattr(player, 'data_source', None)
        if data_source:
            source_str = str(data_source).lower()
            if '247' in source_str or 'rivals' in source_str or 'espn' in source_str:
                has_recruiting_profile = True
                recruiting_sources += 1
    flags.has_recruiting_profile = has_recruiting_profile
    flags.total_recruiting_sources = recruiting_sources

    # ===== TIER 3: SUPPLEMENTAL CONTEXT =====

    # International context
    circuits = profile.get("circuits_played", [])
    has_intl = any(c in ['FIBA', 'ANGT', 'Euroleague'] for c in circuits)
    flags.has_fiba_youth_or_angt = has_intl

    # Check for EuroBasket profiles
    has_eurobasket = False
    for player in raw_players:
        data_source = getattr(player, 'data_source', None)
        if data_source and 'eurobasket' in str(data_source).lower():
            has_eurobasket = True
            break
    flags.has_eurobasket_profile = has_eurobasket

    # High school context
    flags.has_school_info = profile.get("school_name") is not None
    flags.has_position = profile.get("position") is not None

    # ===== MISSING REASONS =====

    flags.missing_247_profile = not flags.has_composite_247 and not has_recruiting_profile
    flags.missing_maxpreps_data = not has_maxpreps
    flags.missing_multi_season_data = len(unique_seasons) < 2
    flags.missing_recruiting_coverage = recruiting_sources == 0
    flags.missing_international_data = not has_intl and not has_eurobasket
    flags.missing_advanced_stats = not (flags.has_ts_pct or flags.has_efg_pct or flags.has_ato_ratio or flags.has_usage_rate)

    # ===== PLAYER SEGMENT =====

    # Determine segment based on data sources and location
    state = profile.get("state")
    country = profile.get("country")

    if state and country == "USA":
        flags.player_segment = "US_HS"
    elif country in ["Spain", "France", "Germany", "Italy", "Greece", "Serbia", "Croatia", "Lithuania"]:
        flags.player_segment = "Europe"
    elif country == "Canada":
        flags.player_segment = "Canada"
    else:
        flags.player_segment = "Other"

    # Total data sources
    flags.total_data_sources = len(raw_players) + len(raw_stats)

    return flags


def get_coverage_summary(scores: List[CoverageScore]) -> Dict[str, Any]:
    """
    Aggregate coverage scores across multiple players.

    Args:
        scores: List of CoverageScore objects

    Returns:
        Summary dict with mean, median, distribution by level
    """

    if not scores:
        return {
            "total_players": 0,
            "mean_coverage": 0.0,
            "median_coverage": 0.0,
            "distribution": {},
        }

    overall_scores = [s.overall_score for s in scores]

    # Calculate statistics
    mean_coverage = sum(overall_scores) / len(overall_scores)
    sorted_scores = sorted(overall_scores)
    median_coverage = sorted_scores[len(sorted_scores) // 2]

    # Distribution by level
    distribution = {
        "EXCELLENT": sum(1 for s in scores if s.coverage_level == "EXCELLENT"),
        "GOOD": sum(1 for s in scores if s.coverage_level == "GOOD"),
        "FAIR": sum(1 for s in scores if s.coverage_level == "FAIR"),
        "POOR": sum(1 for s in scores if s.coverage_level == "POOR"),
    }

    # Tier breakdowns
    tier1_scores = [s.tier1_score for s in scores]
    tier2_scores = [s.tier2_score for s in scores]
    tier3_scores = [s.tier3_score for s in scores]

    mean_tier1 = sum(tier1_scores) / len(tier1_scores)
    mean_tier2 = sum(tier2_scores) / len(tier2_scores)
    mean_tier3 = sum(tier3_scores) / len(tier3_scores)

    # Most common missing critical predictors
    all_missing_critical = []
    for score in scores:
        all_missing_critical.extend(score.missing_critical)

    missing_counts = {}
    for predictor in all_missing_critical:
        missing_counts[predictor] = missing_counts.get(predictor, 0) + 1

    top_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_players": len(scores),
        "mean_coverage": round(mean_coverage, 2),
        "median_coverage": round(median_coverage, 2),
        "min_coverage": round(min(overall_scores), 2),
        "max_coverage": round(max(overall_scores), 2),
        "distribution": distribution,
        "distribution_pct": {
            level: round(count / len(scores) * 100, 1)
            for level, count in distribution.items()
        },
        "tier_averages": {
            "tier1_critical": round(mean_tier1, 2),
            "tier2_important": round(mean_tier2, 2),
            "tier3_supplemental": round(mean_tier3, 2),
        },
        "top_missing_predictors": [
            {"predictor": pred, "missing_count": count, "missing_pct": round(count / len(scores) * 100, 1)}
            for pred, count in top_missing
        ],
    }
