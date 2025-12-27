"""
Módulo para buscar cotações usando yfinance
"""
import yfinance as yf
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session

from assets import get_all_assets, IBOVESPA_STOCKS, COMMODITIES, CRYPTO, CURRENCY
from models import Asset, Quote
from database import SessionLocal


def get_usd_brl_rate() -> float:
    """Obtém a cotação atual do dólar em reais"""
    try:
        ticker = yf.Ticker("USDBRL=X")
        # Usar período maior para garantir dados
        data = ticker.history(period="5d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"⚠️ Erro ao buscar cotação USD/BRL: {e}")
    
    # Fallback: valor aproximado
    return 6.20


def fetch_quote(ticker_symbol: str) -> Optional[dict]:
    """
    Busca a cotação de um ativo específico
    
    Returns:
        dict com dados da cotação ou None se falhar
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Use 5d period to handle weekends/holidays when markets are closed
        hist = ticker.history(period="5d")
        
        if hist.empty:
            print(f"⚠️ Sem dados para {ticker_symbol}")
            return None
        
        latest = hist.iloc[-1]
        
        return {
            "ticker": ticker_symbol,
            "open": float(latest.get('Open', 0)) if latest.get('Open') else None,
            "high": float(latest.get('High', 0)) if latest.get('High') else None,
            "low": float(latest.get('Low', 0)) if latest.get('Low') else None,
            "close": float(latest['Close']),
            "volume": float(latest.get('Volume', 0)) if latest.get('Volume') else None,
            "date": hist.index[-1].to_pydatetime().replace(tzinfo=None)
        }
        
    except Exception as e:
        print(f"❌ Erro ao buscar {ticker_symbol}: {e}")
        return None


def get_or_create_asset(db: Session, ticker: str, info: dict, asset_type: str) -> Asset:
    """Obtém ou cria um ativo no banco de dados"""
    asset = db.query(Asset).filter(Asset.ticker == ticker).first()
    
    if not asset:
        asset = Asset(
            ticker=ticker,
            name=info.get("name", "Desconhecido"),
            sector=info.get("sector", "Outro"),
            asset_type=asset_type,
            unit=info.get("unit", "")
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        print(f"✅ Ativo criado: {ticker} - {info.get('name')}")
    
    return asset


def save_quote(db: Session, asset: Asset, quote_data: dict, price_brl: float, price_usd: float = None):
    """Salva uma cotação no banco de dados"""
    quote_date = quote_data["date"].date() if isinstance(quote_data["date"], datetime) else quote_data["date"]
    
    # Verificar se já existe cotação para este ativo nesta data
    existing = db.query(Quote).filter(
        Quote.asset_id == asset.id,
        Quote.quote_date == datetime.combine(quote_date, datetime.min.time())
    ).first()
    
    if existing:
        # Atualizar cotação existente
        existing.price_brl = price_brl
        existing.price_usd = price_usd
        existing.open_price = quote_data.get("open")
        existing.high_price = quote_data.get("high")
        existing.low_price = quote_data.get("low")
        existing.volume = quote_data.get("volume")
        existing.fetched_at = datetime.utcnow()
        print(f"🔄 Atualizado: {asset.ticker} = R$ {price_brl:.2f}")
    else:
        # Criar nova cotação
        quote = Quote(
            asset_id=asset.id,
            price_brl=price_brl,
            price_usd=price_usd,
            open_price=quote_data.get("open"),
            high_price=quote_data.get("high"),
            low_price=quote_data.get("low"),
            volume=quote_data.get("volume"),
            quote_date=datetime.combine(quote_date, datetime.min.time())
        )
        db.add(quote)
        print(f"💰 Salvo: {asset.ticker} = R$ {price_brl:.2f}")
    
    db.commit()


def fetch_all_quotes():
    """Busca e salva cotações de todos os ativos"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print(f"🚀 Iniciando busca de cotações - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Obter cotação do dólar para conversão
        usd_brl = get_usd_brl_rate()
        print(f"💵 Cotação USD/BRL: R$ {usd_brl:.4f}\n")
        
        success_count = 0
        error_count = 0
        
        # Buscar ações brasileiras
        print("📈 Buscando ações do Ibovespa...")
        for ticker, info in IBOVESPA_STOCKS.items():
            quote_data = fetch_quote(ticker)
            if quote_data:
                asset = get_or_create_asset(db, ticker, info, "stock")
                save_quote(db, asset, quote_data, quote_data["close"])
                success_count += 1
            else:
                error_count += 1
        
        # Buscar commodities (converter USD para BRL)
        print("\n🥇 Buscando commodities...")
        for ticker, info in COMMODITIES.items():
            quote_data = fetch_quote(ticker)
            if quote_data:
                price_usd = quote_data["close"]
                price_brl = price_usd * usd_brl
                asset = get_or_create_asset(db, ticker, info, "commodity")
                save_quote(db, asset, quote_data, price_brl, price_usd)
                success_count += 1
            else:
                error_count += 1
        
        # Buscar criptomoedas (converter USD para BRL)
        print("\n₿ Buscando criptomoedas...")
        for ticker, info in CRYPTO.items():
            quote_data = fetch_quote(ticker)
            if quote_data:
                price_usd = quote_data["close"]
                price_brl = price_usd * usd_brl
                asset = get_or_create_asset(db, ticker, info, "crypto")
                save_quote(db, asset, quote_data, price_brl, price_usd)
                success_count += 1
            else:
                error_count += 1
        
        # Salvar cotação do dólar
        print("\n💱 Salvando cotação do dólar...")
        for ticker, info in CURRENCY.items():
            quote_data = fetch_quote(ticker)
            if quote_data:
                asset = get_or_create_asset(db, ticker, info, "currency")
                save_quote(db, asset, quote_data, quote_data["close"])
                success_count += 1
        
        print("\n" + "="*60)
        print(f"✅ Concluído! Sucesso: {success_count} | Erros: {error_count}")
        print("="*60 + "\n")
        
        return success_count, error_count
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    fetch_all_quotes()
