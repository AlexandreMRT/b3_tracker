"""
Modelos do banco de dados
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Asset(Base):
    """Representa um ativo (ação, commodity, crypto)"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)
    asset_type = Column(String(20), nullable=False)  # stock, commodity, crypto, currency
    unit = Column(String(20), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    quote_date = Column(DateTime, nullable=False)  # Data da cotação
    fetched_at = Column(DateTime, default=datetime.utcnow)  # Quando foi buscado
    
    # Relacionamento com ativo
    asset = relationship("Asset", back_populates="quotes")
    
    # Índice único para evitar duplicatas no mesmo dia
    __table_args__ = (
        UniqueConstraint('asset_id', 'quote_date', name='unique_asset_date'),
    )
    
    def __repr__(self):
        return f"<Quote(asset_id={self.asset_id}, price_brl={self.price_brl}, date={self.quote_date})>"
