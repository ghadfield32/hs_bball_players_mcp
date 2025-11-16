# OSBA Investigation Guide

**Datasource**: OSBA (Ontario Scholastic Basketball Association)
**Website**: www.osba.ca
**Priority**: High (P2) - Canadian prep coverage
**Current Status**: BLOCKED (403 Forbidden)
**Estimated Time**: 1 hour

---

## Objective

Determine if OSBA is viable for implementation by:
1. Verifying player stats pages exist publicly
2. Reviewing ToS and robots.txt for legal compliance
3. Assessing technical implementation approach
4. Making GREEN/YELLOW/RED light decision

---

## Investigation Steps

### Step 1: Site Access (5 minutes)

1. Open browser and visit: **https://www.osba.ca**

2. Check if site loads:
   - [ ] Site loads successfully (not defunct)
   - [ ] Site is in English or has English option
   - [ ] Site appears actively maintained (check copyright year, recent news)

3. Navigate to main sections:
   - [ ] About/League Info
   - [ ] Teams/Divisions
   - [ ] Stats/Statistics
   - [ ] Schedule/Fixtures

**Record observations**:
```
Does site load? ________
Language: ________
Last update date visible: ________
Main navigation items: ________________________________________
```

---

### Step 2: Stats Page Discovery (15 minutes)

**Try these URLs to find stats**:

1. **Direct stats URLs** (try each):
   - https://www.osba.ca/stats
   - https://www.osba.ca/statistics
   - https://www.osba.ca/player-stats
   - https://www.osba.ca/standings

2. **Navigation paths** (try each):
   - Click "Stats" in main menu
   - Click "Teams" → Find team page → Look for stats link
   - Click "Schedule" → Find game → Look for box scores
   - Search for "player stats" or "statistics" on site

**Checklist**:
- [ ] Player stats page found
- [ ] Stats are season averages (PPG, RPG, APG)
- [ ] Stats are game logs (game-by-game)
- [ ] Stats are leaderboards only (top 10 scorers, etc.)
- [ ] No player stats found (fixtures/standings only)

**Stats URL**: _______________________________________

**Stats Format**:
- [ ] HTML tables (server-rendered)
- [ ] JavaScript/React (client-rendered)
- [ ] PDF downloads
- [ ] Embedded widget/iframe

---

### Step 3: Data Verification (15 minutes)

**If stats pages exist, verify data completeness:**

#### Divisions/Age Groups Available:
- [ ] U17 (Under 17)
- [ ] U19 (Under 19)
- [ ] Prep
- [ ] Other: _______________________________________

#### Seasons Available:
- [ ] 2024-25 (current season)
- [ ] 2023-24
- [ ] 2022-23
- [ ] Older seasons: _______________________________________

#### Extract 3 Sample Players:

**Player 1**:
- Name: _______________________________________
- Division: [ U17 / U19 / Prep ]
- Season: _______________________________________
- Team: _______________________________________
- Stats visible:
  - Games: _______
  - PPG: _______
  - RPG: _______
  - APG: _______

**Player 2**:
- Name: _______________________________________
- Division: [ U17 / U19 / Prep ]
- Season: _______________________________________
- Team: _______________________________________
- Stats visible:
  - Games: _______
  - PPG: _______
  - RPG: _______
  - APG: _______

**Player 3**:
- Name: _______________________________________
- Division: [ U17 / U19 / Prep ]
- Season: _______________________________________
- Team: _______________________________________
- Stats visible:
  - Games: _______
  - PPG: _______
  - RPG: _______
  - APG: _______

---

### Step 4: Legal Review (15 minutes)

#### ToS Review

1. Find Terms of Service page:
   - Check footer links
   - URL usually: https://www.osba.ca/terms or /tos or /terms-of-service

2. **ToS URL**: _______________________________________

3. Search ToS for these keywords (Ctrl+F):
   - "scraping"
   - "automated"
   - "robots"
   - "crawling"
   - "data mining"
   - "commercial use"

4. **Scraping Policy** (check one):
   - [ ] Explicitly allows scraping
   - [ ] Explicitly prohibits scraping
   - [ ] No mention (silent)
   - [ ] Requires attribution
   - [ ] Requires permission/contact

**Copy relevant ToS excerpt**:
```
(Paste any text about automated access, scraping, data usage)


```

#### Robots.txt Review

1. Visit: **https://www.osba.ca/robots.txt**

