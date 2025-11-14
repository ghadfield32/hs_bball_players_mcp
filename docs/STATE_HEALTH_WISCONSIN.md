# Wisconsin WIAA State Health Documentation

**State**: Wisconsin (WI)
**Adapter**: WisconsinWiaaDataSource
**Data Source**: halftime.wiaawi.org tournament brackets
**Coverage**: Boys + Girls, Divisions 1-5, 2015-2025
**Last Updated**: 2025-11-14

---

## Health Definition

Wisconsin is considered **HEALTHY** when all of the following criteria are met:

### Critical Criteria (Must Pass)
1. ✅ **Zero Self-Games**: No games where team plays itself
2. ✅ **Zero Duplicate Games**: No duplicate game entries
3. ✅ **Valid Score Range**: All scores between 0-200
4. ✅ **HTTP Success Rate**: ≥ 90% of bracket fetches successful
5. ✅ **Minimum Game Count**: ≥ 200 games per year/gender

### Warning Criteria (Should Pass)
6. ⚠️ **Unknown Round Percentage**: < 20% of games have "Unknown Round"
7. ⚠️ **Round Progression**: Regional ≥ Sectional ≥ State game counts
8. ⚠️ **Score Distribution**: < 5% of scores suspicious (< 10 or > 150)
9. ⚠️ **HTTP 403 Rate**: < 5% forbidden responses (anti-bot detection)
10. ⚠️ **Division Coverage**: All 5 divisions (Div1-Div5) present

---

## Quick Health Check Commands

### Check Current Year (Boys)
```bash
python scripts/diagnose_wisconsin_wiaa.py --year 2025 --gender Boys --verbose
```

### Check Current Year (Girls)
```bash
python scripts/diagnose_wisconsin_wiaa.py --year 2024 --gender Girls --verbose
```

### Check Historical Range
```bash
python scripts/diagnose_wisconsin_wiaa.py --backfill 2020-2025
```

### Run Integration Tests
```bash
pytest tests/test_datasources/test_wisconsin_wiaa.py -v
```

---

## Expected Metrics (Baseline)

Based on WIAA tournament structure:

| Metric | Boys 2024 | Girls 2024 | Tolerance |
|--------|-----------|------------|-----------|
| Total Games | 220-235 | 220-235 | ±10% |
| Unique Teams | 80-100 | 80-100 | ±15% |
| Self-Games | 0 | 0 | Must be 0 |
| Duplicates | 0 | 0 | Must be 0 |
| Unknown Rounds | < 20% | < 20% | Warning threshold |
| HTTP Success | ≥ 90% | ≥ 90% | Warning threshold |
| Avg Score | 50-70 | 50-70 | Information only |

### Per Division (Approximate)
- **Div1**: ~55-60 games
- **Div2**: ~50-55 games
- **Div3**: ~45-50 games
- **Div4**: ~40-45 games
- **Div5**: ~30-35 games

### Per Round Type (Approximate)
- **Regional**: ~120-140 games (60%)
- **Sectional**: ~60-75 games (30%)
- **State**: ~20-25 games (10%)

---

## HTTP Error Handling

The Wisconsin WIAA adapter includes robust error handling:

### 404 Not Found
- **Meaning**: Bracket page doesn't exist
- **Action**: Logged as DEBUG, skipped silently
- **Expected**: Some divisions/sectionals may not have full brackets

### 403 Forbidden (Anti-Bot)
- **Meaning**: Blocked by anti-bot protection
- **Action**: Retry with exponential backoff (3 attempts)
- **Mitigation**: Browser-like headers, delays between requests

### 500+ Server Errors
- **Meaning**: WIAA server issues
- **Action**: Retry with exponential backoff (3 attempts)
- **Expected**: Rare, should be transient

### Timeouts
- **Meaning**: Network/server slow response
- **Action**: Retry with exponential backoff (3 attempts)
- **Timeout**: 30 seconds default

---

## Data Quality Features

### Parser Enhancements (Phase 1)
- ✅ **Self-Game Detection**: Automatically skips games where `home_team == away_team`
- ✅ **Duplicate Detection**: Signature matching on (teams, scores, round)
- ✅ **Score Validation**: Filters scores outside 0-200 range
- ✅ **Round Detection**: 9 regex patterns for tournament rounds
- ✅ **Overtime Parsing**: Detects OT, 2OT, 3OT indicators

