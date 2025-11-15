"""
Schema Validation Utilities for HS Forecasting

Validates that data from various sources matches the expected schemas
for the dataset_builder pipeline. Provides detailed validation reports
and suggestions for fixing schema mismatches.

Created: 2025-11-15
Phase: 14 (Data Validation & Export)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SchemaValidationResult:
    """Result of schema validation check."""

    is_valid: bool
    source_name: str
    total_columns: int
    missing_required: List[str]
    missing_optional: List[str]
    extra_columns: List[str]
    type_mismatches: Dict[str, str]
    null_counts: Dict[str, int]
    warnings: List[str]
    suggestions: List[str]

    def __str__(self) -> str:
        """Generate human-readable validation report."""
        lines = [
            f"\n{'='*70}",
            f"Schema Validation Report: {self.source_name}",
            f"{'='*70}",
            f"Status: {'✅ VALID' if self.is_valid else '❌ INVALID'}",
            f"Total Columns: {self.total_columns}",
            "",
        ]

        if self.missing_required:
            lines.append("❌ Missing Required Columns:")
            for col in self.missing_required:
                lines.append(f"   - {col}")
            lines.append("")

        if self.missing_optional:
            lines.append("⚠️  Missing Optional Columns:")
            for col in self.missing_optional:
                lines.append(f"   - {col}")
            lines.append("")

        if self.extra_columns:
            lines.append("ℹ️  Extra Columns (will be ignored):")
            for col in self.extra_columns:
                lines.append(f"   - {col}")
            lines.append("")

        if self.type_mismatches:
            lines.append("⚠️  Type Mismatches:")
            for col, msg in self.type_mismatches.items():
                lines.append(f"   - {col}: {msg}")
            lines.append("")

        if self.null_counts:
            lines.append("ℹ️  Null Counts:")
            for col, count in sorted(self.null_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"   - {col}: {count} nulls")
            lines.append("")

        if self.warnings:
            lines.append("⚠️  Warnings:")
            for warning in self.warnings:
                lines.append(f"   - {warning}")
            lines.append("")

        if self.suggestions:
            lines.append("💡 Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"   - {suggestion}")
            lines.append("")

        lines.append(f"{'='*70}\n")
        return "\n".join(lines)


def validate_maxpreps_schema(df: pd.DataFrame) -> SchemaValidationResult:
    """
    Validate MaxPreps DataFrame schema.

    Expected schema for MaxPreps data:
        Required:
            - player_name (str)
            - grad_year (int)
            - games_played (int)
            - pts_per_game (float)

        Optional but recommended:
            - state (str)
            - team_name (str)
            - reb_per_game (float)
            - ast_per_game (float)
            - stl_per_game (float)
            - blk_per_game (float)
            - tov_per_game (float)
            - fg_pct (float)
            - three_pct (float)
            - ft_pct (float)
            - fga_per_game (float)
            - three_att_per_game (float)
            - fta_per_game (float)

    Args:
        df: MaxPreps DataFrame to validate

    Returns:
        SchemaValidationResult with detailed validation info
    """
    required_cols = {"player_name", "grad_year", "games_played", "pts_per_game"}
    optional_cols = {
        "state",
        "team_name",
        "reb_per_game",
        "ast_per_game",
        "stl_per_game",
        "blk_per_game",
        "tov_per_game",
        "fg_pct",
        "three_pct",
        "ft_pct",
        "fga_per_game",
        "three_att_per_game",
        "fta_per_game",
    }

    return _validate_schema(
        df=df,
        source_name="MaxPreps",
        required_cols=required_cols,
        optional_cols=optional_cols,
        expected_types={
            "player_name": "object",
            "grad_year": ["int64", "Int64", "int32"],
            "state": "object",
            "team_name": "object",
            "games_played": ["int64", "Int64", "int32"],
            "pts_per_game": ["float64", "Float64", "float32"],
            "reb_per_game": ["float64", "Float64", "float32"],
            "ast_per_game": ["float64", "Float64", "float32"],
        },
    )


def validate_recruiting_schema(df: pd.DataFrame) -> SchemaValidationResult:
    """
    Validate recruiting DataFrame schema.

    Expected schema for recruiting data:
        Required:
            - player_name (str)
            - grad_year (int)

        Optional but recommended:
            - position (str)
            - height_inches (int)
            - weight_lbs (int)
            - stars (int)
            - composite_rating (float)
            - national_rank (int)
            - state_rank (int)
            - position_rank (int)
            - state (str)
            - committed_school (str)
            - committed_conference (str)

    Args:
        df: Recruiting DataFrame to validate

    Returns:
        SchemaValidationResult with detailed validation info
    """
    required_cols = {"player_name", "grad_year"}
    optional_cols = {
        "position", "pos",
        "height_inches", "height_in",
        "weight_lbs",
        "stars",
        "composite_rating", "rating",
        "national_rank",
        "state_rank",
        "position_rank",
        "state",
        "committed_school", "school",
        "committed_conference", "conference",
    }

    return _validate_schema(
        df=df,
        source_name="Recruiting",
        required_cols=required_cols,
        optional_cols=optional_cols,
        expected_types={
            "player_name": "object",
            "grad_year": ["int64", "Int64", "int32"],
            "position": "object",
            "height_inches": ["int64", "Int64", "int32"],
            "weight_lbs": ["int64", "Int64", "int32"],
            "stars": ["int64", "Int64", "int32"],
            "composite_rating": ["float64", "Float64", "float32"],
        },
    )


def validate_eybl_schema(df: pd.DataFrame) -> SchemaValidationResult:
    """
    Validate EYBL DataFrame schema.

    Expected schema for EYBL data:
        Required:
            - player_name (str)
            - gp or games_played (int)

        Optional but recommended:
            - pts_per_game or points_per_game (float)
            - reb_per_game or rebounds_per_game (float)
            - ast_per_game or assists_per_game (float)
            - three_pct (float)

    Args:
        df: EYBL DataFrame to validate

    Returns:
        SchemaValidationResult with detailed validation info
    """
    # EYBL can have either naming convention
    required_cols = {"player_name"}
    optional_cols = {
        "gp", "games_played",
        "pts_per_game", "points_per_game",
        "reb_per_game", "rebounds_per_game",
        "ast_per_game", "assists_per_game",
        "stl_per_game", "steals_per_game",
        "blk_per_game", "blocks_per_game",
        "three_pct", "three_point_percentage",
    }

    # Special check: must have EITHER gp OR games_played
    has_gp = "gp" in df.columns or "games_played" in df.columns

    result = _validate_schema(
        df=df,
        source_name="EYBL",
        required_cols=required_cols,
        optional_cols=optional_cols,
        expected_types={
            "player_name": "object",
            "gp": ["int64", "Int64", "int32"],
            "games_played": ["int64", "Int64", "int32"],
            "pts_per_game": ["float64", "Float64", "float32"],
            "points_per_game": ["float64", "Float64", "float32"],
        },
    )

    # Add custom validation for games_played column
    if not has_gp:
        result.is_valid = False
        result.missing_required.append("gp OR games_played")
        result.suggestions.append(
            "EYBL data must have either 'gp' or 'games_played' column"
        )

    return result


def _validate_schema(
    df: pd.DataFrame,
    source_name: str,
    required_cols: Set[str],
    optional_cols: Set[str],
    expected_types: Optional[Dict[str, any]] = None,
) -> SchemaValidationResult:
    """
    Internal helper to validate DataFrame schema.

    Args:
        df: DataFrame to validate
        source_name: Name of the data source
        required_cols: Set of required column names
        optional_cols: Set of optional column names
        expected_types: Dict of column_name -> expected_dtype(s)

    Returns:
        SchemaValidationResult
    """
    if df.empty:
        return SchemaValidationResult(
            is_valid=False,
            source_name=source_name,
            total_columns=0,
            missing_required=list(required_cols),
            missing_optional=[],
            extra_columns=[],
            type_mismatches={},
            null_counts={},
            warnings=["DataFrame is empty"],
            suggestions=["Ensure data source is returning non-empty results"],
        )

    actual_cols = set(df.columns)
    all_expected_cols = required_cols | optional_cols

    # Find missing and extra columns
    missing_required = [col for col in required_cols if col not in actual_cols]
    missing_optional = [col for col in optional_cols if col not in actual_cols]
    extra_columns = [col for col in actual_cols if col not in all_expected_cols]

    # Check types
    type_mismatches = {}
    if expected_types:
        for col, expected in expected_types.items():
            if col in actual_cols:
                actual_type = str(df[col].dtype)
                # Handle list of acceptable types
                if isinstance(expected, list):
                    if actual_type not in expected:
                        type_mismatches[col] = (
                            f"Expected one of {expected}, got {actual_type}"
                        )
                else:
                    if actual_type != expected:
                        type_mismatches[col] = f"Expected {expected}, got {actual_type}"

    # Count nulls
    null_counts = {}
    for col in actual_cols:
        null_count = df[col].isna().sum()
        if null_count > 0:
            null_counts[col] = null_count

    # Generate warnings
    warnings = []
    if len(df) < 10:
        warnings.append(f"Low row count: {len(df)} rows (expected at least 10)")

    # High null percentage
    for col, null_count in null_counts.items():
        null_pct = (null_count / len(df)) * 100
        if null_pct > 50 and col in required_cols:
            warnings.append(
                f"Required column '{col}' has {null_pct:.1f}% nulls (>{null_count}/{len(df)})"
            )

    # Generate suggestions
    suggestions = []
    if missing_required:
        suggestions.append(
            f"Add missing required columns: {', '.join(missing_required)}"
        )

    if type_mismatches:
        suggestions.append(
            "Convert columns to expected types using pd.astype() or pd.to_numeric()"
        )

    # Determine if valid
    is_valid = len(missing_required) == 0 and len(type_mismatches) == 0

    return SchemaValidationResult(
        is_valid=is_valid,
        source_name=source_name,
        total_columns=len(actual_cols),
        missing_required=missing_required,
        missing_optional=missing_optional,
        extra_columns=extra_columns,
        type_mismatches=type_mismatches,
        null_counts=null_counts,
        warnings=warnings,
        suggestions=suggestions,
    )


def generate_schema_report(
    maxpreps_df: Optional[pd.DataFrame] = None,
    recruiting_df: Optional[pd.DataFrame] = None,
    eybl_df: Optional[pd.DataFrame] = None,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate comprehensive schema validation report for all data sources.

    Args:
        maxpreps_df: Optional MaxPreps DataFrame
        recruiting_df: Optional recruiting DataFrame
        eybl_df: Optional EYBL DataFrame
        output_path: Optional path to save report as text file

    Returns:
        String containing full validation report
    """
    logger.info("Generating schema validation report")

    report_lines = [
        "\n" + "=" * 70,
        "HS FORECASTING DATA VALIDATION REPORT",
        "=" * 70,
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    results = []

    # Validate each source
    if maxpreps_df is not None:
        result = validate_maxpreps_schema(maxpreps_df)
        results.append(result)
        report_lines.append(str(result))

    if recruiting_df is not None:
        result = validate_recruiting_schema(recruiting_df)
        results.append(result)
        report_lines.append(str(result))

    if eybl_df is not None:
        result = validate_eybl_schema(eybl_df)
        results.append(result)
        report_lines.append(str(result))

    # Summary
    report_lines.append("=" * 70)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 70)

    total_sources = len(results)
    valid_sources = sum(1 for r in results if r.is_valid)

    report_lines.append(f"Total sources validated: {total_sources}")
    report_lines.append(f"Valid sources: {valid_sources}")
    report_lines.append(f"Invalid sources: {total_sources - valid_sources}")
    report_lines.append("")

    if valid_sources == total_sources:
        report_lines.append("✅ All sources are valid and ready for processing!")
    else:
        report_lines.append("❌ Some sources have validation issues. Review details above.")

    report_lines.append("=" * 70 + "\n")

    report_text = "\n".join(report_lines)

    # Save to file if requested
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text)
        logger.info(f"Schema validation report saved to {output_path}")

    return report_text


