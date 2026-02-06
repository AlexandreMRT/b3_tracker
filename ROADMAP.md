# B3 Tracker - Roadmap & Future Plans

> This file is structured for AI consumption. Use it to continue development in future sessions.

## 📊 Current State (v1.1 — 2026-02-05)

### Implemented Features
- [x] 128 assets tracked (101 BR stocks, 20 US stocks, 4 commodities, 2 crypto)
- [x] Parallel fetch with ThreadPoolExecutor (8 workers, ~48s for all assets)
- [x] Polymarket sentiment integration (crypto, macro, geopolitical markets)
- [x] Technical indicators: RSI-14, MA50, MA200, golden/death cross
- [x] Fundamental data: P/E, P/B, dividend yield, beta, ROE, market cap
- [x] Trading signals: 10 types (oversold, overbought, trends, volume spikes)
- [x] News sentiment: Bilingual PT-BR (Google News RSS) + EN (yfinance)
- [x] VADER with custom Portuguese financial lexicon
- [x] Benchmark comparison: vs IBOV and S&P 500
- [x] Dual currency: All prices in BRL and USD
- [x] REST API: FastAPI with Swagger UI (port 8000)
- [x] Reports: Human (Markdown) + AI (JSON) consolidated reports
- [x] Algorithmic watchlist scoring (RSI + trend + news)
- [x] Docker Compose: app (scheduler), api (REST), runner (CLI)
- [x] Multi-user system with Google OAuth 2.0
- [x] PostgreSQL database with user authentication
- [x] Portfolio tracking with positions and transactions
- [x] P&L calculations, dividends, IRR tracking
- [x] Watchlist per user
- [x] 36 authenticated API endpoints
- [x] **Test suite**: 173 tests (pytest), 66.6% coverage, 0 warnings
- [x] **Unified signal detection** (`src/signals.py`) — single source of truth for all signal logic
- [x] **Structured logging** (`src/logger.py`) — replaced 70+ print() calls with configurable logging
- [x] **Docker hardening** — non-root user, healthchecks, `.dockerignore`, `docker-compose.prod.yml`
- [x] **Deduplicated save_quote()** — 73 duplicate fields collapsed into shared `_build_quote_fields()` helper
- [x] **Security fixes** — unified SECRET_KEY, restricted CORS, guarded test-login endpoint

### Tech Stack
- Python 3.11 (Docker) / 3.13 (local dev)
- PostgreSQL 16 with SQLAlchemy 2.0
- yfinance for market data
- FastAPI + uvicorn for REST API
- Google OAuth 2.0 with JWT tokens
- NLTK VADER for sentiment analysis
- feedparser for Google News RSS
- Docker Compose for orchestration
- pytest + httpx for testing (SQLite in-memory with StaticPool)

---

## 🎯 Priority Features (Next Up)

### 1. Web Frontend Dashboard 🖥️
**Priority: CRITICAL | Effort: HIGH**

Create a modern web interface for portfolio management:
- Dashboard with portfolio overview and performance charts
- Add/edit/delete portfolios
- Record transactions (buy/sell/dividend)
- View positions with real-time P&L
- Manage watchlist (add/remove tickers)
- View market data for tracked assets
- Responsive design (mobile-friendly)

**Implementation notes:**
- Option A: React/Vue/Svelte SPA with separate API calls
- Option B: Server-side rendered with Jinja2 templates (simpler, faster to implement)
- Use Chart.js or Plotly for visualizations
- Integrate with existing authentication (OAuth + JWT)
- Store static files in `src/static/` and templates in `src/templates/`

**Files to create/modify:**
- `src/templates/dashboard.html` (main dashboard)
- `src/templates/portfolio.html` (portfolio detail view)
- `src/templates/transactions.html` (transaction history)
- `src/static/css/style.css` (styling)
- `src/static/js/app.js` (frontend logic)
- `src/api.py` (add HTML rendering routes)

---

### 2. ~~Test Suite~~ ✅ COMPLETED (2026-02-05)
**Status: DONE**

