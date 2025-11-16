# Manual Site Investigation Template

**Purpose**: Guide manual investigation of datasources that cannot be accessed programmatically due to anti-bot protection or unknown site structure.

**Use this template for**: OSBA, any new datasource requiring manual verification

---

## Investigation Checklist

### Part 1: Site Accessibility

**URL to investigate**: _______________________________________

- [ ] Site loads in browser (not defunct)
- [ ] No login/paywall required for stats
- [ ] Site is in English or has English option
- [ ] Site appears to be actively maintained (recent updates)

**Notes**:
```
(Record any observations about site health, maintenance, etc.)
```

---

### Part 2: Stats Availability

**Navigate to stats section** (check multiple paths if needed):

- [ ] Stats section exists in main navigation
- [ ] Player stats available (not just team stats)
- [ ] Season stats available (not just game-by-game)
- [ ] Historical seasons available (multiple years)

**Stats URL**: _______________________________________

**Available Stats Types** (check all that apply):
- [ ] Season averages (PPG, RPG, APG, etc.)
- [ ] Game logs (game-by-game stats)
- [ ] Leaderboards (top scorers, etc.)
- [ ] Box scores
- [ ] Shooting percentages
- [ ] Advanced stats

**Seasons Available**:
```
List which seasons have stats data:
- 2024-25: [Yes/No/Partial]
- 2023-24: [Yes/No/Partial]
- 2022-23: [Yes/No/Partial]
(Add more as needed)
```

---

### Part 3: Data Structure

**How are stats organized?**
- [ ] By season
- [ ] By division/age group
- [ ] By team/conference
- [ ] By player

**Sample Player Identification**:

Pick 2-3 players and record details:

**Player 1**:
- Name: _______________________________________
- Team: _______________________________________
- Season: _______________________________________
- Stats visible: [ ] Yes [ ] No
- Sample stats: PPG=_____ RPG=_____ APG=_____

**Player 2**:
- Name: _______________________________________
- Team: _______________________________________
- Season: _______________________________________
- Stats visible: [ ] Yes [ ] No
- Sample stats: PPG=_____ RPG=_____ APG=_____

**Player 3**:
- Name: _______________________________________
- Team: _______________________________________
- Season: _______________________________________
- Stats visible: [ ] Yes [ ] No
- Sample stats: PPG=_____ RPG=_____ APG=_____

---

### Part 4: Legal Review

#### 4.1 Terms of Service (ToS)

**ToS URL**: _______________________________________

**Scraping Policy** (check ToS for these keywords):
- [ ] Explicitly allows scraping
- [ ] Explicitly prohibits scraping
- [ ] No mention of scraping/automated access
- [ ] Requires attribution
- [ ] Requires permission/license

**Relevant ToS Excerpts**:
```
(Copy/paste any relevant sections about automated access,
data usage, scraping, API access, etc.)
```

#### 4.2 Robots.txt

**Robots.txt URL**: `{base_url}/robots.txt`

**Check**: _______________________________________

**Disallows stats pages?**
- [ ] Yes (lists /stats or similar)
- [ ] No (stats pages not disallowed)
- [ ] No robots.txt file found

**Robots.txt Content** (paste relevant parts):
```
User-agent: *
Disallow: /admin/
...
```

#### 4.3 Privacy Policy

**Privacy Policy URL**: _______________________________________

**Data Usage Notes**:
```
(Any restrictions on using publicly displayed data)
```

---

### Part 5: Technical Assessment

#### 5.1 Anti-Bot Protection

**Test**: Open browser dev tools (F12), refresh stats page

**Observed Protection**:
- [ ] Cloudflare challenge
- [ ] Akamai bot detection
- [ ] CAPTCHA required
- [ ] JavaScript required (React/SPA)
- [ ] No obvious protection

**JavaScript Framework** (check page source):
- [ ] React
- [ ] Angular
- [ ] Vue
- [ ] Plain HTML/jQuery
- [ ] Unknown

#### 5.2 Data Loading

**How do stats load?**
- [ ] Server-side rendered (HTML table in initial page source)
- [ ] Client-side rendered (AJAX/API calls after page load)
- [ ] Hybrid (some HTML, some AJAX)

**API Endpoints** (check Network tab for XHR/Fetch requests):
```
List any JSON/API endpoints discovered:
1. _______________________________________
2. _______________________________________
3. _______________________________________
```

