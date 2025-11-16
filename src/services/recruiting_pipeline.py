"""
Recruiting Data Pipeline - Normalization and Transformation

Transforms raw recruiting data from various sources into canonical format.

Key Transformations:
- Height parsing: "6-8" → 80 inches
- Hometown parsing: "City, ST" → city + state
- Stable ID generation: hash(source, class_year, external_id)
- Position standardization

Author: Claude Code
Date: 2025-11-15
"""

import hashlib
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd

from ..models.recruiting import RecruitingRank
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RecruitingPipeline:
    """
    Pipeline for normalizing recruiting data from multiple sources.

    Transforms raw source data into canonical player_recruiting format
    suitable for modeling and analysis.
    """

    @staticmethod
    def parse_height_to_inches(height_str: Optional[str]) -> Optional[int]:
        """
        Parse height string to total inches.

        Args:
            height_str: Height in format "6-8", "6'8\"", "6-8\"", etc.

        Returns:
            Total inches (e.g., 80 for 6'8") or None if invalid

        Examples:
            >>> parse_height_to_inches("6-8")
            80
            >>> parse_height_to_inches("6'8\"")
            80
            >>> parse_height_to_inches("6-8\"")
            80
        """
        if not height_str:
            return None

        # Try multiple patterns
        patterns = [
            r"(\d+)['\-](\d+)",  # 6-8 or 6'8
            r"(\d+)'\s*(\d+)\"",  # 6' 8"
            r"(\d+)\s*ft\s*(\d+)",  # 6 ft 8
        ]

        for pattern in patterns:
            match = re.search(pattern, str(height_str))
            if match:
                feet = int(match.group(1))
                inches = int(match.group(2))
                return (feet * 12) + inches

        return None

    @staticmethod
    def parse_hometown(hometown_str: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """
        Parse hometown string into city and state.

        Args:
            hometown_str: Hometown in format "City, ST" or "City, State"

        Returns:
            Tuple of (city, state_code) or (None, None) if invalid

        Examples:
            >>> parse_hometown("Brockton, MA")
            ("Brockton", "MA")
            >>> parse_hometown("Los Angeles, California")
            ("Los Angeles", "California")
        """
        if not hometown_str:
            return None, None

        # Split on comma
        parts = hometown_str.split(',')
        if len(parts) != 2:
            return None, None

        city = parts[0].strip()
        state = parts[1].strip()

        return city if city else None, state if state else None

    @staticmethod
    def generate_recruiting_id(source: str, class_year: int, external_id: str) -> str:
        """
        Generate stable recruiting_id hash.

        Args:
            source: Source name (e.g., 'on3_industry')
            class_year: Graduation year
            external_id: Source-specific player ID

        Returns:
            MD5 hash as hex string

        Examples:
            >>> generate_recruiting_id("on3_industry", 2025, "on3_156943")
            "a1b2c3d4..."
        """
        stable_key = f"{source}_{class_year}_{external_id}"
        return hashlib.md5(stable_key.encode()).hexdigest()

    def normalize_on3_to_player_recruiting(
        self,
        rankings: List[RecruitingRank],
        source: str = "on3_industry"
    ) -> pd.DataFrame:
        """
        Normalize On3 RecruitingRank objects to player_recruiting DataFrame.

        Transforms:
        - Height string → inches
        - Hometown → city + state
        - Generate recruiting_id
        - Extract commitment info

        Args:
            rankings: List of RecruitingRank objects from On3
            source: Source identifier (default: 'on3_industry')

        Returns:
            DataFrame matching player_recruiting schema
        """
        if not rankings:
            logger.warning("No rankings provided for normalization")
            return pd.DataFrame()

        rows = []
        loaded_at = datetime.utcnow()

        for rank in rankings:
            # Parse height
            height_inches = self.parse_height_to_inches(rank.height)

            # Parse hometown
            hometown_city, hometown_state = self.parse_hometown(
                f"{rank.city}, {rank.state}" if rank.city and rank.state else None
            )

            # Generate stable recruiting_id
            external_id = rank.player_id or f"{rank.player_name}_{rank.rank_national}"
            recruiting_id = self.generate_recruiting_id(source, rank.class_year, external_id)

            # Build normalized row
            row = {
                # Identity & Keys
                "recruiting_id": recruiting_id,
                "external_id": external_id,
                "player_uid": None,  # Not yet resolved

                # Source Metadata
                "source": source,
                "source_type": "on3",

                # Player Identity
                "player_name": rank.player_name,
                "class_year": rank.class_year,

                # Position
                "position": rank.position.value if rank.position else None,

                # Physical Stats
                "height_inches": height_inches,
                "weight_lbs": rank.weight,

                # Location
                "hometown_city": hometown_city,
                "hometown_state": hometown_state,
                "high_school_name": rank.school,

                # Rankings
                "national_rank": rank.rank_national,
                "state_rank": rank.rank_state,
                "position_rank": rank.rank_position,

                # Ratings
                "stars": rank.stars,
                "rating_0_1": rank.rating,  # Already normalized to 0-1

                # Commitment
                "is_committed": rank.committed_to is not None,
                "committed_school": rank.committed_to,
                "committed_conf": None,  # Not available from On3
                "committed_level": None,  # Not available from On3
                "commitment_date": rank.commitment_date,

                # Profile
                "profile_url": rank.profile_url,

                # Timestamps
                "loaded_at": loaded_at,
                "source_snapshot_ts": loaded_at,  # Use loaded_at as snapshot time
            }

            rows.append(row)

        df = pd.DataFrame(rows)

        logger.info(
            f"Normalized {len(df)} rankings from {source}",
            class_year=rankings[0].class_year if rankings else None
        )

        return df

    def normalize_on3_raw_to_dataframe(
        self,
        rankings: List[RecruitingRank],
        class_year: int,
        scraped_at: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Convert On3 RecruitingRank objects to raw storage DataFrame.

        This creates the on3_player_rankings_raw format (source-shaped).

        Args:
            rankings: List of RecruitingRank objects
            class_year: Graduation year
            scraped_at: When data was scraped (default: now)

        Returns:
            DataFrame matching on3_player_rankings_raw schema
        """
        if not rankings:
            logger.warning("No rankings provided for raw conversion")
            return pd.DataFrame()

        if scraped_at is None:
            scraped_at = datetime.utcnow()

        loaded_at = datetime.utcnow()

        rows = []
        for rank in rankings:
            row = {
                "raw_id": hashlib.md5(
                    f"on3_{class_year}_{rank.player_id}_{scraped_at.isoformat()}".encode()
                ).hexdigest(),
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
                "consensus_rating": rank.rating * 100 if rank.rating else None,  # Convert 0-1 to 0-100
                "is_committed": rank.committed_to is not None,
                "committed_org_slug": rank.committed_to,
                "commitment_date": rank.commitment_date,
                "player_slug": rank.profile_url.split("/")[-1] if rank.profile_url else None,
                "profile_url": rank.profile_url,
                "scraped_at": scraped_at,
                "loaded_at": loaded_at,
                "raw_json": None,  # Optional: could store full JSON
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        logger.info(
            f"Converted {len(df)} rankings to raw format",
            class_year=class_year
        )

        return df
