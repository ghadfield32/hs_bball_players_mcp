# DataSource Adapter Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing datasource adapters for the basketball player statistics API. It is based on proven patterns from working adapters (EYBL, PSAL, MN Hub, FIBA Youth).

## Prerequisites

Before implementing an adapter, you need:
1. Access to the target website to inspect HTML structure
2. Understanding of the website's URL patterns
3. Knowledge of available statistics on the site
4. Awareness of any rate limiting or access restrictions

## Implementation Steps

### Step 1: Inspect Website Structure

Use browser developer tools to:

**1.1 Identify Key URLs**
```
Stats Page: Where season averages are displayed
Leaders Page: Statistical leaderboards
Teams Page: Team/school listings
Schedule Page: Game schedules and results
Player Profiles: Individual player pages (if available)
```

**1.2 Analyze HTML Structure**
- Find stats tables: Look for `<table>` elements
- Identify column headers: Examine `<thead>` or first `<tr>`
- Locate player links: Check for `<a>` tags in player name cells
- Note table classes: Record class names for reliable selection
- Check pagination: Determine if multiple pages exist

**1.3 Document Data Availability**
Create a checklist:
- [ ] Player names
- [ ] Team/school names
- [ ] Position
- [ ] Height
- [ ] Grad year/class
- [ ] Games played
- [ ] Points (total and/or per game)
- [ ] Rebounds (total and/or per game)
- [ ] Assists (total and/or per game)
- [ ] Steals, blocks, turnovers
- [ ] Shooting percentages (FG%, 3P%, FT%)
- [ ] Made/attempted shooting stats

### Step 2: Define Adapter Configuration

Update the adapter file with actual endpoints:

```python
class DataSourceAdapter(BaseDataSource):
    source_type = DataSourceType.YOUR_SOURCE
    source_name = "Your Source Name"
    base_url = "https://actual-website.com"  # UPDATE THIS
    region = DataSourceRegion.US  # or CANADA, EUROPE, etc.

    def __init__(self):
        super().__init__()

        # Define actual endpoints found in Step 1
        self.stats_url = f"{self.base_url}/stats/leaders"
        self.teams_url = f"{self.base_url}/teams"
        self.schedule_url = f"{self.base_url}/schedule"
        # Add more as needed
```

### Step 3: Implement search_players()

This is usually the first method to implement since it's used by other methods.

**Pattern: Search through stats/leaders page**

```python
async def search_players(
    self,
    name: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 50,
) -> list[Player]:
    """Search for players."""
    try:
        # Fetch stats page with caching
        # Cache for 1 hour (3600s) for frequently accessed pages
        html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
        soup = parse_html(html)

        # Find stats table using helper
        # Try table class hints from Step 1
        table = find_stat_table(soup, table_class_hint="stats")
        if not table:
            self.logger.warning("No stats table found")
            return []

        # Extract table data
        rows = extract_table_data(table)

        # Create data source metadata
        data_source = self.create_data_source_metadata(
            url=self.stats_url,
            quality_flag=DataQualityFlag.COMPLETE
        )

        players = []
        for row in rows[:limit * 2]:  # Get extra for filtering
            # Use helper to parse player
            player_data = parse_player_from_row(
                row,
                source_prefix="your_prefix",  # e.g., "ote", "osba"
                school_state="State" if applicable else None
            )

            if not player_data:
                continue

            # Add data source and level
            player_data["data_source"] = data_source
            player_data["level"] = PlayerLevel.HIGH_SCHOOL  # or appropriate level

            # Validate and create Player object
            player = self.validate_and_log_data(
                Player,
                player_data,
                f"player {player_data.get('full_name')}"
            )

            if not player:
                continue

            # Apply filters
            if name and name.lower() not in player.full_name.lower():
                continue
            if team and (not player.team_name or team.lower() not in player.team_name.lower()):
                continue

            players.append(player)

            if len(players) >= limit:
                break

        self.logger.info(f"Found {len(players)} players")
        return players

    except Exception as e:
        self.logger.error("Failed to search players", error=str(e))
        return []
```

### Step 4: Implement get_player_season_stats()

**Pattern: Find player in stats table and parse their row**

```python
async def get_player_season_stats(
    self, player_id: str, season: Optional[str] = None
) -> Optional[PlayerSeasonStats]:
    """Get player season statistics."""
    try:
        # Fetch stats page
        html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
        soup = parse_html(html)

        # Find stats table
        table = find_stat_table(soup, table_class_hint="stats")
        if not table:
            return None

        # Extract rows
        rows = extract_table_data(table)

        # Extract player name from player_id
        # Format: "prefix_first_last"
        player_name = player_id.replace("prefix_", "").replace("_", " ").title()

        # Find matching player row
        for row in rows:
            row_player = clean_player_name(row.get("Player") or row.get("NAME") or "")
            if player_name.lower() in row_player.lower():
                # Use helper to parse stats
                stats_data = parse_season_stats_from_row(
                    row,
                    player_id,
                    season or "2024-25",
                    "Your League Name"
                )

                # Validate and return
                return self.validate_and_log_data(
                    PlayerSeasonStats,
                    stats_data,
                    f"season stats for {player_name}"
                )

        self.logger.warning(f"Player not found in stats", player_id=player_id)
        return None

    except Exception as e:
        self.logger.error("Failed to get player season stats", error=str(e))
        return None
```

