"""
Signal scoring engine.

IMPORTANT: This does NOT predict future prices. It combines well-known
technical indicators into a probability-based score, the same way most
retail trading tools work. Score is out of +5 (strong bullish) to -5
(strong bearish). Treat it as one input, not a guarantee.
"""

import pandas as pd
from indicators import add_all_indicators


SIGNAL_LABELS = {
    5: "Strong Buy", 4: "Strong Buy",
    3: "Buy", 2: "Buy",
    1: "Weak Buy",
    0: "Neutral",
    -1: "Weak Sell",
    -2: "Sell", -3: "Sell",
    -4: "Strong Sell", -5: "Strong Sell",
}


def score_row(row: pd.Series) -> int:
    """
    Compute a score for a single row (latest day) based on indicator values.
    Each rule contributes -1, 0, or +1 to the total score.
    """
    score = 0

    # 1. Trend: price vs SMA50 and SMA200 (golden/death cross style)
    if pd.notna(row.get("SMA50")) and pd.notna(row.get("SMA200")):
        if row["SMA50"] > row["SMA200"]:
            score += 1
        elif row["SMA50"] < row["SMA200"]:
            score -= 1

    # 2. Price vs SMA20 (short-term trend)
    if pd.notna(row.get("SMA20")) and pd.notna(row.get("Close")):
        if row["Close"] > row["SMA20"]:
            score += 1
        else:
            score -= 1

    # 3. RSI zones
    rsi_val = row.get("RSI14")
    if pd.notna(rsi_val):
        if rsi_val < 30:
            score += 1  # oversold -> potential bounce
        elif rsi_val > 70:
            score -= 1  # overbought -> potential pullback

    # 4. MACD crossover
    if pd.notna(row.get("MACD")) and pd.notna(row.get("MACD_Signal")):
        if row["MACD"] > row["MACD_Signal"]:
            score += 1
        else:
            score -= 1

    # 5. Volume confirmation - only counts if price also moved up/down that day
    if row.get("VolSpike") and pd.notna(row.get("Close")) and pd.notna(row.get("SMA20")):
        if row["Close"] > row["SMA20"]:
            score += 1
        else:
            score -= 1

    return score


def label_for_score(score: int) -> str:
    score = max(-5, min(5, score))
    return SIGNAL_LABELS[score]


def analyze_stock(df: pd.DataFrame) -> dict:
    """
    Run indicators + scoring on a single stock's OHLCV DataFrame.
    Returns a dict summary for the latest available day.
    """
    if df is None or df.empty or len(df) < 60:
        return None

    df_ind = add_all_indicators(df)
    latest = df_ind.iloc[-1]

    score = score_row(latest)
    label = label_for_score(score)

    return {
        "close": round(float(latest["Close"]), 2),
        "score": score,
        "signal": label,
        "rsi": round(float(latest["RSI14"]), 1) if pd.notna(latest["RSI14"]) else None,
        "sma20": round(float(latest["SMA20"]), 2) if pd.notna(latest["SMA20"]) else None,
        "sma50": round(float(latest["SMA50"]), 2) if pd.notna(latest["SMA50"]) else None,
        "sma200": round(float(latest["SMA200"]), 2) if pd.notna(latest["SMA200"]) else None,
        "macd_bullish": bool(latest["MACD"] > latest["MACD_Signal"]) if pd.notna(latest["MACD"]) else None,
        "vol_spike": bool(latest["VolSpike"]) if pd.notna(latest["VolSpike"]) else False,
        "df": df_ind,
    }
