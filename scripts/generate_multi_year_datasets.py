"""
Generate Multi-Year HS Player Datasets Script

Builds comprehensive high school basketball player datasets for multiple graduation years.

Merges data from:
1. MaxPreps - High school season stats
2. EYBL - Elite circuit stats
3. Recruiting services - Rankings, ratings
4. College offers - Offer lists

Outputs:
- data/processed/hs_player_seasons_YYYY.parquet for each year
- Coverage report with data completeness metrics
- Quality validation results

Usage:
    # Generate datasets for 2023-2026 from DuckDB:
    python scripts/generate_multi_year_datasets.py --start-year 2023 --end-year 2026 --use-real-data

    # Generate test datasets with mock data:
    python scripts/generate_multi_year_datasets.py --start-year 2024 --end-year 2025 \\
        --recruiting-count 50 --maxpreps-count 50 --eybl-count 25

    # Generate with custom output directory:
    python scripts/generate_multi_year_datasets.py --start-year 2025 --end-year 2025 \\
        --output-dir custom/path --use-real-data

Author: Claude Code
Date: 2025-11-15
Phase: 15 - Multi-Year Dataset Generation
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.dataset_builder import HSDatasetBuilder, create_mock_data
from src.services.duckdb_storage import get_duckdb_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MultiYearDatasetGenerator:
    """
    Generates HS player datasets for multiple graduation years.

    Supports both real data (from DuckDB) and mock data (for testing).
    """

    def __init__(
        self,
        start_year: int,
        end_year: int,
        output_dir: str = "data/processed/hs_player_seasons",
        use_real_data: bool = False
    ):
        """
        Initialize multi-year dataset generator.

        Args:
            start_year: Starting graduation year (inclusive)
            end_year: Ending graduation year (inclusive)
            output_dir: Output directory for datasets
            use_real_data: If True, use real data from DuckDB; if False, use mock data
        """
        self.start_year = start_year
        self.end_year = end_year
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_real_data = use_real_data

        self.dataset_builder = HSDatasetBuilder(output_dir=str(self.output_dir))

        if use_real_data:
            self.duckdb_storage = get_duckdb_storage()
        else:
            self.duckdb_storage = None

        logger.info(
            "MultiYearDatasetGenerator initialized",
            start_year=start_year,
            end_year=end_year,
            output_dir=str(self.output_dir),
            use_real_data=use_real_data
        )

    def load_real_data_for_year(self, grad_year: int) -> Dict[str, pd.DataFrame]:
        """
        Load real data from DuckDB for a specific graduation year.

        Args:
            grad_year: Graduation year

        Returns:
            Dictionary with 'recruiting', 'maxpreps', 'eybl', 'offers' DataFrames
        """
        logger.info(f"Loading real data from DuckDB for grad year {grad_year}")

        data = {}

        # Load recruiting data
        recruiting_df = self.duckdb_storage.export_recruiting_from_duckdb(
            class_year=grad_year
        )
        data['recruiting'] = recruiting_df

        logger.info(f"  Recruiting: {len(recruiting_df)} records")

        # Load MaxPreps data
        # Note: MaxPreps doesn't have grad_year in stats table, so we get all and filter later
        maxpreps_df = self.duckdb_storage.export_maxpreps_from_duckdb()

        # Filter by grad_year if available
        if 'grad_year' in maxpreps_df.columns:
            maxpreps_df = maxpreps_df[maxpreps_df['grad_year'] == grad_year]

        data['maxpreps'] = maxpreps_df
        logger.info(f"  MaxPreps: {len(maxpreps_df)} records")

        # Load EYBL data
        eybl_df = self.duckdb_storage.export_eybl_from_duckdb()
        data['eybl'] = eybl_df
        logger.info(f"  EYBL: {len(eybl_df)} records")

        # Load offers data
        offers_df = self.duckdb_storage.export_college_offers_from_duckdb()
        data['offers'] = offers_df
        logger.info(f"  Offers: {len(offers_df)} records")

        return data

    def generate_datasets(
        self,
        recruiting_count: Optional[int] = None,
        maxpreps_count: Optional[int] = None,
        eybl_count: Optional[int] = None
    ) -> Dict[int, pd.DataFrame]:
        """
        Generate datasets for all years.

        Args:
            recruiting_count: Number of recruiting profiles (mock mode only)
            maxpreps_count: Number of MaxPreps stat lines (mock mode only)
            eybl_count: Number of EYBL stat lines (mock mode only)

        Returns:
            Dictionary mapping grad_year -> DataFrame
        """
        logger.info(
            f"\n{'='*60}\nGenerating HS datasets for {self.start_year}-{self.end_year}\n{'='*60}"
        )

        datasets = {}
        coverage_reports = {}

        for year in range(self.start_year, self.end_year + 1):
            logger.info(f"\n{'='*60}\nProcessing Graduation Year: {year}\n{'='*60}")

            # Load data (real or mock)
            if self.use_real_data:
                data = self.load_real_data_for_year(year)
            else:
                logger.info(f"Creating mock data for grad year {year}")
                data = create_mock_data(
                    grad_year=year,
                    recruiting_count=recruiting_count or 50,
                    maxpreps_count=maxpreps_count or 50,
                    eybl_count=eybl_count or 25
                )

            # Build dataset for this year
            dataset = self.dataset_builder.build_dataset(
                grad_year=year,
                maxpreps_data=data.get('maxpreps'),
                eybl_data=data.get('eybl'),
                recruiting_data=data.get('recruiting'),
                offers_data=data.get('offers')
            )

            datasets[year] = dataset

            # Generate coverage report
            coverage = self.dataset_builder.get_coverage_report(dataset)
            coverage_reports[year] = coverage

            # Log coverage for this year
            self._log_coverage_report(year, coverage)

        # Save overall coverage summary
        self._save_coverage_summary(coverage_reports)

        # Log overall summary
        self._log_overall_summary(datasets)

        return datasets

    def _log_coverage_report(self, year: int, coverage: Dict) -> None:
        """
        Log coverage report for a specific year.

        Args:
            year: Graduation year
            coverage: Coverage metrics dictionary
        """
        logger.info(f"\nCoverage Report for {year}:")
        logger.info(f"  Total players: {coverage.get('total_players', 0)}")
        logger.info(f"  With recruiting info: {coverage.get('with_recruiting_info', 0)} ({coverage.get('pct_recruiting', 0):.1f}%)")
        logger.info(f"  With HS stats: {coverage.get('with_hs_stats', 0)} ({coverage.get('pct_hs_stats', 0):.1f}%)")
        logger.info(f"  With EYBL stats: {coverage.get('with_eybl_stats', 0)} ({coverage.get('pct_eybl', 0):.1f}%)")
        logger.info(f"  With offers: {coverage.get('with_offers', 0)} ({coverage.get('pct_offers', 0):.1f}%)")
        logger.info(f"  With Power 6 offers: {coverage.get('with_power_6_offers', 0)}")
        logger.info(f"  Avg data completeness: {coverage.get('avg_data_completeness', 0):.2f}")

    def _save_coverage_summary(self, coverage_reports: Dict[int, Dict]) -> None:
        """
        Save coverage summary to JSON file.

        Args:
            coverage_reports: Dictionary mapping year -> coverage metrics
        """
        summary_path = self.output_dir / "coverage_summary.json"

        summary = {
            'generated_at': pd.Timestamp.now().isoformat(),
            'years': list(range(self.start_year, self.end_year + 1)),
            'coverage_by_year': coverage_reports,
            'overall': {
                'total_years': len(coverage_reports),
                'total_players': sum(c.get('total_players', 0) for c in coverage_reports.values()),
                'avg_recruiting_coverage': sum(c.get('pct_recruiting', 0) for c in coverage_reports.values()) / len(coverage_reports) if coverage_reports else 0,
                'avg_hs_stats_coverage': sum(c.get('pct_hs_stats', 0) for c in coverage_reports.values()) / len(coverage_reports) if coverage_reports else 0,
                'avg_eybl_coverage': sum(c.get('pct_eybl', 0) for c in coverage_reports.values()) / len(coverage_reports) if coverage_reports else 0,
            }
        }

        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\nCoverage summary saved to {summary_path}")

    def _log_overall_summary(self, datasets: Dict[int, pd.DataFrame]) -> None:
        """
        Log overall summary of all generated datasets.

        Args:
            datasets: Dictionary mapping year -> DataFrame
        """
        logger.info("\n" + "="*60)
        logger.info("Multi-Year Dataset Generation Complete")
        logger.info("="*60)

        for year, df in datasets.items():
            logger.info(
                f"  {year}: {len(df)} players × {len(df.columns)} columns"
            )

        total_players = sum(len(df) for df in datasets.values())
        logger.info(f"\nTotal players across all years: {total_players}")

        logger.info(f"\nOutput directory: {self.output_dir}")
        logger.info("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate multi-year HS basketball player datasets"
    )

    # Year range
    parser.add_argument(
        '--start-year',
        type=int,
        required=True,
        help='Starting graduation year (inclusive)'
    )

    parser.add_argument(
        '--end-year',
        type=int,
        required=True,
        help='Ending graduation year (inclusive)'
    )

    # Data source
    data_mode = parser.add_mutually_exclusive_group()

    data_mode.add_argument(
        '--use-real-data',
        action='store_true',
        help='Use real data from DuckDB'
    )

    # Mock data options
    parser.add_argument(
        '--recruiting-count',
        type=int,
        default=50,
        help='Number of recruiting profiles per year (mock mode only, default: 50)'
    )

    parser.add_argument(
        '--maxpreps-count',
        type=int,
        default=50,
        help='Number of MaxPreps stat lines per year (mock mode only, default: 50)'
    )

    parser.add_argument(
        '--eybl-count',
        type=int,
        default=25,
        help='Number of EYBL stat lines per year (mock mode only, default: 25)'
    )

    # Output
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/processed/hs_player_seasons',
        help='Output directory for datasets (default: data/processed/hs_player_seasons)'
    )

    args = parser.parse_args()

    # Validate year range
    if args.start_year > args.end_year:
        print(f"Error: start-year ({args.start_year}) must be <= end-year ({args.end_year})")
        sys.exit(1)

    # Create generator
    generator = MultiYearDatasetGenerator(
        start_year=args.start_year,
        end_year=args.end_year,
        output_dir=args.output_dir,
        use_real_data=args.use_real_data
    )

    # Generate datasets
    datasets = generator.generate_datasets(
        recruiting_count=args.recruiting_count if not args.use_real_data else None,
        maxpreps_count=args.maxpreps_count if not args.use_real_data else None,
        eybl_count=args.eybl_count if not args.use_real_data else None
    )

    # Print sample from first dataset
    if datasets:
        first_year = min(datasets.keys())
        first_df = datasets[first_year]

        print(f"\nSample from {first_year} dataset:")
        print("="*80)

        # Select key columns if they exist
        sample_cols = [
            'name', 'position', 'stars', 'national_rank',
            'pts_per_g', 'reb_per_g', 'ast_per_g',
            'eybl_pts_per_g', 'played_eybl',
            'total_offers', 'power_6_offers'
        ]

        available_cols = [col for col in sample_cols if col in first_df.columns]

        if available_cols:
            print(first_df[available_cols].head(10).to_string())
        else:
            print(first_df.head(10).to_string())

        print("="*80)


if __name__ == '__main__':
    main()
