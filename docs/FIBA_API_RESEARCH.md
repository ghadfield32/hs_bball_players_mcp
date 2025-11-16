# FIBA API Research Report

**Created**: 2025-11-16
**Phase**: 15.2 (Legal Triage & Implementation Planning)
**Status**: Research Complete - Partnership Path Recommended

---

## Executive Summary

FIBA has **two official API platforms** for basketball statistics data:

1. **FIBA GDAP (Global Data & API Platform)** - Official FIBA API
2. **Genius Sports LiveStats** - FIBA's technical partner for live stats

**Recommendation**: Pursue official API access through FIBA GDAP portal (partnership required).

**Alternative**: Third-party API (api-basketball.com) covers FIBA youth competitions.

---

## Official FIBA Data Access

### 1. FIBA GDAP (Global Data & API Platform)

**Platform**: https://gdap-portal.fiba.basketball/

**Description**:
- Official FIBA API for competition data and statistics
- Provides data API related to FIBA Competition information systems
- Offers calculations based on FIBA rules for player and team accumulated statistics

**Access Requirements**:
- Authentication required (API key-based)
- Subscription to specific product APIs needed
- API documentation (data model & API definition) available via swagger
- **Status**: 403 Forbidden (authentication/subscription required)

**Coverage**:
- All FIBA official competitions
- Youth championships: U19 and U17 World Championships confirmed
- Likely includes U16 and U18 regional championships

**How to Access**:
1. Visit https://gdap-portal.fiba.basketball/
2. Create account / request API subscription
3. Subscribe to specific product APIs (youth competitions)
4. Receive API key for authentication
5. Access swagger documentation for endpoints

**Contact**:
- FIBA Technical Support (via GDAP portal)
- FIBA Data Services: data@fiba.basketball (verify email)

---

### 2. Genius Sports FIBA LiveStats

**Platform**: https://developer.geniussports.com/

**Description**:
- FIBA's technical partner for LiveStats platform
- Powers live scoring and statistics during FIBA games
- Partnership covers all 212 FIBA members across 150 countries

**Available APIs**:

1. **LiveStats TV Feed**
   - In-venue feed via LAN connection
   - JSON message format
   - Default port: 7677 (TCP socket)
   - Real-time individual actions and aggregated data

2. **Warehouse Read Stream API**
   - Long-running HTTP GET calls
   - Continuous stream of game actions
   - Designed for live data consumption

3. **REST API**
   - Standard HTTP methods (GET, POST, DELETE, PUT)
   - Historical data access
   - Player/team statistics queries

**Authentication**:
- All API calls require `x-api-key` header
- API key provided on signup (must be kept secret)
- **Status**: 403 Forbidden (signup/partnership required)

**Developer Portal**: https://developer.geniussports.com/
- Basketball LiveStats documentation available
- Warehouse API docs for historical data
- Support center for technical questions

**How to Access**:
1. Contact Genius Sports for FIBA data partnership
2. Request API access for FIBA youth competitions
3. Receive API key and access to developer portal
4. Use REST API for historical stats, Stream API for live data

**Contact**:
- Genius Sports Support: https://support.geniussports.com/
- FIBA Genius Sports page: https://www.fiba.basketball/data-video-solutions/genius-sports
- About FIBA Data Solutions: https://about.fiba.basketball/en/services/data-and-video-solutions

---

## Third-Party Alternative

### API-Basketball.com

**Platform**: https://www.api-basketball.com/

**Coverage**:
- FIBA World Championship U17 (Boys & Girls)
- FIBA World Championship U19 (Boys & Girls)
- Regional youth championships (U16, U18, various confederations)
- Appears to be unofficial/third-party aggregator

**Pros**:
- May have simpler access process than official FIBA
- Covers multiple age groups
- Potentially free tier or lower cost

**Cons**:
- Third-party, not official FIBA
- Data quality/completeness unknown
- Legal status unclear (ToS review needed)
- May not have historical data depth

**Next Step**: Research API-Basketball ToS and pricing

---

## Youth Competition Coverage Analysis

### Confirmed Coverage (Official FIBA):

**U19 World Championship**
- Boys and Girls divisions
- LiveStats used for official scoring
- Historical data via GDAP likely available

**U17 World Championship**
- Boys and Girls divisions
- LiveStats used for official scoring
- Historical data via GDAP likely available

**U16 Regional Championships**
- Various FIBA confederations (Europe, Americas, Asia, etc.)
- Coverage likely available but needs confirmation

**U18 Competitions**
- Regional and continental championships
- Coverage likely available but needs confirmation

---

## Recommended Implementation Path

### Option A: FIBA GDAP Official API (RECOMMENDED)

**Why Recommended**:
- Official FIBA data = highest quality
- Legal and compliant
- Complete historical coverage
- Professional support
- Future-proof (official partnership)

**Process**:
1. **Week 1**: Contact FIBA GDAP portal for API access inquiry
   - Visit https://gdap-portal.fiba.basketball/
   - Request information about data access for youth competitions
   - Ask about subscription options and pricing
   - Mention use case: basketball statistics aggregation for research

2. **Week 2-3**: Review partnership terms
   - Evaluate pricing (may be free for non-commercial research)
   - Review API documentation
   - Confirm youth competition coverage (U16/U17/U18/U19)
   - Confirm historical data depth (how many years back)

