"""
Configuração do banco de dados SQLite
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Caminho do banco de dados
DB_PATH = os.environ.get("DB_PATH", "/app/data/cotacoes.db")

# Criar engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

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
    from models import Asset, Quote  # Import aqui para evitar circular import
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado!")
