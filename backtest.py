"""
Backtesting engine.

For every historical day, computes the signal score (using only data available
up to that day - no lookahead bias) and checks what happened to price N days
later. This gives an honest, historical picture of how well the scoring
system has worked - NOT a promise of future performance.
"""

import pandas as pd
import numpy as np
from indicators import add_all_indicators
from signal_engine import score_row


def backtest_stock(df: pd.DataFrame, forward_days: int = 5, buy_threshold: int = 2,
                    sell_threshold: int = -2, cost_pct: float = 0.3) -> dict:
    """
    Run a backtest on a single stock's historical OHLCV data.

    buy_threshold: score >= this value counts as a "Buy" signal day
    sell_threshold: score <= this value counts as a "Sell" signal day
    forward_days: how many trading days later we check the outcome
    cost_pct: total round-trip cost as a % of trade value, deducted from every
        trade's return. Covers brokerage + STT + estimated slippage combined.
        Default 0.3% is a reasonable estimate for NSE delivery trades via a
        discount broker (STT ~0.1-0.2% round trip + slippage). Intraday/
        options costs differ - adjust if backtesting those separately.
    """
    if df is None or len(df) < 220:
        return None

    df_ind = add_all_indicators(df)
    df_ind = df_ind.reset_index(drop=True)

    scores = []
    for i in range(len(df_ind)):
        scores.append(score_row(df_ind.iloc[i]))
    df_ind["Score"] = scores

    closes = df_ind["Close"].values
    n = len(df_ind)

    buy_trades = []   # forward returns after a buy signal
    sell_trades = []  # forward returns after a sell signal (inverse logic)

    for i in range(n - forward_days):
        score = df_ind["Score"].iloc[i]
        entry_price = closes[i]
        exit_price = closes[i + forward_days]
        if entry_price == 0 or np.isnan(entry_price) or np.isnan(exit_price):
            continue
        fwd_return = (exit_price - entry_price) / entry_price * 100
        net_return = fwd_return - cost_pct  # deduct round-trip cost from every trade

        if score >= buy_threshold:
            buy_trades.append(net_return)
        elif score <= sell_threshold:
            # for a short/put-style trade, cost still eats into the return the same way
            sell_trades.append(fwd_return - cost_pct)

    def summarize(trades, positive_is_win=True):
        if not trades:
            return {"count": 0, "win_rate": None, "avg_return": None}
        trades = np.array(trades)
        if positive_is_win:
            wins = (trades > 0).sum()
        else:
            wins = (trades < 0).sum()
        return {
            "count": len(trades),
            "win_rate": round(wins / len(trades) * 100, 1),
            "avg_return": round(float(trades.mean()), 2),
        }

    buy_summary = summarize(buy_trades, positive_is_win=True)
    sell_summary = summarize(sell_trades, positive_is_win=False)  # win = price fell as expected

    # Baseline: what if you just bought randomly / always (buy & hold every day)?
    baseline_returns = []
    for i in range(n - forward_days):
        entry = closes[i]
        exitp = closes[i + forward_days]
        if entry == 0 or np.isnan(entry) or np.isnan(exitp):
            continue
        baseline_returns.append((exitp - entry) / entry * 100)
    baseline_avg = round(float(np.mean(baseline_returns)), 2) if baseline_returns else None

    return {
        "buy_signals": buy_summary,
        "sell_signals": sell_summary,
        "baseline_avg_return_pct": baseline_avg,
        "forward_days": forward_days,
        "total_days_tested": n,
        "cost_pct_applied": cost_pct,
    }
