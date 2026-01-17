"""
Algorithmic scoring service for watchlists.
"""
from typing import Dict, List, Any


def build_algorithmic_watchlist(
    items: List[Dict[str, Any]],
    min_score: float = 3.0,
    max_items: int = 12,
) -> Dict[str, List[Dict[str, Any]]]:
    """Score assets to build an algorithmic watchlist (not financial advice)."""
    candidates: List[Dict[str, Any]] = []
    avoid_list: List[Dict[str, Any]] = []

    def add_reason(reasons: List[str], label: str) -> None:
        if label not in reasons:
            reasons.append(label)

    for r in items:
        if r.get("tipo") not in ("stock", "us_stock"):
            continue

        score = 0.0
        reasons: List[str] = []
        risk_flags: List[str] = []

        rsi = r.get("rsi_14")
        if rsi is not None:
            if rsi < 25:
                score += 3.0
                add_reason(reasons, "rsi_extreme_oversold")
            elif rsi < 30:
                score += 2.0
                add_reason(reasons, "rsi_oversold")
            elif rsi > 80:
                score -= 3.0
                add_reason(risk_flags, "rsi_extreme_overbought")
            elif rsi > 70:
                score -= 2.0
                add_reason(risk_flags, "rsi_overbought")

        summary = r.get("signal_summary")
        if summary == "bullish":
            score += 2.0
            add_reason(reasons, "bullish_trend")
        elif summary == "bearish":
            score -= 2.0
            add_reason(risk_flags, "bearish_trend")

        if r.get("signal_golden_cross") == 1:
            score += 1.0
            add_reason(reasons, "golden_cross")

        if r.get("above_ma_50"):
            score += 0.5
            add_reason(reasons, "above_ma50")

        if r.get("above_ma_200"):
            score += 0.5
            add_reason(reasons, "above_ma200")

        if r.get("signal_52w_low") == 1:
            score += 1.0
            add_reason(reasons, "near_52w_low")

        if r.get("signal_52w_high") == 1:
            score -= 1.0
            add_reason(risk_flags, "near_52w_high")

        if r.get("signal_volume_spike") == 1:
            score += 0.5
            add_reason(reasons, "volume_spike")

        news = r.get("news_sentiment_combined")
        if news is not None:
            if news >= 0.4:
                score += 2.0
                add_reason(reasons, "news_positive_strong")
            elif news >= 0.2:
                score += 1.0
                add_reason(reasons, "news_positive")
            elif news <= -0.4:
                score -= 2.0
                add_reason(risk_flags, "news_negative_strong")
            elif news <= -0.2:
                score -= 1.0
                add_reason(risk_flags, "news_negative")

        var_ytd = r.get("var_ytd")
        if var_ytd is not None:
            if var_ytd >= 20:
                score += 1.0
                add_reason(reasons, "ytd_strong")
            elif var_ytd <= -20:
                score -= 1.0
                add_reason(risk_flags, "ytd_weak")

        entry = {
            "ticker": r.get("ticker"),
            "nome": r.get("nome"),
            "score": round(score, 2),
            "rsi_14": rsi,
            "var_ytd": r.get("var_ytd"),
            "news_sentiment": news,
            "signal_summary": summary,
            "reasons": reasons,
            "risk_flags": risk_flags,
        }

        if score >= min_score:
            candidates.append(entry)
        elif score <= -2.0:
            avoid_list.append(entry)

    candidates.sort(key=lambda x: (x["score"], -(x["rsi_14"] or 0)), reverse=True)
    avoid_list.sort(key=lambda x: x["score"])

    return {
        "watchlist": candidates[:max_items],
        "avoid_list": avoid_list[:max_items],
    }