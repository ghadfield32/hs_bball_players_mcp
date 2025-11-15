"""
Example: Using the Forecasting Data Aggregator

Simple example showing how to use the forecasting service to get
comprehensive player data for forecasting purposes.

This demonstrates:
1. How to get all available data for a player
2. What forecasting metrics are extracted
3. How to use the data for ML/forecasting

Usage:
    python scripts/example_forecasting_usage.py "Cooper Flagg" 2025

Author: Claude Code
Date: 2025-11-15
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services import get_forecasting_data_for_player


async def main(player_name: str, grad_year: int = None):
    """
    Get comprehensive forecasting data for a player.

    Args:
        player_name: Player name to search
        grad_year: Graduation year (optional)
    """
    print(f"\n{'='*80}")
    print(f"Forecasting Data Aggregation Example")
    print(f"Player: {player_name}")
    print(f"Grad Year: {grad_year}")
    print(f"{'='*80}\n")

    # Get comprehensive forecasting profile
    print("Fetching data from all sources...")
    profile = await get_forecasting_data_for_player(
        player_name=player_name,
        grad_year=grad_year,
    )

    # Display key forecasting metrics
    print(f"\n{'='*80}")
    print("KEY FORECASTING METRICS")
    print(f"{'='*80}\n")

    print("=== IDENTITY ===")
    print(f"  Player UID: {profile['player_uid']}")
    print(f"  Name: {profile['player_name']}")
    print(f"  School: {profile['school']}")
    print(f"  City, State: {profile['city']}, {profile['state']}")

    print("\n=== BIO & PHYSICAL (Critical for Forecasting) ===")
    print(f"  Birth Date: {profile['birth_date']}")
    print(f"  Age-for-Grade: {profile['age_for_grade']} years ({profile['age_for_grade_category']})")
    print(f"  Height: {profile['height']}")
    print(f"  Weight: {profile['weight']} lbs")
    print(f"  Position: {profile['position']}")

    print("\n=== RECRUITING METRICS (Top Predictors) ===")
    print(f"  247 Composite Rating: {profile['composite_247_rating']}")
    print(f"  247 Composite Rank: #{profile['composite_247_rank']}")
    print(f"  Stars (247): {profile['stars_247']}★")
    print(f"  ESPN Rank: #{profile['espn_rank']}")
    print(f"  Rivals Rank: #{profile['rivals_rank']}")
    print(f"  On3 Rank: #{profile['on3_rank']}")
    print(f"  Best National Rank: #{profile['best_national_rank']}")
    print(f"  Power 6 Offers: {profile['power_6_offer_count']}")
    print(f"  Total Offers: {profile['total_offer_count']}")
    print(f"  Committed: {profile['is_committed']}")
    if profile['is_committed']:
        print(f"  Committed To: {profile['committed_to']}")
    print(f"  Prediction Consensus: {profile['prediction_consensus']}")
    print(f"  Prediction Confidence: {profile['prediction_confidence']:.1%}" if profile['prediction_confidence'] else "  Prediction Confidence: N/A")

    print("\n=== PERFORMANCE STATS ===")
    print(f"  Total Seasons: {profile['total_seasons']}")
    print(f"  Total Games: {profile['total_games_played']}")
    print(f"  Career PPG: {profile['career_ppg']}")
    print(f"  Career RPG: {profile['career_rpg']}")
    print(f"  Career APG: {profile['career_apg']}")
    print(f"  Career SPG: {profile['career_spg']}")
    print(f"  Career BPG: {profile['career_bpg']}")

    print("\n=== ADVANCED METRICS (Critical for Forecasting) ===")
    print(f"  Best True Shooting %: {profile['best_ts_pct']}")
    print(f"  Best Effective FG %: {profile['best_efg_pct']}")
    print(f"  Best A/TO Ratio: {profile['best_ato_ratio']}")
    print(f"  Best 2-Point %: {profile['best_two_pt_pct']}")
    print(f"  Best 3-Point %: {profile['best_three_pt_pct']}")
    print(f"  Best FT %: {profile['best_ft_pct']}")
    print(f"  Best Per-40 PPG: {profile['best_per_40_ppg']}")
    print(f"  Best Per-40 RPG: {profile['best_per_40_rpg']}")

    print("\n=== COMPETITION CONTEXT ===")
    print(f"  Highest Level: {profile['highest_competition_level']}")
    print(f"  Circuits Played: {', '.join(profile['circuits_played']) if profile['circuits_played'] else 'None'}")
    print(f"  States Played: {', '.join(profile['states_played']) if profile['states_played'] else 'None'}")
    print(f"  Countries Played: {', '.join(profile['countries_played']) if profile['countries_played'] else 'None'}")
    print(f"  Performance Trend: {profile['performance_trend']}")

    print("\n=== FORECASTING SCORES ===")
    print(f"  Forecasting Score: {profile['forecasting_score']}/100")
    print(f"  Data Completeness: {profile['data_completeness']}%")

    # Show seasonal trend
    if profile['seasons']:
        print(f"\n{'='*80}")
        print("SEASONAL PERFORMANCE TREND")
        print(f"{'='*80}\n")

        for season in profile['seasons']:
            print(f"  {season['season']} ({season['league']}):")
            print(f"    GP: {season['games_played']}, PPG: {season['ppg']}, RPG: {season['rpg']}, APG: {season['apg']}")
            print(f"    TS%: {season['ts_pct']}, eFG%: {season['efg_pct']}")

    # Export to JSON
    output_file = Path(__file__).parent / f"forecasting_profile_{player_name.replace(' ', '_')}.json"
    with open(output_file, 'w') as f:
        json.dump(profile, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print(f"Full profile exported to: {output_file}")
    print(f"{'='*80}\n")

    # Print interpretation
    print("\n=== FORECASTING INTERPRETATION ===\n")

    if profile['forecasting_score']:
        score = profile['forecasting_score']
        if score >= 80:
            level = "Elite NBA Prospect"
        elif score >= 65:
            level = "High Major D1 / Potential NBA"
        elif score >= 50:
            level = "Mid-Major D1 / High Major Role Player"
        elif score >= 35:
            level = "Low/Mid Major D1"
        else:
            level = "D2/D3 Level"

        print(f"  Forecasted Level: {level} (Score: {score}/100)")

    # Age-for-grade interpretation
    if profile['age_for_grade'] is not None:
        age_adv = profile['age_for_grade']
        if age_adv > 0.5:
            age_impact = "POSITIVE - Significantly younger than peers (advantage)"
        elif age_adv > 0:
            age_impact = "Positive - Slightly younger than peers"
        elif age_adv > -0.5:
            age_impact = "Neutral - Average age for grade"
        else:
            age_impact = "Negative - Older than peers (reclassified or held back)"

        print(f"  Age-for-Grade Impact: {age_impact}")
        print(f"    (Younger players show 20-30% higher NBA success rates)")

    # Recruiting impact
    if profile['power_6_offer_count'] and profile['power_6_offer_count'] > 10:
        print(f"  Recruiting Status: High Major Interest ({profile['power_6_offer_count']} Power 6 offers)")
    elif profile['power_6_offer_count'] and profile['power_6_offer_count'] > 5:
        print(f"  Recruiting Status: Major Interest ({profile['power_6_offer_count']} Power 6 offers)")

    # Advanced metrics interpretation
    if profile['best_ts_pct'] and profile['best_ts_pct'] > 0.600:
        print(f"  Efficiency: Elite scorer (TS% > 60%)")
    elif profile['best_ts_pct'] and profile['best_ts_pct'] > 0.550:
        print(f"  Efficiency: Good scorer (TS% > 55%)")

    if profile['best_ato_ratio'] and profile['best_ato_ratio'] > 3.0:
        print(f"  Playmaking: Elite facilitator (A/TO > 3.0)")
    elif profile['best_ato_ratio'] and profile['best_ato_ratio'] > 2.0:
        print(f"  Playmaking: Good facilitator (A/TO > 2.0)")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/example_forecasting_usage.py \"Player Name\" [grad_year]")
        print("\nExamples:")
        print('  python scripts/example_forecasting_usage.py "Cooper Flagg" 2025')
        print('  python scripts/example_forecasting_usage.py "Cameron Boozer" 2026')
        print('  python scripts/example_forecasting_usage.py "Dylan Harper"')
        sys.exit(1)

    player_name = sys.argv[1]
    grad_year = int(sys.argv[2]) if len(sys.argv) > 2 else None

    asyncio.run(main(player_name, grad_year))
