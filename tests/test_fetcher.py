"""
Unit tests for the fetcher module – pure-logic functions only.
No network calls; yfinance/feedparser are NOT invoked.
"""

import numpy as np
import pandas as pd
import pytest

from fetcher import (
    calculate_change_percent,
    calculate_rsi,
    calculate_signals,
    calculate_technical_indicators,
)

# ---------------------------------------------------------------------------
# calculate_change_percent
# ---------------------------------------------------------------------------


class TestCalculateChangePercent:
    def test_positive_change(self):
        assert calculate_change_percent(110.0, 100.0) == pytest.approx(10.0)

    def test_negative_change(self):
        assert calculate_change_percent(90.0, 100.0) == pytest.approx(-10.0)

    def test_zero_change(self):
        assert calculate_change_percent(100.0, 100.0) == pytest.approx(0.0)

    def test_previous_is_zero_returns_none(self):
        assert calculate_change_percent(100.0, 0.0) is None

    def test_previous_is_none_returns_none(self):
        assert calculate_change_percent(100.0, None) is None

    def test_large_change(self):
        assert calculate_change_percent(200.0, 100.0) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# calculate_rsi
# ---------------------------------------------------------------------------


class TestCalculateRSI:
    def _make_prices(self, values):
        """Create a pandas Series from a list of prices."""
        return pd.Series(values, dtype=float)

    def test_insufficient_data_returns_none(self):
        prices = self._make_prices([10.0] * 10)  # Only 10 prices, need 15+
        assert calculate_rsi(prices, period=14) is None

    def test_all_gains_returns_100(self):
        # 20 consecutive gains: 100, 101, 102, ..., 119
        prices = self._make_prices([100 + i for i in range(20)])
        rsi = calculate_rsi(prices, period=14)
        assert rsi == 100.0

    def test_rsi_between_0_and_100(self):
        # Mix of ups and downs
        np.random.seed(42)
        prices = self._make_prices(100 + np.cumsum(np.random.randn(50)))
        rsi = calculate_rsi(prices, period=14)
        assert rsi is not None
        assert 0.0 <= rsi <= 100.0

    def test_mostly_losses_gives_low_rsi(self):
        # Consistent downtrend
        prices = self._make_prices([100 - i * 0.5 for i in range(30)])
        rsi = calculate_rsi(prices, period=14)
        assert rsi is not None
        assert rsi < 30.0

    def test_mostly_gains_gives_high_rsi(self):
        # Consistent uptrend
        prices = self._make_prices([100 + i * 0.5 for i in range(30)])
        rsi = calculate_rsi(prices, period=14)
        assert rsi is not None
        assert rsi > 70.0


# ---------------------------------------------------------------------------
# calculate_technical_indicators
# ---------------------------------------------------------------------------


class TestCalculateTechnicalIndicators:
    def _make_hist(self, n_days=250, base_price=100.0, trend=0.0):
        """Create a DataFrame mimicking yfinance historical data."""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="B")
        prices = base_price + trend * np.arange(n_days) + np.random.randn(n_days) * 0.5
        volumes = np.random.randint(1_000_000, 50_000_000, size=n_days)
        return pd.DataFrame(
            {
                "Close": prices,
                "Volume": volumes,
            },
            index=dates,
        )

    def test_ma50_calculated_with_enough_data(self):
        hist = self._make_hist(n_days=60)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "ma_50" in result
        assert isinstance(result["ma_50"], float)

    def test_ma200_calculated_with_enough_data(self):
        hist = self._make_hist(n_days=250)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "ma_200" in result

    def test_above_ma50_flag(self):
        hist = self._make_hist(n_days=60, base_price=50.0)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert result["above_ma_50"] == 1

    def test_below_ma50_flag(self):
        hist = self._make_hist(n_days=60, base_price=150.0)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert result["above_ma_50"] == 0

    def test_rsi_included(self):
        hist = self._make_hist(n_days=60)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "rsi_14" in result
        assert 0.0 <= result["rsi_14"] <= 100.0

    def test_volatility_30d(self):
        hist = self._make_hist(n_days=60)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "volatility_30d" in result
        assert result["volatility_30d"] > 0.0

    def test_volume_analysis(self):
        hist = self._make_hist(n_days=60)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "avg_volume_20d" in result
        assert "volume_ratio" in result

    def test_short_history_no_ma50(self):
        hist = self._make_hist(n_days=30)
        result = calculate_technical_indicators(hist, current_price=100.0)
        assert "ma_50" not in result

    def test_golden_cross_detection(self):
        hist = self._make_hist(n_days=250, base_price=80.0, trend=0.1)
        result = calculate_technical_indicators(hist, current_price=110.0)
        # With uptrend, ma_50 should be above ma_200
        if "ma_50" in result and "ma_200" in result and result["ma_50"] > result["ma_200"]:
            assert result["ma_50_above_200"] == 1


