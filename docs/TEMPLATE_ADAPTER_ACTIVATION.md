# Template Adapter Activation Guide

This document explains how to activate the template adapters that have been created but require URL verification and testing.

## Template Adapters Overview

The following 5 adapters have complete code structure but need URL updates after website inspection:

| Adapter | Region | Source | Status | Priority |
|---------|--------|--------|--------|----------|
| **ANGT** | Europe | EuroLeague Next Generation (U18) | Template | High |
| **OSBA** | Canada | Ontario Scholastic Basketball Assoc | Template | High |
| **PlayHQ** | Australia | Basketball Australia Pathway | Template | High |
| **OTE** | US | Overtime Elite | Template | Medium |
| **Grind Session** | US | Prep Tournament Series | Template | Medium |

---

## Activation Process

### Step 1: Website Inspection

Before activating each adapter, you must inspect the actual website to verify URLs:

#### For ANGT (EuroLeague Next Gen):
```bash
# Visit and inspect:
https://www.euroleaguebasketball.net/next-generation

# Look for:
- Stats/players page for latest tournament
- HTML table structure
- Column names (including PIR - Performance Index Rating)
- URL patterns: /competition, /players, /games
- robots.txt permissions
- Tournament structure (group stage + finals)
```

#### For OSBA (Ontario prep):
```bash
# Visit and inspect:
https://www.osba.ca

# Look for:
- Stats/leaders pages
- Division structure (U17, U19, Prep)
- Player profiles
- Schedule/games pages
- URL patterns
```

#### For PlayHQ (Australia):
```bash
# Visit and inspect:
https://www.playhq.com/basketball

# Look for:
- Competition listings
- U16/U18 Championships
- Stats pages per competition
- Player profile URLs
- Game stats/box scores
- URL patterns: /competitions/{comp_id}/players
```

#### For OTE (Overtime Elite):
```bash
# Visit and inspect:
https://overtimeelite.com

# Look for:
- Stats/players page
- Team rosters
- Game schedules
- Leaderboards
- URL patterns
- Check for JavaScript rendering requirements
```

#### For Grind Session:
```bash
# Visit and inspect:
https://thegrindsession.com

# Look for:
- Event pages
- Event-specific stats
- Team rosters by event
- Game schedules
- URL patterns: /event/{event_id}/stats
```

---

### Step 2: Update Adapter URLs

Once you've inspected the website, update the URLs in each adapter file:

#### Example: Updating ANGT URLs

**File**: `src/datasources/europe/angt.py`

```python
# BEFORE (template placeholders):
self.competition_url = f"{self.base_url}/competition"  # UPDATE AFTER INSPECTION
self.stats_url = f"{self.base_url}/stats"  # UPDATE AFTER INSPECTION

# AFTER (with actual URLs):
self.competition_url = f"{self.base_url}/competition/2024-25"
self.stats_url = f"{self.base_url}/competition/2024-25/statistics"
self.players_url = f"{self.base_url}/competition/2024-25/players"
self.teams_url = f"{self.base_url}/competition/2024-25/teams"
self.games_url = f"{self.base_url}/competition/2024-25/games"
```

**Key sections to update** (search for `# TODO: Replace with actual`):
- Line ~78-82: URL endpoints
- Line ~85: Current season format
- Any `UPDATE AFTER INSPECTION` comments

---

### Step 3: Update Parsing Logic

After updating URLs, you may need to adjust the HTML/JSON parsing logic:

```python
# Example: Update column name mapping if website uses different names
def _parse_stats_table(self, html: str) -> list[dict]:
    """Parse stats table from HTML."""
    soup = parse_html(html)
    table = find_stat_table(soup)

    # Update these column mappings based on actual website:
    column_map = {
        "Player": "player_name",          # Verify actual column name
        "Team": "team",
        "Points": "points",               # Could be "PTS", "Puntos", etc.
        "Rebounds": "rebounds",           # Could be "REB", "Rebonds", etc.
        "Assists": "assists",             # Could be "AST", "Passes", etc.
        "PIR": "pir",                     # Performance Index Rating (Europe)
    }

    # ... rest of parsing logic
```

**Key sections to verify**:
- Column names in stat tables
- Date/time formats
- Player ID formats
- Team name formats
- Season format (YYYY, YYYY-YY, YYYY/YY)

---

### Step 4: Test the Adapter

Create a test file for the adapter:

**File**: `tests/test_datasources/test_angt.py`

