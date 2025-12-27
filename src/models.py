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
