# EYBL Player Extraction Guide

**Datasource**: Nike EYBL (Elite Youth Basketball League)
**Website**: https://nikeeyb.com
**Priority**: Critical (P1) - Track B completion blocker
**Current Status**: 80% complete - Needs real player names
**Estimated Time**: 15 minutes

---

## Objective

Extract **3 real player names** from Nike EYBL website to unblock Track B (making EYBL the first green datasource).

**Why needed**:
- EYBL adapter fully implemented with browser automation
- Validation framework ready
- Only missing: Real player names for test cases (anti-bot blocks automated extraction)

---

## Quick Start (5-Step Process)

### Step 1: Visit EYBL Stats Page (2 minutes)

**URL**: https://nikeeyb.com/cumulative-season-stats

**What to expect**:
- React/JavaScript single-page application
- May take 3-5 seconds to load stats table
- Stats organized by season (dropdown selector)

**Initial view**:
- Default season: Usually current year (2024)
- Stats table: Player names, teams, PPG, RPG, APG, etc.
- Leaderboard format: Top scorers/performers first

---

### Step 2: Select Season - 2024 (3 minutes)

**Action**:
1. Find season dropdown (usually top-right of page)
2. Select **"2024"** or **"2024 Season"**
3. Wait for stats table to reload (3-5 seconds)

**Extract Player 1 (2024 Season)**:

**Scan the stats table and pick ANY player with complete stats**:
- Look for players with 10+ games played
- PPG should be reasonable (5-30 range typical)
- Avoid players with 0.0 stats (incomplete data)

**Record these details**:
- **Player Name** (EXACT as shown): _______________________________________
- **Team Name** (from Team column): _______________________________________
- **Games Played** (from GP or G column): _______
- **PPG** (from PPG or PTS column): _______
- **RPG** (optional, from RPG or REB column): _______

**Pro Tips**:
- Pick players near top of table (usually most games/best stats)
- Avoid players with unusual characters in name (special accents, etc.)
- Pick players from different teams for variety

---

### Step 3: Select Season - 2023 (3 minutes)

**Action**:
1. Change season dropdown to **"2023"**
2. Wait for table reload
3. Repeat player extraction

**Extract Player 2 (2023 Season)**:

**Pick a DIFFERENT player than Player 1** (preferably different team):

- **Player Name** (EXACT as shown): _______________________________________
- **Team Name**: _______________________________________
- **Games Played**: _______
- **PPG**: _______
- **RPG** (optional): _______

---

### Step 4: Select Season - 2022 (3 minutes)

**Action**:
1. Change season dropdown to **"2022"**
2. Wait for table reload
3. Extract third player

**Extract Player 3 (2022 Season)**:

**Pick a DIFFERENT player and team if possible**:

- **Player Name** (EXACT as shown): _______________________________________
- **Team Name**: _______________________________________
- **Games Played**: _______
- **PPG**: _______
- **RPG** (optional): _______

---

### Step 5: Update Test Cases File (4 minutes)

**File to Edit**: `config/datasource_test_cases.yaml`

**Location**: Lines 55-77 (eybl section)

**Replace placeholders with your extracted players**:

```yaml
eybl:
  # Nike EYBL (Elite Youth Basketball League)

  - player_name: "___________"  # Player 1 name from 2024
    season: "2024"
    team_hint: "___________"  # Player 1 team
    expected_min_games: 1
    expected_min_ppg: 5.0
    expected_max_ppg: 50.0
    notes: "2024 season validation player"

  - player_name: "___________"  # Player 2 name from 2023
    season: "2023"
    team_hint: "___________"  # Player 2 team
    expected_min_games: 1
    expected_min_ppg: 5.0
    expected_max_ppg: 50.0
    notes: "2023 season validation player"

  - player_name: "___________"  # Player 3 name from 2022
    season: "2022"
    team_hint: "___________"  # Player 3 team
    expected_min_games: 1
    expected_min_ppg: 5.0
    expected_max_ppg: 50.0
    notes: "2022 season validation player"
```

**Optional: Adjust expected_min_ppg and expected_max_ppg**:
- If player has 15 PPG, you could set min=10.0, max=20.0 for tighter validation
- Default ranges (5.0-50.0) are safe for any player

---

## Detailed Instructions (If Needed)

