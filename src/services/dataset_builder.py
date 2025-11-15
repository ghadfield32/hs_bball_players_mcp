"""
Dataset Builder Service

Builds comprehensive high school basketball player datasets by merging data from:
1. MaxPreps - High school season stats
2. EYBL - Elite circuit stats
3. Recruiting services - Rankings, ratings, offers

Output: Unified Parquet datasets with player_uid joins for multi-year tracking.

Author: Claude Code
Date: 2025-11-15
Phase: 15 - Multi-Year HS Dataset Pipeline
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..models.recruiting import ConferenceLevel, OfferStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HSDatasetBuilder:
    """
    High School Basketball Player Dataset Builder.

    Merges data from multiple sources into unified HS player datasets.
    Handles player identity resolution, stat normalization, and quality flags.
    """

    def __init__(self, output_dir: str = "data/processed/hs_player_seasons"):
        """
        Initialize dataset builder.

        Args:
            output_dir: Directory for output Parquet files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"HSDatasetBuilder initialized with output_dir={output_dir}")

    def build_dataset(
        self,
        grad_year: int,
        maxpreps_data: Optional[pd.DataFrame] = None,
        eybl_data: Optional[pd.DataFrame] = None,
        recruiting_data: Optional[pd.DataFrame] = None,
        offers_data: Optional[pd.DataFrame] = None,
        output_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Build unified HS player dataset for a specific graduation year.

        Merge process:
        1. Start with recruiting data (if available) - most complete player identity
        2. Left join MaxPreps stats (HS stats)
        3. Left join EYBL stats (circuit stats)
        4. Left join offers data (college interest)
        5. Calculate derived fields (played_eybl, power_6_offers, etc.)
        6. Add quality flags

        Args:
            grad_year: High school graduation year
            maxpreps_data: MaxPreps season stats DataFrame
            eybl_data: EYBL season stats DataFrame
            recruiting_data: Recruiting rankings DataFrame
            offers_data: College offers DataFrame
            output_path: Optional custom output path

        Returns:
            Unified DataFrame with merged data
        """
        logger.info(f"Building HS dataset for grad year {grad_year}")

        # Start with recruiting data as the base (most complete player identities)
        if recruiting_data is not None and not recruiting_data.empty:
            logger.info(f"Starting with {len(recruiting_data)} players from recruiting data")
            base_df = recruiting_data.copy()
            base_df = base_df.rename(columns={
                'player_name': 'name',
                'rank_national': 'national_rank',
                'rank_position': 'position_rank',
                'rank_state': 'state_rank',
                'rating': 'composite_rating',
            })
        else:
            # If no recruiting data, start with MaxPreps
            logger.warning("No recruiting data provided, starting with MaxPreps as base")
            if maxpreps_data is not None and not maxpreps_data.empty:
                base_df = maxpreps_data.copy()
                base_df['player_uid'] = base_df.get('player_id', None)
            else:
                logger.error("No base data provided (recruiting or MaxPreps)")
                return pd.DataFrame()

        # Ensure player_uid exists (required for joins)
        if 'player_uid' not in base_df.columns:
            logger.warning("player_uid not found in base data, using player_id as fallback")
            base_df['player_uid'] = base_df.get('player_id', None)

        # Filter by grad year
        if 'class_year' in base_df.columns:
            base_df = base_df[base_df['class_year'] == grad_year].copy()
        elif 'grad_year' in base_df.columns:
            base_df = base_df[base_df['grad_year'] == grad_year].copy()

        logger.info(f"Base dataset after grad year filter: {len(base_df)} players")

        # Join MaxPreps stats (HS stats)
        if maxpreps_data is not None and not maxpreps_data.empty:
            base_df = self._merge_maxpreps_stats(base_df, maxpreps_data, grad_year)

        # Join EYBL stats (circuit stats)
        if eybl_data is not None and not eybl_data.empty:
            base_df = self._merge_eybl_stats(base_df, eybl_data)

        # Join college offers
        if offers_data is not None and not offers_data.empty:
            base_df = self._merge_offers(base_df, offers_data)

        # Calculate derived fields
        base_df = self._calculate_derived_fields(base_df)

        # Add metadata
        base_df['dataset_created_at'] = datetime.now()
        base_df['grad_year'] = grad_year

        # Save to Parquet
        if output_path:
            save_path = Path(output_path)
        else:
            save_path = self.output_dir / f"hs_player_seasons_{grad_year}.parquet"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        base_df.to_parquet(save_path, index=False, compression='snappy')

        logger.info(
            f"Dataset saved to {save_path}",
            shape=base_df.shape,
            players=len(base_df),
            columns=len(base_df.columns)
        )

        return base_df

    def _merge_maxpreps_stats(
        self,
        base_df: pd.DataFrame,
        maxpreps_data: pd.DataFrame,
        grad_year: int
    ) -> pd.DataFrame:
        """
        Merge MaxPreps HS stats into base dataset.

        Args:
            base_df: Base dataset
            maxpreps_data: MaxPreps stats DataFrame
            grad_year: Graduation year for filtering

        Returns:
            Merged DataFrame
        """
        logger.info(f"Merging MaxPreps stats ({len(maxpreps_data)} records)")

        # Filter MaxPreps by grad year if available
        mp_df = maxpreps_data.copy()
        if 'grad_year' in mp_df.columns:
            mp_df = mp_df[mp_df['grad_year'] == grad_year].copy()

        # Standardize column names for HS stats
        mp_df = mp_df.rename(columns={
            'points_per_game': 'pts_per_g',
            'rebounds_per_game': 'reb_per_g',
            'assists_per_game': 'ast_per_g',
            'steals_per_game': 'stl_per_g',
            'blocks_per_game': 'blk_per_g',
            'field_goal_percentage': 'fg_pct',
            'three_point_percentage': 'fg3_pct',
            'free_throw_percentage': 'ft_pct',
            'turnovers_per_game': 'tov_per_g',
            'games_played': 'gp',
            'minutes_played': 'mpg',
        })

        # Select HS stat columns to join
        hs_cols = [
            'player_uid', 'pts_per_g', 'reb_per_g', 'ast_per_g',
            'stl_per_g', 'blk_per_g', 'fg_pct', 'fg3_pct', 'ft_pct',
            'tov_per_g', 'gp', 'mpg', 'school_name', 'school_state'
        ]

        # Only keep columns that exist
        hs_cols = [c for c in hs_cols if c in mp_df.columns]
        mp_df = mp_df[hs_cols].drop_duplicates(subset=['player_uid'])

        # Left join on player_uid
        merged = base_df.merge(
            mp_df,
            on='player_uid',
            how='left',
            suffixes=('', '_maxpreps')
        )

        logger.info(
            f"MaxPreps merge complete",
            before=len(base_df),
            after=len(merged),
            matched=merged['pts_per_g'].notna().sum()
        )

        return merged

    def _merge_eybl_stats(
        self,
        base_df: pd.DataFrame,
        eybl_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge EYBL circuit stats into base dataset.

        Args:
            base_df: Base dataset
            eybl_data: EYBL stats DataFrame

        Returns:
            Merged DataFrame
        """
        logger.info(f"Merging EYBL stats ({len(eybl_data)} records)")

        # Standardize EYBL column names
        eybl_df = eybl_data.copy()
        eybl_df = eybl_df.rename(columns={
            'points_per_game': 'eybl_pts_per_g',
            'rebounds_per_game': 'eybl_reb_per_g',
            'assists_per_game': 'eybl_ast_per_g',
            'steals_per_game': 'eybl_stl_per_g',
            'blocks_per_game': 'eybl_blk_per_g',
            'field_goal_percentage': 'eybl_fg_pct',
            'three_point_percentage': 'eybl_fg3_pct',
            'free_throw_percentage': 'eybl_ft_pct',
            'games_played': 'eybl_gp',
            'team_name': 'eybl_team',
        })

        # Select EYBL columns
        eybl_cols = [
            'player_uid', 'eybl_pts_per_g', 'eybl_reb_per_g',
            'eybl_ast_per_g', 'eybl_stl_per_g', 'eybl_blk_per_g',
            'eybl_fg_pct', 'eybl_fg3_pct', 'eybl_ft_pct',
            'eybl_gp', 'eybl_team'
        ]

        # Only keep columns that exist
        eybl_cols = [c for c in eybl_cols if c in eybl_df.columns]
        eybl_df = eybl_df[eybl_cols].drop_duplicates(subset=['player_uid'])

        # Left join on player_uid
        merged = base_df.merge(
            eybl_df,
            on='player_uid',
            how='left'
        )

        logger.info(
            f"EYBL merge complete",
            before=len(base_df),
            after=len(merged),
            matched=merged['eybl_pts_per_g'].notna().sum()
        )

        return merged

    def _merge_offers(
        self,
        base_df: pd.DataFrame,
        offers_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge college offers data into base dataset.

        Aggregates offers per player:
        - Total offer count
        - Power 6 offer count
        - High major offer count
        - Top offer by conference level

        Args:
            base_df: Base dataset
            offers_data: College offers DataFrame

        Returns:
            Merged DataFrame
        """
        logger.info(f"Merging college offers ({len(offers_data)} records)")

        # Filter to active offers only
        offers_df = offers_data.copy()
        if 'offer_status' in offers_df.columns:
            offers_df = offers_df[
                offers_df['offer_status'].isin(['offered', 'committed', 'signed'])
            ].copy()

        # Group by player_uid and aggregate
        offer_stats = offers_df.groupby('player_uid').agg(
            total_offers=('college', 'count'),
            power_6_offers=('conference_level', lambda x: (x == 'power_6').sum()),
            high_major_offers=('conference_level', lambda x: (x.isin(['power_6', 'high_major'])).sum()),
            committed_to=('college', lambda x: x.iloc[0] if len(x) > 0 else None),
        ).reset_index()

        # Left join
        merged = base_df.merge(
            offer_stats,
            on='player_uid',
            how='left'
        )

        # Fill NaN with 0 for offer counts
        merged['total_offers'] = merged['total_offers'].fillna(0).astype(int)
        merged['power_6_offers'] = merged['power_6_offers'].fillna(0).astype(int)
        merged['high_major_offers'] = merged['high_major_offers'].fillna(0).astype(int)

        logger.info(
            f"Offers merge complete",
            matched=merged['total_offers'].gt(0).sum()
        )

        return merged

    def _calculate_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate derived fields from merged data.

        Derived fields:
        - played_eybl: Boolean if player has EYBL stats
        - has_hs_stats: Boolean if player has HS stats
        - has_recruiting_profile: Boolean if player has recruiting data
        - ts_pct: True shooting percentage (if FT data available)
        - efg_pct: Effective FG% (if 3PT data available)
        - ast_to_ratio: Assist to turnover ratio

        Args:
            df: Merged DataFrame

        Returns:
            DataFrame with derived fields
        """
        logger.info("Calculating derived fields")

        # Boolean flags for data availability
        df['played_eybl'] = df.get('eybl_pts_per_g', pd.Series([pd.NA] * len(df))).notna()
        df['has_hs_stats'] = df.get('pts_per_g', pd.Series([pd.NA] * len(df))).notna()
        df['has_recruiting_profile'] = df.get('composite_rating', pd.Series([pd.NA] * len(df))).notna()

        # True Shooting % = PTS / (2 * (FGA + 0.44 * FTA))
        # Simplified: If we only have percentages, estimate from PPG
        # More accurate if we have FGA, FTA data
        if 'fg_pct' in df.columns and 'fg3_pct' in df.columns and 'ft_pct' in df.columns:
            # Estimate TS% using available percentages (rough approximation)
            df['ts_pct'] = (
                df['fg_pct'].fillna(0) * 0.5 +
                df['fg3_pct'].fillna(0) * 0.2 +
                df['ft_pct'].fillna(0) * 0.3
            )

        # Effective FG% = (FGM + 0.5 * 3PM) / FGA
        # Simplified using percentages
        if 'fg_pct' in df.columns and 'fg3_pct' in df.columns:
            df['efg_pct'] = df['fg_pct'].fillna(0) + (df['fg3_pct'].fillna(0) * 0.15)

        # Assist to Turnover ratio
        if 'ast_per_g' in df.columns and 'tov_per_g' in df.columns:
            df['ast_to_ratio'] = df['ast_per_g'] / df['tov_per_g'].replace(0, pd.NA)

        # Data completeness score (0-1)
        completeness_fields = [
            'has_recruiting_profile', 'has_hs_stats', 'played_eybl',
            'total_offers', 'school_name', 'position'
        ]
        available_fields = [f for f in completeness_fields if f in df.columns]

        if available_fields:
            df['data_completeness'] = (
                df[available_fields].notna().sum(axis=1) / len(available_fields)
            )

        logger.info(
            "Derived fields calculated",
            played_eybl=df.get('played_eybl', pd.Series([False])).sum(),
            has_hs_stats=df.get('has_hs_stats', pd.Series([False])).sum(),
            has_recruiting_profile=df.get('has_recruiting_profile', pd.Series([False])).sum()
        )

        return df

    def build_multi_year_datasets(
        self,
        start_year: int,
        end_year: int,
        maxpreps_data: Optional[pd.DataFrame] = None,
        eybl_data: Optional[pd.DataFrame] = None,
        recruiting_data: Optional[pd.DataFrame] = None,
        offers_data: Optional[pd.DataFrame] = None,
    ) -> Dict[int, pd.DataFrame]:
        """
        Build HS datasets for multiple graduation years.

        Args:
            start_year: Starting graduation year (inclusive)
            end_year: Ending graduation year (inclusive)
            maxpreps_data: MaxPreps season stats DataFrame
            eybl_data: EYBL season stats DataFrame
            recruiting_data: Recruiting rankings DataFrame
            offers_data: College offers DataFrame

        Returns:
            Dictionary mapping grad_year -> DataFrame
        """
        logger.info(f"Building multi-year datasets from {start_year} to {end_year}")

        datasets = {}

        for year in range(start_year, end_year + 1):
            logger.info(f"\n{'='*60}\nProcessing graduation year: {year}\n{'='*60}")

            # Build dataset for this year
            df = self.build_dataset(
                grad_year=year,
                maxpreps_data=maxpreps_data,
                eybl_data=eybl_data,
                recruiting_data=recruiting_data,
                offers_data=offers_data
            )

            datasets[year] = df

        # Log summary
        logger.info("\n" + "="*60)
        logger.info("Multi-year dataset build complete")
        logger.info("="*60)
        for year, df in datasets.items():
            logger.info(
                f"  {year}: {len(df)} players, {len(df.columns)} columns"
            )

        return datasets

    def get_coverage_report(self, df: pd.DataFrame) -> Dict:
        """
        Generate coverage report for a dataset.

        Args:
            df: Dataset to analyze

        Returns:
            Dictionary with coverage metrics
        """
        total_players = len(df)

        report = {
            'total_players': total_players,
            'with_recruiting_info': int(df.get('has_recruiting_profile', pd.Series([False])).sum()),
            'with_hs_stats': int(df.get('has_hs_stats', pd.Series([False])).sum()),
            'with_eybl_stats': int(df.get('played_eybl', pd.Series([False])).sum()),
            'with_offers': int(df.get('total_offers', pd.Series([0])).gt(0).sum()),
            'with_power_6_offers': int(df.get('power_6_offers', pd.Series([0])).gt(0).sum()),
            'avg_data_completeness': float(df.get('data_completeness', pd.Series([0])).mean()),
        }

        # Calculate percentages
        if total_players > 0:
            report['pct_recruiting'] = report['with_recruiting_info'] / total_players * 100
            report['pct_hs_stats'] = report['with_hs_stats'] / total_players * 100
            report['pct_eybl'] = report['with_eybl_stats'] / total_players * 100
            report['pct_offers'] = report['with_offers'] / total_players * 100

        return report


def create_mock_data(
    grad_year: int,
    recruiting_count: int = 50,
    maxpreps_count: int = 50,
    eybl_count: int = 25
) -> Dict[str, pd.DataFrame]:
    """
    Create mock data for testing dataset builder.

    Used for testing the pipeline without hitting real data sources.

    Args:
        grad_year: Graduation year
        recruiting_count: Number of recruiting profiles
        maxpreps_count: Number of MaxPreps stat lines
        eybl_count: Number of EYBL stat lines

    Returns:
        Dictionary with 'recruiting', 'maxpreps', 'eybl', 'offers' DataFrames
    """
    import numpy as np

    # Generate recruiting data
    recruiting_data = pd.DataFrame({
        'player_uid': [f'uid_{grad_year}_{i:04d}' for i in range(recruiting_count)],
        'player_name': [f'Player {i}' for i in range(recruiting_count)],
        'class_year': grad_year,
        'national_rank': range(1, recruiting_count + 1),
        'position_rank': [i % 20 + 1 for i in range(recruiting_count)],
        'state_rank': [i % 10 + 1 for i in range(recruiting_count)],
        'stars': np.random.choice([3, 4, 5], recruiting_count, p=[0.6, 0.3, 0.1]),
        'composite_rating': np.random.uniform(0.8, 0.99, recruiting_count),
        'position': np.random.choice(['PG', 'SG', 'SF', 'PF', 'C'], recruiting_count),
        'height': [f"{np.random.randint(6,7)}-{np.random.randint(0,12)}" for _ in range(recruiting_count)],
        'school': [f'School {i}' for i in range(recruiting_count)],
        'state': np.random.choice(['CA', 'TX', 'FL', 'NY', 'IL'], recruiting_count),
    })

    # Generate MaxPreps data (overlap with recruiting)
    maxpreps_indices = np.random.choice(recruiting_count, maxpreps_count, replace=False)
    maxpreps_data = pd.DataFrame({
        'player_uid': [f'uid_{grad_year}_{i:04d}' for i in maxpreps_indices],
        'grad_year': grad_year,
        'pts_per_g': np.random.uniform(5, 30, maxpreps_count),
        'reb_per_g': np.random.uniform(2, 12, maxpreps_count),
        'ast_per_g': np.random.uniform(1, 8, maxpreps_count),
        'stl_per_g': np.random.uniform(0.5, 3, maxpreps_count),
        'blk_per_g': np.random.uniform(0.2, 3, maxpreps_count),
        'fg_pct': np.random.uniform(0.40, 0.60, maxpreps_count),
        'fg3_pct': np.random.uniform(0.25, 0.45, maxpreps_count),
        'ft_pct': np.random.uniform(0.60, 0.90, maxpreps_count),
        'tov_per_g': np.random.uniform(1, 4, maxpreps_count),
        'gp': np.random.randint(15, 35, maxpreps_count),
        'mpg': np.random.uniform(15, 35, maxpreps_count),
        'school_name': [f'School {i}' for i in maxpreps_indices],
        'school_state': np.random.choice(['CA', 'TX', 'FL', 'NY', 'IL'], maxpreps_count),
    })

    # Generate EYBL data (subset of top players)
    eybl_indices = maxpreps_indices[:eybl_count]
    eybl_data = pd.DataFrame({
        'player_uid': [f'uid_{grad_year}_{i:04d}' for i in eybl_indices],
        'eybl_pts_per_g': np.random.uniform(8, 25, eybl_count),
        'eybl_reb_per_g': np.random.uniform(3, 10, eybl_count),
        'eybl_ast_per_g': np.random.uniform(2, 7, eybl_count),
        'eybl_stl_per_g': np.random.uniform(0.5, 2.5, eybl_count),
        'eybl_blk_per_g': np.random.uniform(0.3, 2, eybl_count),
        'eybl_fg_pct': np.random.uniform(0.42, 0.58, eybl_count),
        'eybl_fg3_pct': np.random.uniform(0.28, 0.42, eybl_count),
        'eybl_ft_pct': np.random.uniform(0.65, 0.88, eybl_count),
        'eybl_gp': np.random.randint(8, 20, eybl_count),
        'eybl_team': [f'EYBL Team {i%10}' for i in range(eybl_count)],
    })

    # Generate offers data
    # Each top player gets multiple offers
    offers_rows = []
    for i in eybl_indices[:15]:  # Top 15 players get offers
        num_offers = np.random.randint(3, 12)
        for j in range(num_offers):
            offers_rows.append({
                'player_uid': f'uid_{grad_year}_{i:04d}',
                'college': f'College {j}',
                'conference_level': np.random.choice(
                    ['power_6', 'high_major', 'mid_major'],
                    p=[0.4, 0.3, 0.3]
                ),
                'offer_status': 'offered',
            })

    offers_data = pd.DataFrame(offers_rows)

    return {
        'recruiting': recruiting_data,
        'maxpreps': maxpreps_data,
        'eybl': eybl_data,
        'offers': offers_data,
    }
