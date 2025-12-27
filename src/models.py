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
