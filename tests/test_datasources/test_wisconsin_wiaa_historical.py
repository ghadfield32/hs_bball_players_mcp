"""
Wisconsin WIAA Historical Coverage Tests

Parametric tests to validate Wisconsin WIAA data across:
- Multiple years (2015-2024)
- Multiple genders (Boys/Girls)
- Multiple divisions (Div1-Div4)

Tests automatically skip when fixture files don't exist,
making coverage gaps explicit.

Fixture file naming convention:
    tests/fixtures/wiaa/{year}_Basketball_{gender}_{division}.html

Example:
    tests/fixtures/wiaa/2024_Basketball_Boys_Div1.html
"""

import pytest
from pathlib import Path
from collections import Counter

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource, DataMode
from src.models import Game


# ========== CONFIGURATION ==========

FIXTURES_DIR = Path("tests/fixtures/wiaa")

# Define coverage grid (expand as fixtures are added)
YEARS = [2023, 2024]  # TODO: Add 2015-2022
GENDERS = ["Boys", "Girls"]
DIVISIONS = ["Div1"]  # TODO: Add Div2-Div4


def has_fixture(year: int, gender: str, division: str) -> bool:
    """Check if fixture file exists for given year/gender/division."""
    fixture_path = FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"
    return fixture_path.exists()


# ========== HEALTH CHECK TESTS (Parametric) ==========

@pytest.mark.parametrize("year", YEARS)
@pytest.mark.parametrize("gender", GENDERS)
@pytest.mark.parametrize("division", DIVISIONS)
@pytest.mark.asyncio
async def test_wisconsin_historical_health(year, gender, division):
    """Basic health check for Wisconsin WIAA historical data.

    Tests:
    - Games can be loaded from fixture
    - No self-games (team vs itself)
    - Scores in valid range (0-200)
    - At least one championship game exists
    """
    if not has_fixture(year, gender, division):
        pytest.skip(f"Fixture missing: {year} {gender} {division}")

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=year,
            gender=gender,
            division=division
        )

        # Basic health checks
        assert len(games) > 0, f"No games found for {year} {gender} {division}"

        # 1. No self-games
        self_games = [g for g in games if g.home_team_name == g.away_team_name]
        assert len(self_games) == 0, f"Found {len(self_games)} self-games"

        # 2. Valid scores
        for game in games:
            assert 0 <= game.home_score <= 200, f"Invalid home score: {game.home_score}"
            assert 0 <= game.away_score <= 200, f"Invalid away score: {game.away_score}"

        # 3. Championship game exists
        round_names = {g.round for g in games}
        assert any("Championship" in r for r in round_names), \
            f"No championship game found. Rounds: {round_names}"

    finally:
        await source.close()


@pytest.mark.parametrize("year", YEARS)
@pytest.mark.parametrize("gender", GENDERS)
@pytest.mark.parametrize("division", DIVISIONS)
@pytest.mark.asyncio
async def test_wisconsin_historical_rounds(year, gender, division):
    """Test round parsing for Wisconsin WIAA historical data.

    Verifies:
    - All tournament tiers (Regional, Sectional, State) are represented
    - Round names follow expected patterns
    - Unknown rounds are < 20% of total
    """
    if not has_fixture(year, gender, division):
        pytest.skip(f"Fixture missing: {year} {gender} {division}")

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=year,
            gender=gender,
            division=division
        )

        # Count rounds
        round_counts = Counter(g.round for g in games)

        # Unknown rounds should be < 20%
        unknown_count = round_counts.get("Unknown Round", 0)
        unknown_pct = (unknown_count / len(games) * 100) if games else 0
        assert unknown_pct < 20, f"Too many unknown rounds: {unknown_pct:.1f}%"

        # Check tournament tiers are represented
        found_rounds = set(round_counts.keys())
        assert any("Regional" in r for r in found_rounds), "Missing Regional rounds"
        assert any("Sectional" in r for r in found_rounds), "Missing Sectional rounds"
        assert any("State" in r for r in found_rounds), "Missing State rounds"

    finally:
        await source.close()


@pytest.mark.parametrize("year", YEARS)
@pytest.mark.parametrize("gender", GENDERS)
@pytest.mark.parametrize("division", DIVISIONS)
@pytest.mark.asyncio
async def test_wisconsin_historical_completeness(year, gender, division):
    """Test data completeness for Wisconsin WIAA historical data.

    Verifies all required fields are populated:
    - game_id
    - team names and IDs
    - scores
    - data source metadata
    """
    if not has_fixture(year, gender, division):
        pytest.skip(f"Fixture missing: {year} {gender} {division}")

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=year,
            gender=gender,
            division=division
        )

        # Check all games have required fields
        for game in games:
            assert game.game_id, "Missing game_id"
            assert game.home_team_name, "Missing home_team_name"
            assert game.away_team_name, "Missing away_team_name"
            assert game.home_team_id.startswith("wiaa_wi_"), "Invalid home_team_id"
            assert game.away_team_id.startswith("wiaa_wi_"), "Invalid away_team_id"
            assert game.home_score is not None, "Missing home_score"
            assert game.away_score is not None, "Missing away_score"
            assert game.data_source, "Missing data_source"
            assert game.data_source.source_type.value == "wiaa", "Wrong source_type"

    finally:
        await source.close()


# ========== COVERAGE REPORTING ==========

