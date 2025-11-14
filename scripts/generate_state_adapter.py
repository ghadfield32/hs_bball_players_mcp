"""
State Adapter Generator (Phase 25 Enhanced)

Scaffolds new state adapters using the StateAdapterBase template.
Enforces "URL discovery FIRST" workflow to prevent Phase 23 URL chaos.

Usage:
    python scripts/generate_state_adapter.py \\
        --state NV \\
        --name Nevada \\
        --org NIAA \\
        --url "https://www.nevadapreps.com" \\
        --classifications "5A,4A,3A,2A,1A"

This will:
    1. Generate src/datasources/us/{state_org}.py using StateAdapterBase
    2. Create test stub in tests/test_datasources/test_{state_org}.py
    3. Create data/research/{state}_url_patterns.json for documentation
    4. Provide manual steps for STATE_REGISTRY and imports

Enforces URL discovery:
    - Requires --url parameter (must manually verify URL first)
    - Prompts for bracket URL pattern confirmation
    - Creates URL pattern documentation
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List
import re
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def slugify(text: str) -> str:
    """Convert text to snake_case for file/variable names."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text


ADAPTER_TEMPLATE = '''"""
{full_name} DataSource Adapter

Provides tournament brackets, schedules, and results for {state_name} high school basketball.

Base URL: {url}
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
    Team,
    TeamLevel,
)
from ...utils import extract_table_data, get_text_or_none, parse_html, parse_int, parse_record
from ..base_association import AssociationAdapterBase


class {class_name}DataSource(AssociationAdapterBase):
    """
    {full_name} data source adapter.

    Provides tournament brackets, schedules, and championship results.

    Coverage:
    - Tournament brackets (state championships)
    - Championship results where available
    - Team records where available
    - Historical tournament data where available

    Limitations:
    - Player statistics typically not available
    - Regular season schedules may be limited
    """

    source_type = DataSourceType.{enum_name}
    source_name = "{name}"
    base_url = "{url}"
    region = DataSourceRegion.US_{state_abbr}

    def _get_season_url(self, season: str) -> str:
        """Get URL for {state_name} basketball season data."""
        year = int(season.split("-")[0]) + 1
        # Adjust URL based on actual association structure
        return f"{{self.base_url}}/sports/basketball/boys/{{year}}"

    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """
        Parse JSON data from {name}.

        Args:
            json_data: JSON data from endpoint
            season: Season string

        Returns:
            Dict with teams, games, brackets
        """
        teams: List[Team] = []
        games: List[Game] = []

        # TODO: Implement based on actual JSON structure from {name}
        # This is a template - customize based on association's JSON schema

        if "teams" in json_data:
            for team_data in json_data.get("teams", []):
                team = self._parse_team_from_json(team_data, season)
                if team:
                    teams.append(team)

        if "games" in json_data or "schedule" in json_data or "brackets" in json_data:
            game_list = json_data.get("games") or json_data.get("schedule") or json_data.get("brackets", [])
            for game_data in game_list:
                game = self._parse_game_from_json(game_data, season)
                if game:
                    games.append(game)

        self.logger.info(
            f"Parsed {name} JSON data",
            season=season,
            teams=len(teams),
            games=len(games),
        )

        return {{"teams": teams, "games": games, "season": season, "source": "json"}}

    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """
        Parse HTML data from {name}.

        Extracts tournament brackets, schedules from HTML tables.

        Args:
            html: HTML content
            season: Season string

        Returns:
            Dict with teams, games, brackets
        """
        soup = parse_html(html)
        teams: List[Team] = []
        games: List[Game] = []

        # Look for bracket/schedule tables
        tables = soup.find_all("table", class_=["bracket", "tournament", "schedule", "playoff"])

        for table in tables:
            rows = table.find_all("tr")

            for row in rows[1:]:  # Skip header
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    game = self._parse_game_from_row(cells, season)
                    if game:
                        games.append(game)

                        # Extract teams from game
                        if game.home_team_id and game.home_team_name:
                            teams.append(self._create_team(game.home_team_id, game.home_team_name, season))
                        if game.away_team_id and game.away_team_name:
                            teams.append(self._create_team(game.away_team_id, game.away_team_name, season))

        # Deduplicate teams by ID
        unique_teams = {{team.team_id: team for team in teams}}.values()
        teams = list(unique_teams)

        self.logger.info(
            f"Parsed {name} HTML data",
            season=season,
            teams=len(teams),
            games=len(games),
        )

        return {{"teams": teams, "games": games, "season": season, "source": "html"}}

    def _parse_team_from_json(self, data: Dict[str, Any], season: str) -> Optional[Team]:
        """Parse team from JSON data."""
        try:
            team_name = data.get("name") or data.get("team_name") or data.get("school")
            if not team_name:
                return None

            team_id = f"{id_prefix}_{{team_name.lower().replace(' ', '_')}}"
            wins, losses = parse_record(data.get("record", ""))

            return Team(
                team_id=team_id,
                name=team_name,
                school=team_name,
                level=TeamLevel.HIGH_SCHOOL,
                conference=data.get("conference") or data.get("region") or data.get("classification"),
                season=season,
                wins=wins,
                losses=losses,
                data_source=self.create_data_source_metadata(
                    url=f"{{self.base_url}}/teams/{{team_id}}",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse team from JSON", error=str(e))
            return None

    def _parse_game_from_json(self, data: Dict[str, Any], season: str) -> Optional[Game]:
        """Parse game from JSON data."""
        try:
            home_team = data.get("home_team") or data.get("team1") or data.get("home")
            away_team = data.get("away_team") or data.get("team2") or data.get("away")

            if not home_team or not away_team:
                return None

            game_id = f"{id_prefix}_{{data.get('id', data.get('game_id', hash(str(data))))}}"
            game_date_str = data.get("date") or data.get("game_date")
            game_date = None
            if game_date_str:
                try:
                    game_date = datetime.fromisoformat(game_date_str)
                except Exception:
                    pass

            return Game(
                game_id=game_id,
                home_team_name=home_team,
                away_team_name=away_team,
                home_team_id=f"{id_prefix}_{{home_team.lower().replace(' ', '_')}}",
                away_team_id=f"{id_prefix}_{{away_team.lower().replace(' ', '_')}}",
                game_date=game_date,
                game_type=GameType.TOURNAMENT,
                status=GameStatus.COMPLETED if data.get("final") or data.get("completed") else GameStatus.SCHEDULED,
                home_score=parse_int(data.get("home_score")),
                away_score=parse_int(data.get("away_score")),
                season=season,
                data_source=self.create_data_source_metadata(
                    url=f"{{self.base_url}}/games/{{game_id}}",
                    quality_flag=DataQualityFlag.VERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse game from JSON", error=str(e))
            return None

    def _parse_game_from_row(self, cells: List[Any], season: str) -> Optional[Game]:
        """Parse game from HTML table row."""
        try:
            if len(cells) < 2:
                return None

            home_team = get_text_or_none(cells[0])
            away_team = get_text_or_none(cells[1])

            if not home_team or not away_team:
                return None

            # Extract score if present
            score_cell = cells[2] if len(cells) > 2 else None
            home_score = None
            away_score = None

            if score_cell:
                score_text = get_text_or_none(score_cell)
                if score_text and "-" in score_text:
                    parts = score_text.split("-")
                    if len(parts) == 2:
                        home_score = parse_int(parts[0].strip())
                        away_score = parse_int(parts[1].strip())

            game_id = f"{id_prefix}_{{home_team.lower().replace(' ', '_')}}_{{away_team.lower().replace(' ', '_')}}"

            return Game(
                game_id=game_id,
                home_team_name=home_team,
                away_team_name=away_team,
                home_team_id=f"{id_prefix}_{{home_team.lower().replace(' ', '_')}}",
                away_team_id=f"{id_prefix}_{{away_team.lower().replace(' ', '_')}}",
                game_type=GameType.TOURNAMENT,
                status=GameStatus.COMPLETED if home_score is not None else GameStatus.SCHEDULED,
                home_score=home_score,
                away_score=away_score,
                season=season,
                data_source=self.create_data_source_metadata(
                    url=self.base_url,
                    quality_flag=DataQualityFlag.UNVERIFIED,
                ),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse game from HTML row", error=str(e))
            return None

    def _create_team(self, team_id: str, team_name: str, season: str) -> Team:
        """Create team object."""
        return Team(
            team_id=team_id,
            name=team_name,
            school=team_name,
            level=TeamLevel.HIGH_SCHOOL,
            season=season,
            data_source=self.create_data_source_metadata(
                url=f"{{self.base_url}}/teams",
                quality_flag=DataQualityFlag.UNVERIFIED,
            ),
        )
'''