### Finding the Stats Table

**Visual Guide**:
1. Page loads with Nike EYBL branding
2. Navigation: Home | Schedule | Stats | Standings | etc.
3. Stats page shows large table with columns:
   - **Player** (or NAME): Full player name
   - **Team** (or TEAM): Club/team name
   - **GP** or **G**: Games Played
   - **PPG** or **PTS**: Points Per Game
   - **RPG** or **REB**: Rebounds Per Game
   - **APG** or **AST**: Assists Per Game
   - Additional columns: FG%, 3P%, FT%, STL, BLK, etc.

### Season Selector Location

**Possible locations**:
- Top-right corner near search bar
- Above stats table
- In navigation tabs (2024 | 2023 | 2022)
- Dropdown labeled "Season" or "Year"

**If you can't find season selector**:
- Check URL for season parameter: `?season=2024`
- Try manually changing URL to: `nikeeyb.com/cumulative-season-stats?season=2023`

### Troubleshooting

#### Table Won't Load
**Problem**: Stats table shows loading spinner indefinitely

**Solutions**:
1. Refresh page (F5)
2. Clear cache and reload (Ctrl+Shift+R)
3. Try different browser (Chrome, Firefox, Edge)
4. Check internet connection
5. Try incognito/private mode

#### Can't Find Season Dropdown
**Problem**: No visible season selector

**Solutions**:
1. Scroll up/down on page (may be off-screen)
2. Check for tabs at top of page
3. Try URL parameter: `?season=2023`
4. Look for "Archive" or "Historical Stats" link

#### Player Names Have Special Characters
**Problem**: Player name has accents (é, ñ, etc.)

**Solution**: Copy EXACTLY as shown, including all accents. YAML supports UTF-8.

**Example**:
```yaml
player_name: "José García"  # Include accents
```

#### Missing Stats Columns
**Problem**: Some stats missing (no RPG, APG, etc.)

**Solution**: That's okay! We only need:
- Player name (required)
- Team name (required)
- Games played (nice to have)
- PPG (nice to have)

The validator will work with whatever stats are available.

---

## Example: Completed Extraction

**Here's what a completed extraction looks like**:

### Player 1 (2024)
- Player Name: "Cooper Flagg"
- Team Name: "Maine United"
- Games: 18
- PPG: 22.5
- RPG: 10.2

### Player 2 (2023)
- Player Name: "DJ Wagner"
- Team Name: "Team Durant"
- Games: 16
- PPG: 19.8
- RPG: 4.3

### Player 3 (2022)
- Player Name: "Dariq Whitehead"
- Team Name: "CP3"
- Games: 14
- PPG: 17.3
- RPG: 5.7

**Updated YAML**:
```yaml
eybl:
  - player_name: "Cooper Flagg"
    season: "2024"
    team_hint: "Maine United"
    expected_min_games: 15  # Adjusted based on observed 18
    expected_min_ppg: 18.0  # Adjusted based on observed 22.5
    expected_max_ppg: 27.0
    notes: "Top prospect from 2024 season"

  - player_name: "DJ Wagner"
    season: "2023"
    team_hint: "Team Durant"
    expected_min_games: 12
    expected_min_ppg: 15.0
    expected_max_ppg: 25.0
    notes: "2023 season elite scorer"

  - player_name: "Dariq Whitehead"
    season: "2022"
    team_hint: "CP3"
    expected_min_games: 10
    expected_min_ppg: 14.0
    expected_max_ppg: 22.0
    notes: "Historical validation case from 2022"
```

**Note**: The names above are examples. Use ACTUAL players you see on the site TODAY.

---

## After Extraction: Next Steps

Once you've updated `config/datasource_test_cases.yaml` with real player names:

### Step 1: Run Validation (5 minutes)

**Command**:
```bash
python scripts/validate_datasource_stats.py --source eybl --verbose
```

**Expected Output**:
```
Validating EYBL...
  ✅ Cooper Flagg (2024): PASS
  ✅ DJ Wagner (2023): PASS
  ✅ Dariq Whitehead (2022): PASS

EYBL Validation: 3/3 passed
```

### Step 2: Fix Any Issues (10-30 minutes)

**If validation fails**:

