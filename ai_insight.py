"""
AI Insight layer using the Anthropic API.

IMPORTANT: Claude does not predict stock prices - no AI can. This module
only helps translate the technical signal into a plain-language summary,
and summarizes recent news sentiment. Treat this as commentary, not advice.
"""

import streamlit as st
from anthropic import Anthropic


def get_client(api_key: str) -> Anthropic:
    return Anthropic(api_key=api_key)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_headlines(symbol: str, limit: int = 8) -> list:
    """Fetch recent news headlines for a symbol via yfinance."""
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        headlines = []
        for item in news[:limit]:
            content = item.get("content", item)  # newer yfinance nests under "content"
            title = content.get("title") or item.get("title")
            publisher = (content.get("provider") or {}).get("displayName") if isinstance(content.get("provider"), dict) else item.get("publisher")
            if title:
                headlines.append({"title": title, "publisher": publisher or "Unknown"})
        return headlines
    except Exception:
        return []


def build_prompt(symbol: str, summary: dict, headlines: list) -> str:
    news_block = "\n".join(f"- {h['title']} (Source: {h['publisher']})" for h in headlines) if headlines else "No recent news available."

    prompt = f"""You are helping a retail investor understand a technical stock signal for {symbol} (NSE, India).

Technical data (already computed, do not recalculate):
- Current price: ₹{summary['close']}
- Signal: {summary['signal']} (score: {summary['score']} on a -5 to +5 scale)
- RSI (14): {summary['rsi']}
- Price vs SMA50: {"above" if summary['sma50'] and summary['close'] > summary['sma50'] else "below"}
- Price vs SMA200: {"above" if summary['sma200'] and summary['close'] > summary['sma200'] else "below"}
- MACD bullish crossover: {summary['macd_bullish']}
- Volume spike today: {summary['vol_spike']}

Recent news headlines:
{news_block}

Write a short, plain-language summary (max 150 words) covering:
1. What the technical signal means in simple terms (no jargon dump - explain it like to a smart friend who isn't a trader)
2. What the news sentiment looks like (positive/negative/mixed/neutral) based only on the headlines above
3. One or two genuine risk factors or things to watch out for

Do NOT predict a price target or tell the person to buy/sell. Do NOT claim certainty. If headlines are unavailable, just skip that part honestly."""
    return prompt


def generate_insight(api_key: str, symbol: str, summary: dict, headlines: list) -> str:
    """Call Claude API to generate the plain-language insight + news sentiment."""
    client = get_client(api_key)
    prompt = build_prompt(symbol, summary, headlines)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_parts).strip()
