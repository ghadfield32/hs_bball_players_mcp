# Datasource Implementation Roadmap

**Created**: 2025-11-16
**Phase**: 15 (Production-Ready Framework)

This document provides the legal triage and implementation roadmap for priority datasources based on Phase 13-14 audit findings.

---

## Legal Triage Framework

### Access Modes

1. **Green Light (Implement Now)**
   - `access_mode: public_html` + `legal_ok: true`
   - Public stats pages, ToS allows reasonable scraping
   - Browser automation may be needed but is permitted

2. **Yellow Light (Proceed with Caution)**
   - `access_mode: official_api` + `legal_ok: true`
   - Official data feeds exist, need to research API access
   - Partnership may be beneficial but not required

3. **Red Light (Partnership Required)**
   - `access_mode: partnership_needed` or `blocked`
   - Commercial service, ToS prohibits scraping, or heavy anti-bot protection
   - Must contact provider for official data access

---

## Priority Source Roadmaps

### 1. EYBL (Nike Elite Youth Basketball League)

**Status**: Work in Progress (Track B - Phase 15)
**Legal**: Green Light ✅
**Priority**: Critical (P1) - Top US prospects

#### Current State
- Adapter implemented with browser automation support (Phase 14)
- React SPA requires Playwright/browser automation
- Public stats pages at https://nikeeyb.com
- ToS: Public data, reasonable scraping allowed

#### Blockers
- ⚠️ **MANUAL STEP REQUIRED**: Need real player names from nikeeyb.com for test cases
- Cannot fetch player names programmatically due to anti-bot protection in test environment
- Browser automation code exists but dependencies not installed in validation environment

#### Next Steps
1. **MANUAL**: Visit https://nikeeyb.com/cumulative-season-stats
2. **MANUAL**: Select seasons 2024, 2023, 2022 from dropdown
3. **MANUAL**: Pick 1 player per season with complete stats
4. **MANUAL**: Update config/datasource_test_cases.yaml with real names
5. Run: `python scripts/validate_datasource_stats.py --source eybl --verbose`
6. Fix any adapter issues found
7. Create backfill script for 2022-2024 data
8. Update status="green" in datasource_status.yaml

#### Estimated Timeline
- Manual player selection: 15 minutes
- Validation + fixes: 1-2 hours
- Backfill implementation: 2-3 hours
- **Total**: 3-5 hours (blocked on manual step)

---

### 2. ANGT (Adidas Next Generation Tournament)

**Status**: Blocked
**Legal**: Red Light 🛑
**Priority**: Critical (P1) - Top European prospects

#### Current State
- All endpoints return 403 Forbidden (Phase 13 audit)
- Heavy anti-bot protection (Cloudflare/Akamai)
- Part of EuroLeague Basketball ecosystem
- Official competition with high-value prospects entering pro pipelines

#### Legal Analysis
- **ToS**: Not yet reviewed (need to check euroleaguebasketball.net ToS)
- **robots.txt**: Not checked
- **Anti-bot**: Heavy (403 on all requests)
- **Recommendation**: Official API or partnership likely required

#### Options

**Option A: Official EuroLeague Data API (RECOMMENDED)**
- EuroLeague likely has official data feeds or LiveStats API
- Used by media partners and official apps
- Contact: data-partnerships@euroleague.net (verify email)
- Pros: Legal, reliable, complete data, professional support
- Cons: May require partnership fee, approval process

**Option B: Browser Automation + ToS Compliance**
- Requires ToS review first to ensure scraping is allowed
- If allowed, implement browser automation similar to EYBL
- Pros: Free, direct control
- Cons: Fragile (anti-bot), may violate ToS, maintenance burden

**Option C: Third-Party Data Provider**
- Companies like Genius Sports, Stats Perform may have EuroLeague data
- Pros: Professional SLA, multiple competitions
- Cons: Expensive, commercial license required

#### Next Steps (Decision Tree)
1. **Immediate**: Review EuroLeague Basketball ToS and robots.txt
2. **If ToS prohibits scraping**: Go to Option A (official API)
3. **If ToS neutral**: Research official LiveStats API availability
4. **If API available**: Contact EuroLeague for API access
5. **If API unavailable & ToS allows**: Consider Option B with caution

#### Decision Needed
- **Recommended**: Pursue official data partnership (Option A)
- **Timeline**: 2-4 weeks for partnership inquiry response
- **Cost**: Unknown (may be free for non-commercial research)

