"""
Fetches IPO data from two sources:
1. ipoalerts.in - instant free self-serve API key, gives IPO dates, price
   band, issue size, listing gain (core IPO details).
2. IPO Guru - free but manually-issued API key, gives GMP (Grey Market
   Premium). Optional - if not configured, IPOs just show without GMP.

IMPORTANT: GMP is NOT official exchange data. It comes from the informal,
unregulated "grey market" where IPO applications/shares trade before
listing. SEBI does not endorse or regulate it. Treat it as a sentiment
indicator only, never as a guarantee of listing price.
"""

import requests
import streamlit as st

IPOALERTS_BASE_URL = "https://api.ipoalerts.in"
IPOGURU_BASE_URL = "https://www.ipoguru.in/api/v1"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ipos_core(api_key: str, status: str = None, ipo_type: str = None) -> list:
    """
    Core IPO details (dates, price band, issue size) from ipoalerts.in.
    status: 'open', 'upcoming', 'closed', 'listed', 'announced' (None = all)
    ipo_type: 'EQ' (mainboard) or 'SME' (None = both)
    """
    if not api_key:
        return []

    headers = {"x-api-key": api_key}
    params = {"page": 1, "limit": 50}
    if status:
        params["status"] = status
    if ipo_type:
        params["type"] = ipo_type

    try:
        resp = requests.get(f"{IPOALERTS_BASE_URL}/ipos", headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("ipos", [])
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)  # GMP updates more often - shorter cache
def fetch_gmp_lookup(api_key: str) -> dict:
    """
    Fetches GMP data from IPO Guru and returns a lookup dict keyed by a
    normalized (lowercased) company name, so it can be merged into the
    ipoalerts data by matching names.
    """
    if not api_key:
        return {}

    headers = {"X-API-KEY": api_key}
    try:
        resp = requests.get(f"{IPOGURU_BASE_URL}/ipos", headers=headers, timeout=15)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        items = data.get("data", []) if data.get("success") else []
    except Exception:
        return {}

    lookup = {}
    for item in items:
        name = (item.get("name") or "").lower().strip()
        if name:
            lookup[name] = item.get("gmp")
    return lookup


def _find_gmp_match(ipo_name: str, gmp_lookup: dict):
    """Fuzzy-ish match: exact match first, then substring match either way."""
    name_lower = (ipo_name or "").lower().strip()
    if name_lower in gmp_lookup:
        return gmp_lookup[name_lower]
    for key, val in gmp_lookup.items():
        if key in name_lower or name_lower in key:
            return val
    return None


def fetch_ipos(ipoalerts_key: str, ipoguru_key: str = None,
                status: str = None, ipo_type: str = None) -> list:
    """
    Combines ipoalerts.in (core details) with IPO Guru (GMP) if the second
    key is provided. Returns a list of normalized IPO dicts ready for the UI.
    """
    core_ipos = fetch_ipos_core(ipoalerts_key, status=status, ipo_type=ipo_type)
    gmp_lookup = fetch_gmp_lookup(ipoguru_key) if ipoguru_key else {}

    results = []
    for ipo in core_ipos:
        gmp_data = _find_gmp_match(ipo.get("name", ""), gmp_lookup) if gmp_lookup else None
        results.append({
            "name": ipo.get("name"),
            "type": "SME" if ipo.get("type") == "SME" else "Mainboard",
            "status": ipo.get("status"),
            "open_date": ipo.get("startDate"),
            "close_date": ipo.get("endDate"),
            "listing_date": ipo.get("listingDate"),
            "price_band": ipo.get("priceRange"),
            "lot_size": ipo.get("minQty"),
            "issue_size": ipo.get("issueSize"),
            "listing_gain": ipo.get("listingGain"),
            "gmp": gmp_data,  # None if no GMP source configured / no match
        })
    return results
