"""
Modelos do banco de dados
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now, compatible with SQLAlchemy defaults."""
    return datetime.now(timezone.utc)


class Asset(Base):
    """Representa um ativo (ação, commodity, crypto)"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)
    asset_type = Column(String(20), nullable=False)  # stock, commodity, crypto, currency
    unit = Column(String(20), default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relacionamento com cotações
    quotes = relationship("Quote", back_populates="asset", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Asset(ticker='{self.ticker}', name='{self.name}')>"


class Quote(Base):
    """Representa uma cotação de um ativo em um determinado momento"""
    __tablename__ = "quotes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    
    price_usd = Column(Float, nullable=True)  # Preço em USD (todos os ativos)
    price_brl = Column(Float, nullable=False)  # Preço em BRL (todos os ativos)
    
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    
    # Variações percentuais históricas (BRL)
    change_1d = Column(Float, nullable=True)   # Variação vs. dia anterior
    change_1w = Column(Float, nullable=True)   # Variação vs. 1 semana
    change_1m = Column(Float, nullable=True)   # Variação vs. 1 mês
    change_ytd = Column(Float, nullable=True)  # Variação year-to-date
    change_5y = Column(Float, nullable=True)   # Variação vs. 5 anos
    change_all = Column(Float, nullable=True)  # Variação desde o início (all-time)
    
    # Preços históricos para referência
    price_1d_ago = Column(Float, nullable=True)
    price_1w_ago = Column(Float, nullable=True)
    price_1m_ago = Column(Float, nullable=True)
    price_ytd = Column(Float, nullable=True)   # Preço no início do ano
    price_5y_ago = Column(Float, nullable=True) # Preço há 5 anos
    price_all_time = Column(Float, nullable=True) # Primeiro preço disponível
    
    # === FUNDAMENTAL DATA (for AI analysis) ===
    market_cap = Column(Float, nullable=True)        # Market capitalization
    pe_ratio = Column(Float, nullable=True)          # Price-to-Earnings ratio
    forward_pe = Column(Float, nullable=True)        # Forward P/E ratio
    pb_ratio = Column(Float, nullable=True)          # Price-to-Book ratio
    dividend_yield = Column(Float, nullable=True)    # Dividend yield (%)
    eps = Column(Float, nullable=True)               # Earnings per share
    
    # === RISK METRICS ===
    beta = Column(Float, nullable=True)              # Beta vs market
    week_52_high = Column(Float, nullable=True)      # 52-week high price
    week_52_low = Column(Float, nullable=True)       # 52-week low price
    pct_from_52w_high = Column(Float, nullable=True) # % distance from 52w high
    
    # === TECHNICAL INDICATORS ===
    ma_50 = Column(Float, nullable=True)             # 50-day moving average
    ma_200 = Column(Float, nullable=True)            # 200-day moving average
    rsi_14 = Column(Float, nullable=True)            # 14-day RSI
    above_ma_50 = Column(Integer, nullable=True)     # 1 if price > MA50, 0 otherwise
    above_ma_200 = Column(Integer, nullable=True)    # 1 if price > MA200, 0 otherwise
    ma_50_above_200 = Column(Integer, nullable=True) # Golden cross indicator
    
    # === FINANCIAL HEALTH ===
    profit_margin = Column(Float, nullable=True)     # Profit margin (%)
    roe = Column(Float, nullable=True)               # Return on Equity (%)
    debt_to_equity = Column(Float, nullable=True)    # Debt/Equity ratio
    
    # === ANALYST DATA ===
    analyst_rating = Column(String(20), nullable=True)  # buy, hold, sell
    target_price = Column(Float, nullable=True)         # Analyst target price
    num_analysts = Column(Integer, nullable=True)       # Number of analysts
    
    # === BENCHMARK COMPARISON ===
    ibov_change_1d = Column(Float, nullable=True)       # Ibovespa 1D change
    ibov_change_1w = Column(Float, nullable=True)       # Ibovespa 1W change
    ibov_change_1m = Column(Float, nullable=True)       # Ibovespa 1M change
    ibov_change_ytd = Column(Float, nullable=True)      # Ibovespa YTD change
    sp500_change_1d = Column(Float, nullable=True)      # S&P500 1D change
    sp500_change_1w = Column(Float, nullable=True)      # S&P500 1W change
    sp500_change_1m = Column(Float, nullable=True)      # S&P500 1M change
    sp500_change_ytd = Column(Float, nullable=True)     # S&P500 YTD change
    vs_ibov_1d = Column(Float, nullable=True)           # Outperformance vs Ibov 1D
    vs_ibov_1m = Column(Float, nullable=True)           # Outperformance vs Ibov 1M
    vs_ibov_ytd = Column(Float, nullable=True)          # Outperformance vs Ibov YTD
    vs_sp500_1d = Column(Float, nullable=True)          # Outperformance vs S&P 1D
    vs_sp500_1m = Column(Float, nullable=True)          # Outperformance vs S&P 1M
    vs_sp500_ytd = Column(Float, nullable=True)         # Outperformance vs S&P YTD
    
    # === SECTOR CONTEXT ===
    sector_avg_pe = Column(Float, nullable=True)        # Sector average P/E
    sector_avg_change_1m = Column(Float, nullable=True) # Sector avg 1M change
    sector_avg_change_ytd = Column(Float, nullable=True)# Sector avg YTD change
    vs_sector_pe = Column(Float, nullable=True)         # P/E vs sector avg (%)
    vs_sector_1m = Column(Float, nullable=True)         # Outperformance vs sector 1M
    vs_sector_ytd = Column(Float, nullable=True)        # Outperformance vs sector YTD
    
    # === TRADING SIGNALS ===
    signal_golden_cross = Column(Integer, nullable=True)  # 1 if MA50 just crossed above MA200
    signal_death_cross = Column(Integer, nullable=True)   # 1 if MA50 just crossed below MA200
    signal_rsi_oversold = Column(Integer, nullable=True)  # 1 if RSI < 30
    signal_rsi_overbought = Column(Integer, nullable=True)# 1 if RSI > 70
    signal_52w_high = Column(Integer, nullable=True)      # 1 if at/near 52w high
    signal_52w_low = Column(Integer, nullable=True)       # 1 if at/near 52w low
    signal_volume_spike = Column(Integer, nullable=True)  # 1 if volume > 2x average
    signal_summary = Column(String(50), nullable=True)    # Overall signal: bullish/bearish/neutral
    
    # === VOLATILITY ===
    volatility_30d = Column(Float, nullable=True)       # 30-day volatility (std dev of returns)
    avg_volume_20d = Column(Float, nullable=True)       # 20-day average volume
    volume_ratio = Column(Float, nullable=True)         # Current volume / avg volume
    
    # === NEWS SENTIMENT ===
    news_sentiment_pt = Column(Float, nullable=True)       # PT-BR sentiment score (-1 to +1)
    news_sentiment_en = Column(Float, nullable=True)       # English sentiment score (-1 to +1)
    news_sentiment_combined = Column(Float, nullable=True) # Combined weighted score
    news_count_pt = Column(Integer, nullable=True)         # Number of PT-BR news articles
    news_count_en = Column(Integer, nullable=True)         # Number of English news articles
    news_headline_pt = Column(String(500), nullable=True)  # Latest PT-BR headline
    news_headline_en = Column(String(500), nullable=True)  # Latest English headline
    news_sentiment_label = Column(String(20), nullable=True)  # positive/negative/neutral
    
    # === POLYMARKET PREDICTION MARKETS ===
    polymarket_score = Column(Float, nullable=True)           # Aggregated sentiment (-1 to +1)
    polymarket_label = Column(String(20), nullable=True)      # bullish/bearish/neutral
    polymarket_confidence = Column(Float, nullable=True)      # Confidence (0-1 based on volume)
    polymarket_market_count = Column(Integer, nullable=True)  # Number of relevant markets
    polymarket_volume = Column(Float, nullable=True)          # Total 24h volume
    polymarket_top_question = Column(String(500), nullable=True)  # Top market question
    polymarket_top_probability = Column(Float, nullable=True)     # Top market probability
    
    quote_date = Column(DateTime, nullable=False)  # Data da cotação
    fetched_at = Column(DateTime, default=_utcnow)  # Quando foi buscado
    
    # Relacionamento com ativo
    asset = relationship("Asset", back_populates="quotes")
    
    # Índice único para evitar duplicatas no mesmo dia
    __table_args__ = (
        UniqueConstraint('asset_id', 'quote_date', name='unique_asset_date'),
    )
    
    def __repr__(self):
        return f"<Quote(asset_id={self.asset_id}, price_brl={self.price_brl}, date={self.quote_date})>"


# === USER MANAGEMENT & AUTHENTICATION ===

class User(Base):
    """Representa um usuário do sistema"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    picture_url = Column(String(500), nullable=True)
    
    # Preferences
    default_currency = Column(String(3), default="BRL")  # BRL or USD
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    last_login = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"


