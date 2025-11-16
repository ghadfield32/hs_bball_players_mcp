"""
Schema Validation for Recruiting Data Pipeline

Validates that DataFrames produced by normalization pipeline match
DuckDB table schemas to prevent insertion errors.

Checks:
- Column names match (order and exact names)
- Column types are compatible
- Required columns are present
- No extra columns that don't exist in schema

Usage:
    python scripts/validate_recruiting_schema.py
    python scripts/validate_recruiting_schema.py --verbose

Author: Claude Code
Date: 2025-11-15
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

from src.datasources.recruiting.on3 import On3DataSource
from src.services.recruiting_pipeline import RecruitingPipeline


class SchemaValidator:
    """Validates DataFrame schemas match DuckDB table schemas."""

    def __init__(self, db_path: str = "data/duckdb/recruiting.duckdb"):
        """
        Initialize schema validator.

        Args:
            db_path: Path to DuckDB file
        """
        self.conn = duckdb.connect(db_path)
        self.pipeline = RecruitingPipeline()

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get DuckDB table schema.

        Args:
            table_name: Name of table

        Returns:
            Dict mapping column names to types
        """
        result = self.conn.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        # Result format: (cid, name, type, notnull, dflt_value, pk)
        schema = {}
        for row in result:
            col_name = row[1]
            col_type = row[2]
            schema[col_name] = col_type

        return schema

    def validate_dataframe_schema(
        self,
        df: pd.DataFrame,
        table_name: str,
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate DataFrame schema matches table schema.

        Args:
            df: DataFrame to validate
            table_name: Target table name
            strict: If True, require exact column match (order matters)

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Get table schema
        table_schema = self.get_table_schema(table_name)
        if not table_schema:
            issues.append(f"Table '{table_name}' not found or has no columns")
            return False, issues

        df_columns = set(df.columns)
        table_columns = set(table_schema.keys())

        # Check for missing columns
        missing = table_columns - df_columns
        if missing:
            issues.append(f"Missing columns in DataFrame: {sorted(missing)}")

        # Check for extra columns
        extra = df_columns - table_columns
        if extra:
            issues.append(f"Extra columns in DataFrame: {sorted(extra)}")

        # If strict mode, check column order
        if strict and not missing and not extra:
            df_col_list = list(df.columns)
            table_col_list = list(table_schema.keys())

            if df_col_list != table_col_list:
                issues.append(
                    f"Column order mismatch:\n"
                    f"  DataFrame: {df_col_list[:5]}...\n"
                    f"  Table:     {table_col_list[:5]}..."
                )

        # Check data types (basic compatibility)
        for col in df_columns & table_columns:
            df_dtype = str(df[col].dtype)
            table_dtype = table_schema[col].upper()

            # Basic type compatibility checks
            compatible = False

            if "INT" in table_dtype and df_dtype in ["int64", "Int64"]:
                compatible = True
            elif "VARCHAR" in table_dtype and df_dtype == "object":
                compatible = True
            elif "DOUBLE" in table_dtype and df_dtype in ["float64", "Float64"]:
                compatible = True
            elif "BOOLEAN" in table_dtype and df_dtype == "bool":
                compatible = True
            elif "TIMESTAMP" in table_dtype and df_dtype == "datetime64[ns]":
                compatible = True
            elif table_dtype == df_dtype.upper():
                compatible = True

            if not compatible:
                issues.append(
                    f"Type mismatch for column '{col}': "
                    f"DataFrame has '{df_dtype}', table expects '{table_dtype}'"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_on3_raw_pipeline(self, verbose: bool = False) -> bool:
        """
        Validate on3_player_rankings_raw schema.

        Args:
            verbose: Show detailed output

        Returns:
            True if valid
        """
        print("\n" + "=" * 80)
        print("VALIDATING: on3_player_rankings_raw")
        print("=" * 80)

        # Create sample DataFrame
        from src.models.recruiting import RecruitingRank
        from src.models.player import Position
        from src.models.source import DataSource, DataSourceType, DataSourceRegion

        sample_rank = RecruitingRank(
            player_id="test_123",
            player_name="Test Player",
            rank_national=1,
            stars=5,
            rating=0.9999,
            service="industry",
            class_year=2025,
            position=Position.PG,
            height="6-5",
            weight=185,
            school="Test High School",
            city="Test City",
            state="TS",
            data_source=DataSource(
                name="On3/Rivals",
                type=DataSourceType.ON3,
                region=DataSourceRegion.US,
                base_url="https://www.on3.com"
            )
        )

        raw_df = self.pipeline.normalize_on3_raw_to_dataframe(
            rankings=[sample_rank],
            class_year=2025,
            scraped_at=datetime.utcnow()
        )

        if verbose:
            print(f"\nDataFrame columns ({len(raw_df.columns)}):")
            print(f"  {list(raw_df.columns)}")

        is_valid, issues = self.validate_dataframe_schema(
            df=raw_df,
            table_name="on3_player_rankings_raw",
            strict=False  # Column order may vary
        )

        if is_valid:
            print("[OK] Schema matches on3_player_rankings_raw")
        else:
            print(f"[ERROR] {len(issues)} schema issues found:")
            for issue in issues:
                print(f"  - {issue}")

        print()
        return is_valid

    def validate_player_recruiting_pipeline(self, verbose: bool = False) -> bool:
        """
        Validate player_recruiting schema.

        Args:
            verbose: Show detailed output

        Returns:
            True if valid
        """
        print("\n" + "=" * 80)
        print("VALIDATING: player_recruiting")
        print("=" * 80)

        # Create sample DataFrame
        from src.models.recruiting import RecruitingRank
        from src.models.player import Position
        from src.models.source import DataSource, DataSourceType, DataSourceRegion

        sample_rank = RecruitingRank(
            player_id="test_123",
            player_name="Test Player",
            rank_national=1,
            stars=5,
            rating=0.9999,
            service="industry",
            class_year=2025,
            position=Position.PG,
            height="6-5",
            weight=185,
            school="Test High School",
            city="Test City",
            state="TS",
            committed_to="Test University",
            data_source=DataSource(
                name="On3/Rivals",
                type=DataSourceType.ON3,
                region=DataSourceRegion.US,
                base_url="https://www.on3.com"
            )
        )

        normalized_df = self.pipeline.normalize_on3_to_player_recruiting(
            rankings=[sample_rank],
            source="on3_industry"
        )

        if verbose:
            print(f"\nDataFrame columns ({len(normalized_df.columns)}):")
            print(f"  {list(normalized_df.columns)}")

        is_valid, issues = self.validate_dataframe_schema(
            df=normalized_df,
            table_name="player_recruiting",
            strict=False  # Column order may vary
        )

        if is_valid:
            print("[OK] Schema matches player_recruiting")
        else:
            print(f"[ERROR] {len(issues)} schema issues found:")
            for issue in issues:
                print(f"  - {issue}")

        print()
        return is_valid

    def validate_all(self, verbose: bool = False) -> bool:
        """
        Run all schema validations.

        Args:
            verbose: Show detailed output

        Returns:
            True if all validations pass
        """
        print("\n" + "=" * 80)
        print("RECRUITING PIPELINE SCHEMA VALIDATION")
        print("=" * 80)

        raw_valid = self.validate_on3_raw_pipeline(verbose=verbose)
        normalized_valid = self.validate_player_recruiting_pipeline(verbose=verbose)

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if raw_valid and normalized_valid:
            print("[SUCCESS] All schemas valid")
            return True
        else:
            print("[FAILURE] Schema validation failed")
            if not raw_valid:
                print("  - on3_player_rankings_raw: FAILED")
            if not normalized_valid:
                print("  - player_recruiting: FAILED")
            return False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate recruiting data pipeline schemas"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/duckdb/recruiting.duckdb",
        help="Path to DuckDB file"
    )

    args = parser.parse_args()

    validator = SchemaValidator(db_path=args.db)

    try:
        success = validator.validate_all(verbose=args.verbose)
        sys.exit(0 if success else 1)
    finally:
        validator.close()


if __name__ == "__main__":
    main()
