"""
State-Level Coverage Reporting

Analyzes HS player dataset coverage by state and graduation year.
Provides quantitative baseline for data completeness before modeling.

Generates:
- Coverage metrics by state (recruiting, HS stats, circuit, offers)
- Top/bottom states by coverage
- JSON/CSV export for tracking over time

Usage:
    python scripts/report_state_coverage.py
    python scripts/report_state_coverage.py --year 2025
    python scripts/report_state_coverage.py --start 2023 --end 2026
    python scripts/report_state_coverage.py --export coverage_report.json

Author: Claude Code
Date: 2025-11-15
Phase: 15b - Coverage Baseline Analysis
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StateCoverageReporter:
    """
    Analyzes and reports player dataset coverage by state.

    Provides detailed metrics on:
    - % players with recruiting data
    - % players with HS stats (from any source)
    - % players with circuit stats (EYBL, OTE, etc.)
    - % players with college offers

    Broken down by state and graduation year.
    """

    def __init__(self, data_dir: str = "data/processed/hs_player_seasons"):
        """
        Initialize coverage reporter.

        Args:
            data_dir: Directory containing HS player season Parquet files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {data_dir}")

        logger.info(f"StateCoverageReporter initialized with data_dir={data_dir}")

    def load_datasets(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load all HS player season datasets.

        Args:
            start_year: Optional start year filter
            end_year: Optional end year filter

        Returns:
            Combined DataFrame with all player-seasons
        """
        parquet_files = list(self.data_dir.glob("hs_player_seasons_*.parquet"))

        if not parquet_files:
            logger.error(f"No dataset files found in {self.data_dir}")
            return pd.DataFrame()

        logger.info(f"Found {len(parquet_files)} dataset files")

        dfs = []
        for file in parquet_files:
            # Extract year from filename: hs_player_seasons_2024.parquet
            try:
                year = int(file.stem.split('_')[-1])

                # Filter by year range if specified
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue

                df = pd.read_parquet(file)
                logger.info(f"Loaded {len(df)} players from {file.name} (year={year})")
                dfs.append(df)

            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse year from {file.name}: {e}")
                continue

        if not dfs:
            logger.error("No datasets loaded")
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"Loaded {len(combined)} total player-seasons")

        return combined

    def calculate_coverage_metrics(
        self,
        df: pd.DataFrame,
        group_by: List[str] = ['hometown_state', 'grad_year']
    ) -> pd.DataFrame:
        """
        Calculate coverage metrics grouped by specified columns.

        Args:
            df: Player dataset DataFrame
            group_by: Columns to group by (default: hometown_state + grad_year)

        Returns:
            DataFrame with coverage metrics per group
        """
        if df.empty:
            return pd.DataFrame()

        # Define coverage indicators
        # Recruiting: has national_rank or stars or rating_0_1
        # Note: rating_0_1 is the normalized 0-1 rating from On3
        df['has_recruiting_calc'] = (
            df.get('national_rank', pd.Series()).notna() |
            df.get('stars', pd.Series()).notna() |
            df.get('rating_0_1', pd.Series()).notna()
        )

        # HS Stats: Use existing has_hs_stats flag if available, otherwise derive
        if 'has_hs_stats' in df.columns:
            # Use existing flag from dataset builder
            df['has_hs_stats_calc'] = df['has_hs_stats'].fillna(False)
        else:
            # Fallback: check for any HS stat columns if they exist
            df['has_hs_stats_calc'] = False
            for col in ['pts_per_g', 'reb_per_g', 'ast_per_g']:
                if col in df.columns:
                    df['has_hs_stats_calc'] = df['has_hs_stats_calc'] | df[col].notna()

        # Circuit Stats: Use played_eybl flag or check for EYBL stats
        if 'played_eybl' in df.columns:
            df['has_circuit_calc'] = df['played_eybl'].fillna(False)
        else:
            df['has_circuit_calc'] = False
            for col in ['eybl_pts_per_g', 'eybl_reb_per_g', 'eybl_ast_per_g']:
                if col in df.columns:
                    df['has_circuit_calc'] = df['has_circuit_calc'] | df[col].notna()

        # Offers: has total_offers > 0 (column may not exist yet)
        if 'total_offers' in df.columns:
            df['has_offers_calc'] = df['total_offers'] > 0
        else:
            df['has_offers_calc'] = False

        # High-value recruits (4+ stars)
        if 'stars' in df.columns:
            df['is_top_recruit'] = df['stars'].fillna(0) >= 4
        else:
            df['is_top_recruit'] = False

        # Use recruiting_id for counting (more reliable than player_uid which can be None)
        count_column = 'recruiting_id' if 'recruiting_id' in df.columns else 'name'

        # Group and aggregate
        coverage = df.groupby(group_by, dropna=False).agg({
            count_column: 'count',  # Total players
            'has_recruiting_calc': 'sum',
            'has_hs_stats_calc': 'sum',
            'has_circuit_calc': 'sum',
            'has_offers_calc': 'sum',
            'is_top_recruit': 'sum',
        }).reset_index()

        # Rename for clarity
        coverage = coverage.rename(columns={
            count_column: 'n_players',
            'has_recruiting_calc': 'has_recruiting',
            'has_hs_stats_calc': 'has_hs_stats',
            'has_circuit_calc': 'has_circuit',
            'has_offers_calc': 'has_offers'
        })

        # Calculate percentages
        coverage['pct_recruiting'] = (
            100.0 * coverage['has_recruiting'] / coverage['n_players']
        ).round(1)

        coverage['pct_hs_stats'] = (
            100.0 * coverage['has_hs_stats'] / coverage['n_players']
        ).round(1)

        coverage['pct_circuit'] = (
            100.0 * coverage['has_circuit'] / coverage['n_players']
        ).round(1)

        coverage['pct_offers'] = (
            100.0 * coverage['has_offers'] / coverage['n_players']
        ).round(1)

        # Calculate top recruit coverage separately
        top_recruits = df[df['is_top_recruit']].groupby(group_by, dropna=False).agg({
            count_column: 'count',
            'has_hs_stats_calc': 'sum',
            'has_circuit_calc': 'sum',
        }).reset_index()

        top_recruits = top_recruits.rename(columns={
            count_column: 'n_top_recruits',
            'has_hs_stats_calc': 'top_has_hs',
            'has_circuit_calc': 'top_has_circuit',
        })

        # Merge top recruit metrics
        coverage = coverage.merge(top_recruits, on=group_by, how='left')
        coverage['n_top_recruits'] = coverage['n_top_recruits'].fillna(0).astype(int)

        coverage['pct_top_hs'] = (
            100.0 * coverage['top_has_hs'] / coverage['n_top_recruits']
        ).round(1)

        coverage['pct_top_circuit'] = (
            100.0 * coverage['top_has_circuit'] / coverage['n_top_recruits']
        ).round(1)

        # Fill NaN percentages (when n_top_recruits = 0)
        coverage['pct_top_hs'] = coverage['pct_top_hs'].fillna(0)
        coverage['pct_top_circuit'] = coverage['pct_top_circuit'].fillna(0)

        # Sort by state and year
        coverage = coverage.sort_values(by=group_by)

        return coverage

    def generate_report(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        min_players: int = 5,
        export_path: Optional[str] = None
    ) -> Dict:
        """
        Generate comprehensive state coverage report.

        Args:
            start_year: Optional start year filter
            end_year: Optional end year filter
            min_players: Minimum players per state to include
            export_path: Optional path to export JSON/CSV

        Returns:
            Dictionary with report data
        """
        logger.info("=" * 80)
        logger.info("STATE COVERAGE REPORT")
        if start_year or end_year:
            year_range = f"{start_year or 'All'}-{end_year or 'All'}"
            logger.info(f"Years: {year_range}")
        logger.info("=" * 80)

        # Load datasets
        df = self.load_datasets(start_year=start_year, end_year=end_year)

        if df.empty:
            logger.error("No data loaded, cannot generate report")
            return {}

        # Calculate coverage by state + year
        coverage = self.calculate_coverage_metrics(df, group_by=['hometown_state', 'grad_year'])

        # Filter states with minimum players
        coverage = coverage[coverage['n_players'] >= min_players]

        # Print summary
        print("\n" + "=" * 120)
        print("COVERAGE BY STATE AND YEAR")
        print("=" * 120)

        # Select key columns for display
        display_cols = [
            'hometown_state', 'grad_year', 'n_players',
            'pct_recruiting', 'pct_hs_stats', 'pct_circuit', 'pct_offers',
            'n_top_recruits', 'pct_top_hs', 'pct_top_circuit'
        ]

        print(coverage[display_cols].to_string(index=False))
        print()

        # Calculate overall stats
        total_players = coverage['n_players'].sum()
        avg_recruiting = coverage['pct_recruiting'].mean()
        avg_hs_stats = coverage['pct_hs_stats'].mean()
        avg_circuit = coverage['pct_circuit'].mean()
        avg_offers = coverage['pct_offers'].mean()

        print("=" * 120)
        print("OVERALL SUMMARY")
        print("=" * 120)
        print(f"Total player-seasons: {total_players:,}")
        print(f"States covered: {coverage['hometown_state'].nunique()}")
        print(f"Years covered: {sorted(coverage['grad_year'].unique())}")
        print()
        print(f"Average coverage:")
        print(f"  - Recruiting data: {avg_recruiting:.1f}%")
        print(f"  - HS stats: {avg_hs_stats:.1f}%")
        print(f"  - Circuit stats: {avg_circuit:.1f}%")
        print(f"  - College offers: {avg_offers:.1f}%")
        print()

        # Top/bottom states by HS stats coverage
        state_avg = coverage.groupby('hometown_state').agg({
            'n_players': 'sum',
            'pct_hs_stats': 'mean',
            'pct_circuit': 'mean',
            'n_top_recruits': 'sum',
            'pct_top_hs': 'mean'
        }).reset_index()

        state_avg = state_avg[state_avg['n_players'] >= min_players * 2]  # At least 2 years
        state_avg = state_avg.sort_values('pct_hs_stats', ascending=False)

        print("=" * 120)
        print("TOP 10 STATES BY HS STATS COVERAGE")
        print("=" * 120)
        top_10 = state_avg.head(10)
        print(top_10.to_string(index=False))
        print()

        print("=" * 120)
        print("BOTTOM 10 STATES BY HS STATS COVERAGE (Need Improvement)")
        print("=" * 120)
        bottom_10 = state_avg.tail(10)
        print(bottom_10.to_string(index=False))
        print()

        # Export if requested
        report_data = {
            'generated_at': pd.Timestamp.now().isoformat(),
            'filters': {
                'start_year': start_year,
                'end_year': end_year,
                'min_players': min_players
            },
            'summary': {
                'total_players': int(total_players),
                'states_covered': int(coverage['hometown_state'].nunique()),
                'years_covered': sorted([int(y) for y in coverage['grad_year'].unique()]),
                'avg_recruiting_pct': float(avg_recruiting),
                'avg_hs_stats_pct': float(avg_hs_stats),
                'avg_circuit_pct': float(avg_circuit),
                'avg_offers_pct': float(avg_offers)
            },
            'coverage_by_state_year': coverage.to_dict(orient='records'),
            'state_averages': state_avg.to_dict(orient='records')
        }

        if export_path:
            export_file = Path(export_path)

            if export_file.suffix == '.json':
                with open(export_file, 'w') as f:
                    json.dump(report_data, f, indent=2)
                logger.info(f"Exported JSON report to {export_path}")

            elif export_file.suffix == '.csv':
                coverage.to_csv(export_path, index=False)
                logger.info(f"Exported CSV report to {export_path}")

            else:
                logger.warning(f"Unknown export format: {export_file.suffix}, skipping export")

        return report_data


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate state-level coverage report for HS player datasets"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Single year to report (alternative to --start/--end)"
    )
    parser.add_argument(
        "--start",
        type=int,
        help="Start year (inclusive)"
    )
    parser.add_argument(
        "--end",
        type=int,
        help="End year (inclusive)"
    )
    parser.add_argument(
        "--min-players",
        type=int,
        default=5,
        help="Minimum players per state to include (default: 5)"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export path for report (.json or .csv)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/processed/hs_player_seasons",
        help="Directory containing HS player season Parquet files"
    )

    args = parser.parse_args()

    # Determine year range
    if args.year:
        start_year = end_year = args.year
    else:
        start_year = args.start
        end_year = args.end

    # Create reporter and generate report
    reporter = StateCoverageReporter(data_dir=args.data_dir)

    report = reporter.generate_report(
        start_year=start_year,
        end_year=end_year,
        min_players=args.min_players,
        export_path=args.export
    )

    if report:
        logger.info("Report generation complete")
    else:
        logger.error("Report generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
