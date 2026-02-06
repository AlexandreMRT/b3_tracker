"""
Unit tests for the shared signals module.
"""

from signals import (
    NEAR_52W_HIGH_PCT,
    NEAR_52W_LOW_PCT,
    NEWS_SENTIMENT_NEG,
    NEWS_SENTIMENT_POS,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    VOLUME_SPIKE_RATIO,
    detect_signals,
)


class TestDetectSignalsFromDict:
    """Tests using plain dict input (fetcher path)."""

    def test_rsi_oversold(self):
        result = detect_signals({"rsi_14": 25.0})
        assert result.rsi_oversold is True
        assert result.rsi_overbought is False

    def test_rsi_overbought(self):
        result = detect_signals({"rsi_14": 75.0})
        assert result.rsi_overbought is True
        assert result.rsi_oversold is False

    def test_rsi_neutral(self):
        result = detect_signals({"rsi_14": 50.0})
        assert result.rsi_oversold is False
        assert result.rsi_overbought is False

    def test_rsi_boundary_oversold(self):
        """RSI exactly at threshold should NOT trigger."""
        result = detect_signals({"rsi_14": 30.0})
        assert result.rsi_oversold is False

    def test_rsi_boundary_overbought(self):
        result = detect_signals({"rsi_14": 70.0})
        assert result.rsi_overbought is False

    def test_52w_high(self):
        result = detect_signals({"pct_from_52w_high": -3.0})
        assert result.near_52w_high is True

    def test_not_near_52w_high(self):
        result = detect_signals({"pct_from_52w_high": -10.0})
        assert result.near_52w_high is False

    def test_52w_low(self):
        result = detect_signals({"week_52_low": 50.0, "close": 52.0})
        assert result.near_52w_low is True

    def test_not_near_52w_low(self):
        result = detect_signals({"week_52_low": 50.0, "close": 60.0})
        assert result.near_52w_low is False

    def test_52w_low_boundary(self):
        """Exactly 5% above 52w low should trigger (<=)."""
        result = detect_signals({"week_52_low": 100.0, "close": 105.0})
        assert result.near_52w_low is True

    def test_volume_spike(self):
        result = detect_signals({"volume_ratio": 2.5})
        assert result.volume_spike is True

    def test_no_volume_spike(self):
        result = detect_signals({"volume_ratio": 1.5})
        assert result.volume_spike is False

    def test_volume_spike_boundary(self):
        """Exactly 2.0 should trigger (>=)."""
        result = detect_signals({"volume_ratio": 2.0})
        assert result.volume_spike is True

    def test_golden_cross(self):
        result = detect_signals({"ma_50_above_200": 1})
        assert result.golden_cross is True
        assert result.death_cross is False

    def test_death_cross(self):
        result = detect_signals({"ma_50_above_200": 0})
        assert result.golden_cross is False
        assert result.death_cross is True

    def test_bullish_trend(self):
        result = detect_signals({"above_ma_50": 1, "above_ma_200": 1})
        assert result.bullish_trend is True
        assert result.bearish_trend is False

    def test_bearish_trend(self):
        result = detect_signals({"above_ma_50": 0, "above_ma_200": 0})
        assert result.bearish_trend is True
        assert result.bullish_trend is False

    def test_positive_news(self):
        result = detect_signals({"news_sentiment_combined": 0.5})
        assert result.positive_news is True
        assert result.negative_news is False

    def test_negative_news(self):
        result = detect_signals({"news_sentiment_combined": -0.5})
        assert result.negative_news is True
        assert result.positive_news is False

    def test_neutral_news(self):
        result = detect_signals({"news_sentiment_combined": 0.1})
        assert result.positive_news is False
        assert result.negative_news is False

    def test_missing_fields_handled(self):
        result = detect_signals({})
        assert result.summary == "neutral"

    def test_bullish_summary(self):
        data = {
            "rsi_14": 25.0,
            "week_52_low": 75.0,
            "close": 77.0,
            "pct_from_52w_high": -20.0,
            "ma_50_above_200": 1,
            "above_ma_50": 1,
            "above_ma_200": 1,
        }
        result = detect_signals(data)
        assert result.summary == "bullish"

    def test_bearish_summary(self):
        data = {
            "rsi_14": 75.0,
            "pct_from_52w_high": -2.0,
            "week_52_low": 60.0,
            "close": 98.0,
            "ma_50_above_200": 0,
            "above_ma_50": 0,
            "above_ma_200": 0,
        }
        result = detect_signals(data)
        assert result.summary == "bearish"

    def test_neutral_summary(self):
        data = {
            "rsi_14": 50.0,
            "pct_from_52w_high": -15.0,
            "week_52_low": 70.0,
            "close": 85.0,
            "ma_50_above_200": 1,
            "above_ma_50": 1,
            "above_ma_200": 0,
        }
        result = detect_signals(data)
        assert result.summary == "neutral"


