#!/usr/bin/env python3
"""
State Association Adapter Scaffolder

Generates a complete Phase 17/18 state adapter from template with metadata enrichment.
Follows proven pattern from CA/TX/FL/GA/OH/PA/NY adapters.

Usage:
    python scripts/scaffold_state_adapter.py --state "Michigan" --abbrev "MI" \\
        --org "MHSAA" --base-url "https://www.mhsaa.com" \\
        --classifications "1,2,3,4" --schools 750

    python scripts/scaffold_state_adapter.py --state "North Carolina" --abbrev "NC" \\
        --org "NCHSAA" --base-url "https://www.nchsaa.org" \\
        --classifications "4A,3A,2A,1A" --schools 400

Features:
- Generates complete adapter with shared bracket parser
- Includes Phase 18 metadata enrichment (round, venue, tipoff)
- Proper imports, docstrings, and type hints
- Canonical team IDs and deduplication
- Configurable classifications (numeric or letter-based)
- State-specific constants and URL patterns

Output:
- src/datasources/us/{state_slug}_{org_slug}.py
"""

import argparse
import re
from pathlib import Path
from typing import List


def slugify(text: str) -> str:
    """Convert text to lowercase slug."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower().strip()).strip('_')


def generate_adapter(
    state_name: str,
    state_abbrev: str,
    organization: str,
    base_url: str,
    classifications: List[str],
    school_count: int,
    notable_players: str = "",
) -> str:
    """
    Generate complete state adapter code from template.

    Args:
        state_name: Full state name (e.g., "Michigan")
        state_abbrev: 2-letter state code (e.g., "MI")
        organization: Organization acronym (e.g., "MHSAA")
        base_url: Base URL without trailing slash
        classifications: List of classification names (e.g., ["1", "2", "3", "4"] or ["4A", "3A"])
        school_count: Approximate number of member schools
        notable_players: Optional comma-separated list of notable players

    Returns:
        Complete Python source code for adapter
    """
    org_slug = slugify(organization)
    state_slug = slugify(state_name)
    prefix = org_slug  # Use org acronym for canonical IDs (e.g., "mhsaa")

    # Format classifications for Python list
    classifications_str = ", ".join([f'"{c}"' for c in classifications])

    # Determine classification type (numeric vs letter-based)
    is_numeric = all(c.isdigit() for c in classifications)
    sample_class = classifications[0]

    # Notable players section
    notable_section = f"\n- Notable tradition ({notable_players})" if notable_players else "\n- Strong basketball tradition"

    # Generate adapter code
    code = f'''"""
{organization} ({state_name} State Association) DataSource Adapter

Provides authoritative tournament brackets, seeds, scores, and championship results
for {state_name} high school basketball.

**Data Authority**: {organization} is the source of truth for:
- Tournament brackets ({len(classifications)} classifications: {", ".join(classifications)})
- Seeds and matchups
- Game dates, times, locations
- Final scores and champions
- Historical tournament data

**Base URL**: {base_url}

**URL Pattern**:
```
Basketball: /sports/basketball/
Boys: /sports/basketball/boys/
Girls: /sports/basketball/girls/
Brackets: /brackets/{{year}}/
Playoffs: /playoffs/{{year}}/{{classification}}/
```

**Coverage**:
- Classifications: {", ".join(classifications)} (enrollment-based)
- {school_count}+ member schools
- Boys and Girls tournaments
- All regions of {state_name}

**{state_name} Basketball Context**:
- {school_count}+ schools{notable_section}
- {organization} manages all high school athletics in {state_name}
- Enrollment-based classifications ({classifications[0]} {"largest" if is_numeric else "highest"}, {classifications[-1]} {"smallest" if is_numeric else "lowest"})
- Regional tournaments → state championships

**Special Features**:
- Historical bracket data available
- Regional tournament structure
- Digital presence with bracket updates