```python
import pytest
from src.datasources.europe.angt import ANGTDataSource


@pytest.fixture
async def angt():
    """Create ANGT datasource instance."""
    source = ANGTDataSource()
    yield source
    await source.close()


@pytest.mark.asyncio
async def test_angt_initialization(angt):
    """Test ANGT adapter initializes correctly."""
    assert angt.source_name == "ANGT (Next Generation)"
    assert angt.base_url == "https://www.euroleaguebasketball.net/next-generation"


@pytest.mark.asyncio
async def test_angt_health_check(angt):
    """Test ANGT health check."""
    is_healthy = await angt.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_angt_search_players(angt):
    """Test searching for players."""
    players = await angt.search_players(name="", limit=10)
    assert len(players) > 0
    assert players[0].player_id.startswith("angt_")


# Add more tests for stats, leaderboards, teams, etc.
```

Run the tests:
```bash
pytest tests/test_datasources/test_angt.py -v
```

---

### Step 5: Update Aggregator

Once the adapter is tested and working, uncomment it in the aggregator:

**File**: `src/services/aggregator.py`

```python
# BEFORE (commented out):
# from ..datasources.europe.angt import ANGTDataSource

# AFTER (uncommented):
from ..datasources.europe.angt import ANGTDataSource

# ...

source_classes = {
    # ... existing sources ...

    # ===== TEMPLATE ADAPTERS (Ready after URL verification) =====
    "angt": ANGTDataSource,           # ← Uncomment after testing
    # "osba": OSBADataSource,           # TODO: Verify URLs
    # "playhq": PlayHQDataSource,       # TODO: Verify URLs
    # "ote": OTEDataSource,             # TODO: Verify URLs
    # "grind_session": GrindSessionDataSource,  # TODO: Verify URLs
}
```

---

### Step 6: Update sources.yaml Status

Update the status in `config/sources.yaml`:

```yaml
# BEFORE:
- id: angt
  status: template

# AFTER:
- id: angt
  status: active
```

---

### Step 7: Update PROJECT_LOG.md

Document the activation in PROJECT_LOG.md:

```markdown
#### [YYYY-MM-DD HH:MM] Phase 12.X: ANGT Adapter Activation
- ✅ Verified URLs at https://www.euroleaguebasketball.net/next-generation
- ✅ Updated adapter endpoints (/competition/2024-25/statistics)
- ✅ Verified column names (Player, Team, Points, PIR)
- ✅ Created test suite (12 tests)
- ✅ All tests passing
- ✅ Uncommented in aggregator
- ✅ Updated sources.yaml status: template → active
- Impact: +1 active adapter, Europe U18 coverage complete
```

---

## Checklist Template

Use this checklist when activating each adapter:

```
[ ] 1. Visit website and inspect structure
[ ] 2. Document URL patterns
[ ] 3. Check robots.txt permissions
[ ] 4. Update adapter URLs (remove TODO comments)
[ ] 5. Update column name mappings
[ ] 6. Verify date/season formats
[ ] 7. Create test file
[ ] 8. Run tests (all passing)
[ ] 9. Uncomment in aggregator
[ ] 10. Update sources.yaml status
[ ] 11. Document in PROJECT_LOG.md
[ ] 12. Test end-to-end with aggregator
```

---

## Common Issues & Solutions

### Issue: Website requires JavaScript rendering
**Solution**: Use browser automation (already configured in config.py)

```python
# In adapter __init__:
self.requires_browser = True  # Enable browser automation
```

### Issue: Different column names than expected
**Solution**: Update column mapping in parsing logic

### Issue: Rate limiting (429 errors)
**Solution**: Adjust rate limits in sources.yaml

```yaml
rate_limit:
  requests_per_minute: 15  # Reduce if getting 429s
```

### Issue: Geo-restricted content
**Solution**: May require VPN or proxy (document in notes)

---

## Priority Order

Recommended activation order based on data quality and coverage:

1. **ANGT** (High priority - Europe U18 elite)
2. **OSBA** (High priority - Canada prep coverage)
3. **PlayHQ** (High priority - Australia nationals)
4. **OTE** (Medium priority - US prep alternative path)
5. **Grind Session** (Medium priority - US showcase events)

---

## Questions?

If you encounter issues during activation:

1. Check PROJECT_LOG.md for similar adapter implementations
2. Review working adapters (e.g., EYBL, NBBL) for patterns
3. Check adapter base class documentation in `src/datasources/base.py`
4. Test with small queries first before full activation

---

**Last Updated**: 2025-11-12
**Status**: 5 template adapters ready for activation
**Estimated Time Per Adapter**: 2-4 hours (inspection + testing)
