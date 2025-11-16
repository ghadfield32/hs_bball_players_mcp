"""
Recruiting DuckDB Storage Service

Specialized storage for recruiting data with On3/247Sports/etc.

Author: Claude Code
Date: 2025-11-15
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import pandas as pd

from ..config import get_settings
from ..models.recruiting import RecruitingRank
from ..utils.logger import get_logger
from ..utils.schema_loader import generate_all_recruiting_ddl

logger = get_logger(__name__)


class RecruitingDuckDBStorage:
    """
    DuckDB storage for recruiting data.

    Manages raw data, normalized data, and coverage metadata.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize recruiting DuckDB storage.

        Args:
            db_path: Path to DuckDB file (default: data/duckdb/recruiting.duckdb)
        """
        if db_path is None:
            db_path = Path("data/duckdb/recruiting.duckdb")
        else:
            db_path = Path(db_path)

        # Create directory
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB
        self.conn = duckdb.connect(str(db_path))
        self.db_path = db_path

        # Configure DuckDB
        self.conn.execute("SET memory_limit='2GB'")
        self.conn.execute("SET threads=4")

        # Initialize schema
        self._initialize_schema()

        logger.info(
            "Recruiting DuckDB storage initialized",
            path=str(db_path)
        )

    def _initialize_schema(self) -> None:
        """Create recruiting tables from YAML schemas."""
        logger.info("Initializing recruiting schema...")

        # Generate DDL from YAML schemas
        ddl_statements = generate_all_recruiting_ddl()

        # Execute all DDL
        for ddl in ddl_statements:
            self.conn.execute(ddl)

        logger.info(f"Created {len(ddl_statements)} schema objects")

    def upsert_on3_raw(
        self,
        class_year: int,
        rankings: List[RecruitingRank],
        scraped_at: Optional[datetime] = None
    ) -> int:
        """
        Insert/update On3 raw rankings.

        Args:
            class_year: Graduation year
            rankings: List of RecruitingRank objects from On3
            scraped_at: When data was scraped (default: now)

        Returns:
            Number of rows inserted
        """
        if not rankings:
            logger.warning("No rankings to insert")
            return 0

        if scraped_at is None:
            scraped_at = datetime.utcnow()

        loaded_at = datetime.utcnow()

        # Convert to raw format
        rows = []
        for rank in rankings:
            row = {
                "raw_id": str(uuid.uuid4()),
                "external_id": rank.player_id,
                "class_year": class_year,
                "player_name": rank.player_name,
                "position_abbr": rank.position.value if rank.position else None,
                "height_formatted": rank.height,
                "weight": rank.weight,
                "hometown": f"{rank.city}, {rank.state}" if rank.city and rank.state else None,
                "high_school_name": rank.school,
                "consensus_national_rank": rank.rank_national,
                "consensus_position_rank": rank.rank_position,
                "consensus_state_rank": rank.rank_state,
                "consensus_stars": rank.stars,
                "consensus_rating": rank.rating * 100 if rank.rating else None,  # Convert 0-1 back to 0-100
                "is_committed": rank.committed_to is not None,
                "committed_org_slug": rank.committed_to,
                "commitment_date": rank.commitment_date,
                "player_slug": rank.profile_url.split("/")[-1] if rank.profile_url else None,
                "profile_url": rank.profile_url,
                "scraped_at": scraped_at,
                "loaded_at": loaded_at,
                "raw_json": None  # Optional: could store full JSON
            }
            rows.append(row)

        # Insert with INSERT OR REPLACE (upsert)
        df = pd.DataFrame(rows)

        # Delete existing rows for this class_year first (simple upsert strategy)
        self.conn.execute(
            "DELETE FROM on3_player_rankings_raw WHERE class_year = ?",
            [class_year]
        )

        # Insert new rows
        self.conn.execute(
            "INSERT INTO on3_player_rankings_raw SELECT * FROM df"
        )

        logger.info(
            f"Inserted {len(rows)} On3 raw rankings",
            class_year=class_year
        )

        return len(rows)

    def upsert_player_recruiting(
        self,
        df: pd.DataFrame
    ) -> int:
        """
        Insert/update normalized player recruiting data.

        Args:
            df: DataFrame with normalized recruiting data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return 0

        # Ensure recruiting_id exists
        if 'recruiting_id' not in df.columns:
            raise ValueError("DataFrame must have 'recruiting_id' column")

        # Delete existing rows with same recruiting_ids (upsert)
        recruiting_ids = df['recruiting_id'].tolist()

        if recruiting_ids:
            placeholders = ','.join(['?'] * len(recruiting_ids))
            self.conn.execute(
                f"DELETE FROM player_recruiting WHERE recruiting_id IN ({placeholders})",
                recruiting_ids
            )

        # Insert new rows
        self.conn.execute(
            "INSERT INTO player_recruiting SELECT * FROM df"
        )

        logger.info(f"Inserted {len(df)} player recruiting records")

        return len(df)

    def upsert_coverage(
        self,
        source: str,
        class_year: int,
        n_players: int,
        n_players_expected: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Insert/update coverage metadata.

        Args:
            source: Source name (e.g., 'on3_industry')
            class_year: Graduation year
            n_players: Number of players found
            n_players_expected: Expected count from pagination
            **kwargs: Additional coverage metrics
        """
        coverage_id = hashlib.md5(
            f"{source}_{class_year}".encode()
        ).hexdigest()

        discovered_at = datetime.utcnow()

        # Build row with all schema columns (use None for missing values)
        row = {
            "coverage_id": coverage_id,
            "source": source,
            "class_year": class_year,
            "n_players": n_players,
            "n_players_expected": n_players_expected,
            "page_count": kwargs.get("page_count"),
            "items_per_page": kwargs.get("items_per_page"),
            "n_players_with_ranks": kwargs.get("n_players_with_ranks"),
            "n_players_with_stars": kwargs.get("n_players_with_stars"),
            "n_players_with_ratings": kwargs.get("n_players_with_ratings"),
            "n_players_committed": kwargs.get("n_players_committed"),
            "has_gaps": kwargs.get("has_gaps"),
            "count_mismatch": kwargs.get("count_mismatch"),
            "parse_errors": kwargs.get("parse_errors"),
            "discovered_at": discovered_at,
            "last_updated_at": discovered_at,  # Same as discovered_at initially
            "notes": kwargs.get("notes"),
        }

        df = pd.DataFrame([row])

        # Delete existing coverage row
        self.conn.execute(
            "DELETE FROM recruiting_coverage WHERE source = ? AND class_year = ?",
            [source, class_year]
        )

        # Insert new row
        self.conn.execute(
            "INSERT INTO recruiting_coverage SELECT * FROM df"
        )

        logger.info(
            f"Updated coverage",
            source=source,
            class_year=class_year,
            n_players=n_players
        )

    def get_coverage(self, source: Optional[str] = None) -> pd.DataFrame:
        """
        Get coverage metadata.

        Args:
            source: Filter by source (optional)

        Returns:
            DataFrame with coverage data
        """
        if source:
            query = "SELECT * FROM recruiting_coverage WHERE source = ? ORDER BY class_year"
            return self.conn.execute(query, [source]).df()
        else:
            query = "SELECT * FROM recruiting_coverage ORDER BY source, class_year"
            return self.conn.execute(query).df()

    def get_recruiting_data(
        self,
        class_year: Optional[int] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get normalized recruiting data.

        Args:
            class_year: Filter by class year
            source: Filter by source
            limit: Limit results

        Returns:
            DataFrame with recruiting data
        """
        query = "SELECT * FROM player_recruiting WHERE 1=1"
        params = []

        if class_year:
            query += " AND class_year = ?"
            params.append(class_year)

        if source:
            query += " AND source = ?"
            params.append(source)

        query += " ORDER BY class_year, national_rank"

        if limit:
            query += f" LIMIT {limit}"

        return self.conn.execute(query, params).df()

    def close(self) -> None:
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("Recruiting DuckDB connection closed")
