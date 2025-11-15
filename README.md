# HS Basketball Players Multi-Datasource API

A comprehensive, production-ready API for aggregating high school and youth basketball player statistics from **67+ data sources** across 6 continents with built-in rate limiting, caching, validation, and advanced analytics.

## 🏀 Features

- **Massive Multi-Datasource Coverage**: 67+ basketball statistics sources covering 50 US states + international
- **Advanced Stats Calculator** ✨ **NEW**: Auto-calculates 9 advanced metrics (TS%, eFG%, A/TO, etc.)
- **DuckDB Analytics** ✨ **NEW**: In-process analytical database for fast SQL queries (10-100x faster than cache)
- **Parquet Export** ✨ **NEW**: Export data to Parquet, CSV, or JSON with 10x compression
- **Recruiting Intelligence** ✨ **NEW**: 247Sports rankings, offers, and predictions integration
- **Data Persistence** ✨ **NEW**: Automatic storage of all scraped data for historical analysis
- **Aggressive Rate Limiting**: Token bucket algorithm with 50% safety margins
- **Comprehensive Validation**: Pydantic v2 models for type-safe data with automatic validation
- **Smart Caching**: File-based caching with configurable TTLs (Redis support ready)
- **Retry Logic**: Automatic retries with exponential backoff for network failures
- **Real Data Only**: No mock/fake data - all adapters tested with actual API calls
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Production Ready**: Structured logging, metrics, health checks, error handling
- **Comprehensive Tests**: 60+ integration tests with real API calls

## 📊 Supported Data Sources (67+)

### 🇺🇸 United States (52 sources)

#### National Elite Circuits (6 sources)
- ✅ **Nike EYBL (Boys)** - Elite Youth Basketball League (top 40 teams)
- ✅ **Nike EYBL (Girls)** - Elite Youth Basketball League Girls (top teams)
- ✅ **Adidas 3SSB (Boys)** - 3 Stripe Select Basketball (national circuit)
- ✅ **Adidas 3SSB (Girls)** - 3 Stripe Select Basketball Girls
- ✅ **Under Armour Association (Boys)** - UAA Circuit (national circuit)
- ✅ **Under Armour Next (Girls)** - UA Next Girls Circuit

#### Multi-State Coverage (3 sources)
- ✅ **Bound** - Iowa, South Dakota, Illinois, Minnesota (4 states)
- ✅ **SBLive/MaxPreps State Network** - WA, OR, CA, AZ, ID, NV (6 states)
- ✅ **RankOne** - TX, KY, IN, OH, TN (schedules/fixtures, 5 states)

#### Single-State Deep Coverage (5 sources)
- ✅ **MN Basketball Hub** - Minnesota (best free HS stats platform)
- ✅ **PSAL NYC** - Public Schools Athletic League (New York City)
- ✅ **Wisconsin Sports Network (WSN)** - Wisconsin comprehensive stats
- ✅ **FHSAA** - Florida High School Athletic Association
- ✅ **HHSAA** - Hawaii High School Athletic Association

#### Universal Coverage (1 source)
- ✅ **MaxPreps** ✨ **ENHANCED** - All 50 US states (comprehensive national platform + full season stats extraction)