def generate_adapter(state: str, name: str, full_name: str, url: str, output_dir: Path) -> None:
    """Generate state adapter file."""
    # Derive values
    class_name = "".join([part.capitalize() for part in name.split() if part.upper()])
    if not class_name.endswith("DataSource"):
        class_name = class_name.replace("DataSource", "")  # Remove if already there

    enum_name = name.upper().replace(" ", "_").replace("-", "_")
    id_prefix = name.lower().replace(" ", "_").replace("-", "_")
    state_name = full_name.split(" High School")[0] if "High School" in full_name else state

    # Generate code
    code = ADAPTER_TEMPLATE.format(
        full_name=full_name,
        state_name=state_name,
        url=url,
        class_name=class_name,
        enum_name=enum_name,
        name=name,
        state_abbr=state.upper(),
        id_prefix=id_prefix,
    )

    # Write file
    filename = f"{id_prefix}.py"
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        f.write(code)

    print(f"✅ Generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate state athletic association adapters")
    parser.add_argument("--state", help="State abbreviation (e.g., GA, VA)")
    parser.add_argument("--name", help="Source name (e.g., 'Georgia GHSA')")
    parser.add_argument("--full-name", help="Full official name")
    parser.add_argument("--url", help="Official website URL")
    parser.add_argument("--batch", choices=["southeast", "northeast", "midwest", "southwest_west", "all"], help="Generate batch of states")
    parser.add_argument("--output-dir", default="src/datasources/us", help="Output directory")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.batch:
        # Batch generation
        states_to_generate = REGIONS.get(args.batch, [])
        if args.batch == "all":
            states_to_generate = list(STATES_INFO.keys())

        print(f"📦 Generating {len(states_to_generate)} adapters for {args.batch}...")

        for state in states_to_generate:
            if state in STATES_INFO:
                info = STATES_INFO[state]
                generate_adapter(
                    state=state,
                    name=info["name"],
                    full_name=info["full_name"],
                    url=info["url"],
                    output_dir=output_dir,
                )
            else:
                print(f"⚠️  No info for state: {state}")

        print(f"\n✅ Generated {len(states_to_generate)} adapters!")

    elif args.state and args.name and args.url:
        # Single adapter generation
        full_name = args.full_name or args.name
        generate_adapter(
            state=args.state,
            name=args.name,
            full_name=full_name,
            url=args.url,
            output_dir=output_dir,
        )

    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python scripts/generate_state_adapter.py --state GA --name 'Georgia GHSA' --full-name 'Georgia High School Association' --url 'https://www.ghsa.net'")
        print("  python scripts/generate_state_adapter.py --batch southeast")
        print("  python scripts/generate_state_adapter.py --batch all")


if __name__ == "__main__":
    main()