### Step 5: Implement get_leaderboard()

**Pattern: Find specific stat table and extract top players**

```python
async def get_leaderboard(
    self,
    stat: str,
    season: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Get statistical leaderboard."""
    try:
        # Fetch leaders page
        html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
        soup = parse_html(html)

        # Find all tables
        tables = soup.find_all("table")

        # Find the table for requested stat
        for table in tables:
            # Check header before table
            header = table.find_previous(["h2", "h3", "h4"])
            if header:
                header_text = get_text_or_none(header).lower()
                if stat.lower() in header_text:
                    # Found the right table
                    rows = extract_table_data(table)
                    leaderboard = []

                    for i, row in enumerate(rows[:limit], 1):
                        player_name = clean_player_name(
                            row.get("Player") or row.get("NAME") or ""
                        )
                        team = row.get("Team") or row.get("School")

                        # Find stat value (try multiple column names)
                        stat_value = parse_float(
                            row.get(stat.upper())
                            or row.get("Value")
                            or row.get("AVG")
                        )

                        if player_name and stat_value is not None:
                            entry = build_leaderboard_entry(
                                rank=i,
                                player_name=player_name,
                                stat_value=stat_value,
                                stat_name=stat,
                                season=season or "2024-25",
                                source_prefix="your_prefix",
                                team_name=team
                            )
                            leaderboard.append(entry)

                    if leaderboard:
                        return leaderboard

        self.logger.warning(f"No leaderboard found for stat: {stat}")
        return []

    except Exception as e:
        self.logger.error("Failed to get leaderboard", error=str(e))
        return []
```

### Step 6: Implement Remaining Methods

**get_player()**
Usually calls search_players() with limit=1:
```python
async def get_player(self, player_id: str) -> Optional[Player]:
    players = await self.search_players(name=player_id, limit=1)
    return players[0] if players else None
```

**get_team()**
Similar pattern to search_players() but for team data:
```python
async def get_team(self, team_id: str) -> Optional[Team]:
    # Fetch standings/teams page
    # Find team in table
    # Parse team data (wins, losses, conference, etc.)
    # Validate and return Team object
    pass
```

**get_games()**
Requires schedule page parsing:
```python
async def get_games(...) -> list[Game]:
    # Fetch schedule page
    # Extract game rows
    # Parse dates, teams, scores
    # Filter by parameters
    # Return list of Game objects
    pass
```

**get_player_game_stats()**
Requires individual game box score pages:
```python
async def get_player_game_stats(self, player_id: str, game_id: str) -> Optional[PlayerGameStats]:
    # Construct box score URL
    # Find player's row in box score
    # Parse game stats
    # Return PlayerGameStats object
    pass
```

## Step 7: Testing

### 7.1 Create Test File

Create `tests/test_datasources/test_<source>.py`:

```python
"""Tests for <Source> DataSource Adapter"""

import pytest

from src.datasources.your_region.your_source import YourSourceDataSource


@pytest.mark.asyncio
class TestYourSourceDataSource:
    """Test suite for Your Source adapter."""

    @pytest.fixture
    async def datasource(self):
        """Create datasource instance."""
        ds = YourSourceDataSource()
        yield ds
        await ds.close()

    async def test_search_players(self, datasource):
        """Test player search."""
        players = await datasource.search_players(limit=10)

        assert len(players) > 0, "Should find players"

        player = players[0]
        assert player.full_name, "Player should have name"
        assert player.player_id.startswith("your_prefix_")
        assert player.data_source is not None

        print(f"\nFound {len(players)} players")
        print(f"Sample player: {player.full_name}")

    async def test_search_players_with_name_filter(self, datasource):
        """Test player search with name filter."""
        # Use a common name that should exist
        players = await datasource.search_players(name="Smith", limit=5)

        for player in players:
            assert "smith" in player.full_name.lower()

    async def test_get_player_season_stats(self, datasource):
        """Test getting player season stats."""
        # First find a player
        players = await datasource.search_players(limit=1)
        if not players:
            pytest.skip("No players found")

        player = players[0]

        # Get their stats
        stats = await datasource.get_player_season_stats(player.player_id)

        assert stats is not None, "Should find stats"
        assert stats.player_id == player.player_id
        assert stats.games_played >= 0

        print(f"\nStats for {player.full_name}:")
        print(f"  Games: {stats.games_played}")
        print(f"  PPG: {stats.points_per_game}")
        print(f"  RPG: {stats.rebounds_per_game}")
        print(f"  APG: {stats.assists_per_game}")

    async def test_get_leaderboard(self, datasource):
        """Test getting statistical leaderboard."""
        leaderboard = await datasource.get_leaderboard("points", limit=10)

        assert len(leaderboard) > 0, "Should find leaders"

        top_player = leaderboard[0]
        assert top_player["rank"] == 1
        assert top_player["player_name"]
        assert top_player["stat_value"] > 0

        print(f"\nTop 5 scorers:")
        for entry in leaderboard[:5]:
            print(f"  {entry['rank']}. {entry['player_name']}: {entry['stat_value']}")

    async def test_rate_limiting(self, datasource):
        """Test that rate limiting is working."""
        import time

        start = time.time()

        # Make multiple requests quickly
        for _ in range(5):
            await datasource.search_players(limit=5)

        elapsed = time.time() - start

        # Should take some time due to rate limiting
        # Adjust assertion based on your rate limit settings
        print(f"\n5 requests took {elapsed:.2f} seconds")
```

