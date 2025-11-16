"""
Cross-Source Identity Resolution - Pilot Cohort

Links players across:
- GoBound (IA, IL, SD) - High school statistics
- 247Sports - Recruiting rankings and profiles
- EYBL - Pre-college circuit statistics

**Pilot**: Top 200 recruits (2025-2027 classes)

**Output**:
- manual_review_candidates.csv: Medium confidence matches for human verification
- pilot_linking_report.json: Summary statistics and findings
- suggested_player_links.sql: High-confidence INSERT statements for manual_player_links

**Usage**:
    python scripts/cross_source_pilot_linking.py --class-years 2025 2026 2027 --limit 200

Author: Claude Code
Date: 2025-11-16
Phase: HS-3b - Cross-Source Identity Resolution
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.duckdb_storage import get_duckdb_storage
from src.services.identity import (
    calculate_match_confidence,
    fuzzy_name_match,
    resolve_player_uid_with_source,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrossSourcePilotLinker:
    """
    Pilot cohort cross-source identity resolution.

    Tests identity resolution on top recruits to identify:
    - Successful automatic matches
    - Edge cases needing manual review
    - Data quality issues (name variations, missing grad years, etc.)
    """

    def __init__(self, class_years: List[int], limit_per_year: int = 200):
        """
        Initialize pilot linker.

        Args:
            class_years: Graduation years to include (e.g., [2025, 2026, 2027])
            limit_per_year: Number of top recruits per year
        """
        self.class_years = class_years
        self.limit_per_year = limit_per_year
        self.duckdb = get_duckdb_storage()
        self.results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'class_years': class_years,
                'limit_per_year': limit_per_year
            },
            'summary': {
                'total_recruits': 0,
                'matched_to_gobound': 0,
                'matched_to_eybl': 0,
                'high_confidence_matches': 0,
                'medium_confidence_matches': 0,
                'low_confidence_matches': 0,
                'no_matches': 0
            },
            'matches': [],
            'manual_review_candidates': [],
            'data_quality_issues': []
        }

    def load_pilot_cohort(self) -> pd.DataFrame:
        """
        Load pilot cohort from recruiting data.

        Returns top N recruits from specified graduation years.

        Returns:
            DataFrame with recruiting data
        """
        if not self.duckdb.conn:
            logger.error("DuckDB not available")
            return pd.DataFrame()

        logger.info(f"Loading top {self.limit_per_year} recruits per year for {self.class_years}")

        # Query recruiting rankings
        class_years_str = ','.join(str(y) for y in self.class_years)
        query = f"""
            SELECT
                player_id,
                player_name,
                class_year,
                national_rank,
                stars,
                rating_0_1 as rating,
                position,
                high_school_name as school,
                hometown_state as state,
                source
            FROM player_recruiting
            WHERE class_year IN ({class_years_str})
                AND national_rank IS NOT NULL
            ORDER BY class_year, national_rank
        """

        try:
            df = self.duckdb.conn.execute(query).fetchdf()

            if df.empty:
                logger.warning(f"No recruiting data found for years {self.class_years}")
                return df

            # Limit to top N per year
            if self.limit_per_year > 0:
                df = df.groupby('class_year').head(self.limit_per_year)

            logger.info(f"Loaded {len(df)} recruits from recruiting data")
            self.results['summary']['total_recruits'] = len(df)

            return df

        except Exception as e:
            logger.error(f"Failed to load pilot cohort: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def search_gobound_match(
        self,
        player_name: str,
        school: Optional[str],
        grad_year: Optional[int],
        state: Optional[str]
    ) -> Optional[Dict]:
        """
        Search for player in GoBound data.

        Args:
            player_name: Player full name
            school: High school name
            grad_year: Graduation year
            state: State code

        Returns:
            Match dictionary if found, None otherwise
        """
        if not self.duckdb.conn:
            return None

        try:
            # Search GoBound players table
            # GoBound only covers IA, IL, SD (MN has no data)
            gobound_states = ['IA', 'IL', 'SD']

            if state and state not in gobound_states:
                # Player is from a state not covered by GoBound
                return None

            # Fuzzy name search
            name_parts = player_name.lower().split()
            if len(name_parts) < 2:
                return None

            first_name, last_name = name_parts[0], name_parts[-1]

            query = """
                SELECT
                    player_id,
                    full_name,
                    school_name,
                    school_state,
                    grad_year,
                    position,
                    jersey_number
                FROM players
                WHERE source_type = 'bound'
                    AND (
                        full_name ILIKE ?
                        OR (first_name ILIKE ? AND last_name ILIKE ?)
                    )
            """

            params = [f"%{player_name}%", f"%{first_name}%", f"%{last_name}%"]

            if state:
                query += " AND school_state = ?"
                params.append(state)

            if grad_year:
                query += " AND grad_year = ?"
                params.append(grad_year)

            query += " LIMIT 5"

            matches = self.duckdb.conn.execute(query, params).fetchall()

            if not matches:
                return None

            # Take best match (first result if multiple)
            match = matches[0]

            # Calculate match confidence
            name_match = fuzzy_name_match(player_name, match[1], threshold=0.85)
            school_match = school and match[2] and school.lower() in match[2].lower()
            grad_year_match = grad_year and match[4] and grad_year == match[4]
            state_match = state and match[3] and state == match[3]

            confidence = calculate_match_confidence(
                name_match=name_match,
                school_match=bool(school_match),
                grad_year_match=bool(grad_year_match),
                state_match=bool(state_match),
                fuzzy_name_score=0.9 if name_match else 0.0
            )

            return {
                'source': 'gobound',
                'player_id': match[0],
                'player_name': match[1],
                'school': match[2],
                'state': match[3],
                'grad_year': match[4],
                'position': match[5],
                'confidence': confidence,
                'match_details': {
                    'name_match': name_match,
                    'school_match': bool(school_match),
                    'grad_year_match': bool(grad_year_match),
                    'state_match': bool(state_match)
                }
            }

        except Exception as e:
            logger.warning(f"Error searching GoBound for {player_name}: {e}")
            return None

    def search_eybl_match(
        self,
        player_name: str,
        grad_year: Optional[int]
    ) -> Optional[Dict]:
        """
        Search for player in EYBL data.

        Args:
            player_name: Player full name
            grad_year: Graduation year

        Returns:
            Match dictionary if found, None otherwise
        """
        if not self.duckdb.conn:
            return None

        try:
            # Search EYBL players table
            name_parts = player_name.lower().split()
            if len(name_parts) < 2:
                return None

            first_name, last_name = name_parts[0], name_parts[-1]

            query = """
                SELECT
                    player_id,
                    full_name,
                    team_name,
                    grad_year,
                    position
                FROM players
                WHERE source_type = 'eybl'
                    AND (
                        full_name ILIKE ?
                        OR (first_name ILIKE ? AND last_name ILIKE ?)
                    )
            """

            params = [f"%{player_name}%", f"%{first_name}%", f"%{last_name}%"]

            if grad_year:
                query += " AND grad_year = ?"
                params.append(grad_year)

            query += " LIMIT 5"

            matches = self.duckdb.conn.execute(query, params).fetchall()

            if not matches:
                return None

            # Take best match
            match = matches[0]

            # Calculate match confidence
            name_match = fuzzy_name_match(player_name, match[1], threshold=0.85)
            grad_year_match = grad_year and match[3] and grad_year == match[3]

            confidence = calculate_match_confidence(
                name_match=name_match,
                grad_year_match=bool(grad_year_match),
                fuzzy_name_score=0.9 if name_match else 0.0
            )

            return {
                'source': 'eybl',
                'player_id': match[0],
                'player_name': match[1],
                'team': match[2],
                'grad_year': match[3],
                'position': match[4],
                'confidence': confidence,
                'match_details': {
                    'name_match': name_match,
                    'grad_year_match': bool(grad_year_match)
                }
            }

        except Exception as e:
            logger.warning(f"Error searching EYBL for {player_name}: {e}")
            return None

    def process_pilot_cohort(self, pilot_df: pd.DataFrame):
        """
        Process pilot cohort to find cross-source matches.

        Args:
            pilot_df: DataFrame with recruiting data
        """
        logger.info(f"Processing {len(pilot_df)} recruits for cross-source matching")

        for idx, row in pilot_df.iterrows():
            player_name = row['player_name']
            school = row.get('school', None)
            grad_year = row.get('class_year', None)
            state = row.get('state', None)
            recruiting_player_id = row['player_id']

            logger.debug(f"Processing: {player_name} ({grad_year}, {state})")

            # Search GoBound
            gobound_match = self.search_gobound_match(
                player_name=player_name,
                school=school,
                grad_year=grad_year,
                state=state
            )

            # Search EYBL
            eybl_match = self.search_eybl_match(
                player_name=player_name,
                grad_year=grad_year
            )

            # Record results
            result = {
                'recruiting_player_id': recruiting_player_id,
                'player_name': player_name,
                'school': school,
                'grad_year': grad_year,
                'state': state,
                'national_rank': row.get('national_rank', None),
                'gobound_match': gobound_match,
                'eybl_match': eybl_match
            }

            self.results['matches'].append(result)

            # Categorize matches
            if gobound_match:
                self.results['summary']['matched_to_gobound'] += 1
                if gobound_match['confidence'] >= 0.9:
                    self.results['summary']['high_confidence_matches'] += 1
                elif gobound_match['confidence'] >= 0.7:
                    self.results['summary']['medium_confidence_matches'] += 1
                    self.results['manual_review_candidates'].append({
                        **result,
                        'match_source': 'gobound',
                        'confidence': gobound_match['confidence']
                    })
                else:
                    self.results['summary']['low_confidence_matches'] += 1

            if eybl_match:
                self.results['summary']['matched_to_eybl'] += 1
                if eybl_match['confidence'] >= 0.9:
                    self.results['summary']['high_confidence_matches'] += 1
                elif eybl_match['confidence'] >= 0.7:
                    self.results['summary']['medium_confidence_matches'] += 1
                    if {'match_source': 'eybl'} not in [m.get('match_source') for m in self.results['manual_review_candidates']]:
                        self.results['manual_review_candidates'].append({
                            **result,
                            'match_source': 'eybl',
                            'confidence': eybl_match['confidence']
                        })
                else:
                    self.results['summary']['low_confidence_matches'] += 1

            if not gobound_match and not eybl_match:
                self.results['summary']['no_matches'] += 1

            # Check for data quality issues
            if not grad_year:
                self.results['data_quality_issues'].append({
                    'player_name': player_name,
                    'issue': 'Missing grad_year',
                    'player_id': recruiting_player_id
                })

        logger.info(f"Processing complete: {len(self.results['matches'])} recruits processed")

    def generate_outputs(self):
        """
        Generate output files:
        - manual_review_candidates.csv
        - pilot_linking_report.json
        - suggested_player_links.sql
        """
        output_dir = Path("data/debug")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Manual review candidates CSV
        if self.results['manual_review_candidates']:
            candidates_df = pd.DataFrame(self.results['manual_review_candidates'])
            csv_path = output_dir / "manual_review_candidates.csv"
            candidates_df.to_csv(csv_path, index=False)
            logger.info(f"Saved {len(candidates_df)} manual review candidates to {csv_path}")
        else:
            logger.info("No manual review candidates to save")

        # 2. Pilot linking report JSON
        json_path = output_dir / "pilot_linking_report.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Saved pilot linking report to {json_path}")

        # 3. Suggested player links SQL (high confidence only)
        sql_lines = ["-- High-confidence player links (auto-generated)", ""]
        link_count = 0

        for match in self.results['matches']:
            gobound_match = match.get('gobound_match')
            eybl_match = match.get('eybl_match')
            recruiting_id = match['recruiting_player_id']

            # GoBound high-confidence links
            if gobound_match and gobound_match['confidence'] >= 0.9:
                canonical_uid = resolve_player_uid_with_source(
                    name=match['player_name'],
                    school=match.get('school', ''),
                    grad_year=match.get('grad_year', None),
                    source_type='recruiting',
                    player_id=recruiting_id
                )

                sql_lines.append(f"""-- {match['player_name']} (Rank #{match.get('national_rank', 'N/A')})""")
                sql_lines.append(f"""INSERT INTO manual_player_links (
    link_id, source1_type, source1_player_id, source2_type, source2_player_id,
    canonical_player_uid, confidence_score, link_type, notes, created_by
) VALUES (
    '{recruiting_id}_{gobound_match["player_id"]}',
    'recruiting', '{recruiting_id}',
    'gobound', '{gobound_match["player_id"]}',
    '{canonical_uid}', {gobound_match['confidence']:.2f},
    'SAME_PLAYER', 'Auto-linked: Pilot cohort high-confidence match', 'pilot_script'
);""")
                sql_lines.append("")
                link_count += 1

            # EYBL high-confidence links
            if eybl_match and eybl_match['confidence'] >= 0.9:
                canonical_uid = resolve_player_uid_with_source(
                    name=match['player_name'],
                    school=match.get('school', ''),
                    grad_year=match.get('grad_year', None),
                    source_type='recruiting',
                    player_id=recruiting_id
                )

                sql_lines.append(f"""-- {match['player_name']} (Rank #{match.get('national_rank', 'N/A')})""")
                sql_lines.append(f"""INSERT INTO manual_player_links (
    link_id, source1_type, source1_player_id, source2_type, source2_player_id,
    canonical_player_uid, confidence_score, link_type, notes, created_by
) VALUES (
    '{recruiting_id}_{eybl_match["player_id"]}',
    'recruiting', '{recruiting_id}',
    'eybl', '{eybl_match["player_id"]}',
    '{canonical_uid}', {eybl_match['confidence']:.2f},
    'SAME_PLAYER', 'Auto-linked: Pilot cohort high-confidence match', 'pilot_script'
);""")
                sql_lines.append("")
                link_count += 1

        sql_path = output_dir / "suggested_player_links.sql"
        with open(sql_path, 'w') as f:
            f.write('\n'.join(sql_lines))

        logger.info(f"Saved {link_count} suggested player links to {sql_path}")

    def print_summary(self):
        """Print summary report to console."""
        print("\n" + "="*70)
        print("CROSS-SOURCE IDENTITY RESOLUTION - PILOT COHORT")
        print("="*70)
        print(f"Timestamp: {self.results['metadata']['timestamp']}")
        print(f"Class Years: {', '.join(str(y) for y in self.class_years)}")
        print(f"Limit Per Year: {self.limit_per_year}")
        print("")
        print("SUMMARY")
        print("-"*70)
        summary = self.results['summary']
        print(f"Total Recruits Processed: {summary['total_recruits']}")
        print(f"Matched to GoBound: {summary['matched_to_gobound']} ({summary['matched_to_gobound'] / max(summary['total_recruits'], 1) * 100:.1f}%)")
        print(f"Matched to EYBL: {summary['matched_to_eybl']} ({summary['matched_to_eybl'] / max(summary['total_recruits'], 1) * 100:.1f}%)")
        print(f"High Confidence Matches (>=0.9): {summary['high_confidence_matches']}")
        print(f"Medium Confidence Matches (0.7-0.89): {summary['medium_confidence_matches']}")
        print(f"Low Confidence Matches (<0.7): {summary['low_confidence_matches']}")
        print(f"No Matches Found: {summary['no_matches']}")
        print("")
        print("DATA QUALITY")
        print("-"*70)
        print(f"Issues Found: {len(self.results['data_quality_issues'])}")
        print("")
        print("="*70)


async def main():
    """Run pilot cohort linking."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-source identity resolution pilot")
    parser.add_argument('--class-years', type=int, nargs='+', default=[2025, 2026, 2027],
                        help='Graduation years to include (default: 2025 2026 2027)')
    parser.add_argument('--limit', type=int, default=200,
                        help='Top N recruits per year (default: 200)')

    args = parser.parse_args()

    # Initialize linker
    linker = CrossSourcePilotLinker(
        class_years=args.class_years,
        limit_per_year=args.limit
    )

    # Load pilot cohort
    pilot_df = linker.load_pilot_cohort()

    if pilot_df.empty:
        logger.error("No pilot cohort data available - exiting")
        return

    # Process matches
    linker.process_pilot_cohort(pilot_df)

    # Generate outputs
    linker.generate_outputs()

    # Print summary
    linker.print_summary()

    logger.info("Pilot cohort linking complete!")


if __name__ == '__main__':
    asyncio.run(main())
