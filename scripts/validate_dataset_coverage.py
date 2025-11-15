"""
Dataset Coverage Validation Script

Validates coverage and quality of generated HS player datasets.

Performs:
1. Per-year coverage checks (recruiting, HS stats, EYBL, offers)
2. Join coverage metrics (overlap between data sources)
3. Quality checks (missing data, outliers, data ranges)
4. Top recruit coverage (ensure highly-ranked players have stats)

Usage:
    python scripts/validate_dataset_coverage.py --year 2025
    python scripts/validate_dataset_coverage.py --year 2025 --min-stars 4
    python scripts/validate_dataset_coverage.py --dataset data/processed/hs_player_seasons_2025.parquet

Author: Claude Code
Date: 2025-11-15
Phase: 15 - Dataset Coverage Validation
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatasetCoverageValidator:
    """
    Validates coverage and quality of HS player datasets.

    Ensures all expected players are captured and data is complete.
    """

    def __init__(self, dataset_path: str):
        """
        Initialize coverage validator.

        Args:
            dataset_path: Path to HS player dataset Parquet file
        """
        self.dataset_path = Path(dataset_path)
        self.df = pd.read_parquet(self.dataset_path)

        logger.info(
            f"Loaded dataset from {dataset_path}: shape={self.df.shape}, players={len(self.df)}"
        )

    def validate_overall_coverage(self) -> Dict:
        """
        Validate overall dataset coverage.

        Returns:
            Dictionary with coverage metrics
        """
        logger.info("Validating overall coverage")

        total = len(self.df)

        metrics = {
            'total_players': total,
            'with_recruiting_info': int(self.df.get('has_recruiting_profile', pd.Series([False])).sum()),
            'with_hs_stats': int(self.df.get('has_hs_stats', pd.Series([False])).sum()),
            'with_eybl_stats': int(self.df.get('played_eybl', pd.Series([False])).sum()),
            'with_offers': int(self.df.get('total_offers', pd.Series([0])).gt(0).sum()),
            'with_power_6_offers': int(self.df.get('power_6_offers', pd.Series([0])).gt(0).sum()),
        }

        # Calculate percentages
        if total > 0:
            metrics['pct_recruiting'] = metrics['with_recruiting_info'] / total * 100
            metrics['pct_hs_stats'] = metrics['with_hs_stats'] / total * 100
            metrics['pct_eybl'] = metrics['with_eybl_stats'] / total * 100
            metrics['pct_offers'] = metrics['with_offers'] / total * 100
            metrics['pct_power_6'] = metrics['with_power_6_offers'] / total * 100

        logger.info(f"Overall coverage: {metrics}")
        return metrics

    def validate_top_recruit_coverage(self, min_stars: int = 4) -> Dict:
        """
        Validate coverage of top recruits.

        Args:
            min_stars: Minimum star rating to consider

        Returns:
            Dictionary with top recruit coverage metrics
        """
        logger.info(f"Validating top recruit coverage (>={min_stars} stars)")

        if 'stars' not in self.df.columns:
            logger.warning("No 'stars' column found, skipping top recruit validation")
            return {}

        # Filter to top recruits
        top_recruits = self.df[self.df['stars'] >= min_stars].copy()

        if len(top_recruits) == 0:
            logger.warning(f"No players with ≥{min_stars} stars found")
            return {}

        metrics = {
            'total_top_recruits': len(top_recruits),
            'with_hs_stats': int(top_recruits.get('has_hs_stats', pd.Series([False])).sum()),
            'with_eybl_stats': int(top_recruits.get('played_eybl', pd.Series([False])).sum()),
            'with_offers': int(top_recruits.get('total_offers', pd.Series([0])).gt(0).sum()),
            'with_power_6_offers': int(top_recruits.get('power_6_offers', pd.Series([0])).gt(0).sum()),
        }

        # Calculate percentages
        total = len(top_recruits)
        if total > 0:
            metrics['pct_hs_stats'] = metrics['with_hs_stats'] / total * 100
            metrics['pct_eybl'] = metrics['with_eybl_stats'] / total * 100
            metrics['pct_offers'] = metrics['with_offers'] / total * 100
            metrics['pct_power_6'] = metrics['with_power_6_offers'] / total * 100

        logger.info(f"Top recruit coverage: {metrics}")
        return metrics

    def validate_data_quality(self) -> Dict:
        """
        Validate data quality (missing values, outliers, ranges).

        Returns:
            Dictionary with quality metrics
        """
        logger.info("Validating data quality")

        issues = []

        # Check for suspicious PPG values
        if 'pts_per_g' in self.df.columns:
            suspicious_ppg = self.df[self.df['pts_per_g'] > 50]
            if len(suspicious_ppg) > 0:
                issues.append({
                    'type': 'outlier',
                    'field': 'pts_per_g',
                    'count': len(suspicious_ppg),
                    'message': f"{len(suspicious_ppg)} players with >50 PPG"
                })

        # Check for suspicious heights (if available)
        if 'height' in self.df.columns:
            # Parse height and check for outliers
            # This is a placeholder - would need actual parsing logic
            pass

        # Check for missing critical fields
        critical_fields = ['name', 'grad_year', 'position']
        for field in critical_fields:
            if field in self.df.columns:
                missing_count = self.df[field].isna().sum()
                if missing_count > 0:
                    issues.append({
                        'type': 'missing',
                        'field': field,
                        'count': missing_count,
                        'pct': missing_count / len(self.df) * 100
                    })

        # Check data completeness score
        if 'data_completeness' in self.df.columns:
            avg_completeness = self.df['data_completeness'].mean()
            low_completeness = self.df[self.df['data_completeness'] < 0.3]

            if len(low_completeness) > 0:
                issues.append({
                    'type': 'low_completeness',
                    'count': len(low_completeness),
                    'pct': len(low_completeness) / len(self.df) * 100,
                    'message': f"{len(low_completeness)} players with <30% data completeness"
                })

        metrics = {
            'total_issues': len(issues),
            'issues': issues,
            'avg_completeness': float(self.df.get('data_completeness', pd.Series([0])).mean()),
        }

        logger.info(f"Data quality metrics: {metrics}")
        return metrics

    def validate_join_coverage(self) -> Dict:
        """
        Validate join coverage between data sources.

        Checks overlap between recruiting, HS stats, EYBL, and offers.

        Returns:
            Dictionary with join coverage metrics
        """
        logger.info("Validating join coverage")

        # Create boolean masks for each source
        has_recruiting = self.df.get('has_recruiting_profile', pd.Series([False]))
        has_hs = self.df.get('has_hs_stats', pd.Series([False]))
        has_eybl = self.df.get('played_eybl', pd.Series([False]))
        has_offers = self.df.get('total_offers', pd.Series([0])).gt(0)

        # Calculate overlaps
        metrics = {
            # All three main sources
            'recruiting_and_hs_and_eybl': int((has_recruiting & has_hs & has_eybl).sum()),

            # Two-way overlaps
            'recruiting_and_hs': int((has_recruiting & has_hs).sum()),
            'recruiting_and_eybl': int((has_recruiting & has_eybl).sum()),
            'hs_and_eybl': int((has_hs & has_eybl).sum()),

            # With offers
            'recruiting_and_offers': int((has_recruiting & has_offers).sum()),
            'hs_and_offers': int((has_hs & has_offers).sum()),
            'eybl_and_offers': int((has_eybl & has_offers).sum()),

            # Only one source
            'only_recruiting': int((has_recruiting & ~has_hs & ~has_eybl).sum()),
            'only_hs': int((has_hs & ~has_recruiting & ~has_eybl).sum()),
            'only_eybl': int((has_eybl & ~has_recruiting & ~has_hs).sum()),
        }

        logger.info(f"Join coverage metrics: {metrics}")
        return metrics

    def generate_report(self, min_stars: int = 4) -> Dict:
        """
        Generate comprehensive coverage validation report.

        Args:
            min_stars: Minimum star rating for top recruit analysis

        Returns:
            Complete validation report
        """
        logger.info("\n" + "="*60)
        logger.info(f"Dataset Coverage Validation Report")
        logger.info(f"Dataset: {self.dataset_path.name}")
        logger.info("="*60 + "\n")

        report = {
            'dataset': str(self.dataset_path),
            'overall_coverage': self.validate_overall_coverage(),
            'top_recruit_coverage': self.validate_top_recruit_coverage(min_stars=min_stars),
            'data_quality': self.validate_data_quality(),
            'join_coverage': self.validate_join_coverage(),
        }

        # Print summary
        print("\n" + "="*60)
        print("Coverage Validation Summary")
        print("="*60)

        overall = report['overall_coverage']
        print(f"\nOverall Coverage:")
        print(f"  Total players: {overall.get('total_players', 0)}")
        print(f"  With recruiting info: {overall.get('with_recruiting_info', 0)} ({overall.get('pct_recruiting', 0):.1f}%)")
        print(f"  With HS stats: {overall.get('with_hs_stats', 0)} ({overall.get('pct_hs_stats', 0):.1f}%)")
        print(f"  With EYBL stats: {overall.get('with_eybl_stats', 0)} ({overall.get('pct_eybl', 0):.1f}%)")
        print(f"  With offers: {overall.get('with_offers', 0)} ({overall.get('pct_offers', 0):.1f}%)")

        top_recruit = report['top_recruit_coverage']
        if top_recruit:
            print(f"\nTop Recruit Coverage (>={min_stars} stars):")
            print(f"  Total: {top_recruit.get('total_top_recruits', 0)}")
            print(f"  With HS stats: {top_recruit.get('with_hs_stats', 0)} ({top_recruit.get('pct_hs_stats', 0):.1f}%)")
            print(f"  With EYBL stats: {top_recruit.get('with_eybl_stats', 0)} ({top_recruit.get('pct_eybl', 0):.1f}%)")

        quality = report['data_quality']
        print(f"\nData Quality:")
        print(f"  Total issues: {quality.get('total_issues', 0)}")
        print(f"  Avg completeness: {quality.get('avg_completeness', 0):.2f}")

        if quality.get('issues'):
            print(f"\n  Issues:")
            for issue in quality['issues'][:5]:  # Show top 5 issues
                print(f"    - {issue}")

        join = report['join_coverage']
        print(f"\nJoin Coverage:")
        print(f"  Recruiting + HS + EYBL: {join.get('recruiting_and_hs_and_eybl', 0)}")
        print(f"  Recruiting + HS: {join.get('recruiting_and_hs', 0)}")
        print(f"  HS + EYBL: {join.get('hs_and_eybl', 0)}")

        print("="*60 + "\n")

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate HS player dataset coverage")

    parser.add_argument(
        '--dataset',
        type=str,
        help='Path to dataset Parquet file'
    )

    parser.add_argument(
        '--year',
        type=int,
        help='Graduation year (will look for data/processed/hs_player_seasons_YYYY.parquet)'
    )

    parser.add_argument(
        '--min-stars',
        type=int,
        default=4,
        help='Minimum star rating for top recruit analysis (default: 4)'
    )

    args = parser.parse_args()

    # Determine dataset path
    if args.dataset:
        dataset_path = args.dataset
    elif args.year:
        dataset_path = f"data/processed/hs_player_seasons/hs_player_seasons_{args.year}.parquet"
    else:
        parser.error("Must specify either --dataset or --year")

    # Validate dataset exists
    if not Path(dataset_path).exists():
        print(f"Error: Dataset not found at {dataset_path}")
        sys.exit(1)

    # Create validator
    validator = DatasetCoverageValidator(dataset_path)

    # Generate report
    report = validator.generate_report(min_stars=args.min_stars)


if __name__ == '__main__':
    main()