**Common Issue 1**: Player name not found
```
❌ Cooper Flagg (2024): FAIL - Player not found in search results
```
**Fix**: Check exact spelling, try partial name search

**Common Issue 2**: Sanity check failure
```
❌ DJ Wagner (2023): FAIL - FGM (150) > FGA (100)
```
**Fix**: Adapter bug, needs investigation

**Common Issue 3**: Season mismatch
```
❌ Dariq Whitehead (2022): FAIL - Season 2022 not available
```
**Fix**: Try different season or verify adapter season parameter handling

### Step 3: Mark EYBL Green (1 minute)

**If all validations pass**, update `config/datasource_status.yaml`:

```yaml
eybl:
  status: "green"  # Changed from "wip"
  notes: "Validation passing with real test cases. Production-ready."
  next_action: "Create backfill script for 2022-2024 data export"
```

### Step 4: Celebrate! 🎉

**Track B Complete**: EYBL is now the first fully green datasource!

---

## Checklist Summary

Before starting:
- [ ] Browser ready (Chrome, Firefox, or Edge)
- [ ] config/datasource_test_cases.yaml file accessible
- [ ] 15 minutes time budget

During extraction:
- [ ] Visit nikeeyb.com/cumulative-season-stats
- [ ] Season 2024 selected, Player 1 extracted
- [ ] Season 2023 selected, Player 2 extracted
- [ ] Season 2022 selected, Player 3 extracted
- [ ] All details recorded (names, teams, stats)

After extraction:
- [ ] Test cases YAML updated with real players
- [ ] File saved
- [ ] Validation script run
- [ ] All tests passing
- [ ] datasource_status.yaml updated to green

**Success Criteria**:
- 3 real player names extracted
- Test cases updated in YAML
- Validation script passes
- EYBL marked as green

---

## Why This Matters

**Track B Goal**: Make EYBL the first fully production-ready datasource.

**Current Blockers**:
- ✅ Adapter implemented (Phase 14)
- ✅ Browser automation working
- ✅ Validation framework ready (Phase 15.1)
- ⏸️ **Test cases need real names** ← YOU ARE HERE
- ⏸️ Validation tests need to pass
- ⏸️ Mark status=green

**After completion**:
- EYBL becomes reference implementation
- Pattern established for other datasources
- Demonstrates full Definition of Done workflow
- Validates entire production framework (Phases 13-15)

**Impact**:
- First green datasource = major milestone
- Proof of concept for remaining 50+ sources
- Template for FIBA, OSBA, 3SSB, UAA implementations

---

## Time Budget Breakdown

| Step | Task | Time |
|------|------|------|
| 1 | Visit stats page | 2 min |
| 2 | Extract 2024 player | 3 min |
| 3 | Extract 2023 player | 3 min |
| 4 | Extract 2022 player | 3 min |
| 5 | Update YAML file | 4 min |
| **Total** | **Complete extraction** | **15 min** |

**Plus validation**:
- Run validation script: 5 min
- Fix issues (if any): 10-30 min
- Update status: 1 min

**Total to green**: 30-50 minutes (including validation)

---

## Support / Questions

**If you get stuck**:

1. **Can't access nikeeyb.com**:
   - Try VPN if blocked by region
   - Check if site is down: https://downforeveryoneorjustme.com/nikeeyb.com
   - Try mobile browser vs desktop

2. **Stats table doesn't load**:
   - Enable JavaScript in browser
   - Disable ad blockers temporarily
   - Try incognito/private mode
   - Use different browser

3. **Season selector missing**:
   - Try URL parameter: `?season=2023`
   - Look for "Archive" link
   - Check navigation tabs

4. **Not sure which player to pick**:
   - ANY player with stats is fine
   - Pick from top 10-20 rows (most games)
   - Avoid 0.0 PPG players (incomplete data)

5. **YAML syntax errors**:
   - Use quotes around names: `"John Doe"`
   - Indent with 2 spaces (not tabs)
   - Watch for special characters

**Still stuck?**
- Document what you see (screenshot helps)
- Note exact error message
- Proceed to OSBA or FIBA tasks while blocked

---

**Guide Version**: 1.0 (EYBL-specific)
**Last Updated**: 2025-11-16
**Estimated Time**: 15 minutes extraction + 15 minutes validation = 30 minutes total
