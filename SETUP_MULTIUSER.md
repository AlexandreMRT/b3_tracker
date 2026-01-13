# 🚀 Multi-User & Portfolio Tracking - Setup Guide

## Overview

Your B3 Tracker now supports multi-user authentication with Google OAuth and personal portfolio tracking!

## 🆕 New Features

### 👥 User Authentication
- **Google OAuth 2.0** - Secure login with Google account
- **JWT tokens** - Stateless authentication
- **User profiles** - Name, email, picture from Google

### 📊 Portfolio Tracking
- **Multiple portfolios** - Create separate portfolios (e.g., "Long-term", "Day Trading")
- **Position tracking** - Track quantities, average prices, P&L
- **Transaction history** - Buy, sell, dividends, splits
- **Performance metrics** - Real-time profit/loss calculations
- **Watchlists** - Save favorite tickers for quick access

## 🗄️ Database Migration

### From SQLite to PostgreSQL

**Why PostgreSQL?**
- ✅ Multi-user support with concurrent writes
- ✅ Better data integrity (ACID compliance)
- ✅ Scalable for many users
- ✅ Row-level security

### Setup Steps

#### 1. Create `.env` file

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
# Generate a secure password
DB_PASSWORD=your_secure_password_here

# Generate a secret key with: openssl rand -hex 32
SECRET_KEY=your_generated_secret_key_here

# Get from Google Cloud Console (instructions below)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
```

#### 2. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs:
   - `http://localhost:8000/auth/callback` (development)
   - `https://yourdomain.com/auth/callback` (production)
7. Copy **Client ID** and **Client Secret** to your `.env` file

#### 3. Start Services

```bash
# Build and start all services (PostgreSQL + App + API)
docker compose up -d

# Check logs
docker compose logs -f

# Wait for PostgreSQL to be ready (look for "database system is ready to accept connections")
```

#### 4. Initialize Database

The database will auto-initialize on first run. You should see:
```
✅ Using PostgreSQL: db:5432/b3tracker
✅ Banco de dados inicializado!
```

## 📱 Using the API

### Authentication Flow

1. **Login with Google**
   ```bash
   # Visit in browser:
   http://localhost:8000/auth/login
   
   # After successful login, you'll get:
   {
     "access_token": "eyJhbGc...",
     "token_type": "bearer",
     "user": {...}
   }
   ```

2. **Use the token in requests**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
        http://localhost:8000/auth/me
   ```

### API Endpoints

#### Authentication
- `GET /auth/login` - Start Google OAuth flow
- `GET /auth/callback` - OAuth callback (automatic)
- `GET /auth/me` - Get current user info

#### Watchlist
- `GET /api/watchlist` - Get your watchlist
- `POST /api/watchlist/{ticker}` - Add ticker to watchlist
- `DELETE /api/watchlist/{ticker}` - Remove from watchlist

#### Portfolio Management
- `GET /api/portfolios` - List your portfolios
- `POST /api/portfolios` - Create new portfolio
- `GET /api/portfolios/{id}` - Get portfolio details
- `PUT /api/portfolios/{id}` - Update portfolio
- `DELETE /api/portfolios/{id}` - Delete portfolio

#### Positions & Performance
- `GET /api/portfolios/{id}/positions` - View all positions
- `GET /api/portfolios/{id}/performance` - Calculate portfolio performance

#### Transactions
- `POST /api/portfolios/{id}/transactions` - Add transaction
- `GET /api/portfolios/{id}/transactions` - List transactions
- `DELETE /api/portfolios/{id}/transactions/{txn_id}` - Delete transaction

### Example: Creating a Portfolio

```bash
# 1. Login and get token (use browser for OAuth)
# Visit: http://localhost:8000/auth/login

# 2. Create portfolio
curl -X POST "http://localhost:8000/api/portfolios?name=My Portfolio&description=Long term investments" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 3. Add a buy transaction
curl -X POST "http://localhost:8000/api/portfolios/1/transactions" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{
       "ticker": "PETR4",
       "transaction_type": "buy",
       "quantity": 100,
       "price_brl": 35.50,
       "fees_brl": 10.0,
       "transaction_date": "2026-01-10T10:00:00",
       "notes": "First purchase"
     }'

# 4. View portfolio performance
curl "http://localhost:8000/api/portfolios/1/performance" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🔧 Development

### Testing without OAuth

For development, you can temporarily disable authentication:

1. Comment out `Depends(get_current_user)` in endpoints
2. Or create a test user manually in PostgreSQL

### Database Inspection

```bash
# Connect to PostgreSQL
docker compose exec db psql -U b3user -d b3tracker

# View tables
\dt

# View users
SELECT * FROM users;

# View portfolios
SELECT * FROM portfolios;

# Exit
\q
```

## 🔄 Migrating Existing Data

If you have existing SQLite data and want to migrate:

```bash
# 1. Export from SQLite (before switching to PostgreSQL)
docker compose run --rm runner python src/main.py --export

# 2. Switch to PostgreSQL (update docker-compose.yml)

# 3. Import data manually or keep both databases
# (Market data in SQLite, user data in PostgreSQL)
```

## 🚀 Production Deployment

For production (Oracle Cloud, AWS, etc.):

1. **Use environment variables** (never commit secrets)
2. **Change redirect URI** to your domain
3. **Use strong passwords** for database
4. **Enable HTTPS** (required for OAuth)
5. **Set up database backups**

### Production docker-compose

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
  
  api:
    environment:
      DATABASE_URL: postgresql://b3user:${DB_PASSWORD}@db:5432/b3tracker
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      SECRET_KEY: ${SECRET_KEY}
      OAUTH_REDIRECT_URI: https://yourdomain.com/auth/callback
    restart: always
```

## 📊 Data Models

### User
- `id` (UUID) - Unique identifier
- `google_id` - Google account ID
- `email` - User email
- `name` - Display name
- `picture_url` - Profile picture
- `default_currency` - BRL or USD

### Portfolio
- `id` - Portfolio ID
- `user_id` - Owner
- `name` - Portfolio name
- `description` - Optional description
- `is_default` - Default portfolio flag

### Position
- `ticker` - Stock ticker
- `quantity` - Shares owned
- `avg_price_brl` - Average purchase price
- `first_purchase_date` - When first bought
- `last_transaction_date` - Last activity

### Transaction
- `type` - BUY, SELL, DIVIDEND, SPLIT, BONUS
- `quantity` - Number of shares
- `price_brl` - Price per share
- `total_brl` - Total transaction value
- `fees_brl` - Transaction fees
- `transaction_date` - When it occurred

## 🐛 Troubleshooting

### "Could not connect to database"
- Check if PostgreSQL is running: `docker compose ps`
- Check credentials in `.env` file
- View logs: `docker compose logs db`

### "OAuth error"
- Verify Google OAuth credentials
- Check redirect URI matches Google Console
- Ensure OAuth is enabled for your domain

### "Token expired"
- Tokens expire after 7 days
- Login again to get new token

## 📚 Next Steps

1. **Frontend** - Build a web UI for portfolio management
2. **Mobile app** - React Native or Flutter
3. **Charts** - Add historical performance charts
4. **Alerts** - Email/Telegram alerts for portfolio changes
5. **Tax reports** - Generate tax documents
6. **Export** - Export portfolio to Excel/PDF

## 🤝 Support

Issues? Check:
- [ROADMAP.md](ROADMAP.md) for planned features
- Docker logs: `docker compose logs`
- API docs: http://localhost:8000/docs

Happy tracking! 📈
