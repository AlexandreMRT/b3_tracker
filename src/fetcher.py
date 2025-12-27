"""
Módulo para buscar cotações usando yfinance
"""
import yfinance as yf
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from assets import get_all_assets, IBOVESPA_STOCKS, COMMODITIES, CRYPTO, CURRENCY, US_STOCKS
from models import Asset, Quote
from database import SessionLocal

# Initialize NLTK VADER for sentiment analysis
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    _vader = SentimentIntensityAnalyzer()
    
    # Add Portuguese financial keywords to VADER lexicon
    # Positive words
    pt_positive = {
        'alta': 2.0, 'subiu': 2.0, 'sobe': 1.5, 'valoriza': 2.0, 'valorização': 2.0,
        'lucro': 2.5, 'lucros': 2.5, 'crescimento': 1.5, 'cresce': 1.5, 'cresceu': 1.5,
        'recorde': 2.0, 'positivo': 1.5, 'otimista': 1.5, 'supera': 1.5, 'superou': 1.5,
        'dividendos': 1.5, 'rentabilidade': 1.5, 'aprovação': 1.5, 'aprovado': 1.5,
        'expansão': 1.5, 'expande': 1.5, 'contrato': 1.0, 'parceria': 1.0,
        'aquisição': 1.0, 'investimento': 1.0, 'recomendação': 0.5, 'compra': 1.0,
    }
    # Negative words
    pt_negative = {
        'queda': -2.0, 'caiu': -2.0, 'cai': -1.5, 'desvaloriza': -2.0, 'desvalorização': -2.0,
        'prejuízo': -2.5, 'prejuízos': -2.5, 'perdas': -2.0, 'perda': -2.0,
        'negativo': -1.5, 'pessimista': -1.5, 'rebaixado': -2.0, 'rebaixa': -2.0,
        'dívida': -1.5, 'dívidas': -1.5, 'endividamento': -1.5, 'risco': -1.0,
        'crise': -2.0, 'problema': -1.5, 'problemas': -1.5, 'investigação': -1.5,
        'multa': -2.0, 'fraude': -3.0, 'demissão': -1.5, 'demissões': -1.5,
        'rombo': -2.5, 'escândalo': -3.0, 'falência': -3.0, 'recuperação judicial': -2.5,
    }
    _vader.lexicon.update(pt_positive)
    _vader.lexicon.update(pt_negative)
    
except Exception as e:
    print(f"⚠️ VADER not available: {e}")
    _vader = None

# Initialize feedparser for Google News RSS
try:
    import feedparser
    _feedparser_available = True
except Exception as e:
    print(f"⚠️ feedparser not available: {e}")
    _feedparser_available = False


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


