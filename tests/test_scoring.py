"""
Unit tests for the scoring module (build_algorithmic_watchlist).
These are pure-function tests – no DB, no network.
"""

from scoring import build_algorithmic_watchlist

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(**overrides) -> dict:
    """Build a minimal quote-like dict for the scorer."""
    base = {
        "ticker": "TEST4.SA",
        "nome": "Test Stock",
        "tipo": "stock",
        "rsi_14": 50.0,
        "signal_summary": "neutral",
        "signal_golden_cross": 0,
        "above_ma_50": False,
        "above_ma_200": False,
        "signal_52w_low": 0,
        "signal_52w_high": 0,
        "signal_volume_spike": 0,
        "news_sentiment_combined": 0.0,
        "var_ytd": 0.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScoringBasic:
    """Basic scoring behaviour."""

    def test_empty_list_returns_empty(self):
        result = build_algorithmic_watchlist([])
        assert result == {"watchlist": [], "avoid_list": []}

    def test_non_stock_assets_are_skipped(self):
        items = [
            _make_item(tipo="crypto", ticker="BTC-USD"),
            _make_item(tipo="commodity", ticker="GC=F"),
            _make_item(tipo="currency", ticker="USDBRL=X"),
        ]
        result = build_algorithmic_watchlist(items)
        assert result["watchlist"] == []
        assert result["avoid_list"] == []

    def test_stock_and_us_stock_are_both_scored(self):
        items = [
            _make_item(tipo="stock", ticker="PETR4.SA", rsi_14=20, signal_summary="bullish"),
            _make_item(tipo="us_stock", ticker="AAPL", rsi_14=20, signal_summary="bullish"),
        ]
        result = build_algorithmic_watchlist(items, min_score=0)
        tickers = [e["ticker"] for e in result["watchlist"]]
        assert "PETR4.SA" in tickers
        assert "AAPL" in tickers


class TestRSIScoring:
    """RSI contribution to score."""

    def test_extreme_oversold_adds_3(self):
        item = _make_item(rsi_14=20)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert "rsi_extreme_oversold" in entry["reasons"]
        assert entry["score"] >= 3.0

    def test_oversold_adds_2(self):
        item = _make_item(rsi_14=28)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert "rsi_oversold" in entry["reasons"]

    def test_extreme_overbought_subtracts_3(self):
        item = _make_item(rsi_14=85)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert "rsi_extreme_overbought" in entry["risk_flags"]
        assert entry["score"] <= -3.0

    def test_overbought_subtracts_2(self):
        item = _make_item(rsi_14=75)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert "rsi_overbought" in entry["risk_flags"]

    def test_neutral_rsi_no_contribution(self):
        item = _make_item(rsi_14=50)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert "rsi_extreme_oversold" not in entry["reasons"]
        assert "rsi_oversold" not in entry["reasons"]
        assert "rsi_extreme_overbought" not in entry["risk_flags"]
        assert "rsi_overbought" not in entry["risk_flags"]

    def test_none_rsi_is_handled(self):
        item = _make_item(rsi_14=None)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert entry["rsi_14"] is None


class TestSignalScoring:
    """Signal-based scoring contributions."""

    def test_bullish_signal_adds_2(self):
        item = _make_item(signal_summary="bullish")
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "bullish_trend" in result["watchlist"][0]["reasons"]

    def test_bearish_signal_subtracts_2(self):
        item = _make_item(signal_summary="bearish")
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "bearish_trend" in result["watchlist"][0]["risk_flags"]

    def test_golden_cross_adds_1(self):
        item = _make_item(signal_golden_cross=1)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "golden_cross" in result["watchlist"][0]["reasons"]

    def test_above_ma50_adds_half(self):
        item = _make_item(above_ma_50=True)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "above_ma50" in result["watchlist"][0]["reasons"]

    def test_above_ma200_adds_half(self):
        item = _make_item(above_ma_200=True)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "above_ma200" in result["watchlist"][0]["reasons"]

    def test_near_52w_low_adds_1(self):
        item = _make_item(signal_52w_low=1)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "near_52w_low" in result["watchlist"][0]["reasons"]

    def test_near_52w_high_subtracts_1(self):
        item = _make_item(signal_52w_high=1)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "near_52w_high" in result["watchlist"][0]["risk_flags"]

    def test_volume_spike_adds_half(self):
        item = _make_item(signal_volume_spike=1)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "volume_spike" in result["watchlist"][0]["reasons"]


class TestNewsSentimentScoring:
    """News sentiment contribution."""

    def test_strong_positive_news(self):
        item = _make_item(news_sentiment_combined=0.5)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "news_positive_strong" in result["watchlist"][0]["reasons"]

    def test_moderate_positive_news(self):
        item = _make_item(news_sentiment_combined=0.25)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "news_positive" in result["watchlist"][0]["reasons"]

    def test_strong_negative_news(self):
        item = _make_item(news_sentiment_combined=-0.5)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "news_negative_strong" in result["watchlist"][0]["risk_flags"]

    def test_moderate_negative_news(self):
        item = _make_item(news_sentiment_combined=-0.25)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "news_negative" in result["watchlist"][0]["risk_flags"]

    def test_none_news_handled(self):
        item = _make_item(news_sentiment_combined=None)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert entry["news_sentiment"] is None


class TestYTDScoring:
    """Year-to-date performance contribution."""

    def test_strong_ytd_adds_1(self):
        item = _make_item(var_ytd=25.0)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "ytd_strong" in result["watchlist"][0]["reasons"]

    def test_weak_ytd_subtracts_1(self):
        item = _make_item(var_ytd=-25.0)
        result = build_algorithmic_watchlist([item], min_score=-100)
        assert "ytd_weak" in result["watchlist"][0]["risk_flags"]

    def test_none_ytd_handled(self):
        item = _make_item(var_ytd=None)
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert entry["var_ytd"] is None


class TestWatchlistOutput:
    """Output structure and sorting."""

    def test_min_score_filters_candidates(self):
        items = [
            _make_item(ticker="A", rsi_14=50),  # score ~0
            _make_item(ticker="B", rsi_14=20, signal_summary="bullish"),  # score high
        ]
        result = build_algorithmic_watchlist(items, min_score=3.0)
        tickers = [e["ticker"] for e in result["watchlist"]]
        assert "B" in tickers
        assert "A" not in tickers

    def test_avoid_list_populated_for_very_negative_scores(self):
        item = _make_item(rsi_14=85, signal_summary="bearish")
        result = build_algorithmic_watchlist([item])
        assert len(result["avoid_list"]) > 0
        assert result["avoid_list"][0]["score"] <= -2.0

    def test_max_items_limits_output(self):
        items = [_make_item(ticker=f"T{i}", rsi_14=20, signal_summary="bullish") for i in range(20)]
        result = build_algorithmic_watchlist(items, min_score=0, max_items=5)
        assert len(result["watchlist"]) <= 5

    def test_watchlist_sorted_by_score_desc(self):
        items = [
            _make_item(ticker="LOW", rsi_14=28),  # score ~2
            _make_item(ticker="HIGH", rsi_14=20, signal_summary="bullish"),  # score ~5+
        ]
        result = build_algorithmic_watchlist(items, min_score=0)
        scores = [e["score"] for e in result["watchlist"]]
        assert scores == sorted(scores, reverse=True)

    def test_output_entry_shape(self):
        item = _make_item()
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        expected_keys = {
            "ticker",
            "nome",
            "score",
            "rsi_14",
            "var_ytd",
            "news_sentiment",
            "signal_summary",
            "reasons",
            "risk_flags",
        }
        assert set(entry.keys()) == expected_keys


class TestCompositeScoring:
    """Test combined scoring from multiple factors."""

    def test_perfect_bull_case(self):
        """Asset with every bullish signal should have a high score."""
        item = _make_item(
            rsi_14=20,  # +3
            signal_summary="bullish",  # +2
            signal_golden_cross=1,  # +1
            above_ma_50=True,  # +0.5
            above_ma_200=True,  # +0.5
            signal_52w_low=1,  # +1
            signal_volume_spike=1,  # +0.5
            news_sentiment_combined=0.5,  # +2
            var_ytd=25.0,  # +1
        )
        result = build_algorithmic_watchlist([item], min_score=-100)
        entry = result["watchlist"][0]
        assert entry["score"] == 11.5

    def test_perfect_bear_case(self):
        """Asset with every bearish signal should have a very negative score."""
        item = _make_item(
            rsi_14=85,  # -3
            signal_summary="bearish",  # -2
            signal_52w_high=1,  # -1
            news_sentiment_combined=-0.5,  # -2
            var_ytd=-25.0,  # -1
        )
        result = build_algorithmic_watchlist([item])
        entry = result["avoid_list"][0]
        assert entry["score"] == -9.0
