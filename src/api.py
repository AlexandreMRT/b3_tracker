"""
B3 Tracker - REST API
FastAPI server for accessing market data, signals, and reports
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional, List
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import Asset, Quote
from sqlalchemy import desc

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="B3 Tracker API",
    description="API para acesso a cotações da B3, ações americanas, commodities e criptomoedas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HELPERS
# =============================================================================

def get_latest_quotes(db, asset_type: Optional[str] = None, limit: int = 200):
    """Get latest quote for each asset"""
    from sqlalchemy import func
    
    # Subquery to get max quote_date per asset
    subq = db.query(
        Quote.asset_id,
        func.max(Quote.quote_date).label('max_date')
    ).group_by(Quote.asset_id).subquery()
    
    # Main query
    query = db.query(Quote).join(
        subq,
        (Quote.asset_id == subq.c.asset_id) & (Quote.quote_date == subq.c.max_date)
    ).join(Asset)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    return query.limit(limit).all()


def quote_to_dict(quote: Quote) -> dict:
    """Convert Quote model to dictionary"""
    return {
        "ticker": quote.asset.ticker,
        "name": quote.asset.name,
        "type": quote.asset.asset_type,
        "sector": quote.asset.sector,
        "quote_date": quote.quote_date.isoformat() if quote.quote_date else None,
        
        # Prices
        "price_brl": quote.price_brl,
        "price_usd": quote.price_usd,
        
        # Changes
        "change_1d_pct": quote.change_1d,
        "change_1w_pct": quote.change_1w,
        "change_1m_pct": quote.change_1m,
        "change_ytd_pct": quote.change_ytd,
        
        # Technical indicators
        "rsi_14": quote.rsi_14,
        "ma_50": quote.ma_50,
        "ma_200": quote.ma_200,
        "above_ma50": bool(quote.above_ma_50),
        "above_ma200": bool(quote.above_ma_200),
        "golden_cross": bool(quote.ma_50_above_200),
        
        # 52 week range
        "week_52_high": quote.week_52_high,
        "week_52_low": quote.week_52_low,
        "pct_from_52w_high": quote.pct_from_52w_high,
        
        # Volume
        "volume": quote.volume,
        "avg_volume": quote.avg_volume_20d,
        "volume_ratio": quote.volume_ratio,
        
        # Fundamentals
        "pe_ratio": quote.pe_ratio,
        "pb_ratio": quote.pb_ratio,
        "dividend_yield": quote.dividend_yield,
        "beta": quote.beta,
        "roe": quote.roe,
        "market_cap": quote.market_cap,
        
        # Benchmark comparison
        "vs_ibov_1d": quote.vs_ibov_1d,
        "vs_ibov_ytd": quote.vs_ibov_ytd,
        "vs_sp500_1d": quote.vs_sp500_1d,
        "vs_sp500_ytd": quote.vs_sp500_ytd,
        
        # News sentiment
        "news_sentiment_score": quote.news_sentiment_combined,
        "news_sentiment_label": quote.news_sentiment_label,
        "news_count": (quote.news_count_pt or 0) + (quote.news_count_en or 0),
        "latest_headline": quote.news_headline_pt or quote.news_headline_en,
    }


def detect_signals(quote: Quote) -> List[str]:
    """Detect trading signals for a quote"""
    signals = []
    
    # RSI signals
    if quote.rsi_14:
        if quote.rsi_14 < 30:
            signals.append("RSI_OVERSOLD")
        elif quote.rsi_14 > 70:
            signals.append("RSI_OVERBOUGHT")
    
    # Moving average signals
    if quote.ma_50_above_200:
        signals.append("GOLDEN_CROSS")
    if quote.above_ma_50 and quote.above_ma_200:
        signals.append("BULLISH_TREND")
    elif quote.above_ma_50 == 0 and quote.above_ma_200 == 0:
        signals.append("BEARISH_TREND")
    
    # 52 week signals
    if quote.pct_from_52w_high is not None and quote.pct_from_52w_high > -5:
        signals.append("NEAR_52W_HIGH")
    if quote.week_52_low and quote.price_brl:
        pct_from_low = ((quote.price_brl - quote.week_52_low) / quote.week_52_low) * 100
        if pct_from_low < 5:
            signals.append("NEAR_52W_LOW")
    
    # Volume spike
    if quote.volume_ratio and quote.volume_ratio > 2.0:
        signals.append("VOLUME_SPIKE")
    
    # News sentiment
    if quote.news_sentiment_combined:
        if quote.news_sentiment_combined > 0.3:
            signals.append("POSITIVE_NEWS")
        elif quote.news_sentiment_combined < -0.3:
            signals.append("NEGATIVE_NEWS")
    
    return signals


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "name": "B3 Tracker API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "quotes": "/api/quotes",
            "quote": "/api/quotes/{ticker}",
            "signals": "/api/signals",
            "news": "/api/news",
            "report": "/api/report",
            "sectors": "/api/sectors",
            "docs": "/docs",
        }
    }


@app.get("/api/quotes")
async def get_quotes(
    type: Optional[str] = Query(None, description="Filter by asset type: stock, us_stock, commodity, crypto, currency"),
    limit: int = Query(200, description="Maximum number of results")
):
    """
    Get all current quotes.
    
    Optional filters:
    - type: stock, us_stock, commodity, crypto, currency
    """
    db = SessionLocal()
    try:
        quotes = get_latest_quotes(db, type, limit)
        return {
            "count": len(quotes),
            "timestamp": datetime.now().isoformat(),
            "data": [quote_to_dict(q) for q in quotes]
        }
    finally:
        db.close()


@app.get("/api/quotes/{ticker}")
async def get_quote(ticker: str):
    """
    Get detailed data for a specific ticker.
    
    Example: /api/quotes/PETR4 or /api/quotes/PETR4.SA
    """
    db = SessionLocal()
    try:
        ticker_upper = ticker.upper()
        # Try exact match first, then with .SA suffix
        asset = db.query(Asset).filter(Asset.ticker == ticker_upper).first()
        if not asset and not ticker_upper.endswith('.SA'):
            asset = db.query(Asset).filter(Asset.ticker == f"{ticker_upper}.SA").first()
        
        if not asset:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
        
        # Get latest quote
        quote = db.query(Quote).filter(
            Quote.asset_id == asset.id
        ).order_by(desc(Quote.quote_date)).first()
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"No quotes found for '{ticker}'")
        
        data = quote_to_dict(quote)
        data["signals"] = detect_signals(quote)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
    finally:
        db.close()


@app.get("/api/signals")
async def get_signals(
    signal_type: Optional[str] = Query(None, description="Filter by signal: RSI_OVERSOLD, RSI_OVERBOUGHT, GOLDEN_CROSS, etc")
):
    """
    Get all active trading signals.
    
    Signal types:
    - RSI_OVERSOLD: RSI < 30 (potential buy)
    - RSI_OVERBOUGHT: RSI > 70 (potential sell)
    - GOLDEN_CROSS: MA50 crossed above MA200
    - BULLISH_TREND: Above MA50 and MA200
    - BEARISH_TREND: Below MA50 and MA200
    - NEAR_52W_HIGH: Within 5% of 52-week high
    - NEAR_52W_LOW: Within 5% of 52-week low
    - VOLUME_SPIKE: Volume > 2x average
    - POSITIVE_NEWS: Sentiment score > 0.3
    - NEGATIVE_NEWS: Sentiment score < -0.3
    """
    db = SessionLocal()
    try:
        quotes = get_latest_quotes(db)
        
        signals_data = {}
        for quote in quotes:
            signals = detect_signals(quote)
            if signals:
                if signal_type and signal_type.upper() not in signals:
                    continue
                    
                signals_data[quote.asset.ticker] = {
                    "name": quote.asset.name,
                    "type": quote.asset.asset_type,
                    "price_brl": quote.price_brl,
                    "change_1d_pct": quote.change_1d,
                    "rsi_14": quote.rsi_14,
                    "signals": signals,
                    "news_sentiment": quote.news_sentiment_label,
                }
        
        # Group by signal type
        signal_groups = {}
        for ticker, data in signals_data.items():
            for sig in data["signals"]:
                if sig not in signal_groups:
                    signal_groups[sig] = []
                signal_groups[sig].append(ticker)
        
        return {
            "count": len(signals_data),
            "timestamp": datetime.now().isoformat(),
            "by_signal": signal_groups,
            "data": signals_data
        }
    finally:
        db.close()


@app.get("/api/news")
async def get_news(
    sentiment: Optional[str] = Query(None, description="Filter: positive, negative, neutral")
):
    """
    Get news sentiment analysis for all assets with news.
    """
    db = SessionLocal()
    try:
        quotes = get_latest_quotes(db)
        
        news_data = []
        for quote in quotes:
            news_count = (quote.news_count_pt or 0) + (quote.news_count_en or 0)
            if news_count > 0:
                score = quote.news_sentiment_combined or 0
                # Apply sentiment filter
                if sentiment:
                    if sentiment.lower() == "positive" and score <= 0.1:
                        continue
                    elif sentiment.lower() == "negative" and score >= -0.1:
                        continue
                    elif sentiment.lower() == "neutral" and abs(score) > 0.1:
                        continue
                
                news_data.append({
                    "ticker": quote.asset.ticker,
                    "name": quote.asset.name,
                    "sentiment_score": score,
                    "sentiment_label": quote.news_sentiment_label,
                    "news_count": news_count,
                    "latest_headline": quote.news_headline_pt or quote.news_headline_en,
                    "price_brl": quote.price_brl,
                    "change_1d_pct": quote.change_1d,
                })
        
        # Sort by sentiment score
        news_data.sort(key=lambda x: x["sentiment_score"] or 0, reverse=True)
        
        # Summary
        positive = [n for n in news_data if (n["sentiment_score"] or 0) > 0.1]
        negative = [n for n in news_data if (n["sentiment_score"] or 0) < -0.1]
        
        return {
            "count": len(news_data),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "positive_count": len(positive),
                "negative_count": len(negative),
                "neutral_count": len(news_data) - len(positive) - len(negative),
            },
            "data": news_data
        }
    finally:
        db.close()


@app.get("/api/sectors")
async def get_sectors():
    """
    Get performance aggregated by sector.
    """
    db = SessionLocal()
    try:
        quotes = get_latest_quotes(db, asset_type="stock")
        
        sectors = {}
        for quote in quotes:
            sector = quote.asset.sector or "Outros"
            if sector not in sectors:
                sectors[sector] = {
                    "count": 0,
                    "tickers": [],
                    "avg_change_1d": 0,
                    "avg_change_ytd": 0,
                    "avg_rsi": 0,
                    "bullish_count": 0,
                    "bearish_count": 0,
                }
            
            sectors[sector]["count"] += 1
            sectors[sector]["tickers"].append(quote.asset.ticker)
            
            if quote.change_1d:
                sectors[sector]["avg_change_1d"] += quote.change_1d
            if quote.change_ytd:
                sectors[sector]["avg_change_ytd"] += quote.change_ytd
            if quote.rsi_14:
                sectors[sector]["avg_rsi"] += quote.rsi_14
            
            # Count bullish/bearish
            if quote.above_ma_50 and quote.above_ma_200:
                sectors[sector]["bullish_count"] += 1
            elif quote.above_ma_50 == 0 and quote.above_ma_200 == 0:
                sectors[sector]["bearish_count"] += 1
        
        # Calculate averages
        for sector, data in sectors.items():
            n = data["count"]
            if n > 0:
                data["avg_change_1d"] = round(data["avg_change_1d"] / n, 2)
                data["avg_change_ytd"] = round(data["avg_change_ytd"] / n, 2)
                data["avg_rsi"] = round(data["avg_rsi"] / n, 1)
        
        # Sort by YTD performance
        sorted_sectors = dict(sorted(
            sectors.items(), 
            key=lambda x: x[1]["avg_change_ytd"], 
            reverse=True
        ))
        
        return {
            "count": len(sorted_sectors),
            "timestamp": datetime.now().isoformat(),
            "data": sorted_sectors
        }
    finally:
        db.close()


@app.get("/api/report")
async def get_report():
    """
    Get consolidated report (same as --report command).
    Returns structured data for AI consumption.
    """
    from exporter import generate_report_data
    
    try:
        data = generate_report_data()
        return {
            "timestamp": datetime.now().isoformat(),
            "report": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """
    Trigger a data refresh in the background.
    Returns immediately, data will be updated asynchronously.
    """
    from fetcher import fetch_all_quotes
    
    background_tasks.add_task(fetch_all_quotes)
    
    return {
        "status": "started",
        "message": "Data refresh started in background. Check /api/quotes for updated data.",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/movers")
async def get_movers(
    period: str = Query("1d", description="Period: 1d, 1w, 1m, ytd"),
    limit: int = Query(10, description="Number of top/bottom movers")
):
    """
    Get top gainers and losers for a given period.
    """
    db = SessionLocal()
    try:
        quotes = get_latest_quotes(db)
        
        # Map period to field
        field_map = {
            "1d": "change_1d",
            "1w": "change_1w", 
            "1m": "change_1m",
            "ytd": "change_ytd",
        }
        
        if period not in field_map:
            raise HTTPException(status_code=400, detail=f"Invalid period. Use: {list(field_map.keys())}")
        
        field = field_map[period]
        
        # Filter quotes with valid data
        valid_quotes = []
        for q in quotes:
            change = getattr(q, field, None)
            if change is not None:
                valid_quotes.append({
                    "ticker": q.asset.ticker,
                    "name": q.asset.name,
                    "type": q.asset.asset_type,
                    "price_brl": q.price_brl,
                    "change_pct": change,
                })
        
        # Sort
        sorted_quotes = sorted(valid_quotes, key=lambda x: x["change_pct"], reverse=True)
        
        return {
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "gainers": sorted_quotes[:limit],
            "losers": sorted_quotes[-limit:][::-1],
        }
    finally:
        db.close()


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
