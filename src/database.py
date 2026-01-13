"""
Configuração do banco de dados (PostgreSQL ou SQLite)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Database URL - supports both PostgreSQL and SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", None)

# Se não tiver DATABASE_URL, usa SQLite (fallback para desenvolvimento local)
if not DATABASE_URL:
    DB_PATH = os.environ.get("DB_PATH", "/app/data/cotacoes.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    print(f"⚠️  Using SQLite: {DB_PATH}")
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
else:
    # PostgreSQL configuration
    print(f"✅ Using PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

def get_db():
    """Generator para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa o banco de dados criando as tabelas"""
    from models import (
        Asset, Quote, User, Watchlist, 
        Portfolio, Position, Transaction
    )  # Import all models
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado!")