def fetch_news_english(ticker_symbol: str, max_news: int = 10) -> list:
    """Fetch English news from yfinance"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        
        if not news:
            return []
        
        results = []
        for item in news[:max_news]:
            title = item.get("title", "")
            # yfinance news structure: use content summary if available
            content = item.get("summary", item.get("description", ""))
            text = f"{title}. {content}" if content else title
            results.append({
                "title": title,
                "text": text,
                "source": item.get("publisher", ""),
                "link": item.get("link", ""),
            })
        
        return results
    except Exception as e:
        print(f"    ⚠️ Error fetching EN news for {ticker_symbol}: {e}")
        return []


def fetch_news_portuguese(company_name: str, ticker: str, max_news: int = 10) -> list:
    """Fetch Portuguese news from Google News RSS"""
    if not _feedparser_available:
        return []
    
    try:
        # Clean ticker for search (remove .SA)
        clean_ticker = ticker.replace(".SA", "")
        
        # Search for company name and ticker
        search_query = f"{company_name} OR {clean_ticker} ações bolsa"
        encoded_query = urllib.parse.quote(search_query)
        
        # Google News RSS for Portuguese (Brazil)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            return []
        
        results = []
        for entry in feed.entries[:max_news]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            text = f"{title}. {summary}" if summary else title
            results.append({
                "title": title,
                "text": text,
                "source": entry.get("source", {}).get("title", "Google News"),
                "link": entry.get("link", ""),
            })
        
        return results
    except Exception as e:
        print(f"    ⚠️ Error fetching PT news for {company_name}: {e}")
        return []


def analyze_sentiment_english(texts: list) -> tuple:
    """Analyze sentiment of English texts using VADER"""
    if not _vader or not texts:
        return None, None
    
    scores = []
    for item in texts:
        text = item.get("text", item) if isinstance(item, dict) else item
        if text:
            score = _vader.polarity_scores(text)
            scores.append(score["compound"])
    
    if not scores:
        return None, None
    
    avg_score = sum(scores) / len(scores)
    # Get the headline from the first (most recent) article
    headline = texts[0].get("title", "") if texts and isinstance(texts[0], dict) else ""
    
    return avg_score, headline


def analyze_sentiment_portuguese(texts: list) -> tuple:
    """Analyze sentiment of Portuguese texts using enhanced VADER with PT keywords"""
    if not _vader or not texts:
        return None, None
    
    scores = []
    for item in texts:
        text = item.get("text", item) if isinstance(item, dict) else item
        if text:
            # Lowercase for better PT keyword matching
            score = _vader.polarity_scores(text.lower())
            scores.append(score["compound"])
    
    if not scores:
        return None, None
    
    avg_score = sum(scores) / len(scores)
    # Get the headline from the first (most recent) article
    headline = texts[0].get("title", "") if texts and isinstance(texts[0], dict) else ""
    
    return avg_score, headline


def fetch_news_sentiment(ticker_symbol: str, company_name: str, is_brazilian: bool = True) -> dict:
    """
    Fetch and analyze news sentiment for a stock
    
    Args:
        ticker_symbol: Stock ticker (e.g., "PETR4.SA", "AAPL")
        company_name: Company name for search
        is_brazilian: Whether this is a Brazilian stock (triggers PT-BR search)
    
    Returns:
        dict with sentiment scores and headlines
    """
    result = {
        "news_sentiment_pt": None,
        "news_sentiment_en": None,
        "news_sentiment_combined": None,
        "news_count_pt": 0,
        "news_count_en": 0,
        "news_headline_pt": None,
        "news_headline_en": None,
        "news_sentiment_label": None,
    }
    
    # Fetch English news (always, using yfinance)
    en_news = fetch_news_english(ticker_symbol)
    if en_news:
        result["news_count_en"] = len(en_news)
        score, headline = analyze_sentiment_english(en_news)
        if score is not None:
            result["news_sentiment_en"] = score
            result["news_headline_en"] = headline[:500] if headline else None
    
    # Fetch Portuguese news (for Brazilian stocks)
    if is_brazilian:
        pt_news = fetch_news_portuguese(company_name, ticker_symbol)
        if pt_news:
            result["news_count_pt"] = len(pt_news)
            score, headline = analyze_sentiment_portuguese(pt_news)
            if score is not None:
                result["news_sentiment_pt"] = score
                result["news_headline_pt"] = headline[:500] if headline else None
    
    # Calculate combined score
    pt_score = result["news_sentiment_pt"]
    en_score = result["news_sentiment_en"]
    
    if pt_score is not None and en_score is not None:
        # Weight: 60% local (PT), 40% international (EN) for Brazilian stocks
        result["news_sentiment_combined"] = (pt_score * 0.6) + (en_score * 0.4)
    elif pt_score is not None:
        result["news_sentiment_combined"] = pt_score
    elif en_score is not None:
        result["news_sentiment_combined"] = en_score
    
    # Determine label
    combined = result["news_sentiment_combined"]
    if combined is not None:
        if combined >= 0.2:
            result["news_sentiment_label"] = "positive"
        elif combined <= -0.2:
            result["news_sentiment_label"] = "negative"
        else:
            result["news_sentiment_label"] = "neutral"
    
    return result


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
        # News sentiment
        existing.news_sentiment_pt = quote_data.get("news_sentiment_pt")
        existing.news_sentiment_en = quote_data.get("news_sentiment_en")
        existing.news_sentiment_combined = quote_data.get("news_sentiment_combined")
        existing.news_count_pt = quote_data.get("news_count_pt")
        existing.news_count_en = quote_data.get("news_count_en")
        existing.news_headline_pt = quote_data.get("news_headline_pt")
        existing.news_headline_en = quote_data.get("news_headline_en")
        existing.news_sentiment_label = quote_data.get("news_sentiment_label")
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
            # News sentiment
            news_sentiment_pt=quote_data.get("news_sentiment_pt"),
            news_sentiment_en=quote_data.get("news_sentiment_en"),
            news_sentiment_combined=quote_data.get("news_sentiment_combined"),
            news_count_pt=quote_data.get("news_count_pt"),
            news_count_en=quote_data.get("news_count_en"),
            news_headline_pt=quote_data.get("news_headline_pt"),
            news_headline_en=quote_data.get("news_headline_en"),
            news_sentiment_label=quote_data.get("news_sentiment_label"),
            quote_date=datetime.combine(quote_date, datetime.min.time())
        )
        db.add(quote)
        print(f"💰 Salvo: {asset.ticker} = R$ {price_brl:.2f}")
    
    db.commit()


def fetch_single_asset(ticker: str, info: dict, asset_type: str, is_brazilian: bool, 
                       usd_brl: float, benchmarks: dict) -> Optional[dict]:
    """
    Fetch a single asset's quote, news, and prepare data for saving.
    This function is designed to be called in parallel.
    
    Returns:
        dict with all data needed for saving, or None if fetch failed
    """
    try:
        quote_data = fetch_quote_with_history(ticker)
        if not quote_data:
            return None
        
        # Add benchmark comparison
        benchmark_comparison = calculate_benchmark_comparison(quote_data, benchmarks)
        quote_data.update(benchmark_comparison)
        
        # Calculate prices based on asset type
        if asset_type == "stock":
            # Brazilian stock: price is in BRL
            price_brl = quote_data["close"]
            price_usd = price_brl / usd_brl
        elif asset_type == "currency":
            # Currency: price is in BRL, USD is always 1
            price_brl = quote_data["close"]
            price_usd = 1.0
        else:
            # US stock, commodity, crypto: price is in USD
            price_usd = quote_data["close"]
            price_brl = price_usd * usd_brl
        
        return {
            "ticker": ticker,
            "info": info,
            "asset_type": asset_type,
            "is_brazilian": is_brazilian,
            "quote_data": quote_data,
            "price_brl": price_brl,
            "price_usd": price_usd,
        }
    except Exception as e:
        print(f"    ❌ Error fetching {ticker}: {e}")
        return None


def fetch_news_for_asset(result: dict) -> dict:
    """
    Fetch news sentiment for a single asset.
    This function is designed to be called in parallel.
    """
    if result is None:
        return result
    
    asset_type = result["asset_type"]
    
    # Only fetch news for stocks
    if asset_type in ("stock", "us_stock"):
        ticker = result["ticker"]
        info = result["info"]
        is_brazilian = result["is_brazilian"]
        
        news_data = fetch_news_sentiment(ticker, info.get("name", ""), is_brazilian=is_brazilian)
        result["quote_data"].update(news_data)
    
    return result


def fetch_all_quotes():
    """Busca e salva cotações de todos os ativos (versão paralela)"""
    
    total_start = time.time()
    
    print("\n" + "="*60)
    print(f"🚀 Iniciando busca de cotações - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # =========================================================================
    # FASE 1: Prerequisites (paralelo)
    # =========================================================================
    phase1_start = time.time()
    print("📊 Fase 1: Buscando dados de referência...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        usd_future = executor.submit(get_usd_brl_rate)
        bench_future = executor.submit(fetch_benchmark_data)
        
        usd_brl = usd_future.result()
        benchmarks = bench_future.result()
    
    print(f"   💵 USD/BRL: R$ {usd_brl:.4f}")
    print(f"   ⏱️  Fase 1 concluída em {time.time() - phase1_start:.1f}s\n")
    
    # =========================================================================
    # FASE 2: Prepare all assets
    # =========================================================================
    all_assets = []
    
    # Brazilian stocks
    for ticker, info in IBOVESPA_STOCKS.items():
        all_assets.append((ticker, info, "stock", True))
    
    # US stocks
    for ticker, info in US_STOCKS.items():
        all_assets.append((ticker, info, "us_stock", False))
    
    # Commodities
    for ticker, info in COMMODITIES.items():
        all_assets.append((ticker, info, "commodity", False))
    
    # Crypto
    for ticker, info in CRYPTO.items():
        all_assets.append((ticker, info, "crypto", False))
    
    # Currency
    for ticker, info in CURRENCY.items():
        all_assets.append((ticker, info, "currency", False))
    
    total_assets = len(all_assets)
    print(f"📈 Total de ativos para buscar: {total_assets}")
    
    # =========================================================================
    # FASE 2: Fetch all quotes in parallel
    # =========================================================================
    phase2_start = time.time()
    print(f"\n📊 Fase 2: Buscando cotações (8 workers paralelos)...")
    
    results = []
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_single_asset, ticker, info, asset_type, is_br, usd_brl, benchmarks): ticker
            for ticker, info, asset_type, is_br in all_assets
        }
        
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"    ❌ Error processing {ticker}: {e}")
                error_count += 1
    
    print(f"   ✅ Cotações: {success_count} sucesso, {error_count} erros")
    print(f"   ⏱️  Fase 2 concluída em {time.time() - phase2_start:.1f}s\n")
    
    # =========================================================================
    # FASE 3: Fetch news in parallel (only for stocks)
    # =========================================================================
    phase3_start = time.time()
    stocks_only = [r for r in results if r["asset_type"] in ("stock", "us_stock")]
    print(f"📰 Fase 3: Buscando notícias para {len(stocks_only)} ações (5 workers)...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_news_for_asset, r): r["ticker"] for r in stocks_only}
        
        for future in as_completed(futures):
            try:
                future.result()  # Just ensure it completes
            except Exception as e:
                ticker = futures[future]
                print(f"    ⚠️ News error for {ticker}: {e}")
    
    print(f"   ⏱️  Fase 3 concluída em {time.time() - phase3_start:.1f}s\n")
    
    # =========================================================================
    # FASE 4: Save all to database (sequential - SQLite safe)
    # =========================================================================
    phase4_start = time.time()
    print(f"💾 Fase 4: Salvando {len(results)} registros no banco...")
    
    db = SessionLocal()
    try:
        saved_count = 0
        for result in results:
            try:
                asset = get_or_create_asset(
                    db, 
                    result["ticker"], 
                    result["info"], 
                    result["asset_type"]
                )
                save_quote(
                    db, 
                    asset, 
                    result["quote_data"], 
                    result["price_brl"], 
                    result["price_usd"]
                )
                saved_count += 1
            except Exception as e:
                print(f"    ❌ Error saving {result['ticker']}: {e}")
        
        print(f"   ✅ Salvos: {saved_count} registros")
        print(f"   ⏱️  Fase 4 concluída em {time.time() - phase4_start:.1f}s\n")
        
    finally:
        db.close()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    total_time = time.time() - total_start
    print("="*60)
    print(f"✅ CONCLUÍDO!")
    print(f"   📊 Ativos processados: {success_count}/{total_assets}")
    print(f"   ⏱️  Tempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"   🚀 Velocidade: {total_assets/total_time:.1f} ativos/segundo")
    print("="*60 + "\n")
    
    return success_count, error_count


if __name__ == "__main__":
    from database import init_db
    init_db()
    fetch_all_quotes()