---

### Part 6: Decision Matrix

Based on investigation above, determine implementation path:

#### Green Light (Implement Now)
- [ ] Public stats pages exist ✅
- [ ] ToS allows or doesn't prohibit scraping ✅
- [ ] Robots.txt allows stats pages ✅
- [ ] Anti-bot: None or moderate (browser automation works)

**→ Action**: Implement adapter with browser automation

---

#### Yellow Light (Proceed with Caution)
- [ ] Public stats pages exist ✅
- [ ] ToS is unclear or silent on scraping ⚠️
- [ ] Robots.txt allows ✅
- [ ] Anti-bot: Heavy (requires sophisticated bypass)

**→ Action**: Implement adapter, monitor for legal objections, consider partnership

---

#### Red Light (Partnership Required)
- [ ] Stats behind paywall or login ❌
- [ ] ToS explicitly prohibits scraping ❌
- [ ] Robots.txt disallows stats pages ❌
- [ ] Commercial service

**→ Action**: Contact for official data access or API partnership

---

#### Dead End (Not Worth Pursuing)
- [ ] No player stats available (fixtures only) ❌
- [ ] Site defunct or unmaintained ❌
- [ ] Data quality too poor ❌

**→ Action**: Mark as inactive, find alternative source

---

## Investigation Summary

**Final Determination** (choose one):

- [ ] **GREEN**: Implement adapter (est. ___ hours)
- [ ] **YELLOW**: Implement with legal monitoring (est. ___ hours)
- [ ] **RED**: Partnership inquiry required (2-4 weeks)
- [ ] **INACTIVE**: Not viable, find alternative

**Recommended Next Steps**:
```
1. _______________________________________
2. _______________________________________
3. _______________________________________
```

**Priority Level** (1-5):
- Coverage: [ 1 / 2 / 3 / 4 / 5 ] - How many players/regions covered?
- Quality: [ 1 / 2 / 3 / 4 / 5 ] - How complete are the stats?
- Uniqueness: [ 1 / 2 / 3 / 4 / 5 ] - Data not available elsewhere?
- ROI: [ 1 / 2 / 3 / 4 / 5 ] - Implementation effort vs coverage?

**Overall Priority**: _____ / 5

---

## Files to Update

After completing investigation:

1. **config/datasource_status.yaml**:
   - Update `has_player_stats` (true/false)
   - Update `access_mode` (public_html, partnership_needed, blocked)
   - Update `legal_ok` (true/false based on ToS review)
   - Update `anti_bot` (none, moderate, heavy)
   - Update `status` (green, yellow, red, inactive)
   - Update `notes` with investigation summary
   - Update `next_action` with recommended next step

2. **config/datasource_test_cases.yaml**:
   - If GREEN: Add 2-3 test cases with real player names
   - If YELLOW/RED: Leave placeholder or empty

3. **DATASOURCE_ROADMAP.md**:
   - Update roadmap section for this datasource
   - Document decision and reasoning
   - Update partnership inquiry if needed

4. **PROJECT_LOG.md**:
   - Add investigation summary to current phase
   - Document findings and decision

---

**Investigation Date**: _______________________________________
**Investigator**: _______________________________________
**Time Spent**: _______________________________________

---

## Example: Completed Investigation

**Datasource**: OSBA (Ontario Scholastic Basketball Association)
**URL**: www.osba.ca
**Investigation Date**: 2025-11-16

### Summary
- ✅ Site loads successfully
- ✅ Player stats section found at /stats
- ✅ Historical data available (2022-2024)
- ⚠️ ToS silent on scraping (not prohibited, not explicitly allowed)
- ⚠️ Heavy anti-bot (403 on programmatic access)
- ✅ Browser automation likely to work

**Decision**: YELLOW LIGHT - Implement with browser automation

**Test Cases Added**:
```yaml
osba:
  - player_name: "John Smith"
    season: "2023-24"
    team_hint: "Toronto Prep"
    division: "U19"
    expected_min_games: 10
    expected_min_ppg: 8.0
```

**Next Steps**:
1. Implement OSBA adapter with browser automation (4-6 hours)
2. Run validation tests
3. Monitor for any legal objections
4. Consider partnership for long-term stability

---

**Template Version**: 1.0
**Last Updated**: 2025-11-16