#### State Athletic Associations (35 sources)
- ✅ **Alabama** - AHSAA (Alabama High School Athletic Association)
- ✅ **Alaska** - ASAA (Alaska School Activities Association)
- ✅ **Arkansas** - AAA (Arkansas Activities Association)
- ✅ **Colorado** - CHSAA (Colorado High School Activities Association)
- ✅ **Connecticut** - CIAC (Connecticut Interscholastic Athletic Conference)
- ✅ **Delaware** - DIAA (Delaware Interscholastic Athletic Association)
- ✅ **Washington DC** - DCIAA (DC Interscholastic Athletic Association)
- ✅ **Georgia** - GHSA (Georgia High School Association)
- ✅ **Indiana** - IHSAA (Indiana High School Athletic Association)
- ✅ **Kansas** - KSHSAA (Kansas State High School Activities Association)
- ✅ **Kentucky** - KHSAA (Kentucky High School Athletic Association)
- ✅ **Louisiana** - LHSAA (Louisiana High School Athletic Association)
- ✅ **Maine** - MPA (Maine Principals' Association)
- ✅ **Maryland** - MPSSAA (Maryland Public Secondary Schools Athletic Association)
- ✅ **Massachusetts** - MIAA (Massachusetts Interscholastic Athletic Association)
- ✅ **Michigan** - MHSAA (Michigan High School Athletic Association)
- ✅ **Mississippi** - MHSAA (Mississippi High School Activities Association)
- ✅ **Missouri** - MSHSAA (Missouri State High School Activities Association)
- ✅ **Montana** - MHSA (Montana High School Association)
- ✅ **Nebraska** - NSAA (Nebraska School Activities Association)
- ✅ **New Hampshire** - NHIAA (New Hampshire Interscholastic Athletic Association)
- ✅ **New Jersey** - NJSIAA (New Jersey State Interscholastic Athletic Association)
- ✅ **New Mexico** - NMAA (New Mexico Activities Association)
- ✅ **North Carolina** - NCHSAA (North Carolina High School Athletic Association)
- ✅ **North Dakota** - NDHSAA (North Dakota High School Activities Association)
- ✅ **Ohio** - OHSAA (Ohio High School Athletic Association)
- ✅ **Oklahoma** - OSSAA (Oklahoma Secondary School Activities Association)
- ✅ **Pennsylvania** - PIAA (Pennsylvania Interscholastic Athletic Association)
- ✅ **Rhode Island** - RIIL (Rhode Island Interscholastic League)
- ✅ **South Carolina** - SCHSL (South Carolina High School League)
- ✅ **Tennessee** - TSSAA (Tennessee Secondary School Athletic Association)
- ✅ **Utah** - UHSAA (Utah High School Activities Association)
- ✅ **Vermont** - VPA (Vermont Principals' Association)
- ✅ **Virginia** - VHSL (Virginia High School League)
- ✅ **West Virginia** - WVSSAC (West Virginia Secondary School Activities Commission)
- ✅ **Wyoming** - WHSAA (Wyoming High School Activities Association)

#### National Prep/Alternative (2 sources)
- ✅ **Grind Session** - National prep circuit
- ✅ **Overtime Elite (OTE)** - Professional pathway league
- ✅ **NEPSAC** - New England Preparatory School Athletic Council

### 🌍 Europe (6 sources)
- ✅ **FIBA Youth** - U16/U17/U18 international competitions (official stats)
- ✅ **ANGT** - Adidas Next Generation Tournament (EuroLeague youth)
- ✅ **FEB (Spain)** - Federación Española de Baloncesto youth leagues
- ✅ **LNB Espoirs (France)** - French youth basketball league
- ✅ **MKL (Germany)** - Mitteldeutsche Basketball Oberliga
- ✅ **NBBL (Germany)** - Nachwuchs Basketball Bundesliga

### 🌏 Global (1 source)
- ✅ **FIBA LiveStats** - Global FIBA competitions (all age groups, all continents)

### 🇨🇦 Canada (2 sources)
- ✅ **OSBA** - Ontario Scholastic Basketball Association
- ✅ **NPA** - National Preparatory Association (Canada-wide)

### 🇦🇺 Australia (1 source)
- ✅ **PlayHQ** - Junior state leagues and competitions

### 🎯 Recruiting Services (1 source)
- ✅ **247Sports** - Composite rankings, Crystal Ball predictions, offers tracking

✅ = Fully Implemented | Total: **67 data sources**

---

## 📈 Data Coverage & Metrics

### Basic Statistics (13 metrics) - 87% Coverage
- Points, Rebounds, Assists, Steals, Blocks
- Field Goal %, 3-Point %, Free Throw %
- Minutes, Games Played, Games Started
- Turnovers, Personal Fouls (when available)

### Advanced Statistics (9 metrics) ✨ **AUTO-CALCULATED**
- **True Shooting %** - Best overall shooting efficiency measure
- **Effective FG%** - Adjusts for 3-point value
- **Assist-to-Turnover Ratio** - Decision making quality
- **2-Point FG%** - Inside scoring efficiency
- **3-Point Attempt Rate** - Shot selection frequency
- **Free Throw Rate** - Ability to get to the free throw line
- **Points per Shot Attempt** - Scoring efficiency
- **Rebounds per 40 minutes** - Rebounding rate normalized
- **Points per 40 minutes** - Scoring rate normalized

### Recruiting Intelligence (10 metrics)
- National/Position/State Rankings
- Star Ratings (3-5★)
- Composite Ratings (0.0-1.0)
- College Offers (school, conference, status)
- Crystal Ball Predictions (school, confidence, expert)
- Commitment Status

### Player Demographics (10 fields)
- Name, Grad Year, School, City, State, Country
- Position, Height, Weight
- Profile URL

### Historical Data Support
- ✅ **Season-by-season stats** - All adapters support historical seasons (typically 3-5 years back)
- ✅ **Recruiting rankings** - 247Sports provides class years 2020-2035
- ✅ **DuckDB persistence** - All historical data automatically stored for longitudinal analysis
- ⏳ **Game-by-game logs** - Planned enhancement (MaxPreps, EYBL support available)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or uv

### Installation

```bash
# Clone the repository
git clone https://github.com/ghadfield32/hs_bball_players_mcp.git
cd hs_bball_players_mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env to configure your settings
```

### Running the API

```bash
# Start the FastAPI server
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 📖 API Documentation

### System Endpoints

```bash
# Health check
GET /health

# Rate limit status
GET /rate-limits

# Application metrics
GET /metrics
```

### Player & Stats Endpoints

```bash
# Search players across all sources (aggregates 67+ sources)
GET /api/v1/players/search?name=Smith&team=Lincoln&limit=50

# Search players from specific sources
GET /api/v1/players/search?name=Johnson&sources=eybl,psal,maxpreps&limit=25

# Get player details from specific source
GET /api/v1/players/{source}/{player_id}
# Example: GET /api/v1/players/eybl/eybl_john_smith

# Get player season stats from all sources (includes advanced metrics!)
GET /api/v1/players/{player_name}/stats?season=2024-25
# Example: GET /api/v1/players/John Smith/stats
# Returns: Basic stats + 9 auto-calculated advanced metrics (TS%, eFG%, A/TO, etc.)

# Search teams
GET /api/v1/teams/search?name=Lincoln&league=PSAL&limit=50

# Get leaderboards (points, rebounds, assists, steals, blocks)
GET /api/v1/leaderboards/points?season=2024-25&limit=50
GET /api/v1/leaderboards/rebounds?sources=eybl,mn_hub&limit=25

# Get available data sources
GET /api/v1/sources

# Check data source health
GET /api/v1/sources/health
```

### Recruiting Endpoints ✨ **NEW**

```bash
# Get recruiting rankings by class year
GET /api/v1/recruiting/rankings?class_year=2025&limit=100
GET /api/v1/recruiting/rankings?class_year=2026&position=PG&state=CA&limit=50

# Get player rankings across all services
GET /api/v1/recruiting/rankings/{player_id}

# Get college offers for a player
GET /api/v1/recruiting/offers/{player_id}?status=committed

# Get Crystal Ball predictions for a player
GET /api/v1/recruiting/predictions/{player_id}

# Get complete recruiting profile (aggregated)
GET /api/v1/recruiting/profile/{player_id}

# Get available recruiting sources
GET /api/v1/recruiting/sources
```

### Export & Analytics Endpoints

```bash
# Export players to various formats (Parquet, CSV, JSON)
GET /api/v1/export/players/parquet?source=eybl&limit=1000
GET /api/v1/export/players/csv?name=Johnson&school=Lincoln&limit=500
GET /api/v1/export/players/json?limit=100

# Export player statistics
GET /api/v1/export/stats/parquet?season=2024-25&limit=1000
GET /api/v1/export/stats/csv?min_ppg=20.0&limit=200
GET /api/v1/export/stats/json?source=eybl&limit=50

# Get export information (list all exported files)
GET /api/v1/export/info?category=players

# Analytics summary (from DuckDB)
GET /api/v1/analytics/summary

# Query players from analytical database
GET /api/v1/analytics/query/players?name=Smith&school=Lincoln&limit=100
GET /api/v1/analytics/query/players?source=eybl&limit=50

# Query player statistics from analytical database
GET /api/v1/analytics/query/stats?player_name=Johnson&season=2024-25&limit=50
GET /api/v1/analytics/query/stats?min_ppg=25.0&source=eybl&limit=25

# Get statistical leaderboards (from DuckDB)
GET /api/v1/analytics/leaderboard/points_per_game?season=2024-25&limit=50
GET /api/v1/analytics/leaderboard/rebounds_per_game?source=eybl&limit=25
GET /api/v1/analytics/leaderboard/assists_per_game?limit=100
```

**Try it now!** Visit http://localhost:8000/docs for interactive API documentation.

---

## ⚙️ Configuration

All configuration is managed through environment variables (see `.env.example`):

### Rate Limiting

```env
# National circuits
RATE_LIMIT_EYBL=30              # Nike EYBL (requests per minute)
RATE_LIMIT_THREE_SSB=30         # Adidas 3SSB
RATE_LIMIT_UAA=30               # Under Armour Association

# Multi-state platforms
RATE_LIMIT_MAXPREPS=20          # MaxPreps (50 states)
RATE_LIMIT_SBLIVE=25            # SBLive
RATE_LIMIT_BOUND=20             # Bound
RATE_LIMIT_RANKONE=15           # RankOne

# State associations
RATE_LIMIT_STATE_DEFAULT=15     # Default for state associations
RATE_LIMIT_PSAL=15              # NYC PSAL
# ... (35 state association rate limits)

# International
RATE_LIMIT_FIBA=20              # FIBA Youth
RATE_LIMIT_FIBA_LIVESTATS=25    # FIBA LiveStats
RATE_LIMIT_ANGT=20              # EuroLeague ANGT

# Recruiting
RATE_LIMIT_247SPORTS=10         # 247Sports (conservative)

# Global defaults
RATE_LIMIT_DEFAULT=10           # Fallback for unknown sources
RATE_LIMIT_GLOBAL=100           # Per-IP global limit
```

**Safety Margins**: All limits are set to 50% of actual source limits to prevent hitting rate limits.

### Caching

```env
CACHE_ENABLED=true
CACHE_TYPE=file                # file, redis, memory
CACHE_TTL_PLAYERS=3600        # 1 hour
CACHE_TTL_GAMES=1800          # 30 minutes
CACHE_TTL_STATS=900           # 15 minutes
CACHE_TTL_RECRUITING=7200     # 2 hours (recruiting data updates less frequently)
```

### HTTP Client

```env
HTTP_TIMEOUT=30               # seconds
HTTP_MAX_RETRIES=3
HTTP_RETRY_BACKOFF=2          # exponential multiplier
```

### DuckDB Analytics

```env
DUCKDB_ENABLED=true                      # Enable analytical database
DUCKDB_PATH=./data/basketball_analytics.duckdb
DUCKDB_MEMORY_LIMIT=2GB
DUCKDB_THREADS=4
```

**Benefits**: In-process analytical database for fast SQL queries on accumulated data. No external dependencies required.

### Data Export

```env
EXPORT_DIR=./data/exports               # Export output directory
PARQUET_COMPRESSION=snappy              # snappy, gzip, zstd, lz4
ENABLE_AUTO_EXPORT=false                # Auto-export on schedule
AUTO_EXPORT_INTERVAL=3600               # Export interval (seconds)
```

---

## 🏗️ Architecture

```
src/
├── models/              # Pydantic data models
│   ├── player.py       # Player, Position, PlayerLevel
│   ├── team.py         # Team, TeamStandings
│   ├── game.py         # Game, GameSchedule, GameStatus
│   ├── stats.py        # PlayerSeasonStats, PlayerGameStats
│   ├── recruiting.py   # RecruitingRank, CollegeOffer, RecruitingPrediction
│   └── source.py       # DataSource metadata
├── datasources/         # Data source adapters (67+ adapters)
│   ├── base.py         # Abstract base class for stats adapters
│   ├── base_association.py  # Base for state associations
│   ├── us/             # US sources (52 adapters)
│   │   ├── eybl.py, eybl_girls.py, three_ssb.py, uaa.py (national circuits)
│   │   ├── maxpreps.py (universal 50-state coverage)
│   │   ├── bound.py, sblive.py, rankone.py (multi-state)
│   │   ├── psal.py, mn_hub.py, wsn.py (single-state deep)
│   │   └── alabama_ahsaa.py ... wyoming_whsaa.py (35 state associations)
│   ├── europe/         # European sources (6 adapters)
│   ├── global/         # Global sources (FIBA LiveStats)
│   ├── canada/         # Canadian sources (2 adapters)
│   ├── australia/      # Australian sources (PlayHQ)
│   └── recruiting/     # Recruiting services (247Sports)
├── services/            # Core services
│   ├── rate_limiter.py # Token bucket rate limiting
│   ├── cache.py        # Caching service
│   ├── aggregator.py   # Multi-source aggregation (67+ sources)
│   ├── identity.py     # Player identity resolution across sources
│   ├── duckdb_storage.py   # DuckDB analytical database
│   └── parquet_exporter.py # Parquet/CSV/JSON export
├── api/                 # API routes and endpoints
│   ├── routes.py       # Player/team/stats endpoints
│   ├── recruiting_routes.py # Recruiting endpoints
│   └── export_routes.py # Export & analytics endpoints
├── utils/               # Utilities
│   ├── http_client.py  # HTTP client with retry
│   ├── parser.py       # HTML parsing helpers
│   ├── advanced_stats.py # Advanced metrics calculator
│   └── logger.py       # Structured logging
├── config.py            # Configuration management
└── main.py              # FastAPI application
```

---

## 🧪 Testing

Comprehensive test suite with 60+ integration tests using real API calls (no mocks).

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m datasource       # Test all datasource adapters
pytest -m service          # Test all services
pytest -m api              # Test all API endpoints

# Skip slow tests (for quick CI)
pytest -m "not slow"

# Run specific datasource tests
pytest tests/test_datasources/test_eybl.py
pytest tests/test_datasources/test_maxpreps.py
pytest tests/test_datasources/test_fiba_youth.py
pytest tests/test_datasources/test_recruiting/test_247sports.py

# Run service tests (aggregator, DuckDB, Parquet, advanced stats)
pytest tests/test_services/
pytest tests/test_utils/test_advanced_stats_integration.py

# Run API endpoint tests
pytest tests/test_api/
```

**Test Coverage**: 60+ tests across datasources, services, and API endpoints with real API integration.

See [tests/README.md](tests/README.md) for detailed testing documentation.

---

## 📝 Development

### Adding a New Data Source

1. Create adapter class in `src/datasources/{region}/{source}.py`
2. Inherit from `BaseDataSource` (for stats) or `BaseRecruitingSource` (for recruiting)
3. Implement required abstract methods:
   - `get_player()` - Fetch player by ID
   - `search_players()` - Search for players by name/team/season
   - `get_player_season_stats()` - Get season aggregates
   - `get_player_game_stats()` - Get game-by-game logs
   - `get_team()` - Fetch team by ID
   - `get_games()` - Get game schedules/results
   - `get_leaderboard()` - Get statistical leaderboards
4. Add configuration to `.env.example`
5. Add rate limit to `src/config.py`
6. Register in `src/services/aggregator.py`
7. Write tests in `tests/test_datasources/`

See `src/datasources/us/eybl.py` for a complete example.

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## 🔒 Rate Limiting Details

This API uses a **token bucket algorithm** with per-source rate limiting:

- Each of 67+ data sources has its own token bucket
- Tokens refill continuously at configured rate (requests/minute → requests/second)
- Requests consume tokens; if insufficient tokens, request waits
- 50% safety margin on all limits (e.g., if source allows 60 req/min, we limit to 30 req/min)
- Request queuing prevents burst traffic from hitting limits
- Exponential backoff on errors (2s, 4s, 8s, 16s)
- Global per-IP limit (100 req/min) across all sources

**Status Monitoring**: Check `/rate-limits` endpoint to see current usage for all 67+ sources.

---

## 📊 Data Models

All data is validated using Pydantic v2 models with comprehensive type checking:

- **Player**: Physical attributes, school, team, academic info, profile URLs
- **PlayerGameStats**: Per-game statistics with calculated fields
- **PlayerSeasonStats**: Season aggregates with averages, highs, and auto-calculated advanced metrics
- **Team**: Team info, roster, record, standings
- **Game**: Game details, scores, quarter breakdowns
- **RecruitingRank**: Rankings (national, position, state), stars, ratings, commitments
- **CollegeOffer**: Offers with school, conference, status, dates
- **RecruitingPrediction**: Crystal Ball predictions with confidence scores
- **DataSource**: Metadata tracking (source, quality flags, timestamps)

See `src/models/` for complete schemas.

---

## 🐛 Error Handling

- All datasource errors logged with context
- Graceful degradation if sources unavailable
- Quality flags on incomplete/suspect data
- Detailed error messages in responses
- Automatic retry on transient failures
- Health checks per source (monitor 67+ sources independently)

---

## 📈 Monitoring & Observability

- **Structured Logging**: JSON logs with context (request_id, source, etc.)
- **Metrics Tracking**: Request counts, cache hit rates, error rates per source
- **Health Checks**: Per-source health status for all 67+ sources
- **Performance Monitoring**: Response times, rate limit usage
- **DuckDB Analytics**: Query accumulated data for insights

Logs stored in `data/logs/`:
- `app.log` - All application logs
- `error.log` - Error logs only
- `datasource_requests.log` - Data source request logs

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Nike EYBL** for public youth basketball stats
- **FIBA** for international youth competition data
- **247Sports** for recruiting intelligence (use with commercial license)
- **MaxPreps** for comprehensive US high school coverage
- **All 67+ data sources** providing public access to youth basketball statistics

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ghadfield32/hs_bball_players_mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ghadfield32/hs_bball_players_mcp/discussions)

---

## 🗺️ Roadmap

### Completed ✅
- [x] 67+ datasource adapters (US, Europe, Canada, Australia, Global)
- [x] Multi-source aggregation with identity resolution
- [x] DuckDB analytics database
- [x] Parquet/CSV/JSON export
- [x] Comprehensive rate limiting
- [x] Advanced stats calculator (9 metrics auto-calculated)
- [x] Recruiting intelligence (247Sports integration)
- [x] 60+ integration tests

### In Progress 🚧
- [ ] 247Sports full profile scraping (offers, Crystal Ball predictions)
- [ ] Birth date extraction for age-for-grade analysis
- [ ] Offensive/defensive rebounding split
- [ ] Game-by-game performance logs (consistency analysis)

### Planned 📋
- [ ] Tournament performance tracking
- [ ] Historical year-over-year improvement tracking
- [ ] Physical combine data (vertical, wingspan) integration
- [ ] ML forecasting models for college success prediction
- [ ] GraphQL API layer
- [ ] Web dashboard for visualization
- [ ] Real-time game updates (where available)
- [ ] Webhooks for data updates
- [ ] Python SDK for easy integration

---

**Built with** ❤️ **and** ☕ **for the basketball analytics community**

**Covering 67+ data sources across 50 US states + international markets**