def check_join_compatibility(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    join_keys: List[str],
    source1_name: str = "Source1",
    source2_name: str = "Source2",
) -> Dict[str, any]:
    """
    Check if two DataFrames can be joined successfully on specified keys.

    Args:
        df1: First DataFrame
        df2: Second DataFrame
        join_keys: List of column names to join on
        source1_name: Name of first source
        source2_name: Name of second source

    Returns:
        Dict with compatibility analysis
    """
    results = {
        "can_join": True,
        "issues": [],
        "statistics": {},
    }

    # Check if join keys exist
    for key in join_keys:
        if key not in df1.columns:
            results["can_join"] = False
            results["issues"].append(f"Join key '{key}' missing in {source1_name}")

        if key not in df2.columns:
            results["can_join"] = False
            results["issues"].append(f"Join key '{key}' missing in {source2_name}")

    if not results["can_join"]:
        return results

    # Check for null values in join keys
    for key in join_keys:
        null_count1 = df1[key].isna().sum()
        null_count2 = df2[key].isna().sum()

        if null_count1 > 0:
            results["issues"].append(
                f"Warning: {source1_name}['{key}'] has {null_count1} null values"
            )

        if null_count2 > 0:
            results["issues"].append(
                f"Warning: {source2_name}['{key}'] has {null_count2} null values"
            )

    # Estimate join matches
    for key in join_keys:
        unique1 = set(df1[key].dropna().unique())
        unique2 = set(df2[key].dropna().unique())

        overlap = unique1 & unique2
        overlap_pct1 = (len(overlap) / len(unique1)) * 100 if unique1 else 0
        overlap_pct2 = (len(overlap) / len(unique2)) * 100 if unique2 else 0

        results["statistics"][key] = {
            f"{source1_name}_unique": len(unique1),
            f"{source2_name}_unique": len(unique2),
            "overlap": len(overlap),
            f"{source1_name}_overlap_pct": round(overlap_pct1, 1),
            f"{source2_name}_overlap_pct": round(overlap_pct2, 1),
        }

        if overlap_pct1 < 10 or overlap_pct2 < 10:
            results["issues"].append(
                f"Low overlap on '{key}': {overlap_pct1:.1f}% ({source1_name}) "
                f"and {overlap_pct2:.1f}% ({source2_name})"
            )

    return results
