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
    
    price_usd = Column(Float, nullable=True)  # Preço em USD (para commodities/crypto)
    price_brl = Column(Float, nullable=False)  # Preço em BRL
    
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    
    change_percent = Column(Float, nullable=True)  # Variação percentual
    
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
