"""
Combines the existing technical signal engine (used for stocks) with options
chain sentiment (PCR, Max Pain, OI buildup) to produce a CE/PE lean.

This is a probability-weighted heuristic, same philosophy as the stock
screener. It is NOT a prediction and does NOT account for time decay
(theta), which can lose you money even if your direction call is right.
"""

from data_fetch import fetch_history
from signal_engine import analyze_stock
from options_indicators import sentiment_summary


def build_options_view(access_token_summary: dict, chain_df, spot: float, underlying_yf_symbol: str) -> dict:
    """
    access_token_summary: not used directly here, kept for future extension.
    chain_df: DataFrame from options_indicators.chain_to_dataframe
    spot: current underlying spot price
    underlying_yf_symbol: e.g. "^NSEI" to pull the underlying's own technical trend
    """
    opt_sentiment = sentiment_summary(chain_df, spot)

    # Pull underlying's own technical bias (reuses the stock signal engine)
    underlying_trend = None
    try:
        df = fetch_history(underlying_yf_symbol, period="6mo")
        if not df.empty:
            summary = analyze_stock(df)
            if summary:
                underlying_trend = {
                    "signal": summary["signal"],
                    "score": summary["score"],
                    "rsi": summary["rsi"],
                }
    except Exception:
        underlying_trend = None

    # Combine into a CE/PE lean
    lean_score = 0
    reasons = []

    if opt_sentiment["pcr"] > 1.2:
        lean_score += 1
        reasons.append(f"PCR is {opt_sentiment['pcr']} — more puts written than calls, a bullish-leaning signal by convention")
    elif opt_sentiment["pcr"] < 0.8:
        lean_score -= 1
        reasons.append(f"PCR is {opt_sentiment['pcr']} — more calls written than puts, a bearish-leaning signal by convention")

    if opt_sentiment["put_oi_change_near_spot"] > opt_sentiment["call_oi_change_near_spot"]:
        lean_score += 1
        reasons.append("Put OI is building up faster near spot — suggests support forming below")
    elif opt_sentiment["call_oi_change_near_spot"] > opt_sentiment["put_oi_change_near_spot"]:
        lean_score -= 1
        reasons.append("Call OI is building up faster near spot — suggests resistance forming above")

    if underlying_trend:
        if underlying_trend["score"] > 0:
            lean_score += 1
            reasons.append(f"Underlying's own technical trend is {underlying_trend['signal']}")
        elif underlying_trend["score"] < 0:
            lean_score -= 1
            reasons.append(f"Underlying's own technical trend is {underlying_trend['signal']}")

    if lean_score >= 2:
        lean = "CE (Call) lean"
    elif lean_score <= -2:
        lean = "PE (Put) lean"
    else:
        lean = "No clear lean — mixed signals"

    return {
        "lean": lean,
        "lean_score": lean_score,
        "reasons": reasons,
        "options_sentiment": opt_sentiment,
        "underlying_trend": underlying_trend,
    }
