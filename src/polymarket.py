"""
Polymarket API Client - Prediction Market Sentiment for B3 Tracker

Fetches prediction market data from Polymarket to provide forward-looking
sentiment signals for tracked assets.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

from logger import get_logger

logger = get_logger(__name__)

# Polymarket Gamma API (public, no auth required)
GAMMA_API = "https://gamma-api.polymarket.com"

# Keywords to match markets to tracked assets/categories
MARKET_KEYWORDS = {
    # Crypto assets
    "BTC-USD": ["bitcoin", "btc"],
    "ETH-USD": ["ethereum", "eth"],
    # US Market / Macro
    "MACRO_FED": ["federal reserve", "fed rate", "interest rate", "fomc", "rate cut", "rate hike"],
    "MACRO_RECESSION": ["recession", "economic downturn", "gdp"],
    "MACRO_INFLATION": ["inflation", "cpi", "consumer price"],
    # Brazil specific
    "MACRO_BRAZIL": ["brazil", "lula", "brazilian"],
    # Commodities
    "GC=F": ["gold price", "gold spot"],
    "CL=F": ["oil price", "crude oil", "wti", "brent"],
    # Tech sector
    "SECTOR_TECH": ["nvidia", "apple", "microsoft", "google", "meta", "ai stocks", "tech stocks"],
    # Geopolitics affecting markets
    "GEOPOLITICS": ["china", "taiwan", "russia", "ukraine", "trade war", "tariff"],
}

# Categories to fetch from Polymarket
RELEVANT_CATEGORIES = [
    "economics",
    "crypto",
    "business",
    "politics",  # for macro/policy impacts
]


def fetch_markets(
    limit: int = 100,
    active: bool = True,
    closed: bool = False,
    order_by: str = "volume24hr",
    category: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch markets from Polymarket Gamma API

    Args:
        limit: Max number of markets to fetch
        active: Only fetch active markets
        closed: Include closed markets
        order_by: Field to order by (volume24hr, liquidity, etc)
        category: Filter by category

    Returns:
        List of market dictionaries
    """
    try:
        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": order_by,
            "ascending": "false",
        }

        if category:
            params["category"] = category

        response = requests.get(f"{GAMMA_API}/markets", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        logger.warning(f"⚠️ Error fetching Polymarket data: {e}")
        return []


def parse_outcome_prices(outcomes_str: str, prices_str: str) -> Dict[str, float]:
    """
    Parse outcome prices from Polymarket format

    Args:
        outcomes_str: JSON string like '["Yes", "No"]'
        prices_str: JSON string like '[0.65, 0.35]'

    Returns:
        Dict mapping outcome to probability
    """
    import json

    try:
        outcomes = json.loads(outcomes_str) if outcomes_str else []
        prices = json.loads(prices_str) if prices_str else []
        return dict(zip(outcomes, prices, strict=True))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def match_market_to_assets(question: str, description: str = "") -> List[str]:
    """
    Match a market question to tracked assets/categories

    Args:
        question: The market question text
        description: Optional market description

    Returns:
        List of matched asset/category keys
    """
    text = f"{question} {description}".lower()
    matches = []

    for asset_key, keywords in MARKET_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            matches.append(asset_key)

    return matches


def calculate_sentiment_from_market(market: Dict) -> Dict[str, Any]:
    """
    Calculate a sentiment signal from a market

    For binary Yes/No markets:
    - Yes price > 0.6 = bullish signal
    - Yes price < 0.4 = bearish signal
    - Otherwise neutral

    Returns dict with sentiment data
    """
    question = market.get("question", "")
    outcomes_str = market.get("outcomes", "")
    prices_str = market.get("outcomePrices", "")

    prices = parse_outcome_prices(outcomes_str, prices_str)

    # Get the "Yes" probability (main outcome)
    yes_prob = prices.get("Yes", prices.get("yes", None))

    if yes_prob is None:
        # Try to get first outcome price
        price_list = list(prices.values())
        yes_prob = price_list[0] if price_list else None

    # Ensure yes_prob is a float
    if yes_prob is not None:
        try:
            yes_prob = float(yes_prob)
        except (ValueError, TypeError):
            yes_prob = None

    # Calculate sentiment
    if yes_prob is not None:
        if yes_prob >= 0.6:
            sentiment = "bullish"
        elif yes_prob <= 0.4:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
    else:
        sentiment = None

    return {
        "question": question,
        "yes_probability": yes_prob,
        "sentiment": sentiment,
        "volume_24h": market.get("volume24hr"),
        "volume_total": market.get("volumeNum"),
        "liquidity": market.get("liquidityNum"),
        "price_change_1d": market.get("oneDayPriceChange"),
        "price_change_1w": market.get("oneWeekPriceChange"),
        "end_date": market.get("endDate"),
        "slug": market.get("slug"),
    }


def fetch_polymarket_sentiment(max_markets: int = 200) -> Dict[str, List[Dict]]:
    """
    Fetch Polymarket data and match to tracked assets

    Returns:
        Dict mapping asset keys to list of relevant markets with sentiment
    """
    logger.info("📊 Fetching Polymarket prediction markets...")

    all_markets = []

    # Fetch markets by relevant categories
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_markets, limit=50, category=cat): cat for cat in RELEVANT_CATEGORIES}

        for future in as_completed(futures):
            category = futures[future]
            try:
                markets = future.result()
                all_markets.extend(markets)
            except Exception as e:
                logger.warning(f"⚠️ Error fetching {category}: {e}")

    # Also fetch top markets by volume (any category)
    top_markets = fetch_markets(limit=50, category=None)
    all_markets.extend(top_markets)

    # Deduplicate by market ID
    seen_ids = set()
    unique_markets = []
    for m in all_markets:
        mid = m.get("id")
        if mid and mid not in seen_ids:
            seen_ids.add(mid)
            unique_markets.append(m)

    logger.info(f"✅ Fetched {len(unique_markets)} unique markets")

    # Match markets to assets and calculate sentiment
    asset_markets: Dict[str, List[Dict]] = {}

    for market in unique_markets:
        question = market.get("question", "")
        description = market.get("description", "")

        matched_assets = match_market_to_assets(question, description)

        if matched_assets:
            sentiment_data = calculate_sentiment_from_market(market)

            for asset_key in matched_assets:
                if asset_key not in asset_markets:
                    asset_markets[asset_key] = []
                asset_markets[asset_key].append(sentiment_data)

    # Sort each asset's markets by volume
    for asset_key in asset_markets:
        asset_markets[asset_key].sort(key=lambda x: x.get("volume_24h") or 0, reverse=True)
        # Keep top 5 most relevant markets per asset
        asset_markets[asset_key] = asset_markets[asset_key][:5]

    matched_count = sum(len(v) for v in asset_markets.values())
    logger.info(f"✅ Matched {matched_count} markets to {len(asset_markets)} assets/categories")

    return asset_markets


