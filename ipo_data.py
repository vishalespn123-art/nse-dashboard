"""
Fetches upcoming/open/closed IPO data + GMP (Grey Market Premium) via the
free IPO Guru API.

IMPORTANT: GMP is NOT official exchange data. It comes from the informal,
unregulated "grey market" where IPO applications/shares trade before
listing. SEBI does not endorse or regulate it. Treat it as a sentiment
indicator only, never as a guarantee of listing price.
"""

import requests
import streamlit as st

BASE_URL = "https://www.ipoguru.in/api/v1"


@st.cache_data(ttl=900, show_spinner=False)  # GMP updates a few times a day - 15 min cache is plenty
def fetch_ipos(api_key: str, status: str = None, ipo_type: str = None) -> list:
    """
    status: 'open', 'upcoming', or 'closed' (None = all)
    ipo_type: 'mainboard' or 'sme' (None = both)
    Returns a list of IPO dicts, or [] on any failure.
    """
    if not api_key:
        return []

    headers = {"X-API-KEY": api_key}
    params = {}
    if status:
        params["status"] = status
    if ipo_type:
        params["type"] = ipo_type

    try:
        resp = requests.get(f"{BASE_URL}/ipos", headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", []) if data.get("success") else []
    except Exception:
        return []
