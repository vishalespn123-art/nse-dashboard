"""
Fetches option chain data from the Upstox API.
"""

import requests
import streamlit as st

BASE_URL = "https://api.upstox.com/v2"

# Common index instrument keys (Upstox format).
INDEX_INSTRUMENTS = {
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "BANK NIFTY": "NSE_INDEX|Nifty Bank",
    "FIN NIFTY": "NSE_INDEX|Nifty Fin Service",
}

# Matching yfinance symbols, used to pull the underlying's technical trend.
INDEX_YF_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "FIN NIFTY": "NIFTY_FIN_SERVICE.NS",  # fallback; may not always resolve
}


def _headers(access_token: str) -> dict:
    return {"Accept": "application/json", "Authorization": f"Bearer {access_token}"}


@st.cache_data(ttl=300, show_spinner=False)
def get_expiries(access_token: str, instrument_key: str) -> list:
    """Fetch available expiry dates for an instrument by listing its option contracts."""
    url = f"{BASE_URL}/option/contract"
    params = {"instrument_key": instrument_key}
    resp = requests.get(url, headers=_headers(access_token), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    expiries = sorted(set(item["expiry"] for item in data if "expiry" in item))
    return expiries


@st.cache_data(ttl=120, show_spinner=False)
def get_option_chain(access_token: str, instrument_key: str, expiry_date: str) -> list:
    """
    Fetch the full option chain (all strikes) for an instrument + expiry.
    Returns the raw list of strike-level records from Upstox.
    """
    url = f"{BASE_URL}/option/chain"
    params = {"instrument_key": instrument_key, "expiry_date": expiry_date}
    resp = requests.get(url, headers=_headers(access_token), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])