2. **Robots.txt exists?**
   - [ ] Yes (copy content below)
   - [ ] No (404 error)

**Robots.txt content** (if exists):
```
(Paste content here, or note "Not found")


```

3. **Does robots.txt disallow stats pages?**
   - [ ] Yes (stats pages explicitly disallowed)
   - [ ] No (stats pages not mentioned or allowed)
   - [ ] N/A (no robots.txt)

---

### Step 5: Technical Assessment (10 minutes)

#### Browser Developer Tools Test

1. Open stats page in browser
2. Press F12 (open developer tools)
3. Go to **Network** tab
4. Refresh page (F5)

**Observe**:

1. **Anti-Bot Protection** (check Console and Network tabs):
   - [ ] Cloudflare challenge page
   - [ ] Akamai bot detection
   - [ ] No obvious protection

2. **JavaScript Framework** (check page source or React DevTools):
   - [ ] React/Next.js
   - [ ] Vue
   - [ ] Angular
   - [ ] Plain HTML (no framework)
   - [ ] Unknown

3. **Data Loading Method**:
   - [ ] Server-side (tables visible in HTML source)
   - [ ] Client-side (AJAX calls load data after page load)
   - [ ] Hybrid

4. **API Endpoints** (check Network tab for XHR/Fetch):
```
List any JSON API endpoints discovered:
1. _______________________________________
2. _______________________________________
```

---

## Decision Matrix

Based on investigation, determine implementation path:

### Scenario A: GREEN LIGHT ✅

**Conditions**:
- [ ] Player stats pages exist and are public
- [ ] ToS doesn't prohibit scraping (silent or allows)
- [ ] Robots.txt doesn't disallow stats pages
- [ ] Anti-bot protection: None or moderate

**Decision**: **Implement adapter with browser automation**

**Estimated Effort**: 4-6 hours
**Priority**: High (P2)
**Next Steps**:
1. Create OSBA adapter using SBLive/EYBL pattern
2. Implement browser automation for anti-bot bypass
3. Add 2-3 test cases with real player names from investigation
4. Run semantic validation
5. Mark status="green" once passing

---

### Scenario B: YELLOW LIGHT ⚠️

**Conditions**:
- [ ] Player stats pages exist and are public
- [ ] ToS is silent/unclear on scraping
- [ ] Robots.txt allows
- [ ] Anti-bot protection: Heavy (sophisticated)

**Decision**: **Implement adapter, monitor for legal objections**

**Estimated Effort**: 6-8 hours (more complex anti-bot handling)
**Priority**: Medium-High (P2-3)
**Next Steps**:
1. Implement adapter with browser automation
2. Add disclaimer in code about ToS ambiguity
3. Monitor for any DMCA/legal notices
4. Consider partnership inquiry in parallel

---

### Scenario C: RED LIGHT 🛑

**Conditions**:
- [ ] ToS explicitly prohibits scraping
- [ ] Stats behind paywall/login
- [ ] Robots.txt disallows stats pages
- [ ] Commercial/proprietary service

**Decision**: **Partnership inquiry required**

**Estimated Timeline**: 2-4 weeks
**Priority**: Medium (P2-3)
**Next Steps**:
1. Find contact email (info@osba.ca or similar)
2. Draft partnership inquiry email
3. Request official data access or API
4. Update datasource_status.yaml with blocked status

**Email Template**:
```
Subject: Data Partnership Inquiry - Basketball Statistics Access

Dear OSBA Team,

I am reaching out to inquire about official data access for Ontario
basketball statistics. I am building a basketball statistics aggregation
platform and would like to include OSBA data with proper authorization.

Could you please advise on:
1. Whether official API or data access is available
2. Terms for using OSBA statistics data
3. Attribution requirements
4. Contact for data partnerships

Thank you for your time.

Best regards,
[Your name]
```

---

### Scenario D: DEAD END ❌

**Conditions**:
- [ ] No player stats available (fixtures/standings only)
- [ ] Site defunct or unmaintained
- [ ] Data quality too poor

**Decision**: **Mark as inactive, find alternative**

**Action**: Update datasource_status.yaml:
```yaml
osba:
  has_player_stats: false
  status: "inactive"
  priority: 5
  notes: "No player stats available. Fixtures/standings only. Find alternative Canadian source."
  next_action: "Research NPA Canada or other Ontario prep sources"
```

