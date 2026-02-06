"""
Shared test fixtures for B3 Tracker.

Provides:
- In-memory SQLite database for fast isolated tests
- Pre-populated test data (assets, quotes, users, portfolios)
- FastAPI TestClient with auth helpers
"""
import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Set test environment BEFORE any src imports.
# database.py reads DATABASE_URL at import time; we must NOT set it so the
# module falls into the SQLite branch.  We point DB_PATH at a temp file that
# will be created by the module (but we never actually use that engine — we
# create our own in-memory engine below).
if "DATABASE_URL" in os.environ:
    del os.environ["DATABASE_URL"]
os.environ["DB_PATH"] = ":memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from sqlalchemy import create_engine, event, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# We need to patch DATABASE_URL *before* importing database module so it
# creates the engine pointing at our test DB.  But for unit tests we
# simply construct our own engine and override the session.

from database import Base  # noqa: E402
from models import (  # noqa: E402
    Asset, Quote, User, Watchlist,
    Portfolio, Position, Transaction, TransactionType,
)


# ---------------------------------------------------------------------------
# SQLite UUID compatibility
# ---------------------------------------------------------------------------
# PostgreSQL has a native UUID column type.  SQLite doesn't, and SQLAlchemy's
# UUID type adapter breaks when it receives a plain string (no .hex attr).
# We monkey-patch the UUID columns to store as CHAR(36) strings on SQLite.

from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # noqa: E402