---

### 3. OSBA (Ontario Scholastic Basketball Association)

**Status**: Blocked
**Legal**: Red Light 🛑
**Priority**: High (P2) - Canadian prep coverage

#### Current State
- All endpoints return 403 Forbidden (Phase 13 audit)
- Heavy anti-bot protection
- Canadian prep basketball (Ontario)
- Covers U17, U19, Prep divisions

#### Legal Analysis
- **ToS**: NOT YET REVIEWED ⚠️
- **robots.txt**: NOT YET CHECKED ⚠️
- **Anti-bot**: Heavy (403 on all requests)
- **Stats availability**: UNVERIFIED (need manual site visit)

#### Investigation Required

**Step 1: Manual Site Inspection (REQUIRED BEFORE ANY IMPLEMENTATION)**
1. Visit www.osba.ca in a browser manually
2. Navigate to stats section (if exists)
3. Verify player stats pages exist publicly
4. Check if stats are for current season only or historical
5. Review ToS page for scraping policies
6. Check /robots.txt

**Step 2: Legal Determination**
- If ToS prohibits scraping → Red light (partnership needed)
- If ToS neutral + robots.txt allows → Yellow light (browser automation)
- If ToS explicitly allows → Green light (implement)

#### Possible Outcomes

**Scenario A: Stats Pages Don't Exist**
- OSBA may only have fixtures/standings, not player stats
- Mark as `has_player_stats: false` in datasource_status.yaml
- Set priority=5 (inactive)
- Find alternative Canadian source (NPA, PrepHoops Canada, etc.)

**Scenario B: Stats Exist, ToS Allows**
- Implement browser automation adapter
- Similar pattern to EYBL (React SPA likely)
- Add to Track B for validation

**Scenario C: Stats Exist, ToS Prohibits**
- Contact OSBA for official data access
- Partnership or API inquiry
- Timeline: 2-4 weeks

#### Next Steps
1. **MANUAL**: Visit www.osba.ca and inspect site structure
2. **MANUAL**: Review ToS and robots.txt
3. **DECIDE**: Green/Yellow/Red light based on findings
4. Update datasource_status.yaml with findings
5. If green/yellow: Implement adapter
6. If red: Contact for partnership

#### Estimated Timeline
- Manual inspection: 30 minutes
- Legal review: 30 minutes
- Decision + status update: 15 minutes
- **Implementation** (if green): 3-5 hours
- **Total**: 1 hour investigation + 3-5 hours implementation (if approved)

---

### 4. FIBA Youth (U16/U17/U18 Official)

**Status**: To Do
**Legal**: Yellow Light ⚠️
**Priority**: High (P2) - Official international competitions

#### Current State
- SSL handshake failures in Phase 13 audit (likely test environment issue)
- Official FIBA competitions (U16, U17, U18 World Championships)
- High-value international prospects
- FIBA likely has official data infrastructure

#### Legal Analysis
- **ToS**: FIBA is official federation, data likely available officially
- **Official API**: FIBA LiveStats platform exists
- **Access**: Likely free for non-commercial use
- **Recommendation**: Research official API first, don't scrape

#### Investigation Required

**Research Official FIBA Data Access**
1. Visit FIBA.basketball and research data/API offerings
2. Check if FIBA LiveStats has public API documentation
3. Look for developer portal or data access page
4. Check if youth competitions use same LiveStats platform as senior
5. Review FIBA's data usage policies

#### Possible Data Sources

**Option A: FIBA LiveStats API (PREFERRED)**
- Platform: https://livefiba.dcd.shared.geniussports.com
- Used for live scoring and stats during competitions
- May have public API or data feeds
- Research: Check Genius Sports integration docs

**Option B: FIBA.basketball Official Site**
- Competition pages may have stats tables
- Less comprehensive than LiveStats
- Browser automation may be needed

**Option C: Genius Sports Partnership**
- FIBA uses Genius Sports for LiveStats
- May offer data licensing
- Commercial option if official API unavailable

#### Next Steps
1. Research FIBA.basketball for data/API documentation
2. Research FIBA LiveStats API availability
3. Check if youth competitions included in data feeds
4. If API available: Implement official API adapter
5. If API unavailable: Contact FIBA media/data department
6. Update datasource_status.yaml based on findings

#### Estimated Timeline
- Research: 1-2 hours
- API implementation (if available): 4-6 hours
- Partnership inquiry (if needed): 2-4 weeks
- **Total**: 1-2 hours research + implementation or partnership path