@pytest.mark.asyncio
async def test_wisconsin_fixture_coverage_report():
    """Generate a coverage report showing which fixtures exist.

    This test always passes but prints a coverage matrix
    showing which year/gender/division combinations have fixtures.
    """
    print("\n" + "=" * 80)
    print("WISCONSIN WIAA FIXTURE COVERAGE REPORT")
    print("=" * 80)

    # Extended coverage grid for reporting
    all_years = list(range(2015, 2025))
    all_genders = ["Boys", "Girls"]
    all_divisions = ["Div1", "Div2", "Div3", "Div4"]

    coverage = {}
    for year in all_years:
        coverage[year] = {}
        for gender in all_genders:
            coverage[year][gender] = {}
            for division in all_divisions:
                coverage[year][gender][division] = has_fixture(year, gender, division)

    # Print matrix
    print(f"\nFixture directory: {FIXTURES_DIR.absolute()}")
    print("\nCoverage by Year/Gender/Division:")
    print("  ✅ = fixture exists | ❌ = fixture missing\n")

    for gender in all_genders:
        print(f"\n{gender}:")
        print(f"  Year   | Div1 | Div2 | Div3 | Div4 |")
        print(f"  -------|------|------|------|------|")
        for year in all_years:
            div_status = []
            for division in all_divisions:
                has_it = coverage[year][gender][division]
                div_status.append("✅" if has_it else "❌")
            print(f"  {year}  |  {div_status[0]}  |  {div_status[1]}  |  {div_status[2]}  |  {div_status[3]}  |")

    # Summary stats
    total_cells = len(all_years) * len(all_genders) * len(all_divisions)
    filled_cells = sum(
        1 for year in all_years
        for gender in all_genders
        for division in all_divisions
        if coverage[year][gender][division]
    )
    coverage_pct = (filled_cells / total_cells * 100)

    print(f"\nSummary:")
    print(f"  Total possible fixtures: {total_cells}")
    print(f"  Fixtures present: {filled_cells}")
    print(f"  Coverage: {coverage_pct:.1f}%")
    print("\n" + "=" * 80)

    # Always pass - this is just informational
    assert True


# ========== FIXTURE VALIDATION ==========

@pytest.mark.asyncio
async def test_all_fixtures_parse_without_errors():
    """Validate that all existing fixture files parse without errors.

    This catches broken fixtures early before they're used in specific tests.
    """
    all_years = list(range(2015, 2025))
    all_genders = ["Boys", "Girls"]
    all_divisions = ["Div1", "Div2", "Div3", "Div4"]

    broken_fixtures = []

    for year in all_years:
        for gender in all_genders:
            for division in all_divisions:
                if not has_fixture(year, gender, division):
                    continue  # Skip missing fixtures

                source = WisconsinWiaaDataSource(
                    data_mode=DataMode.FIXTURE,
                    fixtures_dir=FIXTURES_DIR
                )

                try:
                    games = await source.get_tournament_brackets(
                        year=year,
                        gender=gender,
                        division=division
                    )

                    # Fixture should produce at least some games
                    if len(games) == 0:
                        broken_fixtures.append({
                            "year": year,
                            "gender": gender,
                            "division": division,
                            "error": "Parsed 0 games"
                        })

                except Exception as e:
                    broken_fixtures.append({
                        "year": year,
                        "gender": gender,
                        "division": division,
                        "error": str(e)
                    })

                finally:
                    await source.close()

    if broken_fixtures:
        error_msg = "Found broken fixtures:\n"
        for item in broken_fixtures:
            error_msg += f"  - {item['year']} {item['gender']} {item['division']}: {item['error']}\n"
        pytest.fail(error_msg)


# ========== SPECIFIC TEAM VALIDATION (Spot Checks) ==========

@pytest.mark.asyncio
async def test_wisconsin_2024_boys_div1_known_teams():
    """Spot check: Verify known teams from 2024 Boys Div1 bracket."""
    if not has_fixture(2024, "Boys", "Div1"):
        pytest.skip("Fixture missing: 2024 Boys Div1")

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=2024,
            gender="Boys",
            division="Div1"
        )

        teams = {g.home_team_name for g in games} | {g.away_team_name for g in games}

        # Known teams from 2024 Boys Div1 bracket (from fixture file)
        expected_teams = {
            "Arrowhead",
            "Marquette",
            "Franklin",
            "Neenah",
        }

        for team in expected_teams:
            assert any(team in t for t in teams), \
                f"Expected team '{team}' not found in 2024 Boys Div1. Found: {teams}"

    finally:
        await source.close()


@pytest.mark.asyncio
async def test_wisconsin_2024_girls_div1_known_teams():
    """Spot check: Verify known teams from 2024 Girls Div1 bracket."""
    if not has_fixture(2024, "Girls", "Div1"):
        pytest.skip("Fixture missing: 2024 Girls Div1")

    source = WisconsinWiaaDataSource(
        data_mode=DataMode.FIXTURE,
        fixtures_dir=FIXTURES_DIR
    )

    try:
        games = await source.get_tournament_brackets(
            year=2024,
            gender="Girls",
            division="Div1"
        )

        teams = {g.home_team_name for g in games} | {g.away_team_name for g in games}

        # Known teams from 2024 Girls Div1 bracket (from fixture file)
        expected_teams = {
            "Homestead",
            "Muskego",
            "Appleton North",
        }

        for team in expected_teams:
            assert any(team in t for t in teams), \
                f"Expected team '{team}' not found in 2024 Girls Div1. Found: {teams}"

    finally:
        await source.close()
