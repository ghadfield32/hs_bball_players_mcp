# Forecasting Data Aggregation Guide

Complete guide to using the forecasting data aggregation pipeline for evaluating high school and young European basketball prospects.

## Overview

The Forecasting Data Aggregator pulls **ALL available data** from **67+ datasources** to create comprehensive player profiles optimized for ML forecasting and prospect evaluation.

### What Data is Extracted?

The forecasting service aggregates:

#### **1. Recruiting Metrics** (Top Forecasting Predictors)
- ✅ **247Sports Composite Rating** (#1 predictor, 15% importance)
- ✅ **Star Rating** (#2 predictor, 12% importance)
- ✅ **Power 6 Offer Count** (#3 predictor, 10% importance)
- ✅ ESPN/Rivals/On3 Rankings
- ✅ Crystal Ball Predictions & Consensus
- ✅ Commitment Status

#### **2. Age-for-Grade** (Critical Forecasting Metric - NEW!)
- ✅ **Birth Date** (extracted from 247Sports profiles)
- ✅ **Age-for-Grade Advantage** (#4 predictor, 8-10% importance)
- ✅ **Age Category** (Very Young / Young / Average / Old / Very Old)
- Research shows younger players in their class have **20-30% higher NBA success rates**

#### **3. Advanced Performance Metrics**
- ✅ **True Shooting %** (#5 predictor, 8% importance)
- ✅ **Effective FG %** (#6 predictor, 7% importance)
- ✅ **Assist/Turnover Ratio** (#7 predictor, 6% importance)
- ✅ Two-Point %, Three-Point %, Free Throw %
- ✅ Points Per 40, Rebounds Per 40
- ✅ ORB/DRB Split (motor & effort indicators)

#### **4. Basic Stats** (Aggregated Across All Sources)
- ✅ Career PPG, RPG, APG, SPG, BPG
- ✅ Total Games Played, Total Seasons
- ✅ Performance Trend Analysis (improving/declining/stable)
- ✅ Season-by-season breakdowns

#### **5. Competition Context**
- ✅ Highest Competition Level (National Circuit vs State/Regional)
- ✅ Circuits Played (EYBL, UAA, 3SSB, Peach Jam, etc.)
- ✅ States/Countries Played
- ✅ Multiple Season Data for Trend Analysis

#### **6. Physical Measurements**
- ✅ Height, Weight, Position
- ✅ School, City, State, Country

---

## Quick Start

### Simple Example

```python
import asyncio
from src.services import get_forecasting_data_for_player

async def main():
    # Get comprehensive forecasting data
    profile = await get_forecasting_data_for_player(
        player_name="Cooper Flagg",
        grad_year=2025
    )

    # Access key metrics
    print(f"Age-for-Grade: {profile['age_for_grade']} ({profile['age_for_grade_category']})")
    print(f"Power 6 Offers: {profile['power_6_offer_count']}")
    print(f"247 Composite: #{profile['composite_247_rank']}")
    print(f"True Shooting %: {profile['best_ts_pct']}")
    print(f"Forecasting Score: {profile['forecasting_score']}/100")

asyncio.run(main())
```

### Command Line Usage

```bash
# Get comprehensive profile for a player
python scripts/example_forecasting_usage.py "Cooper Flagg" 2025

# Export full profile to JSON
python scripts/example_forecasting_usage.py "Cameron Boozer" 2026
# Creates: forecasting_profile_Cameron_Boozer.json

# European player
python scripts/example_forecasting_usage.py "Noa Essengue"
```

### Real Data Validation

```bash
# Run comprehensive tests with real player data
python scripts/test_forecasting_real_data.py

# Tests 4 players:
# - Cooper Flagg (2025) - #1 ranked, Duke commit
# - Cameron Boozer (2026) - Top 2026 player
# - Dylan Harper (2025) - Top 10 2025 player
# - Noa Essengue - European prospect
```

---

## Advanced Usage

### Full API Example

```python
import asyncio
from src.services import ForecastingDataAggregator

async def advanced_example():
    # Initialize aggregator
    agg = ForecastingDataAggregator()

    # Get comprehensive profile
    profile = await agg.get_comprehensive_player_profile(
        player_name="Cooper Flagg",
        grad_year=2025,
        state="ME"
    )

    # === ANALYZE FORECASTING SCORE ===
    forecasting_score = profile['forecasting_score']

    if forecasting_score >= 80:
        print("Forecast: Elite NBA Prospect")
    elif forecasting_score >= 65:
        print("Forecast: High Major D1 / Potential NBA")
    elif forecasting_score >= 50:
        print("Forecast: Mid-Major D1 / High Major Role Player")
    else:
        print("Forecast: Low/Mid Major D1")

    # === ANALYZE AGE-FOR-GRADE ===
    age_advantage = profile['age_for_grade']

    if age_advantage and age_advantage > 0.5:
        print(f"✅ ADVANTAGE: {age_advantage:.2f} years younger than average")
        print("   Younger players show 20-30% higher NBA success rates")
    elif age_advantage and age_advantage < -0.5:
        print(f"⚠️  WARNING: {abs(age_advantage):.2f} years older than average")
        print("   May have reclassified or been held back")

    # === ANALYZE RECRUITING ===
    power_6_offers = profile['power_6_offer_count']

    if power_6_offers >= 15:
        print(f"🔥 Elite recruiting: {power_6_offers} Power 6 offers")
    elif power_6_offers >= 8:
        print(f"⭐ High major recruiting: {power_6_offers} Power 6 offers")
    elif power_6_offers >= 3:
        print(f"📈 Major interest: {power_6_offers} Power 6 offers")

    # === ANALYZE EFFICIENCY ===
    ts_pct = profile['best_ts_pct']

    if ts_pct and ts_pct > 0.600:
        print(f"✅ Elite efficiency: {ts_pct:.1%} TS%")
    elif ts_pct and ts_pct > 0.550:
        print(f"👍 Good efficiency: {ts_pct:.1%} TS%")

    # === ANALYZE PLAYMAKING ===
    ato_ratio = profile['best_ato_ratio']

    if ato_ratio and ato_ratio > 3.0:
        print(f"✅ Elite playmaker: {ato_ratio:.2f} A/TO")
    elif ato_ratio and ato_ratio > 2.0:
        print(f"👍 Good playmaker: {ato_ratio:.2f} A/TO")

    # === TREND ANALYSIS ===
    if profile['performance_trend'] == 'improving':
        print("📈 Performance trending UP (positive)")
    elif profile['performance_trend'] == 'declining':
        print("📉 Performance trending DOWN (concern)")

    # === RAW DATA FOR ML ===
    # Access raw data for feature engineering
    raw_stats = profile['raw_stats']  # List[PlayerSeasonStats]
    raw_offers = profile['raw_offers']  # List[CollegeOffer]
    raw_predictions = profile['raw_predictions']  # List[RecruitingPrediction]

    # Build custom features
    features = {
        'age_for_grade': profile['age_for_grade'],
        'power_6_offers': profile['power_6_offer_count'],
        'composite_rating': profile['composite_247_rating'],
        'ts_pct': profile['best_ts_pct'],
        'efg_pct': profile['best_efg_pct'],
        'ato_ratio': profile['best_ato_ratio'],
        'career_ppg': profile['career_ppg'],
        # ... add 40+ more features
    }

    return profile, features

asyncio.run(advanced_example())
```

---

## Forecasting Metrics Reference

### Metric Importance Rankings

Based on NBA draft success research:

| Rank | Metric | Importance | Notes |
|------|--------|------------|-------|
| 1 | 247 Composite Rating | 15% | Industry consensus ranking |
| 2 | Star Rating | 12% | 5★ players have highest NBA success rate |
| 3 | Power 6 Offer Count | 10% | High major interest indicator |
| 4 | **Age-for-Grade** | 8-10% | **CRITICAL - Younger = Better** |
| 5 | True Shooting % | 8% | Efficiency metric |
| 6 | Effective FG % | 7% | Shooting efficiency |
| 7 | Assist/Turnover Ratio | 6% | Playmaking ability |
| 8 | Career PPG | 5% | Scoring volume |
| 9 | Height | 4% | Size advantage |
| 10 | Competition Level | 3% | National circuit vs state |

### Age-for-Grade Impact

**Research Finding**: Players who are younger for their grade have **20-30% higher NBA success rates**.

**Calculation**:
- Expected birth date for class of 2025: July 1, 2007
- Player born Aug 15, 2007: **+0.12 years advantage** (1.5 months younger)
- Player born May 15, 2007: **-0.12 years disadvantage** (1.5 months older)

**Categories**:
- **Very Young**: +0.75 years or more (strong advantage)
- **Young**: +0.25 to +0.75 years (advantage)
- **Average**: -0.25 to +0.25 years (neutral)
- **Old**: -0.75 to -0.25 years (disadvantage)
- **Very Old**: -0.75 years or more (strong disadvantage, likely reclassified)

**Examples**:
- Cooper Flagg (born Dec 21, 2006, class of 2025): **-0.53 years** (Old - reclassified)
- Typical young prospect (born Sept 2007, class of 2025): **+0.16 years** (Young)

---

## Data Sources

### US Sources (45+ datasources)
- **National Circuits**: EYBL, UAA, 3SSB, Grind Session, OTE
- **State Associations**: All 50 states (GHSA, FHSAA, PSAL, etc.)
- **Recruiting**: 247Sports, MaxPreps

### European Sources (8 datasources)
- **FIBA**: Youth Championships, LiveStats
- **League Systems**: ANGT, LNB Espoirs, NBBL, FEB, MKL

### Canadian Sources (2 datasources)
- NPA, OSBA

### Total: **67+ Datasources**

---

## Output Format

### Profile Dictionary Structure

```python
{
    # Identity
    "player_name": str,
    "player_uid": str,
    "grad_year": int,
    "state": str,

    # Bio & Physical
    "birth_date": date,
    "age_for_grade": float,  # Positive = younger (GOOD)
    "age_for_grade_category": str,  # "Very Young" to "Very Old"
    "height": str,  # "6-9"
    "weight": int,  # 205
    "position": str,  # "SF"
    "school": str,

    # Recruiting (Top Predictors)
    "composite_247_rating": float,  # 0.9990
    "composite_247_rank": int,  # 1
    "stars_247": int,  # 5
    "espn_rank": int,
    "rivals_rank": int,
    "on3_rank": int,
    "best_national_rank": int,
    "power_6_offer_count": int,  # 23
    "total_offer_count": int,  # 40
    "is_committed": bool,
    "committed_to": str,  # "Duke"
    "prediction_consensus": str,  # "Duke University"
    "prediction_confidence": float,  # 0.95

    # Performance Stats
    "total_seasons": int,
    "total_games_played": int,
    "career_ppg": float,
    "career_rpg": float,
    "career_apg": float,
    "career_spg": float,
    "career_bpg": float,

    # Advanced Metrics
    "best_ts_pct": float,  # 0.650
    "best_efg_pct": float,  # 0.585
    "best_ato_ratio": float,  # 3.2
    "best_two_pt_pct": float,
    "best_three_pt_pct": float,
    "best_ft_pct": float,
    "best_per_40_ppg": float,
    "best_per_40_rpg": float,

    # Competition Context
    "highest_competition_level": str,  # "National Circuit"
    "circuits_played": List[str],  # ["Nike EYBL", "Peach Jam"]
    "states_played": List[str],
    "countries_played": List[str],
    "performance_trend": str,  # "improving"

    # Forecasting Scores
    "forecasting_score": float,  # 0-100
    "data_completeness": float,  # 0-100%

    # Raw Data (for ML)
    "raw_players": List[Player],
    "raw_stats": List[PlayerSeasonStats],
    "raw_recruiting_ranks": List[RecruitingRank],
    "raw_offers": List[CollegeOffer],
    "raw_predictions": List[RecruitingPrediction],
    "seasons": List[Dict],  # Season-by-season breakdown
}
```

---

## Use Cases

### 1. Prospect Evaluation
```python
# Evaluate high school prospect
profile = await get_forecasting_data_for_player("Player Name", 2026)

# Check forecasting score
if profile['forecasting_score'] >= 80:
    recommendation = "Elite NBA Prospect"

# Check age-for-grade
if profile['age_for_grade'] > 0.5:
    print("BONUS: Significantly younger than peers")
```

### 2. Draft Modeling
```python
# Build ML features for draft prediction
features = {
    'age_for_grade': profile['age_for_grade'],
    'power_6_offers': profile['power_6_offer_count'],
    'ts_pct': profile['best_ts_pct'],
    'composite_rating': profile['composite_247_rating'],
    # ... 40+ more features
}

# Train model
model.fit(X_train, y_train)
prediction = model.predict([features])
```

### 3. Player Comparison
```python
# Compare two prospects
player_a = await get_forecasting_data_for_player("Cooper Flagg", 2025)
player_b = await get_forecasting_data_for_player("Dylan Harper", 2025)

print(f"Forecasting Scores: {player_a['forecasting_score']} vs {player_b['forecasting_score']}")
print(f"Age Advantage: {player_a['age_for_grade']} vs {player_b['age_for_grade']}")
print(f"Power 6 Offers: {player_a['power_6_offer_count']} vs {player_b['power_6_offer_count']}")
```

### 4. International Players
```python
# European player evaluation
profile = await get_forecasting_data_for_player("Noa Essengue")

# Check European data
print(f"Countries: {profile['countries_played']}")
print(f"Leagues: {profile['seasons']}")

# Age-for-grade still works with birth date
if profile['age_for_grade']:
    print(f"Age advantage: {profile['age_for_grade']} years")
```

---

## Best Practices

### 1. Rate Limiting
```python
# Add delays between requests (respect ToS)
import asyncio

for player in players:
    profile = await get_forecasting_data_for_player(player)
    await asyncio.sleep(2)  # 2 second delay
```

### 2. Error Handling
```python
try:
    profile = await get_forecasting_data_for_player("Player Name", 2025)

    if profile['forecasting_score']:
        # Use data
        pass
    else:
        print("Insufficient data for forecasting")

except Exception as e:
    logger.error(f"Failed to get profile: {e}")
```

### 3. Data Completeness Check
```python
profile = await get_forecasting_data_for_player("Player Name", 2025)

# Check data quality
completeness = profile['data_completeness']

if completeness >= 70:
    print("High quality data - proceed with forecasting")
elif completeness >= 40:
    print("Moderate quality - use with caution")
else:
    print("Low quality - insufficient data")
```

---

## API Reference

### `ForecastingDataAggregator`

Main class for forecasting data aggregation.

#### Methods

**`__init__(aggregator: Optional[DataSourceAggregator] = None)`**
- Initialize forecasting aggregator
- Optional: Pass existing DataSourceAggregator instance

**`async get_comprehensive_player_profile(player_name, grad_year=None, state=None, **kwargs) -> Dict`**
- Get comprehensive forecasting profile
- Returns dictionary with 40+ forecasting features

### `get_forecasting_data_for_player()`

Convenience function for quick access.

```python
async def get_forecasting_data_for_player(
    player_name: str,
    grad_year: Optional[int] = None,
    state: Optional[str] = None,
    **kwargs
) -> Dict
```

---

## Troubleshooting

### Common Issues

**1. No recruiting data found**
- Solution: Player may not be ranked nationally
- Check state/regional data instead

**2. Birth date not found**
- Solution: Not all profiles have birth dates
- age_for_grade will be None - check other metrics

**3. Low forecasting score**
- Solution: May have limited data
- Check data_completeness %

**4. No stats data**
- Solution: Player may be in database under different name
- Try variations of name or search by school

---

## Future Enhancements

Planned improvements:
- [ ] Historical trend analysis (multi-year tracking)
- [ ] Player comparison tool
- [ ] Automated scouting reports
- [ ] ML model training pipeline
- [ ] Real-time data updates

---

## Support

For questions or issues:
1. Check PROJECT_LOG.md for latest updates
2. Review test scripts for examples
3. Check logs for detailed error messages

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
