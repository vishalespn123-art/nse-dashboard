"""
Data fetching layer built on yfinance for NSE-listed stocks.
Symbols must be in Yahoo Finance format, e.g. "RELIANCE.NS".
"""

import time
import yfinance as yf
import pandas as pd
import streamlit as st


@st.cache_data(ttl=900, show_spinner=False)  # cache for 15 minutes
def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch historical OHLCV data for a single symbol."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return pd.DataFrame()


def _fetch_batch_uncached(symbols: list, period: str = "1y", interval: str = "1d",
                           retry_missing: bool = True) -> dict:
    """
    Fetch multiple symbols using yfinance's batch download.
    Falls back to fetching each missing symbol individually, since Yahoo
    Finance frequently drops symbols silently from large batch requests
    (rate limiting), especially with threading enabled.
    """
    result = {}
    if not symbols:
        return result

    try:
        data = yf.download(
            tickers=symbols,
            period=period,
            interval=interval,
            group_by="ticker",
            threads=False,       # sequential is slower but far more reliable with Yahoo
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        data = None

    if data is not None and not data.empty:
        if len(symbols) == 1:
            sym = symbols[0]
            df = data.copy()
            if not df.empty:
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if not df.empty:
                    result[sym] = df
        else:
            for sym in symbols:
                try:
                    df = data[sym][["Open", "High", "Low", "Close", "Volume"]].dropna()
                    if not df.empty:
                        result[sym] = df
                except Exception:
                    continue

    # Retry any symbol that didn't come back from the batch call, one by one.
    if retry_missing:
        missing = [s for s in symbols if s not in result]
        for sym in missing:
            try:
                df = yf.Ticker(sym).history(period=period, interval=interval)
                if df is not None and not df.empty:
                    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                    if not df.empty:
                        result[sym] = df
                time.sleep(0.15)  # small pause to avoid tripping rate limits
            except Exception:
                continue

    return result


@st.cache_data(ttl=900, show_spinner=False)
def fetch_batch(symbols: list, period: str = "1y", interval: str = "1d") -> dict:
    """Cached wrapper around _fetch_batch_uncached."""
    return _fetch_batch_uncached(symbols, period, interval)


def chunked(lst, size):
    """Yield successive chunks from list."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]
