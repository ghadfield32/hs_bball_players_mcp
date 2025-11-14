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
from typing import List, Tuple, Optional
import yaml

from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource, DataMode
from src.models import Game


# ========== CONFIGURATION ==========

FIXTURES_DIR = Path("tests/fixtures/wiaa")
MANIFEST_PATH = FIXTURES_DIR / "manifest_wisconsin.yml"

# Manifest cache
_MANIFEST_CACHE: Optional[dict] = None


def load_manifest() -> dict:
    """Load the Wisconsin WIAA fixture manifest (cached)."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            _MANIFEST_CACHE = yaml.safe_load(f)
    return _MANIFEST_CACHE


def get_test_parameters() -> List[Tuple[int, str, str]]:
    """
    Get test parameters from manifest for parametric tests.

    Returns list of (year, gender, division) tuples for all combinations
    defined in the manifest's coverage grid.
    """
    manifest = load_manifest()
    years = manifest.get("years", [])
    genders = manifest.get("genders", [])
    divisions = manifest.get("divisions", [])

    # Generate all combinations from coverage grid
    parameters = [
        (year, gender, division)
        for year in years
        for gender in genders
        for division in divisions
    ]

    return parameters


def has_fixture(year: int, gender: str, division: str) -> bool:
    """Check if fixture file exists for given year/gender/division."""
    fixture_path = FIXTURES_DIR / f"{year}_Basketball_{gender}_{division}.html"
    return fixture_path.exists()


def get_fixture_status(year: int, gender: str, division: str) -> str:
    """
    Get manifest status for a specific fixture.

    Returns:
        Status string: "present", "planned", "future", "unavailable", or "unknown"
    """
    manifest = load_manifest()
    for entry in manifest.get("fixtures", []):
        if (entry["year"] == year and
            entry["gender"] == gender and
            entry["division"] == division):
            return entry.get("status", "unknown")
    return "unknown"


# Generate test parameters from manifest
TEST_PARAMS = get_test_parameters()
PARAM_IDS = [f"{y}_{g}_{d}" for y, g, d in TEST_PARAMS]


# ========== HEALTH CHECK TESTS (Parametric) ==========

@pytest.mark.parametrize("year,gender,division", TEST_PARAMS, ids=PARAM_IDS)
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


@pytest.mark.parametrize("year,gender,division", TEST_PARAMS, ids=PARAM_IDS)
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


@pytest.mark.parametrize("year,gender,division", TEST_PARAMS, ids=PARAM_IDS)
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
    showing which year/gender/division combinations have fixtures
    and compares against manifest status.
    """
    print("\n" + "=" * 80)
    print("WISCONSIN WIAA FIXTURE COVERAGE REPORT")
    print("=" * 80)

    # Load manifest to get coverage grid
    manifest = load_manifest()
    all_years = manifest.get("years", [])
    all_genders = manifest.get("genders", [])
    all_divisions = manifest.get("divisions", [])

    # Collect coverage data
    coverage = {}
    status_counts = {"present": 0, "planned": 0, "future": 0, "unknown": 0}

    for year in all_years:
        coverage[year] = {}
        for gender in all_genders:
            coverage[year][gender] = {}
            for division in all_divisions:
                file_exists = has_fixture(year, gender, division)
                manifest_status = get_fixture_status(year, gender, division)
                coverage[year][gender][division] = {
                    "exists": file_exists,
                    "status": manifest_status
                }
                status_counts[manifest_status] = status_counts.get(manifest_status, 0) + 1

    # Print matrix
    print(f"\nFixture directory: {FIXTURES_DIR.absolute()}")
    print(f"Manifest: {MANIFEST_PATH.absolute()}")
    print("\nCoverage by Year/Gender/Division:")
    print("  ✅ = present | 📋 = planned | ⏳ = future | ❌ = missing/unknown\n")

    for gender in all_genders:
        print(f"\n{gender}:")
        print(f"  Year   | Div1 | Div2 | Div3 | Div4 |")
        print(f"  -------|------|------|------|------|")
        for year in all_years:
            div_status = []
            for division in all_divisions:
                info = coverage[year][gender][division]
                if info["exists"] and info["status"] == "present":
                    div_status.append("✅")
                elif info["status"] == "planned":
                    div_status.append("📋")
                elif info["status"] == "future":
                    div_status.append("⏳")
                else:
                    div_status.append("❌")
            print(f"  {year}  |  {div_status[0]}  |  {div_status[1]}  |  {div_status[2]}  |  {div_status[3]}  |")

    # Summary stats
    total_cells = len(all_years) * len(all_genders) * len(all_divisions)
    filled_cells = sum(
        1 for year in all_years
        for gender in all_genders
        for division in all_divisions
        if coverage[year][gender][division]["exists"]
    )
    coverage_pct = (filled_cells / total_cells * 100) if total_cells > 0 else 0

    print(f"\nSummary:")
    print(f"  Total coverage grid: {total_cells} fixtures")
    print(f"  Fixtures present (✅): {filled_cells} ({coverage_pct:.1f}%)")
    print(f"  Planned (📋): {status_counts.get('planned', 0)}")
    print(f"  Future (⏳): {status_counts.get('future', 0)}")

    # Check for manifest/filesystem mismatches
    mismatches = []
    for year in all_years:
        for gender in all_genders:
            for division in all_divisions:
                info = coverage[year][gender][division]
                if info["exists"] and info["status"] != "present":
                    mismatches.append(f"{year} {gender} {division}: file exists but status={info['status']}")
                elif not info["exists"] and info["status"] == "present":
                    mismatches.append(f"{year} {gender} {division}: status=present but file missing")

    if mismatches:
        print(f"\n⚠️  Manifest/Filesystem Mismatches ({len(mismatches)}):")
        for mismatch in mismatches[:10]:
            print(f"   - {mismatch}")
        if len(mismatches) > 10:
            print(f"   ... and {len(mismatches) - 10} more")

    print("\n" + "=" * 80)

    # Always pass - this is just informational
    assert True


