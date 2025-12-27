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


def calculate_rsi(prices, period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return None
    
    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = (-deltas).where(deltas < 0, 0)
    
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def fetch_fundamental_data(ticker: yf.Ticker) -> dict:
    """Fetch fundamental and analyst data from yfinance"""
    try:
        info = ticker.info
        
        # Safe getter for percentages
        def safe_pct(key):
            val = info.get(key)
            if val is not None:
                return val * 100 if val < 1 else val  # Handle if already in %
            return None
        
        return {
            # Fundamentals
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": safe_pct("dividendYield"),
            "eps": info.get("trailingEps"),
            
            # Risk metrics
            "beta": info.get("beta"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            
            # Financial health
            "profit_margin": safe_pct("profitMargins"),
            "roe": safe_pct("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            
            # Analyst data
            "analyst_rating": info.get("recommendationKey"),
            "target_price": info.get("targetMeanPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
        }
    except Exception as e:
        print(f"⚠️ Error fetching fundamentals: {e}")
        return {}


def calculate_technical_indicators(hist, current_price: float) -> dict:
    """Calculate technical indicators from historical data"""
    result = {}
    
    if len(hist) >= 50:
        ma_50 = float(hist['Close'].tail(50).mean())
        result["ma_50"] = ma_50
        result["above_ma_50"] = 1 if current_price > ma_50 else 0
    
    if len(hist) >= 200:
        ma_200 = float(hist['Close'].tail(200).mean())
        result["ma_200"] = ma_200
        result["above_ma_200"] = 1 if current_price > ma_200 else 0
        
        if "ma_50" in result:
            result["ma_50_above_200"] = 1 if result["ma_50"] > ma_200 else 0
    
    # RSI
    rsi = calculate_rsi(hist['Close'])
    if rsi is not None:
        result["rsi_14"] = rsi
    
    # Volatility (30-day standard deviation of daily returns)
    if len(hist) >= 30:
        returns = hist['Close'].pct_change().tail(30)
        result["volatility_30d"] = float(returns.std() * 100)  # As percentage
    
    # Volume analysis
    if len(hist) >= 20 and 'Volume' in hist.columns:
        avg_vol = float(hist['Volume'].tail(20).mean())
        current_vol = float(hist['Volume'].iloc[-1])
        result["avg_volume_20d"] = avg_vol
        if avg_vol > 0:
            result["volume_ratio"] = current_vol / avg_vol
    
    return result


def calculate_signals(quote_data: dict) -> dict:
    """Calculate trading signals based on technical indicators"""
    signals = {}
    
    # RSI signals
    rsi = quote_data.get("rsi_14")
    if rsi is not None:
        signals["signal_rsi_oversold"] = 1 if rsi < 30 else 0
        signals["signal_rsi_overbought"] = 1 if rsi > 70 else 0
    
    # 52-week high/low signals (within 5%)
    pct_from_high = quote_data.get("pct_from_52w_high")
    week_52_high = quote_data.get("week_52_high")
    week_52_low = quote_data.get("week_52_low")
    close = quote_data.get("close")
    
    if pct_from_high is not None:
        signals["signal_52w_high"] = 1 if pct_from_high >= -5 else 0
    
    if week_52_low and close:
        pct_from_low = ((close - week_52_low) / week_52_low) * 100
        signals["signal_52w_low"] = 1 if pct_from_low <= 5 else 0
    
    # Volume spike (2x average)
    volume_ratio = quote_data.get("volume_ratio")
    if volume_ratio is not None:
        signals["signal_volume_spike"] = 1 if volume_ratio >= 2.0 else 0
    
    # Golden/Death cross
    ma_50_above_200 = quote_data.get("ma_50_above_200")
    signals["signal_golden_cross"] = 1 if ma_50_above_200 == 1 else 0
    signals["signal_death_cross"] = 1 if ma_50_above_200 == 0 else 0
    
    # Overall signal summary
    bullish_count = sum([
        signals.get("signal_rsi_oversold", 0),
        signals.get("signal_52w_low", 0),
        signals.get("signal_golden_cross", 0),
        1 if quote_data.get("above_ma_50") == 1 else 0,
        1 if quote_data.get("above_ma_200") == 1 else 0,
    ])
    
    bearish_count = sum([
        signals.get("signal_rsi_overbought", 0),
        signals.get("signal_52w_high", 0),
        signals.get("signal_death_cross", 0),
        1 if quote_data.get("above_ma_50") == 0 else 0,
        1 if quote_data.get("above_ma_200") == 0 else 0,
    ])
    
    if bullish_count >= 3 and bullish_count > bearish_count:
        signals["signal_summary"] = "bullish"
    elif bearish_count >= 3 and bearish_count > bullish_count:
        signals["signal_summary"] = "bearish"
    else:
        signals["signal_summary"] = "neutral"
    
    return signals


# Global cache for benchmark data (fetched once per run)
_benchmark_cache = {}


def fetch_benchmark_data() -> dict:
    """Fetch Ibovespa and S&P 500 historical changes (cached)"""
    global _benchmark_cache
    
    if _benchmark_cache:
        return _benchmark_cache
    
    print("📊 Buscando dados de benchmark (IBOV, S&P500)...")
    
    benchmarks = {
        "^BVSP": "ibov",   # Ibovespa
        "^GSPC": "sp500",  # S&P 500
    }
    
    result = {}
    
    for ticker_symbol, prefix in benchmarks.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                continue
            
            today = hist.index[-1].date()
            current_price = float(hist['Close'].iloc[-1])
            
            # Calculate changes
            date_1d = today - timedelta(days=1)
            date_1w = today - timedelta(weeks=1)
            date_1m = today - timedelta(days=30)
            date_ytd = date(today.year, 1, 1)
            
            price_1d = get_historical_price(hist, date_1d)
            price_1w = get_historical_price(hist, date_1w)
            price_1m = get_historical_price(hist, date_1m)
            price_ytd = get_historical_price(hist, date_ytd)
            
            result[f"{prefix}_change_1d"] = calculate_change_percent(current_price, price_1d)
            result[f"{prefix}_change_1w"] = calculate_change_percent(current_price, price_1w)
            result[f"{prefix}_change_1m"] = calculate_change_percent(current_price, price_1m)
            result[f"{prefix}_change_ytd"] = calculate_change_percent(current_price, price_ytd)
            
            print(f"  ✅ {ticker_symbol}: YTD {result[f'{prefix}_change_ytd']:.1f}%")
            
        except Exception as e:
            print(f"  ⚠️ Error fetching {ticker_symbol}: {e}")
    
    _benchmark_cache = result
    return result


def calculate_benchmark_comparison(quote_data: dict, benchmarks: dict) -> dict:
    """Calculate outperformance vs benchmarks"""
    result = {}
    
    # Copy benchmark data
    for key, value in benchmarks.items():
        result[key] = value
    
    # Calculate outperformance vs Ibovespa
    if quote_data.get("change_1d") and benchmarks.get("ibov_change_1d"):
        result["vs_ibov_1d"] = quote_data["change_1d"] - benchmarks["ibov_change_1d"]
    if quote_data.get("change_1m") and benchmarks.get("ibov_change_1m"):
        result["vs_ibov_1m"] = quote_data["change_1m"] - benchmarks["ibov_change_1m"]
    if quote_data.get("change_ytd") and benchmarks.get("ibov_change_ytd"):
        result["vs_ibov_ytd"] = quote_data["change_ytd"] - benchmarks["ibov_change_ytd"]
    
    # Calculate outperformance vs S&P 500
    if quote_data.get("change_1d") and benchmarks.get("sp500_change_1d"):
        result["vs_sp500_1d"] = quote_data["change_1d"] - benchmarks["sp500_change_1d"]
    if quote_data.get("change_1m") and benchmarks.get("sp500_change_1m"):
        result["vs_sp500_1m"] = quote_data["change_1m"] - benchmarks["sp500_change_1m"]
    if quote_data.get("change_ytd") and benchmarks.get("sp500_change_ytd"):
        result["vs_sp500_ytd"] = quote_data["change_ytd"] - benchmarks["sp500_change_ytd"]
    
    return result


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
    Busca a cotação de um ativo com dados históricos, fundamentais e técnicos
    
    Returns:
        dict com dados completos para análise de AI ou None se falhar
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
        
        # Fetch fundamental data
        fundamentals = fetch_fundamental_data(ticker)
        
        # Calculate technical indicators
        technicals = calculate_technical_indicators(hist, current_price)
        
        # Calculate % from 52-week high
        week_52_high = fundamentals.get("week_52_high")
        pct_from_52w_high = None
        if week_52_high and week_52_high > 0:
            pct_from_52w_high = ((current_price - week_52_high) / week_52_high) * 100
        
        result = {
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
            # % from 52-week high
            "pct_from_52w_high": pct_from_52w_high,
        }
        
        # Merge fundamentals and technicals
        result.update(fundamentals)
        result.update(technicals)
        
        # Calculate signals
        signals = calculate_signals(result)
        result.update(signals)
        
        return result
        
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
        # Fundamental data
        existing.market_cap = quote_data.get("market_cap")
        existing.pe_ratio = quote_data.get("pe_ratio")
        existing.forward_pe = quote_data.get("forward_pe")
        existing.pb_ratio = quote_data.get("pb_ratio")
        existing.dividend_yield = quote_data.get("dividend_yield")
        existing.eps = quote_data.get("eps")
        # Risk metrics
        existing.beta = quote_data.get("beta")
        existing.week_52_high = quote_data.get("week_52_high")
        existing.week_52_low = quote_data.get("week_52_low")
        existing.pct_from_52w_high = quote_data.get("pct_from_52w_high")
        # Technical indicators
        existing.ma_50 = quote_data.get("ma_50")
        existing.ma_200 = quote_data.get("ma_200")
        existing.rsi_14 = quote_data.get("rsi_14")
        existing.above_ma_50 = quote_data.get("above_ma_50")
        existing.above_ma_200 = quote_data.get("above_ma_200")
        existing.ma_50_above_200 = quote_data.get("ma_50_above_200")
        # Financial health
        existing.profit_margin = quote_data.get("profit_margin")
        existing.roe = quote_data.get("roe")
        existing.debt_to_equity = quote_data.get("debt_to_equity")
        # Analyst data
        existing.analyst_rating = quote_data.get("analyst_rating")
        existing.target_price = quote_data.get("target_price")
        existing.num_analysts = quote_data.get("num_analysts")
        # Benchmark data
        existing.ibov_change_1d = quote_data.get("ibov_change_1d")
        existing.ibov_change_1w = quote_data.get("ibov_change_1w")
        existing.ibov_change_1m = quote_data.get("ibov_change_1m")
        existing.ibov_change_ytd = quote_data.get("ibov_change_ytd")
        existing.sp500_change_1d = quote_data.get("sp500_change_1d")
        existing.sp500_change_1w = quote_data.get("sp500_change_1w")
        existing.sp500_change_1m = quote_data.get("sp500_change_1m")
        existing.sp500_change_ytd = quote_data.get("sp500_change_ytd")
        existing.vs_ibov_1d = quote_data.get("vs_ibov_1d")
        existing.vs_ibov_1m = quote_data.get("vs_ibov_1m")
        existing.vs_ibov_ytd = quote_data.get("vs_ibov_ytd")
        existing.vs_sp500_1d = quote_data.get("vs_sp500_1d")
        existing.vs_sp500_1m = quote_data.get("vs_sp500_1m")
        existing.vs_sp500_ytd = quote_data.get("vs_sp500_ytd")
        # Signals
        existing.signal_golden_cross = quote_data.get("signal_golden_cross")
        existing.signal_death_cross = quote_data.get("signal_death_cross")
        existing.signal_rsi_oversold = quote_data.get("signal_rsi_oversold")
        existing.signal_rsi_overbought = quote_data.get("signal_rsi_overbought")
        existing.signal_52w_high = quote_data.get("signal_52w_high")
        existing.signal_52w_low = quote_data.get("signal_52w_low")
        existing.signal_volume_spike = quote_data.get("signal_volume_spike")
        existing.signal_summary = quote_data.get("signal_summary")
        # Volatility
        existing.volatility_30d = quote_data.get("volatility_30d")
        existing.avg_volume_20d = quote_data.get("avg_volume_20d")
        existing.volume_ratio = quote_data.get("volume_ratio")
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
            # Fundamental data
            market_cap=quote_data.get("market_cap"),
            pe_ratio=quote_data.get("pe_ratio"),
            forward_pe=quote_data.get("forward_pe"),
            pb_ratio=quote_data.get("pb_ratio"),
            dividend_yield=quote_data.get("dividend_yield"),
            eps=quote_data.get("eps"),
            # Risk metrics
            beta=quote_data.get("beta"),
            week_52_high=quote_data.get("week_52_high"),
            week_52_low=quote_data.get("week_52_low"),
            pct_from_52w_high=quote_data.get("pct_from_52w_high"),
            # Technical indicators
            ma_50=quote_data.get("ma_50"),
            ma_200=quote_data.get("ma_200"),
            rsi_14=quote_data.get("rsi_14"),
            above_ma_50=quote_data.get("above_ma_50"),
            above_ma_200=quote_data.get("above_ma_200"),
            ma_50_above_200=quote_data.get("ma_50_above_200"),
            # Financial health
            profit_margin=quote_data.get("profit_margin"),
            roe=quote_data.get("roe"),
            debt_to_equity=quote_data.get("debt_to_equity"),
            # Analyst data
            analyst_rating=quote_data.get("analyst_rating"),
            target_price=quote_data.get("target_price"),
            num_analysts=quote_data.get("num_analysts"),
            # Benchmark data
            ibov_change_1d=quote_data.get("ibov_change_1d"),
            ibov_change_1w=quote_data.get("ibov_change_1w"),
            ibov_change_1m=quote_data.get("ibov_change_1m"),
            ibov_change_ytd=quote_data.get("ibov_change_ytd"),
            sp500_change_1d=quote_data.get("sp500_change_1d"),
            sp500_change_1w=quote_data.get("sp500_change_1w"),
            sp500_change_1m=quote_data.get("sp500_change_1m"),
            sp500_change_ytd=quote_data.get("sp500_change_ytd"),
            vs_ibov_1d=quote_data.get("vs_ibov_1d"),
            vs_ibov_1m=quote_data.get("vs_ibov_1m"),
            vs_ibov_ytd=quote_data.get("vs_ibov_ytd"),
            vs_sp500_1d=quote_data.get("vs_sp500_1d"),
            vs_sp500_1m=quote_data.get("vs_sp500_1m"),
            vs_sp500_ytd=quote_data.get("vs_sp500_ytd"),
            # Signals
            signal_golden_cross=quote_data.get("signal_golden_cross"),
            signal_death_cross=quote_data.get("signal_death_cross"),
            signal_rsi_oversold=quote_data.get("signal_rsi_oversold"),
            signal_rsi_overbought=quote_data.get("signal_rsi_overbought"),
            signal_52w_high=quote_data.get("signal_52w_high"),
            signal_52w_low=quote_data.get("signal_52w_low"),
            signal_volume_spike=quote_data.get("signal_volume_spike"),
            signal_summary=quote_data.get("signal_summary"),
            # Volatility
            volatility_30d=quote_data.get("volatility_30d"),
            avg_volume_20d=quote_data.get("avg_volume_20d"),
            volume_ratio=quote_data.get("volume_ratio"),
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
        
        # Fetch benchmark data once (Ibovespa and S&P 500)
        benchmarks = fetch_benchmark_data()
        
        success_count = 0
        error_count = 0
        
        # Buscar ações brasileiras (preço nativo em BRL, calcular USD)
        print("\n📈 Buscando ações do Ibovespa...")
        for ticker, info in IBOVESPA_STOCKS.items():
            quote_data = fetch_quote_with_history(ticker)
            if quote_data:
                # Add benchmark comparison
                benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
                quote_data.update(benchmark_comparison)
                
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
                # Add benchmark comparison
                benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
                quote_data.update(benchmark_comparison)
                
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
                # Add benchmark comparison
                benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
                quote_data.update(benchmark_comparison)
                
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
                # Add benchmark comparison
                benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
                quote_data.update(benchmark_comparison)
                
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
                # Add benchmark comparison
                benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
                quote_data.update(benchmark_comparison)
                
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
