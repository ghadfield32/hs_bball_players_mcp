"""
QA and Validation Queries for Recruiting Data

Comprehensive validation suite for recruiting data quality:
- Count validation (raw vs normalized)
- Rank monotonicity checks
- Coverage gap analysis
- Data completeness metrics
- Spot-check top players

Usage:
    python scripts/qa_recruiting_data.py
    python scripts/qa_recruiting_data.py --year 2024
    python scripts/qa_recruiting_data.py --verbose

Author: Claude Code
Date: 2025-11-15
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
import pandas as pd


class RecruitingDataQA:
    """QA validator for recruiting data."""

    def __init__(self, db_path: str = "data/duckdb/recruiting.duckdb"):
        """
        Initialize QA validator.

        Args:
            db_path: Path to DuckDB file
        """
        self.conn = duckdb.connect(db_path)

    def check_count_consistency(self, year: int = None) -> pd.DataFrame:
        """
        Validate count consistency between raw and normalized tables.

        Args:
            year: Optional year filter

        Returns:
            DataFrame showing count comparison
        """
        print("\n" + "=" * 80)
        print("COUNT CONSISTENCY CHECK")
        print("=" * 80)

        query = """
        SELECT
            COALESCE(r.class_year, p.class_year) as year,
            COUNT(DISTINCT r.raw_id) as raw_count,
            COUNT(DISTINCT p.recruiting_id) as normalized_count,
            COUNT(DISTINCT r.raw_id) - COUNT(DISTINCT p.recruiting_id) as diff,
            CASE
                WHEN COUNT(DISTINCT r.raw_id) = COUNT(DISTINCT p.recruiting_id) THEN 'OK'
                ELSE 'MISMATCH'
            END as status
        FROM on3_player_rankings_raw r
        FULL OUTER JOIN player_recruiting p
            ON r.class_year = p.class_year AND r.external_id = p.external_id
        WHERE 1=1
        """

        if year:
            query += f" AND COALESCE(r.class_year, p.class_year) = {year}"

        query += """
        GROUP BY COALESCE(r.class_year, p.class_year)
        ORDER BY year
        """

        df = self.conn.execute(query).df()
        print(df.to_string(index=False))
        print()

        return df

    def check_rank_monotonicity(self, year: int = None) -> pd.DataFrame:
        """
        Validate that national ranks are sequential (no gaps).

        Args:
            year: Optional year filter

        Returns:
            DataFrame showing rank gaps
        """
        print("\n" + "=" * 80)
        print("RANK MONOTONICITY CHECK")
        print("=" * 80)

        query = """
        WITH ranked AS (
            SELECT
                class_year,
                national_rank,
                LAG(national_rank) OVER (PARTITION BY class_year ORDER BY national_rank) as prev_rank
            FROM player_recruiting
            WHERE national_rank IS NOT NULL
        """

        if year:
            query += f" AND class_year = {year}"

        query += """
        )
        SELECT
            class_year,
            national_rank,
            prev_rank,
            national_rank - prev_rank as gap
        FROM ranked
        WHERE national_rank - prev_rank > 1
        ORDER BY class_year, national_rank
        """

        df = self.conn.execute(query).df()

        if df.empty:
            print("OK - No ranking gaps found")
        else:
            print(f"WARNING - Found {len(df)} ranking gaps:")
            print(df.to_string(index=False))

        print()
        return df

    def check_data_completeness(self, year: int = None) -> pd.DataFrame:
        """
        Check completeness of key fields.

        Args:
            year: Optional year filter

        Returns:
            DataFrame with completeness metrics
        """
        print("\n" + "=" * 80)
        print("DATA COMPLETENESS CHECK")
        print("=" * 80)

        query = """
        SELECT
            class_year,
            COUNT(*) as total_players,
            SUM(CASE WHEN player_name IS NOT NULL THEN 1 ELSE 0 END) as has_name,
            SUM(CASE WHEN national_rank IS NOT NULL THEN 1 ELSE 0 END) as has_rank,
            SUM(CASE WHEN stars IS NOT NULL THEN 1 ELSE 0 END) as has_stars,
            SUM(CASE WHEN rating_0_1 IS NOT NULL THEN 1 ELSE 0 END) as has_rating,
            SUM(CASE WHEN height_inches IS NOT NULL THEN 1 ELSE 0 END) as has_height,
            SUM(CASE WHEN position IS NOT NULL THEN 1 ELSE 0 END) as has_position,
            SUM(CASE WHEN high_school_name IS NOT NULL THEN 1 ELSE 0 END) as has_school,
            ROUND(100.0 * SUM(CASE WHEN national_rank IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_ranked,
            ROUND(100.0 * SUM(CASE WHEN height_inches IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_height
        FROM player_recruiting
        WHERE 1=1
        """

        if year:
            query += f" AND class_year = {year}"

        query += """
        GROUP BY class_year
        ORDER BY class_year
        """

        df = self.conn.execute(query).df()
        print(df.to_string(index=False))
        print()

        return df

    def spot_check_top_players(self, year: int, top_n: int = 10) -> pd.DataFrame:
        """
        Spot-check top N players for a year.

        Args:
            year: Year to check
            top_n: Number of top players

        Returns:
            DataFrame with top players
        """
        print("\n" + "=" * 80)
        print(f"TOP {top_n} PLAYERS FOR {year}")
        print("=" * 80)

        query = f"""
        SELECT
            national_rank,
            player_name,
            position,
            height_inches,
            stars,
            ROUND(rating_0_1, 3) as rating,
            high_school_name,
            hometown_city,
            hometown_state,
            CASE WHEN is_committed THEN committed_school ELSE 'Uncommitted' END as status
        FROM player_recruiting
        WHERE class_year = {year}
            AND national_rank IS NOT NULL
        ORDER BY national_rank
        LIMIT {top_n}
        """

        df = self.conn.execute(query).df()
        print(df.to_string(index=False))
        print()

        return df

    def check_coverage_gaps(self) -> pd.DataFrame:
        """
        Identify years with no data or low coverage.

        Returns:
            DataFrame showing coverage gaps
        """
        print("\n" + "=" * 80)
        print("COVERAGE GAP ANALYSIS")
        print("=" * 80)

        query = """
        WITH year_range AS (
            SELECT UNNEST(GENERATE_SERIES(2020, 2027)) as year
        )
        SELECT
            yr.year,
            COALESCE(c.n_players, 0) as players_loaded,
            CASE
                WHEN c.n_players IS NULL THEN 'NO DATA'
                WHEN c.n_players < 50 THEN 'LOW COVERAGE'
                ELSE 'OK'
            END as status,
            c.notes
        FROM year_range yr
        LEFT JOIN recruiting_coverage c
            ON yr.year = c.class_year AND c.source = 'on3_industry'
        ORDER BY yr.year
        """

        df = self.conn.execute(query).df()
        print(df.to_string(index=False))
        print()

        return df

    def validate_all(self, year: int = None, verbose: bool = False) -> bool:
        """
        Run all validation checks.

        Args:
            year: Optional year filter
            verbose: Show detailed output

        Returns:
            True if all validations pass (no issues), False otherwise
        """
        print("\n" + "=" * 80)
        print("RECRUITING DATA QA VALIDATION")
        if year:
            print(f"Year: {year}")
        print("=" * 80)

        # Run all checks
        count_df = self.check_count_consistency(year=year)
        rank_df = self.check_rank_monotonicity(year=year)
        completeness_df = self.check_data_completeness(year=year)

        if verbose:
            if year:
                self.spot_check_top_players(year=year)
            else:
                # Spot-check most recent year
                recent_year = completeness_df['class_year'].max()
                self.spot_check_top_players(year=int(recent_year))

        if not year:
            self.check_coverage_gaps()

        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        total_issues = 0

        # Count consistency
        count_mismatches = (count_df['status'] == 'MISMATCH').sum()
        if count_mismatches > 0:
            print(f"[WARNING] {count_mismatches} years with count mismatches")
            total_issues += count_mismatches
        else:
            print("[OK] All counts consistent between raw and normalized tables")

        # Rank monotonicity
        if not rank_df.empty:
            print(f"[WARNING] {len(rank_df)} ranking gaps found")
            total_issues += len(rank_df)
        else:
            print("[OK] All rankings sequential (no gaps)")

        # Data completeness
        avg_rank_pct = completeness_df['pct_ranked'].mean()
        avg_height_pct = completeness_df['pct_height'].mean()
        print(f"[INFO] Average data completeness: {avg_rank_pct:.1f}% ranked, {avg_height_pct:.1f}% with height")

        print("\n" + "=" * 80)
        if total_issues == 0:
            print("[SUCCESS] All validation checks passed!")
        else:
            print(f"[WARNING] Found {total_issues} issues - review output above")
        print("=" * 80 + "\n")

        # Return True only if no issues found
        return total_issues == 0

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="QA validation for recruiting data")
    parser.add_argument(
        "--year",
        type=int,
        help="Filter by year (optional)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including top players"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/duckdb/recruiting.duckdb",
        help="Path to DuckDB file"
    )

    args = parser.parse_args()

    qa = RecruitingDataQA(db_path=args.db)

    try:
        success = qa.validate_all(year=args.year, verbose=args.verbose)
        # Exit with non-zero code if validation failed (for CI/CD pipelines)
        sys.exit(0 if success else 1)
    finally:
        qa.close()


if __name__ == "__main__":
    main()
