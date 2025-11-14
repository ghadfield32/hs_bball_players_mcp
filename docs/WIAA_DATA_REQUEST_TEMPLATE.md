# WIAA Official Data Feed Request Template

This template can be used to contact WIAA to request an official data feed for basketball tournament brackets. If they provide a sanctioned data source (API, CSV, JSON, or regular exports), we can integrate it into the automated pipeline and eliminate manual downloads entirely.

## Why Request Official Access?

**Current situation:**
- WIAA blocks automated HTTP requests (403 errors)
- Manual browser downloads required for each fixture
- Limited to historical data (can't proactively pull new tournaments)

**Benefits of official access:**
- Fully automated data ingestion
- Real-time updates during tournament season
- No manual download step required
- Proper attribution and licensing
- Sustainable long-term solution

## Contact Information

**Find WIAA contacts at:**
- Website: https://www.wiaawi.org/
- Look for: "Contact Us", "Media Relations", "Statistics", or "IT/Web Services"
- Email: Look for media@wiaawi.org, stats@wiaawi.org, or similar

## Email Template

---

**Subject:** Request for Basketball Tournament Bracket Data Access

**To:** [WIAA appropriate contact - media/stats/IT]

**Email Body:**

Dear WIAA Team,

I am writing to request access to historical and ongoing Wisconsin high school basketball tournament bracket data for an open-source analytics project.

**Project Overview:**
I am developing open-source tools to aggregate and analyze high school basketball data from multiple states and data sources. The goal is to provide researchers, journalists, and basketball enthusiasts with comprehensive historical statistics and trend analysis.

The project repository is publicly available at: [your GitHub URL]

**Current Approach:**
I am currently manually downloading HTML bracket files from your public website at halftime.wiaawi.org. However, I want to ensure I'm respecting your terms of service and not creating unnecessary load on your servers through repeated manual downloads.

**What I'm Requesting:**
I would greatly appreciate if WIAA could provide any of the following:

1. **Historical data dump** (preferred):
   - Basketball tournament brackets for 2015-present
   - Format: CSV, JSON, XML, or similar machine-readable format
   - Data fields: Game date, teams, scores, division, round, location

2. **API access** (if available):
   - Simple HTTP endpoint to fetch bracket data by year/division
   - Can be limited to authenticated access with rate limiting
   - Example: GET /api/basketball/brackets/2024/division/1

3. **Scheduled data exports**:
   - Weekly or monthly CSV/JSON exports during tournament season
   - Delivered via email, FTP, or public URL
   - Historical backfill for 2015-present

4. **Permission for programmatic access**:
   - If the above aren't feasible, explicit permission to make scripted HTTP requests
   - I would implement rate limiting (e.g., 1 request per 10 seconds)
   - Downloads would only occur once per tournament season

**My Commitments:**
- **Attribution**: I will clearly credit WIAA as the data source in all outputs
- **Non-commercial**: This is a research/educational project with no commercial use
- **Respect terms**: I will abide by any usage constraints or licensing requirements you specify
- **Data caching**: I will cache data locally to minimize repeat requests
- **Transparency**: The project is open-source, so data usage is fully auditable

**Benefits to WIAA:**
- Increased visibility for Wisconsin high school basketball
- Proper attribution in analytics and research
- Reduced server load (one structured export vs. multiple browser sessions)
- Partnership with open-source community

**Technical Details:**
- Coverage goal: 10 years × 2 genders × 4 divisions = 80 tournament brackets
- Update frequency: Once per year (during/after tournament season)
- Data retention: Historical archive for trend analysis

I am happy to discuss technical implementation, data formats, or any restrictions you'd like to place on the data usage. I can also provide progress reports or demonstrations of the analytics tools being built.

Thank you for considering this request. I look forward to hearing from you and potentially partnering with WIAA to make Wisconsin high school basketball data more accessible for research and analysis.

Best regards,

[Your Name]
[Your Email]
[Your Phone - optional]
[GitHub Profile - optional]
[Project Repository URL]

---

## Follow-Up Strategy

**If they respond positively:**
1. Clarify data format and delivery method
2. Implement data ingestion in `src/datasources/us/wisconsin_wiaa_api.py`
3. Add CI job to fetch data weekly/monthly
4. Update tests to use API mode when available
5. Document integration in PROJECT_LOG

**If they decline or don't respond:**
- Continue with human-in-the-loop workflow (current approach)
- Browser helper + batch processor is sustainable long-term
- Re-contact annually to check if policy has changed

**If they provide partial access:**
- Integrate what's available (e.g., just current season)
- Continue manual downloads for historical backfill
- Hybrid approach: API for new data, fixtures for historical

## Integration Plan (If Approved)

**Technical implementation if WIAA provides official access:**

1. **Create API DataSource** (`src/datasources/us/wisconsin_wiaa_api.py`):
   ```python
   class WisconsinWiaaApiDataSource(WisconsinWiaaDataSource):
       """WIAA official API/feed integration."""

       def __init__(self, api_key: Optional[str] = None, base_url: str = "..."):
           self.api_key = api_key
           self.base_url = base_url
           self.cache_dir = Path("cache/wiaa_api")

       def fetch_brackets(self, year: int, gender: str, division: str) -> List[Game]:
           """Fetch bracket data from official API/feed."""
           # Implementation depends on provided format
   ```

2. **Add DataMode.API**:
   ```python
   class DataMode(Enum):
       LIVE = "live"
       FIXTURE = "fixture"
       API = "api"  # New mode for official feed
   ```

3. **Update WisconsinWiaaDataSource**:
   ```python
   def __init__(self, data_mode: DataMode = DataMode.API):
       """Default to API mode if available, fallback to FIXTURE."""
       if data_mode == DataMode.API and not self._api_available():
           logger.warning("API not available, falling back to FIXTURE mode")
           data_mode = DataMode.FIXTURE
   ```

4. **CI Integration** (`.github/workflows/wiaa_sync.yml`):
   ```yaml
   name: WIAA Data Sync
   on:
     schedule:
       - cron: '0 0 * * 0'  # Weekly on Sunday
     workflow_dispatch:  # Manual trigger

   jobs:
     sync:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Fetch WIAA data
           env:
             WIAA_API_KEY: ${{ secrets.WIAA_API_KEY }}
           run: python scripts/sync_wiaa_api.py
         - name: Run validation
           run: python scripts/process_fixtures.py --planned
         - name: Commit updates
           run: |
             git add tests/fixtures/wiaa/
             git commit -m "Automated WIAA data sync"
             git push
   ```

5. **Documentation**:
   - Add API setup instructions to FIXTURE_AUTOMATION_GUIDE.md
   - Document API credentials in README (if applicable)
   - Note attribution requirements in all outputs

## Summary

**Asking for official access is worth trying because:**
- ✅ Eliminates manual download step entirely
- ✅ Enables real-time tournament tracking
- ✅ Proper licensing and attribution
- ✅ Sustainable long-term solution

**Current approach is still solid if request is declined:**
- ✅ Browser helper automates everything except the actual download
- ✅ Batch processor handles all validation/testing
- ✅ One ~20-minute session per year for maintenance
- ✅ Respects WIAA's bot protection
- ✅ No ToS or legal concerns

**Action items:**
1. Find appropriate WIAA contact (media/stats/IT)
2. Customize email template with your details
3. Send request
4. If approved: Implement API integration (Phase 14.7)
5. If declined: Continue with current workflow (works great!)