def _patch_uuid_columns_for_sqlite():
    """Replace PostgreSQL UUID columns with String(36) for SQLite compat."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_UUID):
                column.type = String(36)

_patch_uuid_columns_for_sqlite()


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _engine():
    """Create a single in-memory SQLite engine for the whole test session.

    Uses StaticPool so that every Session / connection shares the same
    underlying SQLite database – this is required for in-memory SQLite,
    where each new connection would otherwise get its own empty database.
    """
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign-key enforcement in SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(_engine):
    """
    Provide a clean database session for each test.
    Tables are recreated each time so tests are fully isolated, even when
    the code under test calls session.commit() (which SQLite savepoints
    cannot easily roll back).
    """
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)

    Session = sessionmaker(bind=_engine)
    session = Session()

    yield session

    session.close()


# ---------------------------------------------------------------------------
# Seed data helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture()
def sample_user(db_session):
    """Create a test user and return it."""
    user = User(
        id=TEST_USER_ID,
        google_id="google_test_123",
        email="test@example.com",
        name="Test User",
        picture_url=None,
        default_currency="BRL",
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def sample_assets(db_session):
    """Create a small set of test assets."""
    assets = [
        Asset(ticker="PETR4.SA", name="Petrobras PN", sector="Petróleo", asset_type="stock"),
        Asset(ticker="VALE3.SA", name="Vale ON", sector="Mineração", asset_type="stock"),
        Asset(ticker="AAPL", name="Apple Inc", sector="Technology", asset_type="us_stock"),
        Asset(ticker="BTC-USD", name="Bitcoin USD", sector="Crypto", asset_type="crypto"),
        Asset(ticker="USDBRL=X", name="Dólar/Real", sector="Moedas", asset_type="currency"),
    ]
    for a in assets:
        db_session.add(a)
    db_session.commit()
    return {a.ticker: a for a in assets}


@pytest.fixture()
def sample_quotes(db_session, sample_assets):
    """Create realistic quotes for each test asset."""
    now = datetime.now(timezone.utc)
    quotes = []
    quote_data = {
        "PETR4.SA": dict(
            price_brl=38.50, price_usd=6.21, open_price=38.00,
            high_price=39.00, low_price=37.80, volume=45_000_000,
            change_1d=1.85, change_1w=3.20, change_1m=-2.10, change_ytd=12.50,
            rsi_14=42.5, ma_50=37.20, ma_200=35.80,
            above_ma_50=1, above_ma_200=1, ma_50_above_200=1,
            week_52_high=42.00, week_52_low=28.50, pct_from_52w_high=-8.33,
            pe_ratio=5.2, pb_ratio=1.1, dividend_yield=8.5, beta=1.3,
            signal_golden_cross=1, signal_death_cross=0,
            signal_rsi_oversold=0, signal_rsi_overbought=0,
            signal_52w_high=0, signal_52w_low=0, signal_volume_spike=0,
            signal_summary="bullish",
            volatility_30d=2.1, avg_volume_20d=40_000_000, volume_ratio=1.12,
            news_sentiment_pt=0.35, news_sentiment_en=0.20,
            news_sentiment_combined=0.28, news_count_pt=5, news_count_en=3,
            news_headline_pt="Petrobras anuncia dividendos recordes",
            news_headline_en="Petrobras raises dividend forecast",
            news_sentiment_label="positive",
        ),
        "VALE3.SA": dict(
            price_brl=62.30, price_usd=10.05, open_price=63.00,
            high_price=63.50, low_price=61.80, volume=30_000_000,
            change_1d=-1.10, change_1w=-2.50, change_1m=-5.30, change_ytd=-8.20,
            rsi_14=28.0, ma_50=65.00, ma_200=67.50,
            above_ma_50=0, above_ma_200=0, ma_50_above_200=0,
            week_52_high=78.00, week_52_low=58.00, pct_from_52w_high=-20.13,
            pe_ratio=4.8, pb_ratio=1.4, dividend_yield=9.2, beta=1.1,
            signal_golden_cross=0, signal_death_cross=1,
            signal_rsi_oversold=1, signal_rsi_overbought=0,
            signal_52w_high=0, signal_52w_low=0, signal_volume_spike=0,
            signal_summary="bearish",
            volatility_30d=2.8, avg_volume_20d=28_000_000, volume_ratio=1.07,
            news_sentiment_pt=-0.25, news_sentiment_en=-0.10,
            news_sentiment_combined=-0.18, news_count_pt=4, news_count_en=2,
            news_headline_pt="Vale enfrenta queda de minério",
            news_headline_en="Iron ore prices pressure Vale shares",
            news_sentiment_label="negative",
        ),
        "AAPL": dict(
            price_brl=1120.00, price_usd=180.50, open_price=179.00,
            high_price=181.00, low_price=178.50, volume=55_000_000,
            change_1d=0.84, change_1w=2.10, change_1m=5.40, change_ytd=8.90,
            rsi_14=58.0, ma_50=175.00, ma_200=168.00,
            above_ma_50=1, above_ma_200=1, ma_50_above_200=1,
            week_52_high=199.00, week_52_low=150.00, pct_from_52w_high=-9.30,
            pe_ratio=28.5, pb_ratio=45.0, dividend_yield=0.55, beta=1.2,
            signal_golden_cross=1, signal_death_cross=0,
            signal_rsi_oversold=0, signal_rsi_overbought=0,
            signal_52w_high=0, signal_52w_low=0, signal_volume_spike=0,
            signal_summary="bullish",
            volatility_30d=1.5, avg_volume_20d=50_000_000, volume_ratio=1.10,
            news_sentiment_pt=None, news_sentiment_en=0.42,
            news_sentiment_combined=0.42, news_count_pt=0, news_count_en=6,
            news_headline_pt=None,
            news_headline_en="Apple Vision Pro sales beat expectations",
            news_sentiment_label="positive",
        ),
        "BTC-USD": dict(
            price_brl=620_000.00, price_usd=100_000.00, open_price=99_000.00,
            high_price=101_500.00, low_price=98_500.00, volume=25_000_000_000,
            change_1d=1.01, change_1w=4.50, change_1m=12.30, change_ytd=25.00,
            rsi_14=65.0, ma_50=95_000.00, ma_200=80_000.00,
            above_ma_50=1, above_ma_200=1, ma_50_above_200=1,
            week_52_high=108_000.00, week_52_low=45_000.00, pct_from_52w_high=-7.41,
            pe_ratio=None, pb_ratio=None, dividend_yield=None, beta=None,
            signal_golden_cross=1, signal_death_cross=0,
            signal_rsi_oversold=0, signal_rsi_overbought=0,
            signal_52w_high=0, signal_52w_low=0, signal_volume_spike=0,
            signal_summary="bullish",
            volatility_30d=3.5, avg_volume_20d=22_000_000_000, volume_ratio=1.14,
            news_sentiment_pt=None, news_sentiment_en=0.30,
            news_sentiment_combined=0.30, news_count_pt=0, news_count_en=8,
            news_headline_pt=None,
            news_headline_en="Bitcoin hits $100K milestone again",
            news_sentiment_label="positive",
        ),
        "USDBRL=X": dict(
            price_brl=6.20, price_usd=1.00, open_price=6.18,
            high_price=6.22, low_price=6.16, volume=0,
            change_1d=0.32, change_1w=0.80, change_1m=1.20, change_ytd=2.50,
            rsi_14=55.0, ma_50=6.10, ma_200=5.90,
            above_ma_50=1, above_ma_200=1, ma_50_above_200=1,
            week_52_high=6.40, week_52_low=4.85, pct_from_52w_high=-3.12,
            pe_ratio=None, pb_ratio=None, dividend_yield=None, beta=None,
            signal_golden_cross=1, signal_death_cross=0,
            signal_rsi_oversold=0, signal_rsi_overbought=0,
            signal_52w_high=0, signal_52w_low=0, signal_volume_spike=0,
            signal_summary="neutral",
            volatility_30d=0.8, avg_volume_20d=0, volume_ratio=0,
            news_sentiment_pt=None, news_sentiment_en=None,
            news_sentiment_combined=None, news_count_pt=0, news_count_en=0,
            news_headline_pt=None, news_headline_en=None,
            news_sentiment_label=None,
        ),
    }

    for ticker, data in quote_data.items():
        asset = sample_assets[ticker]
        q = Quote(asset_id=asset.id, quote_date=now, fetched_at=now, **data)
        db_session.add(q)
        quotes.append(q)

    db_session.commit()
    return quotes


@pytest.fixture()
def sample_portfolio(db_session, sample_user):
    """Create a test portfolio with some positions and transactions."""
    portfolio = Portfolio(
        user_id=sample_user.id,
        name="Test Portfolio",
        description="For testing",
        is_default=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(portfolio)
    db_session.commit()

    # Add a BUY transaction + position for PETR4
    tx1 = Transaction(
        portfolio_id=portfolio.id,
        ticker="PETR4.SA",
        transaction_type=TransactionType.BUY,
        quantity=100,
        price_brl=35.00,
        total_brl=3500.00,
        fees_brl=0.0,
        transaction_date=datetime.now(timezone.utc) - timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(tx1)

    pos1 = Position(
        portfolio_id=portfolio.id,
        ticker="PETR4.SA",
        quantity=100,
        avg_price_brl=35.00,
        first_purchase_date=datetime.now(timezone.utc) - timedelta(days=30),
        last_transaction_date=datetime.now(timezone.utc) - timedelta(days=30),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(pos1)

    # Add a BUY transaction + position for VALE3
    tx2 = Transaction(
        portfolio_id=portfolio.id,
        ticker="VALE3.SA",
        transaction_type=TransactionType.BUY,
        quantity=50,
        price_brl=68.00,
        total_brl=3400.00,
        fees_brl=0.0,
        transaction_date=datetime.now(timezone.utc) - timedelta(days=15),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(tx2)

    pos2 = Position(
        portfolio_id=portfolio.id,
        ticker="VALE3.SA",
        quantity=50,
        avg_price_brl=68.00,
        first_purchase_date=datetime.now(timezone.utc) - timedelta(days=15),
        last_transaction_date=datetime.now(timezone.utc) - timedelta(days=15),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(pos2)

    # Add a dividend transaction
    tx3 = Transaction(
        portfolio_id=portfolio.id,
        ticker="PETR4.SA",
        transaction_type=TransactionType.DIVIDEND,
        quantity=100,
        price_brl=0.50,
        total_brl=50.00,
        fees_brl=0.0,
        transaction_date=datetime.now(timezone.utc) - timedelta(days=5),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(tx3)

    db_session.commit()
    return portfolio


# ---------------------------------------------------------------------------
# FastAPI TestClient fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_client(_engine, db_session, sample_user):
    """
    Provide a FastAPI TestClient with all DB access redirected to the test
    in-memory SQLite, including:
    - Depends(get_db) endpoints
    - Direct SessionLocal() calls in api.py, auth.py, etc.
    - Auth middleware (get_current_user)
    """
    from fastapi.testclient import TestClient
    from auth import create_access_token, get_current_user
    from database import get_db

    from api import app

    # 1) Override get_db for Depends()-based endpoints
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    # 2) Override get_current_user so it uses our test session
    #    (avoids the auth middleware querying the wrong DB)
    def _override_get_current_user():
        return sample_user

    app.dependency_overrides[get_current_user] = _override_get_current_user

    # 3) Patch SessionLocal in EVERY module that imported it directly so that
    #    endpoints using `db = SessionLocal()` also hit the test engine.
    TestSessionLocal = sessionmaker(bind=_engine)
    import database as db_module
    import api as api_module

    _orig_db_SL = db_module.SessionLocal
    _orig_api_SL = api_module.SessionLocal

    db_module.SessionLocal = TestSessionLocal
    api_module.SessionLocal = TestSessionLocal

    # Create a valid token for the test user
    token = create_access_token(data={"sub": str(sample_user.id)})

    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"

    yield client

    app.dependency_overrides.clear()
    db_module.SessionLocal = _orig_db_SL
    api_module.SessionLocal = _orig_api_SL


@pytest.fixture()
def unauthenticated_client(_engine, db_session):
    """
    Provide a FastAPI TestClient **without** auth, so that endpoints
    requiring authentication correctly reject the request.
    """
    from fastapi.testclient import TestClient
    from database import get_db
    from api import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    TestSessionLocal = sessionmaker(bind=_engine)
    import database as db_module
    import api as api_module

    _orig_db_SL = db_module.SessionLocal
    _orig_api_SL = api_module.SessionLocal
    db_module.SessionLocal = TestSessionLocal
    api_module.SessionLocal = TestSessionLocal

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    db_module.SessionLocal = _orig_db_SL
    api_module.SessionLocal = _orig_api_SL