### 7.2 Run Tests

```bash
# Run specific datasource tests
pytest tests/test_datasources/test_your_source.py -v

# Run with output
pytest tests/test_datasources/test_your_source.py -v -s

# Run async tests
pytest tests/test_datasources/test_your_source.py -v --asyncio-mode=auto
```

### 7.3 Validate Data Quality

Check test output for:
- All players have required fields (name, player_id)
- Stats are reasonable (no negative values, realistic ranges)
- Grad years are valid (2024-2030 range)
- Heights are in inches (60-90 range)
- Percentages are 0-100 or 0-1 range
- No missing critical data

## Rate Limiting Best Practices

### Configuration

Rate limits are configured in `BaseDataSource`:

```python
# In BaseDataSource
self.rate_limiter = TokenBucketRateLimiter(
    rate=10.0,  # 10 requests per second
    capacity=20.0  # Burst capacity
)
```

### Monitoring

Check rate limit metrics:
```python
# In tests or debugging
print(datasource.http_client.metrics.total_requests)
print(datasource.http_client.metrics.cache_hits)
print(datasource.http_client.metrics.cache_misses)
```

### Recommendations

1. **Start Conservative**: Begin with 5-10 req/sec
2. **Use Caching**: Set appropriate cache_ttl values
3. **Test Gradually**: Increase load slowly
4. **Monitor Errors**: Watch for 429 (Too Many Requests) responses
5. **Respect robots.txt**: Check website's robots.txt file

## Common Issues and Solutions

### Issue: Table not found
**Solution**: Try different table finding strategies:
```python
# Strategy 1: By class
table = soup.find("table", class_="stats-table")

# Strategy 2: By ID
table = soup.find("table", id="player-stats")

# Strategy 3: First table
table = soup.find("table")

# Strategy 4: After header
header = soup.find("h2", text="Season Stats")
table = header.find_next("table")
```

### Issue: Column names vary
**Solution**: Use fallback column name patterns:
```python
player_name = (
    row.get("Player")
    or row.get("NAME")
    or row.get("Name")
    or row.get("PLAYER")
    or row.get("PLAYER NAME")
)
```

### Issue: Stats in wrong format
**Solution**: Use parsing helpers that handle multiple formats:
```python
# parse_float handles "15.5", "15,5", "15.5%"
ppg = parse_float(row.get("PPG"))

# parse_int handles "1,234", "1 234", "1234"
points = parse_int(row.get("PTS"))
```

### Issue: Player names have jersey numbers
**Solution**: Use `clean_player_name()`:
```python
player_name = clean_player_name(row.get("Player"))
# "23 Michael Jordan" -> "Michael Jordan"
```

## Validation Checklist

Before committing your adapter implementation:

- [ ] All abstract methods implemented
- [ ] Endpoints are real URLs (not placeholder)
- [ ] Rate limiting tested and within limits
- [ ] At least 3 test cases passing
- [ ] Data validation passing (no negative stats, valid ranges)
- [ ] Error handling in place (try/except blocks)
- [ ] Logging statements added
- [ ] Documentation strings complete
- [ ] Integration tested with aggregation service
- [ ] Tested with real API calls (no fake data)

## Next Steps

After implementing and testing your adapter:

1. **Update Aggregator**: Add your datasource to `src/services/aggregator.py`
2. **Update Models**: Add new `DataSourceType` enum value if needed
3. **Document**: Add notes to PROJECT_LOG.md
4. **Integration Test**: Test through API endpoints
5. **Performance Test**: Monitor response times and cache hit rates

## Reference: Working Adapters

Study these for proven patterns:
- `src/datasources/us/eybl.py` - Simple stats page scraping
- `src/datasources/us/psal.py` - Multiple stat tables, leaderboards
- `src/datasources/us/mn_hub.py` - Player profiles, detailed parsing
- `src/datasources/europe/fiba_youth.py` - Competition-based structure
