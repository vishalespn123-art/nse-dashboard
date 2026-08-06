"""
Equity historical data via Upstox API (instead of scraping Yahoo Finance).

Why: Yahoo Finance rate-limits/blocks large batch requests, which is why the
screener was returning only a handful of stocks out of 500. Upstox is the
same authenticated connection already used for options, so using it for
equity data too means one consistent, reliable data source instead of two.

NOTE on corporate actions: Upstox's historical candle API returns raw
traded prices. It is NOT guaranteed to be split/bonus-adjusted the way
`auto_adjust=True` in yfinance attempts to do. If a stock in your scan shows
a sudden implausible jump/drop, check for a recent split, bonus, or
dividend - the indicators (SMA/RSI) will misread that day as a real
price move otherwise. A full corporate-action adjustment feed (from
NSE/BSE bhavcopy) is a bigger project - see README roadmap.
"""

import time
import datetime as dt
import requests
import pandas as pd
import streamlit as st

from stock_list import SYMBOL_TO_ISIN

BASE_URL = "https://api.upstox.com/v2"


def _headers(access_token: str) -> dict:
    return {"Accept": "application/json", "Authorization": f"Bearer {access_token}"}


def symbol_to_instrument_key(symbol: str) -> str | None:
    """Convert a plain NSE symbol (e.g. 'RELIANCE') to an Upstox instrument key."""
    isin = SYMBOL_TO_ISIN.get(symbol)
    if not isin:
        return None
    return f"NSE_EQ|{isin}"


@st.cache_data(ttl=900, show_spinner=False)
def fetch_history_upstox(access_token: str, symbol: str, days_back: int = 400,
                          interval: str = "day") -> pd.DataFrame:
    """
    Fetch historical OHLCV for a single NSE equity symbol via Upstox.
    `symbol` should be the plain NSE symbol without ".NS" (e.g. "RELIANCE").
    """
    instrument_key = symbol_to_instrument_key(symbol)
    if not instrument_key:
        return pd.DataFrame()

    to_date = dt.date.today().isoformat()
    from_date = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()

    url = f"{BASE_URL}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
    try:
        resp = requests.get(url, headers=_headers(access_token), timeout=15)
        if resp.status_code != 200:
            return pd.DataFrame()
        candles = resp.json().get("data", {}).get("candles", [])
    except Exception:
        return pd.DataFrame()

    if not candles:
        return pd.DataFrame()

    # Each candle: [timestamp, open, high, low, close, volume, open_interest]
    df = pd.DataFrame(candles, columns=["Date", "Open", "High", "Low", "Close", "Volume", "OI"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df[["Open", "High", "Low", "Close", "Volume"]]


def fetch_batch_upstox(access_token: str, symbols: list, days_back: int = 400,
                        interval: str = "day", pause: float = 0.1) -> dict:
    """
    Fetch multiple NSE symbols via Upstox, sequentially (Upstox has per-second
    rate limits too, so a small pause between calls avoids 429s).
    `symbols` should be plain NSE symbols without ".NS".
    Returns {symbol: DataFrame}.
    """
    result = {}
    for sym in symbols:
        df = fetch_history_upstox(access_token, sym, days_back=days_back, interval=interval)
        if not df.empty:
            result[sym] = df
        time.sleep(pause)
    return result