def aggregate_sentiment(markets: List[Dict]) -> Dict[str, Any]:
    """
    Aggregate sentiment from multiple markets for an asset

    Uses volume-weighted average of probabilities

    Returns:
        Dict with aggregated sentiment score and label
    """
    if not markets:
        return {
            "score": None,
            "label": None,
            "confidence": None,
            "market_count": 0,
            "total_volume": 0,
            "top_market": None,
        }

    total_volume = 0
    weighted_prob = 0

    for m in markets:
        vol = m.get("volume_24h") or 0
        prob = m.get("yes_probability")

        if prob is not None and vol > 0:
            weighted_prob += prob * vol
            total_volume += vol

    if total_volume > 0:
        avg_prob = weighted_prob / total_volume

        # Convert to sentiment score (-1 to +1)
        # 0.5 probability = 0 sentiment
        # 1.0 probability = +1 sentiment
        # 0.0 probability = -1 sentiment
        score = (avg_prob - 0.5) * 2

        if score >= 0.2:
            label = "bullish"
        elif score <= -0.2:
            label = "bearish"
        else:
            label = "neutral"

        # Confidence based on volume (log scale)
        import math

        confidence = min(1.0, math.log10(total_volume + 1) / 7)  # ~$10M = 100% confidence
    else:
        score = None
        label = None
        confidence = None

    return {
        "score": round(score, 3) if score else None,
        "label": label,
        "confidence": round(confidence, 3) if confidence else None,
        "market_count": len(markets),
        "total_volume": total_volume,
        "top_market": markets[0] if markets else None,
    }