# ---------------------------------------------------------------------------
# calculate_signals
# ---------------------------------------------------------------------------


class TestCalculateSignals:
    def test_rsi_oversold_signal(self):
        data = {"rsi_14": 25.0}
        signals = calculate_signals(data)
        assert signals["signal_rsi_oversold"] == 1
        assert signals["signal_rsi_overbought"] == 0

    def test_rsi_overbought_signal(self):
        data = {"rsi_14": 75.0}
        signals = calculate_signals(data)
        assert signals["signal_rsi_overbought"] == 1
        assert signals["signal_rsi_oversold"] == 0

    def test_rsi_neutral(self):
        data = {"rsi_14": 50.0}
        signals = calculate_signals(data)
        assert signals["signal_rsi_oversold"] == 0
        assert signals["signal_rsi_overbought"] == 0

    def test_52w_high_signal(self):
        data = {"pct_from_52w_high": -3.0, "week_52_high": 100.0, "close": 97.0}
        signals = calculate_signals(data)
        assert signals["signal_52w_high"] == 1

    def test_52w_low_signal(self):
        data = {"week_52_low": 50.0, "close": 52.0, "pct_from_52w_high": -20.0, "week_52_high": 65.0}
        signals = calculate_signals(data)
        assert signals["signal_52w_low"] == 1

    def test_volume_spike(self):
        data = {"volume_ratio": 2.5}
        signals = calculate_signals(data)
        assert signals["signal_volume_spike"] == 1

    def test_no_volume_spike(self):
        data = {"volume_ratio": 1.2}
        signals = calculate_signals(data)
        assert signals["signal_volume_spike"] == 0

    def test_golden_cross_from_ma(self):
        data = {"ma_50_above_200": 1}
        signals = calculate_signals(data)
        assert signals["signal_golden_cross"] == 1
        assert signals["signal_death_cross"] == 0

    def test_death_cross_from_ma(self):
        data = {"ma_50_above_200": 0}
        signals = calculate_signals(data)
        assert signals["signal_golden_cross"] == 0
        assert signals["signal_death_cross"] == 1

    def test_bullish_summary(self):
        """A strongly bullish asset should get a 'bullish' summary."""
        data = {
            "rsi_14": 25.0,  # oversold
            "pct_from_52w_high": -20.0,
            "week_52_high": 100.0,
            "week_52_low": 75.0,
            "close": 77.0,  # near 52w low
            "ma_50_above_200": 1,  # golden cross
            "above_ma_50": 1,
            "above_ma_200": 1,
            "volume_ratio": 1.5,
        }
        signals = calculate_signals(data)
        assert signals["signal_summary"] == "bullish"

    def test_bearish_summary(self):
        """A strongly bearish asset should get a 'bearish' summary."""
        data = {
            "rsi_14": 75.0,  # overbought
            "pct_from_52w_high": -2.0,
            "week_52_high": 100.0,
            "week_52_low": 60.0,
            "close": 98.0,  # near 52w high
            "ma_50_above_200": 0,  # death cross
            "above_ma_50": 0,
            "above_ma_200": 0,
            "volume_ratio": 1.0,
        }
        signals = calculate_signals(data)
        assert signals["signal_summary"] == "bearish"

    def test_neutral_summary(self):
        """A mixed-signal asset should get 'neutral'."""
        data = {
            "rsi_14": 50.0,
            "pct_from_52w_high": -15.0,
            "week_52_high": 100.0,
            "week_52_low": 70.0,
            "close": 85.0,
            "ma_50_above_200": 1,
            "above_ma_50": 1,
            "above_ma_200": 0,
            "volume_ratio": 1.0,
        }
        signals = calculate_signals(data)
        assert signals["signal_summary"] == "neutral"

    def test_missing_rsi_handled(self):
        data = {}
        signals = calculate_signals(data)
        assert signals["signal_rsi_oversold"] == 0
        assert signals["signal_rsi_overbought"] == 0
        assert signals.get("signal_summary") is not None
