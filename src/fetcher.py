"""
Módulo para buscar cotações usando yfinance
"""
import yfinance as yf
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from assets import get_all_assets, IBOVESPA_STOCKS, COMMODITIES, CRYPTO, CURRENCY, US_STOCKS
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


def calculate_change_percent(current: float, previous: float) -> Optional[float]:
    """Calcula a variação percentual entre dois preços"""
    if previous and previous > 0:
        return ((current - previous) / previous) * 100
    return None


def get_historical_price(hist_data, target_date: date) -> Optional[float]:
    """Obtém o preço de fechamento mais próximo de uma data alvo"""
    if hist_data.empty:
        return None
    
    # Converter índice para dates
    hist_dates = hist_data.index.date if hasattr(hist_data.index, 'date') else hist_data.index
    
    # Procurar a data alvo ou a mais próxima anterior
    for i in range(len(hist_data) - 1, -1, -1):
        if hist_data.index[i].date() <= target_date:
            return float(hist_data['Close'].iloc[i])
    
    return None


def fetch_quote_with_history(ticker_symbol: str) -> Optional[dict]:
    """
    Busca a cotação de um ativo com dados históricos para comparação
    
    Returns:
        dict com dados da cotação atual + preços históricos ou None se falhar
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Buscar dados máximos para cobrir todas as comparações (5Y e ALL)
        hist = ticker.history(period="max")
        
        if hist.empty:
            print(f"⚠️ Sem dados para {ticker_symbol}")
            return None
        
        latest = hist.iloc[-1]
        today = hist.index[-1].date()
        
        # Calcular datas de referência
        date_1d = today - timedelta(days=1)
        date_1w = today - timedelta(weeks=1)
        date_1m = today - timedelta(days=30)
        date_ytd = date(today.year, 1, 1)
        date_5y = today - timedelta(days=5*365)
        
        # Obter preços históricos
        price_1d = get_historical_price(hist, date_1d)
        price_1w = get_historical_price(hist, date_1w)
        price_1m = get_historical_price(hist, date_1m)
        price_ytd = get_historical_price(hist, date_ytd)
        price_5y = get_historical_price(hist, date_5y)
        
        # Primeiro preço disponível (all-time)
        price_all = float(hist['Close'].iloc[0]) if len(hist) > 0 else None
        
        current_price = float(latest['Close'])
        
        return {
            "ticker": ticker_symbol,
            "open": float(latest.get('Open', 0)) if latest.get('Open') else None,
            "high": float(latest.get('High', 0)) if latest.get('High') else None,
            "low": float(latest.get('Low', 0)) if latest.get('Low') else None,
            "close": current_price,
            "volume": float(latest.get('Volume', 0)) if latest.get('Volume') else None,
            "date": hist.index[-1].to_pydatetime().replace(tzinfo=None),
            # Preços históricos
            "price_1d": price_1d,
            "price_1w": price_1w,
            "price_1m": price_1m,
            "price_ytd": price_ytd,
            "price_5y": price_5y,
            "price_all": price_all,
            # Variações calculadas
            "change_1d": calculate_change_percent(current_price, price_1d),
            "change_1w": calculate_change_percent(current_price, price_1w),
            "change_1m": calculate_change_percent(current_price, price_1m),
            "change_ytd": calculate_change_percent(current_price, price_ytd),
            "change_5y": calculate_change_percent(current_price, price_5y),
            "change_all": calculate_change_percent(current_price, price_all),
        }
        
    except Exception as e:
        print(f"❌ Erro ao buscar {ticker_symbol}: {e}")
        return None


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
    """Salva uma cotação no banco de dados com dados históricos"""
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
        # Atualizar campos históricos
        existing.change_1d = quote_data.get("change_1d")
        existing.change_1w = quote_data.get("change_1w")
        existing.change_1m = quote_data.get("change_1m")
        existing.change_ytd = quote_data.get("change_ytd")
        existing.price_1d_ago = quote_data.get("price_1d")
        existing.price_1w_ago = quote_data.get("price_1w")
        existing.price_1m_ago = quote_data.get("price_1m")
        existing.price_ytd = quote_data.get("price_ytd")
        existing.price_5y_ago = quote_data.get("price_5y")
        existing.price_all_time = quote_data.get("price_all")
        existing.change_5y = quote_data.get("change_5y")
        existing.change_all = quote_data.get("change_all")
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
            # Campos históricos
            change_1d=quote_data.get("change_1d"),
            change_1w=quote_data.get("change_1w"),
            change_1m=quote_data.get("change_1m"),
            change_ytd=quote_data.get("change_ytd"),
            price_1d_ago=quote_data.get("price_1d"),
            price_1w_ago=quote_data.get("price_1w"),
            price_1m_ago=quote_data.get("price_1m"),
            price_ytd=quote_data.get("price_ytd"),
            price_5y_ago=quote_data.get("price_5y"),
            price_all_time=quote_data.get("price_all"),
            change_5y=quote_data.get("change_5y"),
            change_all=quote_data.get("change_all"),
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
        
        # Buscar ações brasileiras (preço nativo em BRL, calcular USD)
        print("📈 Buscando ações do Ibovespa...")
        for ticker, info in IBOVESPA_STOCKS.items():
            quote_data = fetch_quote_with_history(ticker)
            if quote_data:
                price_brl = quote_data["close"]
                price_usd = price_brl / usd_brl  # Converter BRL para USD
                asset = get_or_create_asset(db, ticker, info, "stock")
                save_quote(db, asset, quote_data, price_brl, price_usd)
                success_count += 1
            else:
                error_count += 1
        
        # Buscar ações americanas (preço nativo em USD, calcular BRL)
        print("\n🇺🇸 Buscando ações americanas...")
        for ticker, info in US_STOCKS.items():
            quote_data = fetch_quote_with_history(ticker)
            if quote_data:
                price_usd = quote_data["close"]
                price_brl = price_usd * usd_brl  # Converter USD para BRL
                asset = get_or_create_asset(db, ticker, info, "us_stock")
                save_quote(db, asset, quote_data, price_brl, price_usd)
                success_count += 1
            else:
                error_count += 1
        
        # Buscar commodities (converter USD para BRL)
        print("\n🥇 Buscando commodities...")
        for ticker, info in COMMODITIES.items():
            quote_data = fetch_quote_with_history(ticker)
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
            quote_data = fetch_quote_with_history(ticker)
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
            quote_data = fetch_quote_with_history(ticker)
            if quote_data:
                asset = get_or_create_asset(db, ticker, info, "currency")
                # Dólar: preço já é em BRL, USD é sempre 1
                save_quote(db, asset, quote_data, quote_data["close"], 1.0)
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
