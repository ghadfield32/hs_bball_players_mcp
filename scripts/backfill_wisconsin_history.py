#!/usr/bin/env python3
"""
Wisconsin WIAA Historical Backfill Script

Fetches and stores historical Wisconsin WIAA tournament bracket data (2015-2025).

Features:
- Fetches both Boys and Girls basketball
- Stores games in CSV/JSON/Parquet format
- Progress tracking and error handling
- Summary statistics per year

Usage:
    python scripts/backfill_wisconsin_history.py
    python scripts/backfill_wisconsin_history.py --start 2020 --end 2025
    python scripts/backfill_wisconsin_history.py --format json
    python scripts/backfill_wisconsin_history.py --output data/wisconsin_backfill.csv
"""

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource
from src.models import Game


class WisconsinBackfill:
    """Historical backfill processor for Wisconsin WIAA."""

    def __init__(self, output_dir: Path = None, output_format: str = "csv"):
        self.datasource = WisconsinWiaaDataSource()
        self.output_dir = output_dir or Path("data/wisconsin_wiaa")
        self.output_format = output_format
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def backfill_year(self, year: int, gender: str) -> List[Game]:
        """
        Backfill data for a specific year and gender.

        Args:
            year: Tournament year (e.g., 2025)
            gender: "Boys" or "Girls"

        Returns:
            List of games
        """
        print(f"Fetching {year} {gender}...", end=" ", flush=True)

        try:
            games = await self.datasource.get_tournament_brackets(
                year=year,
                gender=gender
            )

            teams = set()
            for game in games:
                if game.home_team_name:
                    teams.add(game.home_team_name)
                if game.away_team_name:
                    teams.add(game.away_team_name)

            print(f"✓ {len(games)} games, {len(teams)} teams")
            return games

        except Exception as e:
            print(f"✗ Error: {e}")
            return []

    async def backfill_range(self, start_year: int, end_year: int):
        """
        Backfill data for a range of years.

        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
        """
        print(f"\n{'='*80}")
        print(f"Wisconsin WIAA Historical Backfill ({start_year}-{end_year})")
        print(f"{'='*80}\n")
        print(f"Output directory: {self.output_dir}")
        print(f"Output format: {self.output_format}\n")

        all_games = []
        summary_data = []

        for year in range(start_year, end_year + 1):
            for gender in ["Boys", "Girls"]:
                games = await self.backfill_year(year, gender)

                if games:
                    all_games.extend(games)

                    # Extract summary stats
                    teams = set()
                    for game in games:
                        if game.home_team_name:
                            teams.add(game.home_team_name)
                        if game.away_team_name:
                            teams.add(game.away_team_name)

                    # Count errors/issues
                    self_games = sum(
                        1 for g in games
                        if g.home_team_name.lower() == g.away_team_name.lower()
                    )

                    summary_data.append({
                        "year": year,
                        "gender": gender,
                        "num_games": len(games),
                        "num_teams": len(teams),
                        "self_games": self_games
                    })

                # Small delay to be respectful of server
                await asyncio.sleep(0.5)

        # Save all games
        if all_games:
            await self._save_games(all_games, "all_games")

        # Save summary
        await self._save_summary(summary_data)

        # Print summary
        print(f"\n{'='*80}")
        print("BACKFILL SUMMARY")
        print(f"{'='*80}\n")
        print(f"{'Year':<6} {'Gender':<8} {'Games':<8} {'Teams':<8} {'Issues':<8}")
        print("-" * 80)

        for row in summary_data:
            print(
                f"{row['year']:<6} {row['gender']:<8} {row['num_games']:<8} "
                f"{row['num_teams']:<8} {row['self_games']:<8}"
            )

        total_games = sum(r["num_games"] for r in summary_data)
        total_issues = sum(r["self_games"] for r in summary_data)

        print(f"\n{'='*80}")
        print(f"Total games fetched: {total_games}")
        print(f"Total issues: {total_issues}")
        print(f"Output saved to: {self.output_dir}")
        print(f"{'='*80}\n")

    async def _save_games(self, games: List[Game], filename_prefix: str):
        """Save games to file in specified format."""
        if self.output_format == "csv":
            await self._save_csv(games, filename_prefix)
        elif self.output_format == "json":
            await self._save_json(games, filename_prefix)
        elif self.output_format == "parquet":
            await self._save_parquet(games, filename_prefix)
        else:
            print(f"Warning: Unknown format '{self.output_format}', defaulting to CSV")
            await self._save_csv(games, filename_prefix)

    async def _save_csv(self, games: List[Game], filename_prefix: str):
        """Save games to CSV file."""
        filepath = self.output_dir / f"{filename_prefix}.csv"

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not games:
                return

            # Get all fields from first game
            fieldnames = [
                "game_id", "year", "gender", "division", "sectional", "round",
                "home_team", "away_team", "home_score", "away_score",
                "location", "overtime", "season"
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for game in games:
                writer.writerow({
                    "game_id": game.game_id,
                    "year": getattr(game, "year", ""),
                    "gender": getattr(game, "gender", ""),
                    "division": getattr(game, "division", ""),
                    "sectional": getattr(game, "sectional", ""),
                    "round": game.round,
                    "home_team": game.home_team_name,
                    "away_team": game.away_team_name,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "location": game.location or "",
                    "overtime": getattr(game, "overtime_periods", 0) or 0,
                    "season": game.season
                })

        print(f"✓ Saved {len(games)} games to {filepath}")

    async def _save_json(self, games: List[Game], filename_prefix: str):
        """Save games to JSON file."""
        filepath = self.output_dir / f"{filename_prefix}.json"

        games_data = []
        for game in games:
            game_dict = {
                "game_id": game.game_id,
                "year": getattr(game, "year", None),
                "gender": getattr(game, "gender", None),
                "division": getattr(game, "division", None),
                "sectional": getattr(game, "sectional", None),
                "round": game.round,
                "home_team": game.home_team_name,
                "away_team": game.away_team_name,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "location": game.location,
                "overtime_periods": getattr(game, "overtime_periods", 0),
                "season": game.season,
                "game_date": game.game_date.isoformat() if game.game_date else None,
                "status": game.status.value if hasattr(game.status, "value") else str(game.status)
            }
            games_data.append(game_dict)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(games_data, f, indent=2)

        print(f"✓ Saved {len(games)} games to {filepath}")

    async def _save_parquet(self, games: List[Game], filename_prefix: str):
        """Save games to Parquet file."""
        try:
            import pandas as pd
        except ImportError:
            print("Warning: pandas not installed, falling back to CSV")
            await self._save_csv(games, filename_prefix)
            return

        filepath = self.output_dir / f"{filename_prefix}.parquet"

        # Convert games to DataFrame
        games_data = []
        for game in games:
            games_data.append({
                "game_id": game.game_id,
                "year": getattr(game, "year", None),
                "gender": getattr(game, "gender", None),
                "division": getattr(game, "division", None),
                "sectional": getattr(game, "sectional", None),
                "round": game.round,
                "home_team": game.home_team_name,
                "away_team": game.away_team_name,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "location": game.location,
                "overtime_periods": getattr(game, "overtime_periods", 0),
                "season": game.season,
                "game_date": game.game_date,
                "status": str(game.status)
            })

        df = pd.DataFrame(games_data)
        df.to_parquet(filepath, index=False)

        print(f"✓ Saved {len(games)} games to {filepath}")

    async def _save_summary(self, summary_data: List[dict]):
        """Save summary statistics to CSV."""
        filepath = self.output_dir / "backfill_summary.csv"

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["year", "gender", "num_games", "num_teams", "self_games"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_data)

        print(f"✓ Saved summary to {filepath}")


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical Wisconsin WIAA tournament data"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=2015,
        help="Starting year (default: 2015)"
    )
    parser.add_argument(
        "--end",
        type=int,
        default=2025,
        help="Ending year (default: 2025)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "parquet"],
        default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: data/wisconsin_wiaa)"
    )

    args = parser.parse_args()

    backfill = WisconsinBackfill(
        output_dir=args.output,
        output_format=args.format
    )

    await backfill.backfill_range(args.start, args.end)


if __name__ == "__main__":
    asyncio.run(main())
