# HS Basketball Players Multi-Datasource API

A comprehensive, production-ready API for aggregating high school and youth basketball player statistics from multiple data sources with built-in rate limiting, caching, and validation.

## 🏀 Features

- **Multi-Datasource Support**: Integrates with 9+ basketball statistics sources (EYBL, FIBA, PSAL, MN Hub, etc.)
- **Aggressive Rate Limiting**: Token bucket algorithm with 50% safety margins to never hit source limits
- **Comprehensive Validation**: Pydantic v2 models for type-safe data with automatic validation
- **Smart Caching**: File-based caching with configurable TTLs (Redis support ready)
- **Retry Logic**: Automatic retries with exponential backoff for network failures
- **Real Data Only**: No mock/fake data - all adapters tested with actual API calls
- **Detailed Statistics**: Maximum available stats extracted from each source
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Production Ready**: Structured logging, metrics, health checks, error handling

## 📊 Supported Data Sources

### United States
- ✅ **Nike EYBL** - Elite Youth Basketball League stats, schedules, standings, leaderboards
- ✅ **PSAL NYC** - Public Schools Athletic League (New York City) leaders and standings
- ✅ **MN Basketball Hub** - Minnesota high school stats, teams, and leaderboards
- ⏳ **Grind Session** - High school prep circuit (adapter ready to implement)
- ⏳ **Overtime Elite (OTE)** - Professional pathway league (adapter ready to implement)

### Europe & Global
- ✅ **FIBA Youth** - U16/U17/U18 international competitions with box scores
- ⏳ **NextGen EuroLeague (ANGT)** - European youth elite (adapter ready to implement)

### Canada
- ⏳ **OSBA** - Ontario Scholastic Basketball Association (adapter ready to implement)

### Australia
- ⏳ **PlayHQ** - Junior leagues and state competitions (adapter ready to implement)

✅ = Fully Implemented | ⏳ = Planned

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
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

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

### Data Endpoints ✅ **NOW AVAILABLE**

```bash
# Search players across all sources
GET /api/v1/players/search?name=Smith&team=Lincoln&limit=50

# Search players from specific sources
GET /api/v1/players/search?name=Johnson&sources=eybl,psal&limit=25

# Get player details from specific source
GET /api/v1/players/{source}/{player_id}
# Example: GET /api/v1/players/eybl/eybl_john_smith

# Get player season stats from all sources
GET /api/v1/players/{player_name}/stats?season=2024-25
# Example: GET /api/v1/players/John Smith/stats

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

**Try it now!** Visit http://localhost:8000/docs for interactive API documentation.

## ⚙️ Configuration

All configuration is managed through environment variables (see `.env.example`):

### Rate Limiting

```env
RATE_LIMIT_EYBL=30           # requests per minute
RATE_LIMIT_FIBA=20
RATE_LIMIT_PSAL=15
# ... etc
```

**Safety Margins**: All limits are set to 50% of actual source limits to prevent hitting rate limits.

### Caching

```env
CACHE_ENABLED=true
CACHE_TYPE=file                # file, redis, memory
CACHE_TTL_PLAYERS=3600        # 1 hour
CACHE_TTL_GAMES=1800          # 30 minutes
CACHE_TTL_STATS=900           # 15 minutes
```

### HTTP Client

```env
HTTP_TIMEOUT=30               # seconds
HTTP_MAX_RETRIES=3
HTTP_RETRY_BACKOFF=2          # exponential multiplier
```

## 🏗️ Architecture

```
src/
├── models/              # Pydantic data models
│   ├── player.py       # Player models
│   ├── team.py         # Team models
│   ├── game.py         # Game models
│   ├── stats.py        # Statistics models
│   └── source.py       # Data source metadata
├── datasources/         # Data source adapters
│   ├── base.py         # Abstract base class
│   ├── us/             # US sources (EYBL, PSAL, etc.)
│   ├── europe/         # European sources
│   ├── canada/         # Canadian sources
│   └── australia/      # Australian sources
├── services/            # Core services
│   ├── rate_limiter.py # Token bucket rate limiting
│   ├── cache.py        # Caching service
│   └── aggregator.py   # Multi-source aggregation
├── api/                 # API routes and endpoints
├── utils/               # Utilities
│   ├── http_client.py  # HTTP client with retry
│   ├── parser.py       # HTML parsing helpers
│   └── logger.py       # Structured logging
├── config.py            # Configuration management
└── main.py              # FastAPI application
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_datasources/test_eybl.py

# Run with real API calls (not mocked)
pytest --real-api
```

## 📝 Development

### Adding a New Data Source

1. Create adapter class in `src/datasources/{region}/{source}.py`
2. Inherit from `BaseDataSource`
3. Implement required abstract methods:
   - `get_player()`
   - `search_players()`
   - `get_player_season_stats()`
   - `get_player_game_stats()`
   - `get_team()`
   - `get_games()`
   - `get_leaderboard()`
4. Add configuration to `.env.example`
5. Add rate limit to `src/config.py`
6. Write tests in `tests/test_datasources/`

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

## 🔒 Rate Limiting Details

This API uses a **token bucket algorithm** with per-source rate limiting:

- Each data source has its own token bucket
- Tokens refill continuously at configured rate (requests/minute converted to requests/second)
- Requests consume tokens; if insufficient tokens, request waits
- 50% safety margin on all limits (e.g., if source allows 60 req/min, we limit to 30 req/min)
- Request queuing prevents burst traffic from hitting limits
- Exponential backoff on errors (2s, 4s, 8s, 16s)

**Status Monitoring**: Check `/rate-limits` endpoint to see current usage for all sources.

## 📊 Data Models

All data is validated using Pydantic v2 models with comprehensive type checking:

- **Player**: Physical attributes, school, team, academic info
- **PlayerGameStats**: Per-game statistics with calculated fields
- **PlayerSeasonStats**: Season aggregates with averages and highs
- **Team**: Team info, roster, record, standings
- **Game**: Game details, scores, quarter breakdowns
- **DataSource**: Metadata tracking (source, quality flags, timestamps)

See `src/models/` for complete schemas.

## 🐛 Error Handling

- All datasource errors logged with context
- Graceful degradation if sources unavailable
- Quality flags on incomplete/suspect data
- Detailed error messages in responses
- Automatic retry on transient failures

## 📈 Monitoring & Observability

- **Structured Logging**: JSON logs with context (request_id, source, etc.)
- **Metrics Tracking**: Request counts, cache hit rates, error rates
- **Health Checks**: Per-source health status
- **Performance Monitoring**: Response times, rate limit usage

Logs stored in `data/logs/`:
- `app.log` - All application logs
- `error.log` - Error logs only
- `datasource_requests.log` - Data source request logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Nike EYBL for public stats
- FIBA for youth competition data
- All data sources providing free public access

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ghadfield32/hs_bball_players_mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ghadfield32/hs_bball_players_mcp/discussions)

## 🗺️ Roadmap

- [ ] Complete all planned datasource adapters
- [ ] Add full API endpoint implementations
- [ ] Implement Redis caching backend
- [ ] Add player identity resolution across sources
- [ ] Create data export functionality (CSV, JSON, Excel)
- [ ] Add GraphQL API layer
- [ ] Build web dashboard for visualization
- [ ] Add real-time game updates (where available)
- [ ] Implement webhooks for data updates
- [ ] Create Python SDK for easy integration

---

**Built with** ❤️ **and** ☕ **for the basketball analytics community**