# ========== FIXTURE VALIDATION ==========

@pytest.mark.asyncio
async def test_manifest_validation():
    """Validate the Wisconsin WIAA fixture manifest structure.

    Checks:
    - Manifest file exists and is valid YAML
    - Required fields are present (years, genders, divisions, fixtures)
    - All fixture entries have required fields (year, gender, division, status)
    - Years/genders/divisions match coverage grid
    - All 80 combinations are accounted for in fixtures list
    """
    # Check manifest exists
    assert MANIFEST_PATH.exists(), f"Manifest not found: {MANIFEST_PATH}"

    # Load and parse manifest
    manifest = load_manifest()
    assert isinstance(manifest, dict), "Manifest should be a dict"

    # Check required top-level fields
    assert "years" in manifest, "Manifest missing 'years' field"
    assert "genders" in manifest, "Manifest missing 'genders' field"
    assert "divisions" in manifest, "Manifest missing 'divisions' field"
    assert "fixtures" in manifest, "Manifest missing 'fixtures' field"

    years = manifest["years"]
    genders = manifest["genders"]
    divisions = manifest["divisions"]
    fixtures = manifest["fixtures"]

    # Check types
    assert isinstance(years, list), "'years' should be a list"
    assert isinstance(genders, list), "'genders' should be a list"
    assert isinstance(divisions, list), "'divisions' should be a list"
    assert isinstance(fixtures, list), "'fixtures' should be a list"

    # Check non-empty
    assert len(years) > 0, "'years' should not be empty"
    assert len(genders) > 0, "'genders' should not be empty"
    assert len(divisions) > 0, "'divisions' should not be empty"
    assert len(fixtures) > 0, "'fixtures' should not be empty"

    # Check coverage: should have entry for all year/gender/division combos
    expected_count = len(years) * len(genders) * len(divisions)
    assert len(fixtures) == expected_count, \
        f"Expected {expected_count} fixture entries, found {len(fixtures)}"

    # Check all fixture entries have required fields
    valid_statuses = {"present", "planned", "future", "unavailable"}
    for i, entry in enumerate(fixtures):
        assert "year" in entry, f"Fixture {i} missing 'year'"
        assert "gender" in entry, f"Fixture {i} missing 'gender'"
        assert "division" in entry, f"Fixture {i} missing 'division'"
        assert "status" in entry, f"Fixture {i} missing 'status'"

        assert entry["year"] in years, f"Fixture {i} year {entry['year']} not in years list"
        assert entry["gender"] in genders, f"Fixture {i} gender {entry['gender']} not in genders list"
        assert entry["division"] in divisions, f"Fixture {i} division {entry['division']} not in divisions list"
        assert entry["status"] in valid_statuses, \
            f"Fixture {i} invalid status '{entry['status']}', must be one of {valid_statuses}"

    # Check for duplicate entries
    combos_seen = set()
    for entry in fixtures:
        combo = (entry["year"], entry["gender"], entry["division"])
        assert combo not in combos_seen, \
            f"Duplicate fixture entry: {combo}"
        combos_seen.add(combo)

    print(f"\n✅ Manifest validation passed")
    print(f"   Coverage grid: {len(years)} years × {len(genders)} genders × {len(divisions)} divisions")
    print(f"   Total fixtures tracked: {len(fixtures)}")


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
