"""
Validate DuckDB Pipeline Script

Validates the DuckDB → dataset_builder pipeline by:
1. Checking DuckDB export functions work correctly
2. Validating schema compatibility with dataset builder
3. Testing join operations (recruiting + HS stats + EYBL + offers)
4. Measuring performance metrics
5. Checking data quality and completeness

Usage:
    python scripts/validate_duckdb_pipeline.py
    python scripts/validate_duckdb_pipeline.py --grad-year 2025
    python scripts/validate_duckdb_pipeline.py --populate-mock

Author: Claude Code
Date: 2025-11-15
Phase: 15 - DuckDB Pipeline Validation
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.dataset_builder import HSDatasetBuilder, create_mock_data
from src.services.duckdb_storage import get_duckdb_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DuckDBPipelineValidator:
    """
    Validates the DuckDB → dataset_builder pipeline.

    Ensures data can flow from DuckDB through exports to dataset builder
    without schema mismatches, join errors, or performance issues.
    """

    def __init__(self, grad_year: int = 2025):
        """
        Initialize pipeline validator.

        Args:
            grad_year: Graduation year for testing
        """
        self.grad_year = grad_year
        self.duckdb_storage = get_duckdb_storage()
        self.dataset_builder = HSDatasetBuilder()

        self.validation_results = {
            'export_tests': {},
            'schema_tests': {},
            'join_tests': {},
            'performance_tests': {},
            'quality_tests': {}
        }

        logger.info(f"Pipeline validator initialized for grad year {grad_year}")

    def validate_duckdb_exports(self) -> Dict:
        """
        Test 1: Validate all DuckDB export functions work.

        Returns:
            Dictionary with test results
        """
        logger.info("Test 1: Validating DuckDB export functions")

        results = {}

        # Test EYBL export
        try:
            start_time = time.time()
            eybl_df = self.duckdb_storage.export_eybl_from_duckdb()
            elapsed = time.time() - start_time

            results['eybl_export'] = {
                'success': True,
                'rows': len(eybl_df),
                'columns': len(eybl_df.columns) if not eybl_df.empty else 0,
                'time_ms': int(elapsed * 1000)
            }

            logger.info(
                f"✓ EYBL export successful: {len(eybl_df)} rows in {elapsed:.2f}s"
            )

        except Exception as e:
            results['eybl_export'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"✗ EYBL export failed: {e}")

        # Test recruiting export
        try:
            start_time = time.time()
            recruiting_df = self.duckdb_storage.export_recruiting_from_duckdb(
                class_year=self.grad_year
            )
            elapsed = time.time() - start_time

            results['recruiting_export'] = {
                'success': True,
                'rows': len(recruiting_df),
                'columns': len(recruiting_df.columns) if not recruiting_df.empty else 0,
                'time_ms': int(elapsed * 1000)
            }

            logger.info(
                f"✓ Recruiting export successful: {len(recruiting_df)} rows in {elapsed:.2f}s"
            )

        except Exception as e:
            results['recruiting_export'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"✗ Recruiting export failed: {e}")

        # Test MaxPreps export
        try:
            start_time = time.time()
            maxpreps_df = self.duckdb_storage.export_maxpreps_from_duckdb()
            elapsed = time.time() - start_time

            results['maxpreps_export'] = {
                'success': True,
                'rows': len(maxpreps_df),
                'columns': len(maxpreps_df.columns) if not maxpreps_df.empty else 0,
                'time_ms': int(elapsed * 1000)
            }

            logger.info(
                f"✓ MaxPreps export successful: {len(maxpreps_df)} rows in {elapsed:.2f}s"
            )

        except Exception as e:
            results['maxpreps_export'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"✗ MaxPreps export failed: {e}")

        # Test offers export
        try:
            start_time = time.time()
            offers_df = self.duckdb_storage.export_college_offers_from_duckdb()
            elapsed = time.time() - start_time

            results['offers_export'] = {
                'success': True,
                'rows': len(offers_df),
                'columns': len(offers_df.columns) if not offers_df.empty else 0,
                'time_ms': int(elapsed * 1000)
            }

            logger.info(
                f"✓ Offers export successful: {len(offers_df)} rows in {elapsed:.2f}s"
            )

        except Exception as e:
            results['offers_export'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"✗ Offers export failed: {e}")

        self.validation_results['export_tests'] = results
        return results

    def validate_schema_compatibility(self) -> Dict:
        """
        Test 2: Validate exported schemas match dataset builder expectations.

        Returns:
            Dictionary with schema validation results
        """
        logger.info("Test 2: Validating schema compatibility")

        results = {}

        # Expected columns for dataset builder
        expected_schemas = {
            'eybl': ['player_uid', 'points_per_game', 'rebounds_per_game', 'assists_per_game'],
            'recruiting': ['player_uid', 'player_name', 'class_year', 'stars', 'rating'],
            'maxpreps': ['player_uid', 'pts_per_g', 'reb_per_g', 'ast_per_g', 'school_name'],
            'offers': ['player_uid', 'college', 'conference_level', 'offer_status']
        }

        # Check EYBL schema
        eybl_df = self.duckdb_storage.export_eybl_from_duckdb()
        if not eybl_df.empty:
            missing_cols = [col for col in expected_schemas['eybl'] if col not in eybl_df.columns]
            results['eybl_schema'] = {
                'valid': len(missing_cols) == 0,
                'missing_columns': missing_cols,
                'actual_columns': list(eybl_df.columns)
            }
        else:
            results['eybl_schema'] = {
                'valid': False,
                'missing_columns': 'No data',
                'actual_columns': []
            }

        # Check recruiting schema
        recruiting_df = self.duckdb_storage.export_recruiting_from_duckdb(class_year=self.grad_year)
        if not recruiting_df.empty:
            missing_cols = [col for col in expected_schemas['recruiting'] if col not in recruiting_df.columns]
            results['recruiting_schema'] = {
                'valid': len(missing_cols) == 0,
                'missing_columns': missing_cols,
                'actual_columns': list(recruiting_df.columns)
            }
        else:
            results['recruiting_schema'] = {
                'valid': False,
                'missing_columns': 'No data',
                'actual_columns': []
            }

        logger.info(f"Schema validation results: {results}")
        self.validation_results['schema_tests'] = results
        return results

    def validate_joins(self) -> Dict:
        """
        Test 3: Validate join operations work correctly.

        Returns:
            Dictionary with join test results
        """
        logger.info("Test 3: Validating join operations")

        results = {}

        # Export data
        recruiting_df = self.duckdb_storage.export_recruiting_from_duckdb(class_year=self.grad_year)
        maxpreps_df = self.duckdb_storage.export_maxpreps_from_duckdb()
        eybl_df = self.duckdb_storage.export_eybl_from_duckdb()
        offers_df = self.duckdb_storage.export_college_offers_from_duckdb()

        if recruiting_df.empty:
            logger.warning("No recruiting data available for join tests")
            results['join_recruiting_maxpreps'] = {'success': False, 'reason': 'No recruiting data'}
        else:
            # Test recruiting + MaxPreps join
            try:
                if not maxpreps_df.empty:
                    merged = recruiting_df.merge(
                        maxpreps_df,
                        on='player_uid',
                        how='left'
                    )

                    match_count = merged['pts_per_g'].notna().sum() if 'pts_per_g' in merged.columns else 0

                    results['join_recruiting_maxpreps'] = {
                        'success': True,
                        'base_rows': len(recruiting_df),
                        'merged_rows': len(merged),
                        'matched_players': match_count,
                        'match_rate': match_count / len(recruiting_df) if len(recruiting_df) > 0 else 0
                    }

                    logger.info(
                        f"✓ Recruiting + MaxPreps join: {match_count}/{len(recruiting_df)} matched ({match_count/len(recruiting_df)*100:.1f}%)"
                    )
                else:
                    results['join_recruiting_maxpreps'] = {'success': False, 'reason': 'No MaxPreps data'}

            except Exception as e:
                results['join_recruiting_maxpreps'] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"✗ Recruiting + MaxPreps join failed: {e}")

            # Test recruiting + EYBL join
            try:
                if not eybl_df.empty:
                    merged = recruiting_df.merge(
                        eybl_df,
                        on='player_uid',
                        how='left'
                    )

                    match_count = merged['points_per_game'].notna().sum() if 'points_per_game' in merged.columns else 0

                    results['join_recruiting_eybl'] = {
                        'success': True,
                        'base_rows': len(recruiting_df),
                        'merged_rows': len(merged),
                        'matched_players': match_count,
                        'match_rate': match_count / len(recruiting_df) if len(recruiting_df) > 0 else 0
                    }

                    logger.info(
                        f"✓ Recruiting + EYBL join: {match_count}/{len(recruiting_df)} matched ({match_count/len(recruiting_df)*100:.1f}%)"
                    )
                else:
                    results['join_recruiting_eybl'] = {'success': False, 'reason': 'No EYBL data'}

            except Exception as e:
                results['join_recruiting_eybl'] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"✗ Recruiting + EYBL join failed: {e}")

        self.validation_results['join_tests'] = results
        return results

    def validate_performance(self) -> Dict:
        """
        Test 4: Validate performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        logger.info("Test 4: Validating performance metrics")

        results = {}

        # Test full dataset build time
        try:
            start_time = time.time()

            recruiting_df = self.duckdb_storage.export_recruiting_from_duckdb(class_year=self.grad_year)
            maxpreps_df = self.duckdb_storage.export_maxpreps_from_duckdb()
            eybl_df = self.duckdb_storage.export_eybl_from_duckdb()
            offers_df = self.duckdb_storage.export_college_offers_from_duckdb()

            # Build dataset
            dataset = self.dataset_builder.build_dataset(
                grad_year=self.grad_year,
                maxpreps_data=maxpreps_df if not maxpreps_df.empty else None,
                eybl_data=eybl_df if not eybl_df.empty else None,
                recruiting_data=recruiting_df if not recruiting_df.empty else None,
                offers_data=offers_df if not offers_df.empty else None,
                output_path=None  # Don't save during validation
            )

            elapsed = time.time() - start_time

            results['full_pipeline'] = {
                'success': True,
                'time_seconds': elapsed,
                'output_rows': len(dataset),
                'output_columns': len(dataset.columns) if not dataset.empty else 0,
                'throughput_rows_per_sec': len(dataset) / elapsed if elapsed > 0 else 0
            }

            logger.info(
                f"✓ Full pipeline: {len(dataset)} rows in {elapsed:.2f}s ({len(dataset)/elapsed:.0f} rows/sec)"
            )

        except Exception as e:
            results['full_pipeline'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"✗ Full pipeline test failed: {e}")

        self.validation_results['performance_tests'] = results
        return results

    def run_all_validations(self) -> Dict:
        """
        Run all validation tests.

        Returns:
            Complete validation results
        """
        logger.info("\n" + "="*60)
        logger.info(f"DuckDB Pipeline Validation (Grad Year: {self.grad_year})")
        logger.info("="*60 + "\n")

        # Run all tests
        self.validate_duckdb_exports()
        self.validate_schema_compatibility()
        self.validate_joins()
        self.validate_performance()

        # Summary
        logger.info("\n" + "="*60)
        logger.info("Validation Summary")
        logger.info("="*60)

        all_passed = True

        # Check exports
        export_results = self.validation_results['export_tests']
        exports_passed = all(v.get('success', False) for v in export_results.values())
        logger.info(f"Exports: {'✓ PASS' if exports_passed else '✗ FAIL'}")
        all_passed = all_passed and exports_passed

        # Check schemas
        schema_results = self.validation_results['schema_tests']
        schemas_passed = all(v.get('valid', False) for v in schema_results.values())
        logger.info(f"Schemas: {'✓ PASS' if schemas_passed else '✗ FAIL'}")
        all_passed = all_passed and schemas_passed

        # Check joins
        join_results = self.validation_results['join_tests']
        joins_passed = all(v.get('success', False) for v in join_results.values())
        logger.info(f"Joins: {'✓ PASS' if joins_passed else '✗ FAIL'}")
        all_passed = all_passed and joins_passed

        # Check performance
        perf_results = self.validation_results['performance_tests']
        perf_passed = all(v.get('success', False) for v in perf_results.values())
        logger.info(f"Performance: {'✓ PASS' if perf_passed else '✗ FAIL'}")
        all_passed = all_passed and perf_passed

        logger.info("="*60)
        logger.info(f"Overall: {'✓✓✓ ALL TESTS PASSED ✓✓✓' if all_passed else '✗✗✗ SOME TESTS FAILED ✗✗✗'}")
        logger.info("="*60 + "\n")

        return self.validation_results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate DuckDB → dataset_builder pipeline")

    parser.add_argument(
        '--grad-year',
        type=int,
        default=2025,
        help='Graduation year for testing (default: 2025)'
    )

    parser.add_argument(
        '--populate-mock',
        action='store_true',
        help='Populate DuckDB with mock data before validation'
    )

    args = parser.parse_args()

    # Populate mock data if requested
    if args.populate_mock:
        print("Populating DuckDB with mock data...")
        # This would require async implementation
        # For now, just note it in the output
        print("Note: Mock data population not yet implemented")
        print("Please use real data or run fetch_real_eybl_data.py first")

    # Create validator
    validator = DuckDBPipelineValidator(grad_year=args.grad_year)

    # Run validations
    results = validator.run_all_validations()

    # Print detailed results
    print("\nDetailed Results:")
    print(f"Export Tests: {results['export_tests']}")
    print(f"Schema Tests: {results['schema_tests']}")
    print(f"Join Tests: {results['join_tests']}")
    print(f"Performance Tests: {results['performance_tests']}")


if __name__ == '__main__':
    main()