3. **Week 4**: Begin implementation
   - Receive API key
   - Implement official API adapter
   - Use swagger docs for endpoint integration
   - Test with U17/U19 World Championships first

**Estimated Cost**: Unknown (possibly free for research, may require commercial license)

**Timeline**: 2-4 weeks for partnership approval + 1-2 weeks implementation

---

### Option B: Genius Sports Partnership

**Why Consider**:
- Same data as FIBA (official technical partner)
- May have more flexible pricing tiers
- Developer-friendly documentation
- Real-time and historical data access

**Process**:
1. Contact Genius Sports for FIBA data partnership
2. Request access to FIBA youth competition data
3. Negotiate pricing and terms
4. Implement using REST API (historical) or Stream API (live)

**Estimated Cost**: Likely commercial pricing (Genius Sports is enterprise-focused)

**Timeline**: 2-4 weeks for partnership + 1-2 weeks implementation

---

### Option C: Hybrid Approach (Short-term Alternative)

**For Immediate Progress**:
1. Research api-basketball.com ToS and pricing
2. If ToS allows and pricing is reasonable, use as temporary solution
3. Migrate to official FIBA GDAP once partnership approved

**Why Hybrid**:
- Allows immediate progress on FIBA datasource
- Validates adapter architecture
- Can be replaced later with official API
- Reduces risk if official partnership is slow/expensive

**Risk**: May waste implementation effort if we eventually switch APIs

---

## Decision Matrix

| Factor | FIBA GDAP | Genius Sports | API-Basketball |
|--------|-----------|---------------|----------------|
| **Data Quality** | Official (best) | Official (best) | Third-party (unknown) |
| **Legal Status** | Fully compliant | Fully compliant | Unknown (needs review) |
| **Cost** | Unknown (possibly free) | Likely expensive | Possibly free tier |
| **Timeline** | 2-4 weeks | 2-4 weeks | Potentially immediate |
| **Coverage** | Complete | Complete | Partial (needs verification) |
| **Support** | Official FIBA | Professional | Limited |
| **Future-proof** | Yes | Yes | No (third-party) |

---

## Next Actions

### Immediate (This Week):

1. **FIBA GDAP Inquiry** (2 hours)
   - [ ] Create account at https://gdap-portal.fiba.basketball/
   - [ ] Submit inquiry for API access
   - [ ] Request information about youth competition coverage
   - [ ] Ask about pricing for non-commercial research use

2. **API-Basketball Research** (1 hour)
   - [ ] Review https://www.api-basketball.com/ ToS
   - [ ] Check pricing and coverage
   - [ ] Verify youth competition data availability
   - [ ] Determine if suitable as short-term alternative

3. **Update Datasource Status** (30 min)
   - [ ] Update `datasource_status.yaml` with FIBA findings
   - [ ] Set `access_mode: official_api` for FIBA GDAP path
   - [ ] Document partnership inquiry in `next_action` field

### Follow-up (Weeks 2-4):

1. **If FIBA GDAP approves access**:
   - Implement official API adapter
   - Test with U17/U19 World Championships
   - Add test cases to `datasource_test_cases.yaml`
   - Mark status="green" once validated

2. **If FIBA GDAP requires expensive license**:
   - Evaluate api-basketball.com as alternative
   - Or defer FIBA until budget available
   - Update roadmap with cost barrier

3. **If FIBA GDAP denies access**:
   - Contact Genius Sports as alternative
   - Or pursue api-basketball.com if ToS allows
   - Document decision in datasource_status.yaml

---

## Implementation Considerations

### If Using Official API (GDAP or Genius Sports):

**Adapter Architecture**:
```python
class FIBAYouthDataSource(BaseDataSource):
    """
    FIBA Youth (U16/U17/U18/U19) via official GDAP API.
    """
    source_type = DataSourceType.FIBA_YOUTH
    source_name = "FIBA Youth Competitions"
    base_url = "https://gdap-portal.fiba.basketball/api/v1"  # Verify actual endpoint
    region = DataSourceRegion.GLOBAL

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}

    async def search_players(
        self, name: str, competition: str, season: str
    ) -> list[Player]:
        # Use official API endpoints from swagger docs
        pass
```

**Advantages**:
- No browser automation needed (official API)
- Structured JSON responses
- Reliable, professional support
- Complete historical data

**Test Cases** (once API access granted):
```yaml
fiba_youth:
  - player_name: "Victor Wembanyama"  # Historical example
    season: "2019"
    competition: "FIBA U19 World Cup"
    expected_min_games: 1
    expected_min_ppg: 10.0
    expected_max_ppg: 30.0
    notes: "Historical FIBA U19 star (verify season)"
```

---

## Summary & Recommendation

**FIBA Official API Access Exists**: Both FIBA GDAP and Genius Sports provide official APIs.

**Best Path**: Pursue FIBA GDAP partnership (official, potentially free for research).

**Timeline**: 2-4 weeks for partnership approval, not immediate.

**Action Required**: Manual inquiry to FIBA GDAP portal (cannot be automated).

**Alternative**: api-basketball.com for immediate progress (pending ToS review).

**Next Step**: Visit https://gdap-portal.fiba.basketball/ and submit API access request.

---

**Last Updated**: 2025-11-16
**Research Status**: Complete - Awaiting Partnership Inquiry
