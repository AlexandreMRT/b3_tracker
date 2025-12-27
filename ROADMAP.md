# B3 Tracker - Roadmap & Future Plans

> This file is structured for AI consumption. Use it to continue development in future sessions.

## 📊 Current State (v1.0)

### Implemented Features
- [x] 104 assets tracked (77 BR stocks, 20 US stocks, 4 commodities, 2 crypto)
- [x] Parallel fetch with ThreadPoolExecutor (8 workers, ~30s for all assets)
- [x] Technical indicators: RSI-14, MA50, MA200, golden/death cross
- [x] Fundamental data: P/E, P/B, dividend yield, beta, ROE, market cap
- [x] Trading signals: 10 types (oversold, overbought, trends, volume spikes)
- [x] News sentiment: Bilingual PT-BR (Google News RSS) + EN (yfinance)
- [x] VADER with custom Portuguese financial lexicon
- [x] Benchmark comparison: vs IBOV and S&P 500
- [x] Dual currency: All prices in BRL and USD
- [x] REST API: FastAPI with Swagger UI (port 8000)
- [x] Reports: Human (Markdown) + AI (JSON) consolidated reports
- [x] Docker Compose: app (scheduler), api (REST), runner (CLI)

### Tech Stack
- Python 3.11
- SQLite with SQLAlchemy 2.0
- yfinance for market data
- FastAPI + uvicorn for REST API
- NLTK VADER for sentiment analysis
- feedparser for Google News RSS
- Docker Compose for orchestration

---

## 🎯 Priority Features (Next Up)

### 1. Telegram Bot 🔔
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

### 2. Weekly Email Report 📧
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

### 3. Static HTML Dashboard 📈
**Priority: MEDIUM | Effort: MEDIUM**

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

---

### 4. Deploy to Oracle Cloud Free Tier ☁️
**Priority: HIGH | Effort: LOW**

Free forever VM with:
- 4 OCPUs, 24GB RAM (ARM Ampere)
- Always-on scheduler
- API accessible from anywhere
- Telegram bot running 24/7

**Implementation notes:**
- Create `deploy/` folder with scripts
- Use docker-compose in production mode
- Setup Caddy or nginx for HTTPS
- Use Cloudflare for DNS/protection
- Backup SQLite to object storage

**Files to create:**
- `deploy/setup.sh` (server setup script)
- `deploy/docker-compose.prod.yml` (production config)
- `deploy/Caddyfile` (reverse proxy)
- `deploy/README.md` (deployment guide)

---

## 🔮 Future Features (Backlog)

### 5. Portfolio Tracking 💼
**Priority: MEDIUM | Effort: HIGH**

Track personal portfolio:
- Add positions: ticker, quantity, avg price, date
- Calculate total return, IRR
- Compare vs IBOV/S&P 500
- Dividend tracking

**Data model:**
```python
class Position:
    ticker: str
    quantity: float
    avg_price: float
    purchase_date: date
    
class Transaction:
    ticker: str
    type: buy | sell | dividend
    quantity: float
    price: float
    date: datetime
```

---

### 6. Backtesting Engine 🧪
**Priority: LOW | Effort: HIGH**

Test signal effectiveness historically:
- Requires historical data accumulation (run for 6+ months first)
- Calculate win rate of each signal type
- Sharpe ratio if followed signals

---

### 7. Graham Valuation Multiples 📐
**Priority: LOW | Effort: LOW**

Add Benjamin Graham valuation:
- Graham Number: √(22.5 × EPS × Book Value)
- Graham Multiple: P/E × P/B < 22.5
- Margin of Safety calculation

**Files to modify:**
- `src/fetcher.py` (add calculations)
- `src/models.py` (add fields)

---

### 8. Sector Correlation Matrix 🔗
**Priority: LOW | Effort: MEDIUM**

Identify correlated assets:
- Calculate 30-day rolling correlation
- Heatmap visualization
- Alert on unusual correlation breaks

---

### 9. Insider Trading Alerts 👔
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
│                    SQLite Database                       │
│                    (data/cotacoes.db)                   │
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
│ SQLite  │◄─┘        │                                    │
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

Current state:
- 104 assets (BR stocks, US stocks, commodities, crypto)
- Parallel fetch (~30s for all)
- Technical indicators, fundamentals, news sentiment
- REST API with FastAPI
- Docker Compose setup

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

# Test API
curl http://localhost:8000/api/quotes/PETR4
curl http://localhost:8000/api/signals
```

---

*Last updated: 2025-12-27*