def get_macro_sentiment() -> Dict[str, Dict]:
    """
    Get overall macro sentiment from prediction markets

    Returns sentiment for:
    - Fed/Rates
    - Recession
    - Inflation
    - Brazil
    - Geopolitics
    """
    asset_markets = fetch_polymarket_sentiment()

    macro_categories = [
        "MACRO_FED",
        "MACRO_RECESSION",
        "MACRO_INFLATION",
        "MACRO_BRAZIL",
        "GEOPOLITICS",
        "SECTOR_TECH",
    ]

    macro_sentiment = {}

    for category in macro_categories:
        markets = asset_markets.get(category, [])
        macro_sentiment[category] = aggregate_sentiment(markets)

    # Also add crypto
    for crypto in ["BTC-USD", "ETH-USD"]:
        markets = asset_markets.get(crypto, [])
        macro_sentiment[crypto] = aggregate_sentiment(markets)

    return macro_sentiment


def print_polymarket_summary(asset_markets: Optional[Dict] = None):
    """Print a summary of Polymarket sentiment"""

    if asset_markets is None:
        asset_markets = fetch_polymarket_sentiment()

    logger.info("=" * 100)
    logger.info("🎯 POLYMARKET PREDICTION MARKET SENTIMENT")
    logger.info("=" * 100)

    if not asset_markets:
        logger.warning("⚠️ No relevant prediction markets found")
        return

    for asset_key, markets in sorted(asset_markets.items()):
        if not markets:
            continue

        agg = aggregate_sentiment(markets)

        # Format header
        label_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(agg.get("label"), "❓")

        logger.info(f"{label_emoji} {asset_key}")
        logger.info(f"   Sentiment: {agg.get('label', 'N/A').upper()} (score: {agg.get('score', 'N/A')})")
        logger.info(f"   Markets: {agg.get('market_count')} | Volume 24h: ${agg.get('total_volume', 0):,.0f}")

        # Show top markets
        for i, m in enumerate(markets[:3], 1):
            prob = m.get("yes_probability")
            prob_str = f"{prob * 100:.0f}%" if prob else "N/A"
            vol = m.get("volume_24h") or 0

            logger.info(f"   {i}. [{prob_str}] {m.get('question', 'N/A')[:70]}...")
            logger.info(f"      Vol: ${vol:,.0f} | Change: {m.get('price_change_1d') or 0:+.1f}%")

    logger.info("=" * 100)
    logger.info("  Score range: -1.0 (bearish) to +1.0 (bullish)")
    logger.info("  Probability: 0% (won't happen) to 100% (will happen)")
    logger.info("=" * 100)


# Standalone test
if __name__ == "__main__":
    logger.info("Testing Polymarket API...")

    # Fetch and display sentiment
    asset_markets = fetch_polymarket_sentiment()
    print_polymarket_summary(asset_markets)

    # Show macro sentiment
    logger.info("📊 MACRO SENTIMENT SUMMARY:")
    macro = get_macro_sentiment()
    for key, sentiment in macro.items():
        if sentiment.get("score") is not None:
            logger.info(f"  {key}: {sentiment.get('label', 'N/A')} ({sentiment.get('score'):+.2f})")