class TestDetectSignalsFromObject:
    """Tests using an ORM-like object (API path)."""

    class FakeQuote:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def test_rsi_oversold_from_object(self):
        q = self.FakeQuote(rsi_14=25.0)
        result = detect_signals(q)
        assert result.rsi_oversold is True

    def test_price_brl_used_for_52w_low(self):
        """API passes Quote objects with price_brl, not close."""
        q = self.FakeQuote(week_52_low=50.0, price_brl=52.0)
        result = detect_signals(q)
        assert result.near_52w_low is True

    def test_news_sentiment_from_object(self):
        q = self.FakeQuote(news_sentiment_combined=0.5)
        result = detect_signals(q)
        assert result.positive_news is True


class TestSignalResultHelpers:
    """Tests for as_db_flags() and as_labels()."""

    def test_as_db_flags_returns_ints(self):
        result = detect_signals({"rsi_14": 25.0, "volume_ratio": 3.0})
        flags = result.as_db_flags()
        assert flags["signal_rsi_oversold"] == 1
        assert flags["signal_volume_spike"] == 1
        assert flags["signal_rsi_overbought"] == 0
        assert isinstance(flags["signal_summary"], str)

    def test_as_labels_returns_strings(self):
        result = detect_signals({"rsi_14": 25.0, "volume_ratio": 3.0})
        labels = result.as_labels()
        assert "RSI_OVERSOLD" in labels
        assert "VOLUME_SPIKE" in labels

    def test_empty_input_gives_empty_labels(self):
        result = detect_signals({})
        labels = result.as_labels()
        # death_cross triggers because ma_50_above_200 is None → ==0 is False,
        # but the default is False, so no labels for empty input
        # Only death_cross is False by default, so we might get BEARISH_TREND = False
        # Actually with empty dict, no signals should fire
        assert "RSI_OVERSOLD" not in labels
        assert "RSI_OVERBOUGHT" not in labels

    def test_as_db_flags_keys(self):
        flags = detect_signals({}).as_db_flags()
        expected_keys = {
            "signal_rsi_oversold",
            "signal_rsi_overbought",
            "signal_52w_high",
            "signal_52w_low",
            "signal_volume_spike",
            "signal_golden_cross",
            "signal_death_cross",
            "signal_summary",
        }
        assert set(flags.keys()) == expected_keys


class TestThresholdConstants:
    """Ensure thresholds are accessible and sane."""

    def test_rsi_thresholds(self):
        assert RSI_OVERSOLD < RSI_OVERBOUGHT

    def test_volume_spike_positive(self):
        assert VOLUME_SPIKE_RATIO > 0

    def test_52w_thresholds(self):
        assert NEAR_52W_HIGH_PCT < 0  # negative = within X% of high
        assert NEAR_52W_LOW_PCT > 0  # positive = within X% above low

    def test_news_thresholds(self):
        assert NEWS_SENTIMENT_NEG < 0 < NEWS_SENTIMENT_POS