---

## Investigation Checklist Summary

**Site Access**:
- [ ] Site loads and is maintained

**Stats Availability**:
- [ ] Player stats pages found
- [ ] Season averages available
- [ ] Historical data (2+ seasons)
- [ ] 3 sample players extracted

**Legal Compliance**:
- [ ] ToS reviewed
- [ ] Robots.txt reviewed
- [ ] Scraping determination made

**Technical Feasibility**:
- [ ] Anti-bot protection assessed
- [ ] Data loading method identified
- [ ] Implementation approach determined

**Decision Made**:
- [ ] GREEN / YELLOW / RED / INACTIVE

---

## Files to Update After Investigation

### 1. config/datasource_status.yaml

Update OSBA section (lines 46-60):

```yaml
osba:
  name: "OSBA (Ontario Scholastic Basketball Association)"
  region: "Canada (Ontario)"
  level: "High School / Prep"
  has_player_stats: ___________  # true or false (from investigation)
  stats_types: ["season_averages"]  # Update based on what you found
  access_mode: ___________  # "public_html", "partnership_needed", or "blocked"
  legal_ok: ___________  # true or false (from ToS review)
  anti_bot: ___________  # "none", "moderate", or "heavy"
  status: ___________  # "green", "wip", "blocked", or "inactive"
  priority: ___________  # 1-5 based on decision
  seasons_supported: [___________]  # e.g., ["2024-25", "2023-24"]
  divisions: ["U17", "U19", "Prep"]  # Update if different
  notes: "___________"  # Investigation summary
  next_action: "___________"  # Next step from decision above
```

### 2. config/datasource_test_cases.yaml

**If GREEN or YELLOW**, add test cases:

```yaml
osba:
  # OSBA (Ontario Scholastic Basketball Association)
  # Status: GREEN - Implement adapter (or YELLOW - Proceed with caution)

  - player_name: "___________"  # Player 1 from investigation
    season: "___________"
    team_hint: "___________"
    division: "___________"  # U17, U19, or Prep
    expected_min_games: 1
    expected_min_ppg: 5.0
    expected_max_ppg: 40.0
    notes: "Verified player from OSBA investigation"

  - player_name: "___________"  # Player 2 from investigation
    season: "___________"
    team_hint: "___________"
    division: "___________"
    expected_min_games: 1
    expected_min_ppg: 5.0
    expected_max_ppg: 40.0
    notes: "Verified player from OSBA investigation"
```

### 3. DATASOURCE_ROADMAP.md

Update OSBA section with investigation findings:

```markdown
### 3. OSBA (Ontario Scholastic Basketball Association)

**Investigation Date**: [DATE]
**Status**: [GREEN/YELLOW/RED/INACTIVE]
**Legal**: [Green Light / Yellow Light / Red Light]

#### Investigation Findings
- Stats pages: [Found / Not found]
- ToS: [Allows / Silent / Prohibits]
- Robots.txt: [Allows / Disallows / Not found]
- Anti-bot: [None / Moderate / Heavy]

#### Decision
[Explain decision and reasoning]

#### Next Steps
[List concrete next steps from decision matrix]
```

### 4. PROJECT_LOG.md

Add Phase 15.2 entry for OSBA investigation:

```markdown
**OSBA Investigation** (1 hour):
- Manual site inspection completed
- Stats availability: [Yes/No]
- Legal status: [GREEN/YELLOW/RED]
- Decision: [Implement / Partnership / Inactive]
```

---

## Expected Outcomes

### Best Case (GREEN):
- Player stats confirmed to exist
- ToS allows or is silent on scraping
- Browser automation feasible
- **Result**: 4-6 hour implementation → OSBA adapter complete

### Likely Case (YELLOW):
- Player stats exist but ToS unclear
- Heavy anti-bot protection
- **Result**: 6-8 hour implementation with legal monitoring

### Worst Case (RED):
- ToS prohibits or stats paywalled
- **Result**: 2-4 week partnership inquiry

### Dead End (INACTIVE):
- No player stats (fixtures only)
- **Result**: Find alternative Canadian source

---

**Investigation Time Budget**: 1 hour
**Decision Time**: By end of investigation
**Implementation**: 4-8 hours (if GREEN/YELLOW) or 2-4 weeks (if RED)

---

**Template Version**: 1.0 (OSBA-specific)
**Last Updated**: 2025-11-16
