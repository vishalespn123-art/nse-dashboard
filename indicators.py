"""
Technical indicator calculations.
All functions take a pandas DataFrame with columns: Open, High, Low, Close, Volume
and return either a Series or add columns to the DataFrame.
"""

import pandas as pd
import numpy as np


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (0-100). <30 oversold, >70 overbought."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    # Wilder's smoothing after the initial window
    for i in range(window, len(gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (window - 1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (window - 1) + loss.iloc[i]) / window

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    rsi_val = rsi_val.fillna(50)  # neutral when undefined
    return rsi_val


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD (Moving Average Convergence Divergence)
    Returns (macd_line, signal_line, histogram)
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def volume_spike(volume: pd.Series, window: int = 20, threshold: float = 1.5) -> pd.Series:
    """
    Returns boolean series: True where volume is `threshold`x above its rolling average.
    """
    avg_vol = volume.rolling(window=window, min_periods=window).mean()
    return volume > (avg_vol * threshold)


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    """Returns (upper_band, middle_band, lower_band)"""
    middle = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    return upper, middle, lower


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicator columns to a price DataFrame (Open, High, Low, Close, Volume)."""
    out = df.copy()
    out["SMA20"] = sma(out["Close"], 20)
    out["SMA50"] = sma(out["Close"], 50)
    out["SMA200"] = sma(out["Close"], 200)
    out["EMA20"] = ema(out["Close"], 20)
    out["RSI14"] = rsi(out["Close"], 14)
    macd_line, signal_line, hist = macd(out["Close"])
    out["MACD"] = macd_line
    out["MACD_Signal"] = signal_line
    out["MACD_Hist"] = hist
    out["VolSpike"] = volume_spike(out["Volume"])
    upper, mid, lower = bollinger_bands(out["Close"])
    out["BB_Upper"] = upper
    out["BB_Mid"] = mid
    out["BB_Lower"] = lower
    return out
