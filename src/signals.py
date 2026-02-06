"""
Unified signal detection for B3 Tracker.

Single source of truth for trading signals.  Both the fetcher (which stores
0/1 flags in the database) and the API (which returns human-readable labels)
consume the same logic through different entry points.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Thresholds (single place to tune)
# ---------------------------------------------------------------------------

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
VOLUME_SPIKE_RATIO = 2.0
NEAR_52W_HIGH_PCT = -5       # within 5% of 52-week high
NEAR_52W_LOW_PCT = 5         # within 5% of 52-week low
NEWS_SENTIMENT_POS = 0.3
NEWS_SENTIMENT_NEG = -0.3
BULLISH_MIN_COUNT = 3
BEARISH_MIN_COUNT = 3


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    """Holds all computed signals for a single quote."""

    rsi_oversold: bool = False
    rsi_overbought: bool = False
    near_52w_high: bool = False
    near_52w_low: bool = False
    volume_spike: bool = False
    golden_cross: bool = False
    death_cross: bool = False
    bullish_trend: bool = False
    bearish_trend: bool = False
    positive_news: bool = False
    negative_news: bool = False
    summary: str = "neutral"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def as_db_flags(self) -> Dict[str, Any]:
        """Return a dict of 0/1 flags + summary string for DB storage."""
        return {
            "signal_rsi_oversold": int(self.rsi_oversold),
            "signal_rsi_overbought": int(self.rsi_overbought),
            "signal_52w_high": int(self.near_52w_high),
            "signal_52w_low": int(self.near_52w_low),
            "signal_volume_spike": int(self.volume_spike),
            "signal_golden_cross": int(self.golden_cross),
            "signal_death_cross": int(self.death_cross),
            "signal_summary": self.summary,
        }

    def as_labels(self) -> List[str]:
        """Return a list of human-readable signal labels for the API."""
        labels: List[str] = []
        if self.rsi_oversold:
            labels.append("RSI_OVERSOLD")
        if self.rsi_overbought:
            labels.append("RSI_OVERBOUGHT")
        if self.golden_cross:
            labels.append("GOLDEN_CROSS")
        if self.bullish_trend:
            labels.append("BULLISH_TREND")
        if self.bearish_trend:
            labels.append("BEARISH_TREND")
        if self.near_52w_high:
            labels.append("NEAR_52W_HIGH")
        if self.near_52w_low:
            labels.append("NEAR_52W_LOW")
        if self.volume_spike:
            labels.append("VOLUME_SPIKE")
        if self.positive_news:
            labels.append("POSITIVE_NEWS")
        if self.negative_news:
            labels.append("NEGATIVE_NEWS")
        return labels


# ---------------------------------------------------------------------------
# Core detection – works on plain dicts *or* ORM objects
# ---------------------------------------------------------------------------

def _get(source: Any, key: str, default=None):
    """Get a value from a dict or an ORM object attribute."""
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def detect_signals(data: Any) -> SignalResult:
    """
    Detect trading signals from quote data.

    Parameters
    ----------
    data : dict | ORM Quote object
        Must expose at least some of the following keys/attributes:
        rsi_14, pct_from_52w_high, week_52_high, week_52_low, close/price_brl,
        volume_ratio, ma_50_above_200, above_ma_50, above_ma_200,
        news_sentiment_combined.

    Returns
    -------
    SignalResult
        Structured object with boolean flags, a summary, and helpers to
        convert to DB flags or API labels.
    """
    result = SignalResult()

    # RSI ------------------------------------------------------------------
    rsi = _get(data, "rsi_14")
    if rsi is not None:
        result.rsi_oversold = rsi < RSI_OVERSOLD
        result.rsi_overbought = rsi > RSI_OVERBOUGHT

    # 52-week high ---------------------------------------------------------
    pct_from_high = _get(data, "pct_from_52w_high")
    if pct_from_high is not None:
        result.near_52w_high = pct_from_high >= NEAR_52W_HIGH_PCT

    # 52-week low ----------------------------------------------------------
    week_52_low = _get(data, "week_52_low")
    # Support both "close" (fetcher dict) and "price_brl" (ORM Quote)
    close = _get(data, "close") or _get(data, "price_brl")
    if week_52_low and close:
        pct_from_low = ((close - week_52_low) / week_52_low) * 100
        result.near_52w_low = pct_from_low <= NEAR_52W_LOW_PCT

    # Volume spike ---------------------------------------------------------
    volume_ratio = _get(data, "volume_ratio")
    if volume_ratio is not None:
        result.volume_spike = volume_ratio >= VOLUME_SPIKE_RATIO

    # Moving-average crosses -----------------------------------------------
    ma_50_above_200 = _get(data, "ma_50_above_200")
    result.golden_cross = ma_50_above_200 == 1
    result.death_cross = ma_50_above_200 == 0

    # Trend direction (above/below both MAs) --------------------------------
    above_50 = _get(data, "above_ma_50")
    above_200 = _get(data, "above_ma_200")
    if above_50 and above_200:
        result.bullish_trend = True
    elif above_50 == 0 and above_200 == 0:
        result.bearish_trend = True

    # News sentiment -------------------------------------------------------
    news = _get(data, "news_sentiment_combined")
    if news is not None:
        result.positive_news = news > NEWS_SENTIMENT_POS
        result.negative_news = news < NEWS_SENTIMENT_NEG

    # Overall summary ------------------------------------------------------
    bullish_count = sum([
        result.rsi_oversold,
        result.near_52w_low,
        result.golden_cross,
        bool(above_50),
        bool(above_200),
    ])
    bearish_count = sum([
        result.rsi_overbought,
        result.near_52w_high,
        result.death_cross,
        above_50 == 0 if above_50 is not None else False,
        above_200 == 0 if above_200 is not None else False,
    ])
    if bullish_count >= BULLISH_MIN_COUNT and bullish_count > bearish_count:
        result.summary = "bullish"
    elif bearish_count >= BEARISH_MIN_COUNT and bearish_count > bullish_count:
        result.summary = "bearish"
    else:
        result.summary = "neutral"

    return result