---

### 5. SBLive Sports (Multi-State Platform)

**Status**: Green ✅ (Phase 12.1)
**Legal**: Green Light ✅
**Priority**: Critical (P1) - Multi-state coverage

#### Current State
- Browser automation implemented and working (Phase 12.1)
- Covers 6 states currently: WA, OR, CA, AZ, ID, NV
- Public HTML with heavy anti-bot protection
- ToS allows reasonable scraping (reviewed in Phase 12)

#### Expansion Opportunity
- SBLive operates in 14+ additional states
- States: TX, FL, GA, NC, VA, OH, PA, IN, NJ, MI, TN, KY, LA, AL, SC, MD, IL, WI, IA, +
- URL pattern: https://{state}.sblive.com/high-school/boys-basketball/stats

#### Next Steps
1. Validate current 6 states work correctly
2. Add test cases for WA state in datasource_test_cases.yaml
3. Research which additional states have active stats pages
4. Verify ToS applies to all state subdomains
5. Implement multi-state support in adapter
6. Add state parameter to search_players() method
7. Create state-specific test cases

#### Estimated Timeline
- Validation of current states: 1 hour
- Expansion research: 2 hours
- Multi-state implementation: 3-4 hours
- **Total**: 6-7 hours for full expansion

---

## Summary and Recommendations

### Immediate Actions (Next 1-2 Days)

1. **EYBL (Track B)**
   - ⚠️ **BLOCKED ON MANUAL STEP**: Need real player names from nikeeyb.com
   - Person needed: Someone to visit site and extract 3 player names
   - Time: 15 minutes manual + 3-5 hours implementation

2. **OSBA Investigation**
   - MANUAL: Visit www.osba.ca, check if stats exist, review ToS
   - Time: 1 hour
   - Outcome: Determines if we can proceed or need partnership

3. **FIBA Research**
   - Research official FIBA LiveStats API
   - Time: 1-2 hours
   - Outcome: API implementation or partnership path

### Partnership Inquiries (2-4 Week Timeline)

1. **ANGT (EuroLeague Basketball)**
   - Contact: data-partnerships@euroleague.net (verify email)
   - Value: Top European U18 prospects
   - Cost: Unknown (may be free for research)

2. **OSBA** (if ToS prohibits scraping)
   - Contact: info@osba.ca or data contact
   - Value: Ontario prep coverage
   - Cost: Unknown

### ROI Analysis

| Source | Implementation Time | Coverage | Priority | Status |
|--------|-------------------|----------|----------|--------|
| EYBL | 3-5 hours (blocked on manual step) | US National Elite | P1 | 80% done, needs player names |
| SBLive Expansion | 6-7 hours | 20+ US states | P1 | Ready to implement |
| FIBA Youth | 1-2 hours research + TBD | Global U16/U17/U18 | P2 | Need API research |
| OSBA | 1 hour + 3-5 hours | Ontario Canada | P2 | Need site inspection |
| ANGT | Partnership path | Europe U18 Elite | P1 | 403 blocked, needs partnership |

### Recommended Priority Order

1. **OSBA Investigation** (1 hour) - Quick decision point
2. **FIBA API Research** (1-2 hours) - May unlock easy win
3. **EYBL Player Names** (15 min manual) - Unblock Track B
4. **SBLive Expansion** (6-7 hours) - Highest ROI for US coverage
5. **ANGT Partnership Inquiry** (async 2-4 weeks) - Start conversation

---

## Decision Points

### EYBL Green Status Criteria
- [ ] Real player names added to test cases
- [ ] Validation script passes all 3 test cases
- [ ] Sanity checks pass (FGM ≤ FGA, games ≥ 1, etc.)
- [ ] Backfill script created for 2022-2024 seasons
- [ ] Data exports to Parquet successfully
- [ ] Documentation updated in datasource_status.yaml

### OSBA Go/No-Go Criteria
- [ ] Stats pages verified to exist publicly
- [ ] ToS reviewed (allows scraping OR partnership path defined)
- [ ] robots.txt checked
- [ ] Sample player data verified manually

### FIBA Implementation Path
- [ ] Official API documentation found → Implement API adapter
- [ ] No public API, ToS allows scraping → Browser automation
- [ ] No public API, ToS prohibits scraping → Partnership inquiry

---

**Last Updated**: 2025-11-16
**Next Review**: After EYBL reaches green status (Track B completion)