Comprehensive test suite implemented:
- ✅ 173 tests across 7 test files
- ✅ 66.6% code coverage (threshold: 60%)
- ✅ 0 warnings (DeprecationWarning treated as error)
- ✅ Unit tests for signals, scoring, fetcher calculations, portfolio, users
- ✅ Integration tests for 41 API endpoints
- ✅ Authentication flow tests (JWT creation/verification)
- ✅ SQLite in-memory DB with StaticPool for fast isolated tests
- ✅ pyproject.toml with pytest config, markers, coverage settings

**Files created:**
- `tests/conftest.py` — fixtures (engine, sessions, TestClient, auth override)
- `tests/test_api.py` — 41 API integration tests
- `tests/test_auth.py` — JWT token tests
- `tests/test_fetcher.py` — pure-logic function tests
- `tests/test_portfolio.py` — portfolio CRUD & P&L tests
- `tests/test_scoring.py` — algorithmic watchlist scoring tests
- `tests/test_signals.py` — unified signal detection tests (35 tests)
- `tests/test_users.py` — user management & watchlist tests
- `pyproject.toml` — pytest, coverage, filterwarnings config

**Still TODO:**
- [ ] GitHub Actions CI/CD pipeline (`.github/workflows/tests.yml`)
- [ ] Increase coverage to 80%+ (add exporter, scheduler, polymarket tests)

---

### 3. Telegram Bot 🔔
**Priority: HIGH | Effort: MEDIUM**

Notify user when important events happen:
- RSI < 30 (oversold) or > 70 (overbought) on watched assets
- Golden/Death cross detected
- Volume spike > 2x average
- Price near 52-week high/low
- Negative/positive news sentiment spike

**Implementation notes:**
- Use python-telegram-bot library
- Create `/src/telegram_bot.py`
- Store TELEGRAM_BOT_TOKEN and CHAT_ID in environment variables
- Add `bot` service to docker-compose.yml
- Commands: `/status`, `/watchlist`, `/add TICKER`, `/remove TICKER`, `/signals`

**Files to create/modify:**
- `src/telegram_bot.py` (new)
- `src/alerts.py` (new - alert detection logic)
- `docker-compose.yml` (add bot service)
- `requirements.txt` (add python-telegram-bot)

---

### 4. Data Quality & Health Monitor ✅
**Priority: HIGH | Effort: MEDIUM**

Ensure data reliability before downstream analysis:
- Detect stale quotes (last update older than N hours)
- Missing/NaN fields per asset and per source
- Outlier detection on price/volume changes
- Market session anomalies (e.g., extreme spikes)
- Daily health report + alerts

**Implementation notes:**
- Add validation rules + thresholds per asset type
- Persist health checks to DB for auditability
- Expose `/api/health/data` and include in reports

**Files to create/modify:**
- `src/health.py` (new - validation rules)
- `src/exporter.py` (include health summary)
- `src/api.py` (add health endpoint)
- `src/scheduler.py` (run daily health check)

---

### 5. Weekly Email Report 📧
**Priority: MEDIUM | Effort: LOW**

Send summary email every Friday after market close:
- Week's top gainers/losers
- New signals detected
- News sentiment summary
- Portfolio performance (if tracking implemented)

**Implementation notes:**
- Use smtplib or SendGrid/Mailgun for reliability
- Create HTML email template
- Add SMTP_* env vars to docker-compose.yml
- Add to scheduler: run every Friday at 18:30

**Files to create/modify:**
- `src/email_report.py` (new)
- `src/templates/email_weekly.html` (new)
- `src/scheduler.py` (add weekly job)

---

### 6. Deploy to Oracle Cloud Free Tier ☁️
**Priority: HIGH | Effort: LOW**

Free forever VM with:
- 4 OCPUs, 24GB RAM (ARM Ampere)
- Always-on scheduler
- API accessible from anywhere
- Telegram bot running 24/7

**Implementation notes:**
- `docker-compose.prod.yml` already created (no volume mounts, DEV_MODE=0, LOG_LEVEL=WARNING)
- Deploy: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- Setup Caddy or nginx for HTTPS
- Use Cloudflare for DNS/protection
- Backup PostgreSQL with pg_dump to object storage

**Files to create:**
- `deploy/setup.sh` (server setup script)
- `deploy/Caddyfile` (reverse proxy)
- `deploy/README.md` (deployment guide)

---

## 🔮 Future Features (Backlog)

### Static HTML Dashboard 📈
**Priority: LOW | Effort: MEDIUM**