**Limitations**:
- Player statistics NOT available (state associations focus on brackets/lineage)
- Regular season schedules typically on MaxPreps (separate source)
- Box scores rarely available

**Recommended Use**: {organization} provides official tournament brackets.
For player-level stats, combine with MaxPreps or other stats providers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    GameType,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Team,
    TeamLevel,
)
from ...utils import get_text_or_none, parse_html, parse_int
from ...utils.brackets import parse_bracket_tables_and_divs, canonical_team_id, extract_team_seed, parse_block_meta
from ..base_association import AssociationAdapterBase
from ...config import get_settings


class {state_name.replace(' ', '')}{organization}DataSource(AssociationAdapterBase):
    """
    {state_name} {organization} adapter.

    **PRIMARY PURPOSE**: Authoritative tournament bracket and postseason results.

    **COVERAGE**: {school_count}+ schools with basketball programs.

    This adapter provides:
    1. Tournament brackets for all classifications ({", ".join(classifications)})
    2. Seeds, matchups, dates, locations
    3. Game scores and final results
    4. Historical tournament data
    5. Regional and state championship results

    **ARCHITECTURE**:
    - Inherits from AssociationAdapterBase
    - Prioritizes HTML parsing (bracket pages)
    - Enumerates classifications: {", ".join(classifications)}
    - Generates unique game IDs: {prefix}_{{year}}_{{class}}_{{home}}@{{away}}

    **DATA QUALITY**: HIGH (official source, authoritative)

    **LIMITATIONS**:
    - No player-level statistics (use MaxPreps for this)
    - No regular season schedules
    - Bracket-focused, not stats-focused
    """

    source_type = DataSourceType.{organization.upper()}
    source_name = "{organization}"
    base_url = "{base_url}"
    region = DataSourceRegion.US_{state_abbrev}

    # {organization} specific constants
    CLASSIFICATIONS = [{classifications_str}]
    GENDERS = ["Boys", "Girls"]
    MIN_YEAR = 2015  # Historical data availability
    STATE_CODE = "{state_abbrev}"
    STATE_NAME = "{state_name}"
    ORGANIZATION = "{organization}"

    def __init__(self):
        """Initialize {organization} datasource with {state_name}-specific configuration."""
        super().__init__()
        self.settings = get_settings()
        self.logger.info(
            "{organization} initialized",
            classifications=len(self.CLASSIFICATIONS),
            genders=len(self.GENDERS),
            min_year=self.MIN_YEAR,
            organization=self.ORGANIZATION,
        )

    def _build_bracket_url(
        self, classification: str, gender: str = "Boys", year: Optional[int] = None
    ) -> str:
        """
        Build URL for specific tournament bracket.

        **{organization} URL Format**:
        ```
        /sports/basketball/{{gender}}/brackets/{{year}}/{{classification}}/
        /sports/basketball/boys/brackets/2025/{sample_class.lower()}/
        /sports/basketball/girls/brackets/2025/{sample_class.lower()}/

        Alternative patterns:
        /playoffs/{{year}}/basketball-{{gender}}-{{classification}}/
        /brackets/{{year}}-basketball-{{classification}}-{{gender}}
        ```

        Args:
            classification: Classification name ({", ".join(classifications)})
            gender: "Boys" or "Girls"
            year: Tournament year (optional)

        Returns:
            Full bracket URL
        """
        year = year or datetime.now().year
        gender_lower = gender.lower()
        class_lower = classification.lower()

        # Try multiple URL patterns ({organization} structure may vary)
        # Pattern 1: /sports/basketball/{{gender}}/brackets/{{year}}/{{classification}}
        url_pattern_1 = (
            f"{{self.base_url}}/sports/basketball/{{gender_lower}}/"
            f"brackets/{{year}}/{{class_lower}}"
        )

        # Pattern 2: /playoffs/{{year}}/basketball-{{gender}}-{{classification}}
        url_pattern_2 = (
            f"{{self.base_url}}/playoffs/{{year}}/basketball-{{gender_lower}}-{{class_lower}}"
        )

        # Return primary pattern (can try fallbacks in get_tournament_brackets)
        return url_pattern_1

    def _extract_year(self, season: Optional[str]) -> int:
        """Extract year from season string."""
        if not season:
            return datetime.now().year
        year = int(season.split("-")[1]) if "-" in season else int(season)
        return year + 2000 if year < 100 else year

    async def get_tournament_brackets(
        self,
        season: Optional[str] = None,
        classification: Optional[str] = None,
        gender: str = "Boys",
    ) -> Dict[str, Any]:
        """
        Get tournament brackets for a season.

        **ENUMERATION STRATEGY**:
        - If season provided: fetch brackets for that year
        - If classification provided: only fetch that classification's bracket
        - Otherwise: fetch current year, all classifications

        Args:
            season: Season string (e.g., "2024-25"), None for current
            classification: Specific classification ({", ".join(classifications)}), None for all
            gender: "Boys" or "Girls"

        Returns:
            Dict with keys:
                - games: List[Game] - all tournament games
                - teams: List[Team] - all participating teams
                - brackets: Dict[str, List[Game]] - games grouped by classification
                - metadata: bracket metadata (year, updated timestamps)
        """
        year = self._extract_year(season)
        classifications = [classification] if classification else self.CLASSIFICATIONS

        all_games: List[Game] = []
        all_teams: Dict[str, Team] = {{}}
        brackets: Dict[str, List[Game]] = {{}}
        metadata: Dict[str, Any] = {{}}

        self.logger.info(
            f"Fetching {organization} tournament brackets",
            year=year,
            classifications=classifications,
            gender=gender,
        )

        # Enumerate all bracket combinations
        for cls in classifications:
            bracket_key = f"class_{{cls.lower()}}"

            try:
                url = self._build_bracket_url(cls, gender, year)
                status, content, headers = await self.http_get(url, timeout=30.0)

                if status != 200:
                    self.logger.warning(
                        f"Failed to fetch bracket",
                        status=status,
                        classification=cls,
                        url=url,
                    )
                    continue

                html = content.decode("utf-8", errors="ignore")
                soup = parse_html(html)

                # Parse bracket HTML
                bracket_data = self._parse_bracket_html(soup, year, cls, gender, url)

                self.logger.info(
                    f"Parsed {organization} bracket",
                    classification=cls,
                    games=len(bracket_data["games"]),
                    teams=len(bracket_data["teams"]),
                )

                # Collect games and teams
                for game in bracket_data["games"]:
                    all_games.append(game)
                    brackets.setdefault(bracket_key, []).append(game)

                for team in bracket_data["teams"]:
                    all_teams[team.team_id] = team

                # Collect metadata
                if bracket_data.get("metadata"):
                    metadata[bracket_key] = bracket_data["metadata"]

            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch bracket",
                    year=year,
                    classification=cls,
                    gender=gender,
                    error=str(e),
                )
                continue

        self.logger.info(
            f"Fetched all {organization} tournament brackets",
            year=year,
            total_games=len(all_games),
            total_teams=len(all_teams),
        )

        return {{
            "games": all_games,
            "teams": list(all_teams.values()),
            "brackets": brackets,
            "metadata": metadata,
            "year": year,
            "gender": gender,
        }}

    def _parse_bracket_html(
        self, soup, year: int, classification: str, gender: str, url: str
    ) -> Dict[str, Any]:
        """
        Parse tournament bracket from HTML using shared bracket utilities.

        {organization} bracket pages typically contain:
        - Tournament tree/bracket visualization
        - Game results in tables or divs
        - Team names with seeds
        - Scores for completed games
        - Regional/state championship structure

        Args:
            soup: BeautifulSoup parsed HTML
            year: Tournament year
            classification: Classification name ({", ".join(classifications)})
            gender: Boys or Girls
            url: Source URL

        Returns:
            Dict with games, teams, metadata
        """
        games: List[Game] = []
        teams: Dict[str, Team] = {{}}
        seen_ids = set()  # Deduplication
        season = f"{{year-1}}-{{str(year)[2:]}}"

        # Extract page-level metadata (round, venue, tipoff) - Phase 18 enhancement
        page_meta = parse_block_meta(soup, year=year) or {{}}

        # Use shared bracket parser (handles both table and div layouts)
        for team1, team2, score1, score2 in parse_bracket_tables_and_divs(soup):
            if not team1 or not team2:
                continue

            # Pass metadata to game creation - Phase 18 enhancement
            game = self._create_game(
                team1, team2, score1, score2, year, classification, gender, url, extra=page_meta
            )

            # Deduplicate games
            if game.game_id in seen_ids:
                continue
            seen_ids.add(game.game_id)
            games.append(game)

            # Extract teams using canonical IDs
            for name, tid in [
                (game.home_team_name, game.home_team_id),
                (game.away_team_name, game.away_team_id),
            ]:
                if tid not in teams:
                    teams[tid] = self._create_team(tid, name, classification, season)

        return {{
            "games": games,
            "teams": list(teams.values()),
            "metadata": {{"source_url": url}},
        }}

    def _create_game(
        self,
        team1: str,
        team2: str,
        score1: Optional[int],
        score2: Optional[int],
        year: int,
        classification: str,
        gender: str,
        url: str,
        extra: Optional[Dict[str, str]] = None,
    ) -> Game:
        """Create Game object from parsed data using canonical team IDs.

        Phase 18 enhancement: Added optional extra parameter for metadata (round, venue, tipoff).
        """
        # Use shared canonical team ID generator
        team1_id = canonical_team_id("{prefix}", team1)
        team2_id = canonical_team_id("{prefix}", team2)

        return Game(
            game_id=f"{prefix}_{{year}}_{{classification.lower()}}_{{team1_id.split('_', 1)[1]}}_vs_{{team2_id.split('_', 1)[1]}}",
            home_team_id=team1_id,
            home_team_name=team1,
            away_team_id=team2_id,
            away_team_name=team2,
            home_score=score1,
            away_score=score2,
            status=GameStatus.FINAL if score1 is not None and score2 is not None else GameStatus.SCHEDULED,
            game_type=GameType.PLAYOFF,
            level="high_school_varsity",
            league=f"{organization} {{classification}}",
            season=f"{{year-1}}-{{str(year)[2:]}}",
            gender=gender.lower(),
            data_source=self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.VERIFIED, extra=extra or {{}}
            ),
        )

    def _create_team(
        self, team_id: str, name: str, classification: str, season: str
    ) -> Team:
        """Create Team object."""
        return Team(
            team_id=team_id,
            team_name=name,
            school_name=name,
            state=self.STATE_CODE,
            country="USA",
            level=TeamLevel.HIGH_SCHOOL_VARSITY,
            league=f"{organization} {{classification}}",
            season=season,
            data_source=self.create_data_source_metadata(
                quality_flag=DataQualityFlag.VERIFIED
            ),
        )

    # Required base methods (minimal implementation for bracket-only adapter)
    async def _parse_json_data(self, json_data: Dict, season: str) -> Dict:
        return {{"teams": [], "games": [], "season": season}}

    async def _parse_html_data(self, html: str, season: str) -> Dict:
        year = self._extract_year(season)
        soup = parse_html(html)
        bracket_data = self._parse_bracket_html(soup, year, "{sample_class}", "Boys", "")
        return {{
            "teams": bracket_data["teams"],
            "games": bracket_data["games"],
            "season": season,
        }}

    async def get_player(self, player_id: str) -> Optional[Player]:
        self.logger.warning("{organization} does not provide player data - use MaxPreps for {state_name}")
        return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> List[Player]:
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        brackets = await self.get_tournament_brackets(season="2024-25")
        for team in brackets["teams"]:
            if team.team_id == team_id:
                return team
        return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> List[Game]:
        brackets = await self.get_tournament_brackets(season=season)
        games = brackets["games"]

        if team_id:
            games = [
                g for g in games if team_id in [g.home_team_id, g.away_team_id]
            ]
        if start_date:
            games = [g for g in games if g.game_date and g.game_date >= start_date]
        if end_date:
            games = [g for g in games if g.game_date and g.game_date <= end_date]

        return games[:limit]

    async def get_leaderboard(
        self, stat: str, season: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        return []
'''

    return code


def main():
    parser = argparse.ArgumentParser(
        description="Generate Phase 17/18 state adapter from template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Michigan with numeric classifications
  python scripts/scaffold_state_adapter.py --state "Michigan" --abbrev "MI" \\
      --org "MHSAA" --base-url "https://www.mhsaa.com" \\
      --classifications "1,2,3,4" --schools 750

  # North Carolina with letter classifications
  python scripts/scaffold_state_adapter.py --state "North Carolina" --abbrev "NC" \\
      --org "NCHSAA" --base-url "https://www.nchsaa.org" \\
      --classifications "4A,3A,2A,1A" --schools 400 \\
      --players "Michael Jordan,Chris Paul,James Worthy"

  # Illinois with roman numeral divisions
  python scripts/scaffold_state_adapter.py --state "Illinois" --abbrev "IL" \\
      --org "IHSA" --base-url "https://www.ihsa.org" \\
      --classifications "1A,2A,3A,4A" --schools 800
        """
    )

    parser.add_argument("--state", required=True, help="Full state name (e.g., 'Michigan')")
    parser.add_argument("--abbrev", required=True, help="2-letter state code (e.g., 'MI')")
    parser.add_argument("--org", required=True, help="Organization acronym (e.g., 'MHSAA')")
    parser.add_argument("--base-url", required=True, help="Base URL without trailing slash")
    parser.add_argument("--classifications", required=True, help="Comma-separated classifications (e.g., '1,2,3,4' or '4A,3A,2A,1A')")
    parser.add_argument("--schools", type=int, required=True, help="Approximate number of member schools")
    parser.add_argument("--players", default="", help="Optional comma-separated notable players")
    parser.add_argument("--output-dir", default="src/datasources/us", help="Output directory (default: src/datasources/us)")
    parser.add_argument("--dry-run", action="store_true", help="Print generated code without writing file")

    args = parser.parse_args()

    # Parse classifications
    classifications = [c.strip() for c in args.classifications.split(",")]

    # Generate adapter code
    code = generate_adapter(
        state_name=args.state,
        state_abbrev=args.abbrev,
        organization=args.org,
        base_url=args.base_url,
        classifications=classifications,
        school_count=args.schools,
        notable_players=args.players,
    )

    # Determine output filename
    state_slug = slugify(args.state)
    org_slug = slugify(args.org)
    filename = f"{state_slug}_{org_slug}.py"
    output_path = Path(args.output_dir) / filename

    if args.dry_run:
        print(f"# Generated adapter for {args.state} ({args.org})")
        print(f"# Would write to: {output_path}")
        print()
        print(code)
    else:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write adapter file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(code)

        print(f"[OK] Generated adapter: {output_path}")
        print(f"State: {args.state} ({args.abbrev})")
        print(f"Organization: {args.org}")
        print(f"Classifications: {', '.join(classifications)}")
        print(f"Schools: ~{args.schools}")
        print()
        print("Next steps:")
        print(f"1. Review and customize {output_path}")
        print(f"2. Add DataSourceType.{args.org.upper()} to src/models/source.py")
        print(f"3. Register adapter in src/datasources/us/__init__.py")
        print(f"4. Add entry to config/sources.yaml")
        print(f"5. Create smoke test in tests/test_datasources/test_{org_slug}.py")
        print(f"6. Update PROJECT_LOG.md with new adapter")


if __name__ == "__main__":
    main()