class Watchlist(Base):
    """Representa um ativo sendo observado por um usuário"""
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    
    # Unique constraint: user can't add same ticker twice
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='unique_user_ticker'),
    )
    
    def __repr__(self):
        return f"<Watchlist(user_id={self.user_id}, ticker='{self.ticker}')>"


# === PORTFOLIO TRACKING ===

class TransactionType(enum.Enum):
    """Tipos de transação"""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    BONUS = "bonus"


class Portfolio(Base):
    """Representa um portfólio de investimentos de um usuário"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Integer, default=0)  # 1 if default portfolio
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Portfolio(user_id={self.user_id}, name='{self.name}')>"


class Position(Base):
    """Representa uma posição atual em um portfólio"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    
    # Position details
    quantity = Column(Float, nullable=False)  # Current quantity held
    avg_price_brl = Column(Float, nullable=False)  # Average purchase price in BRL
    first_purchase_date = Column(DateTime, nullable=False)
    last_transaction_date = Column(DateTime, nullable=False)
    
    # Optional tracking
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    
    # Unique constraint: one position per ticker per portfolio
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'ticker', name='unique_portfolio_ticker'),
    )
    
    def __repr__(self):
        return f"<Position(portfolio_id={self.portfolio_id}, ticker='{self.ticker}', quantity={self.quantity})>"


class Transaction(Base):
    """Representa uma transação (compra, venda, dividendo)"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price_brl = Column(Float, nullable=False)  # Price per unit in BRL
    total_brl = Column(Float, nullable=False)  # Total transaction value in BRL
    fees_brl = Column(Float, default=0.0)  # Transaction fees in BRL
    
    # Metadata
    transaction_date = Column(DateTime, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(ticker='{self.ticker}', type={self.transaction_type.value}, quantity={self.quantity}, date={self.transaction_date})>"
