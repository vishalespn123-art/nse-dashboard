"""
Upstox OAuth2 login helper.

Upstox uses an interactive login flow (no simple API key like Anthropic).
You need to:
1. Register a free app at https://developer.upstox.com (get API Key + API Secret)
2. Set a redirect URI when registering (e.g. https://127.0.0.1:5000/callback - it
   doesn't need to actually be running, we just read the "code" from the URL)
3. Log in once per day using the link this app generates
4. Paste the authorization code back into the app to get an access token

The access token is valid until ~3:30 AM the next day (Upstox policy), so
you'll need to re-login once daily if you use this regularly.
"""

import requests

AUTH_BASE = "https://api.upstox.com/v2/login/authorization/dialog"
TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"


def build_login_url(api_key: str, redirect_uri: str) -> str:
    return (
        f"{AUTH_BASE}?response_type=code"
        f"&client_id={api_key}"
        f"&redirect_uri={redirect_uri}"
    )


def exchange_code_for_token(api_key: str, api_secret: str, redirect_uri: str, code: str) -> dict:
    """
    Exchange the one-time authorization code for an access token.
    Returns dict with 'access_token' on success, or raises an Exception with the error.
    """
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "code": code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)
    result = resp.json()
    if resp.status_code != 200 or "access_token" not in result:
        raise Exception(result.get("errors", result))
    return result