### URL Discovery (Phase 2)
- ✅ **Navigation Link Extraction**: Discovers brackets from HTML navigation
- ✅ **Pattern Fallback**: Generates URLs when discovery fails
- ✅ **Smart 404 Handling**: Skips non-existent brackets gracefully

### Coverage (Phases 3-4)
- ✅ **Boys & Girls**: Unified parser handles both genders
- ✅ **Historical**: 2015-2025 (11 years) accessible
- ✅ **All Divisions**: Div1-Div5 support

---

## Monitoring Schedule

### Daily (Current Season)
```bash
# Morning check - both genders
python scripts/diagnose_wisconsin_wiaa.py --year $(date +%Y) --gender Boys
python scripts/diagnose_wisconsin_wiaa.py --year $(date +%Y) --gender Girls
```

### Weekly (Integration Tests)
```bash
# Full test suite
pytest tests/test_datasources/test_wisconsin_wiaa.py -v --tb=short
```

### Monthly (Historical Validation)
```bash
# Validate last 3 years
python scripts/diagnose_wisconsin_wiaa.py --backfill $(expr $(date +%Y) - 2)-$(date +%Y)
```

### Seasonal (Full Backfill)
```bash
# Complete historical fetch (2015-2025)
python scripts/backfill_wisconsin_history.py --format parquet --output data/wisconsin_wiaa
```

---

## Troubleshooting

### High 403 Rate (> 5%)
**Cause**: Anti-bot detection triggered
**Solutions**:
1. Increase delays between requests
2. Rotate User-Agent strings
3. Use residential proxy if available
4. Contact WIAA for API access

### Low Game Count (< 200)
**Cause**: Missing brackets or parser failures
**Check**:
1. HTTP stats for 404 rate (expected divisions missing?)
2. Parser logs for parsing errors
3. WIAA website structure changes

### High Unknown Round %
**Cause**: Round detection patterns not matching
**Solutions**:
1. Check WIAA HTML for new round naming
2. Update round regex patterns in parser
3. Add new patterns to `round_patterns` list

### Score Distribution Outliers
**Cause**: Parsing errors or data entry issues
**Action**:
1. Review suspicious games in verbose mode
2. Check HTML source for format changes
3. Validate against WIAA official results

---

## Status History

| Date | Status | Boys Games | Girls Games | Notes |
|------|--------|------------|-------------|-------|
| 2025-11-14 | ✅ HEALTHY | TBD | TBD | Initial implementation complete |
| 2025-11-15 | ⏳ PENDING | - | - | Awaiting first live validation |

---

## Contacts & Resources

- **WIAA Official Site**: https://www.wiaawi.org
- **Tournament Brackets**: https://halftime.wiaawi.org
- **Adapter Source**: `src/datasources/us/wisconsin_wiaa.py`
- **Diagnostic Script**: `scripts/diagnose_wisconsin_wiaa.py`
- **Tests**: `tests/test_datasources/test_wisconsin_wiaa.py`

---

## Health Alert Thresholds

### CRITICAL (Immediate Action Required)
- Self-games > 0
- Duplicate games > 0
- HTTP success rate < 80%
- Game count < 150 (should be ~220+)

### WARNING (Investigation Needed)
- Unknown round % > 30%
- HTTP success rate < 90%
- 403 rate > 10%
- Game count 150-200 (should be 220+)
- Suspicious scores > 10%

### INFO (Monitoring Only)
- Unknown round % 20-30%
- HTTP success rate 90-95%
- Game count 200-220
- Suspicious scores 5-10%

---

## Automated Alerts (Future)

Potential integration with monitoring systems:

```python
# Example health check integration
from src.datasources.us.wisconsin_wiaa import WisconsinWiaaDataSource

async def check_wisconsin_health():
    wiaa = WisconsinWiaaDataSource()
    games = await wiaa.get_tournament_brackets(year=2025, gender="Boys")

    stats = wiaa.get_http_stats()

    # Alert conditions
    if stats['success_rate'] < 0.90:
        send_alert("WARNING: Wisconsin HTTP success rate low")

    if len(games) < 200:
        send_alert("WARNING: Wisconsin game count low")

    # ... more checks
```