Generate a beautiful self-contained HTML file daily:
- Interactive charts with Chart.js or Plotly
- Sector heatmap
- Top movers cards
- Signal summary
- No server needed - just open the HTML file

**Implementation notes:**
- Use Jinja2 for templating
- Embed all CSS/JS inline for portability
- Generate after each fetch
- Save to `exports/dashboard_YYYY-MM-DD.html`

**Files to create/modify:**
- `src/dashboard.py` (new)
- `src/templates/dashboard.html` (new)
- `src/fetcher.py` (call dashboard generation after fetch)

### 5. ~~Multi-User System with Google OAuth~~ ✅ COMPLETED
**Status: DONE**

Multi-user platform implemented:
- ✅ Google OAuth 2.0 authentication
- ✅ User registration and profile management
- ✅ Personal watchlists and portfolios
- ✅ Privacy: users see only their own data

**Architecture changes required:**
- **Database upgrade**: Migrate from SQLite to PostgreSQL
  - Better concurrent write handling
  - JSONB support for flexible data
  - Row-level security for data isolation
  - Scalability for multiple users
- **Authentication layer**: OAuth 2.0 with Google
  - Libraries: `authlib` or `FastAPI-Users`
  - Session management with JWT tokens
  - Secure cookie handling
- **API changes**: Add user context to all endpoints
  - `/api/users/me` - Get current user profile
  - `/api/users/me/portfolio` - User's portfolio
  - `/api/users/me/watchlist` - User's watchlist
  - Protected routes with OAuth middleware

**Data model:**
```python
class User:
    id: UUID (primary key)
    google_id: str (unique)
    email: str
    name: str
    picture_url: str
    created_at: datetime
    last_login: datetime
    
class Watchlist:
    id: int
    user_id: UUID (foreign key)
    ticker: str
    created_at: datetime
```

**Database choice:**
- ✅ **PostgreSQL** (RECOMMENDED)
  - Free tier: Supabase (500MB), Neon (3GB), Railway
  - Excellent multi-user support
  - ACID compliance, concurrent writes
  - JSON support for flexible schemas
  - Can be containerized with docker-compose
- ⚠️ **SQLite** (NOT recommended for multi-user)
  - Single-writer limitation
  - No built-in user management
  - OK for single-user only

**Docker Compose changes:**
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: b3tracker
      POSTGRES_USER: b3user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  app:
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://b3user:${DB_PASSWORD}@db:5432/b3tracker
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
```

**Files to create/modify:**
- `src/auth.py` (new - OAuth logic)
- `src/users.py` (new - user management)
- `src/database.py` (modify - PostgreSQL instead of SQLite)
- `src/models.py` (add User, Watchlist models)
- `src/api.py` (add protected routes)
- `docker-compose.yml` (add PostgreSQL service)
- `requirements.txt` (add authlib, psycopg2-binary, sqlalchemy[postgresql])
- `alembic/` (new - database migrations)

---

### 6. ~~Portfolio Tracking~~ ✅ COMPLETED
**Status: DONE**

Personal portfolio tracking implemented:
- ✅ Add/edit positions: ticker, quantity, avg price, date
- ✅ Calculate total return, IRR, profit/loss
- ✅ Dividend tracking and yield calculation
- ✅ Multi-portfolio support per user
- [ ] Compare vs IBOV/S&P 500 (pending)
- [ ] Historical performance charts (pending — requires frontend)

**Data model:**
```python
class Portfolio:
    id: int
    user_id: UUID (foreign key to User)
    name: str  # e.g., "Main Portfolio", "Long-term", "Day Trading"
    created_at: datetime
    
class Position:
    id: int
    portfolio_id: int (foreign key)
    ticker: str
    quantity: float
    avg_price: float  # in BRL
    purchase_date: date
    notes: str (optional)
    
class Transaction:
    id: int
    portfolio_id: int (foreign key)
    ticker: str
    type: buy | sell | dividend
    quantity: float
    price: float  # in BRL
    fees: float
    date: datetime
    notes: str (optional)
```

**API endpoints:**
- `POST /api/portfolio` - Create portfolio
- `GET /api/portfolio/{id}` - Get portfolio details
- `POST /api/portfolio/{id}/positions` - Add position
- `PUT /api/portfolio/{id}/positions/{position_id}` - Update position
- `DELETE /api/portfolio/{id}/positions/{position_id}` - Remove position
- `POST /api/portfolio/{id}/transactions` - Add transaction
- `GET /api/portfolio/{id}/performance` - Calculate returns

**Files to create/modify:**
- `src/portfolio.py` (new - portfolio logic)
- `src/models.py` (add Portfolio, Position, Transaction)
- `src/api.py` (add portfolio endpoints)
- Frontend: Portfolio dashboard page

---

### 7. Backtesting Engine 🧪
**Priority: LOW | Effort: HIGH**

Test signal effectiveness historically:
- Requires historical data accumulation (run for 6+ months first)
- Calculate win rate of each signal type
- Sharpe ratio if followed signals

---

### 8. Graham Valuation Multiples 📐
**Priority: LOW | Effort: LOW**

Add Benjamin Graham valuation:
- Graham Number: √(22.5 × EPS × Book Value)
- Graham Multiple: P/E × P/B < 22.5
- Margin of Safety calculation

**Files to modify:**
- `src/fetcher.py` (add calculations)
- `src/models.py` (add fields)

---

### 9. Sector Correlation Matrix 🔗
**Priority: LOW | Effort: MEDIUM**

Identify correlated assets:
- Calculate 30-day rolling correlation
- Heatmap visualization
- Alert on unusual correlation breaks

---

### 10. Insider Trading Alerts 👔
**Priority: LOW | Effort: HIGH**

Monitor CVM filings for insider transactions:
- Scrape CVM website or use API
- Alert on significant insider buys/sells

---

## 🏗️ Architecture Notes

### Current Flow
```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────┬─────────────┬─────────────────────────────┤
│    app      │    api      │         runner              │
│  (scheduler)│  (FastAPI)  │         (CLI)               │
└──────┬──────┴──────┬──────┴─────────────────────────────┘
       │             │
       ▼             │
┌──────────────┐     │
│ fetch_all_   │     │
│ quotes()     │     │
│ (parallel)   │     │
└──────┬───────┘     │
       │             │
       ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                   │
│                    (db:5432/b3tracker)                  │
└─────────────────────────────────────────────────────────┘
```

### Proposed Flow with Alerts
```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├────────┬────────┬────────┬────────┬─────────────────────┤
│  app   │  api   │  bot   │ runner │                     │
└───┬────┴───┬────┴───┬────┴────────┘                     │
    │        │        │                                    │
    ▼        │        │                                    │
fetch_all    │        │                                    │
    │        │        │                                    │
    ▼        │        │                                    │
┌─────────┐  │        │                                    │
│ Postgres│◄─┘        │                                    │
└────┬────┘           │                                    │
     │                │                                    │
     ▼                │                                    │
┌─────────┐           │                                    │
│ alerts  │───────────┘                                    │
│ check   │──────────► Telegram                            │
└─────────┘──────────► Email (weekly)                      │
```

---

## 📝 Session Continuation Prompt

Use this prompt to continue development:

```
I'm working on B3 Tracker, a stock market tracking application.

Current state (v1.1 — 2026-02-05):
- 128 assets (101 BR + 20 US stocks + 4 commodities + 2 crypto)
- Parallel fetch (~48s for all)
- Polymarket sentiment integration
- Technical indicators, fundamentals, news sentiment
- REST API with FastAPI (36 authenticated endpoints)
- Docker Compose setup (dev + production)
- Multi-user with Google OAuth 2.0
- Portfolio tracking with P&L, dividends, IRR
- 173 tests (pytest), 66.6% coverage
- Unified signal detection (src/signals.py)
- Structured logging (src/logger.py)

Check ROADMAP.md for detailed feature plans.

I want to work on: [FEATURE NAME]
```

---

## 🔧 Development Commands

```bash
# Fetch data once
docker compose run --rm runner python src/main.py --once

# Start API
docker compose up -d api

# View signals
docker compose run --rm runner python src/main.py --signals

# Generate reports
docker compose run --rm runner python src/main.py --report

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Deploy to production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Test API
curl http://localhost:8000/api/quotes/PETR4
curl http://localhost:8000/api/signals
```

---

*Last updated: 2026-02-05*
