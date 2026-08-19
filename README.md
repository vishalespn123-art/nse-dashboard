# NSE Stock Signal Dashboard

Personal-use dashboard that screens NSE (Nifty 500) stocks using technical
indicators and gives you a **probability-based signal** (Strong Buy → Strong
Sell). It also lets you **backtest** the strategy on historical data so you
can see how well it has actually worked in the past.

## ⚠️ Read this first

This tool does **not predict** stock prices. No software can. It combines
well-known technical indicators (moving averages, RSI, MACD, volume) into a
score — the same building blocks professional tools use — to highlight
patterns that have *historically* leaned bullish or bearish. Treat every
signal as **one input into your decision**, not an instruction. Always use
risk management (position sizing, stop-loss) and never invest money you
can't afford to lose.

## What's inside

| File | Purpose |
|---|---|
| `stock_list.py` | Nifty 500 stock symbols (NSE, Yahoo Finance format) |
| `data_fetch.py` | Fetches price data via `yfinance` (fallback source), with caching |
| `upstox_equity_data.py` | Fetches equity price data via Upstox (primary source once connected) |
| `indicators.py` | SMA, EMA, RSI, MACD, Bollinger Bands, volume spike |
| `signal_engine.py` | Combines indicators into a -5 to +5 score and label |
| `backtest.py` | Tests the strategy against real historical outcomes |
| `ai_insight.py` | Optional: uses your Anthropic API key for plain-language explanations + news sentiment |
| `upstox_auth.py` | Login flow to connect your free Upstox broker account |
| `options_data.py` | Fetches live option chain data (Nifty/Bank Nifty/Fin Nifty) |
| `options_indicators.py` | PCR, Max Pain, OI buildup analysis |
| `options_signal.py` | Combines options sentiment + underlying trend into a CE/PE lean |
| `app.py` | Streamlit dashboard (the app you run) |

## Setup

1. **Install Python 3.9+** if you don't already have it.
2. Open a terminal in this folder and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```
4. It will open in your browser automatically (usually `http://localhost:8501`).

You need an active internet connection every time you run it — it fetches
live/recent data from Yahoo Finance.

## How to use it

### 🔍 Screener tab
Scans a batch of Nifty 500 stocks and shows a signal for each (Strong Buy,
Buy, Neutral, Sell, Strong Sell), along with RSI, trend, and volume info.
Start with "Quick scan (50 stocks)" — the full 500-stock scan takes several
minutes and may hit Yahoo Finance's rate limits.

### 📊 Stock Detail tab
Pick one stock to see a full candlestick chart with SMA, Bollinger Bands,
RSI, and MACD — plus the current signal and score.

### 🧪 Backtest tab
Pick a stock and see: historically, when this strategy said "Buy," what
actually happened to the price N days later? Compare the win rate to the
"baseline" (what happens on a random day) — if the strategy isn't clearly
beating the baseline, its edge is weak for that stock.

## How the scoring works

Each of these contributes +1 / 0 / -1 to a total score (range -5 to +5):

1. **Trend** — SMA50 above/below SMA200 (golden/death cross logic)
2. **Short-term trend** — price above/below SMA20
3. **RSI** — below 30 (oversold, +1) / above 70 (overbought, -1)
4. **MACD** — MACD line above/below its signal line
5. **Volume confirmation** — a volume spike combined with the price direction

You can open `signal_engine.py` and tweak the rules/weights yourself — it's
plain, readable Python.

### 🤖 AI Insight (optional, needs your Anthropic API key)
Paste your key in the sidebar (kept only in your browser session, never
written to disk). On the Stock Detail tab, click **Generate AI Insight** to
get:
- A plain-language explanation of the current signal
- A summary of recent news sentiment for that stock (based on real headlines
  fetched from Yahoo Finance)
- One or two risk factors to be aware of

This is Claude explaining and summarizing what's already known — it does
**not** predict future prices either. Every API call uses your own key and
is billed to your Anthropic account (a single request is typically a few
cents or less on Claude Sonnet).

### 🎯 Options (CE/PE) tab — needs a free Upstox account
Unlike the Anthropic API, Upstox doesn't offer a simple "paste your key"
flow — it uses an interactive login (OAuth2) that must be repeated roughly
once a day. Steps:

1. Go to [developer.upstox.com](https://developer.upstox.com), sign up free,
   and create an app to get an **API Key** and **API Secret**.
2. When registering the app, set any **Redirect URI** you like (it doesn't
   need to be a live server — e.g. `https://127.0.0.1:5000/callback` works).
   Just remember it, since it must match exactly in the dashboard too.
3. In the app's Options tab, paste your API Key, API Secret, and Redirect
   URI, then click the generated login link and sign in with your Upstox
   credentials.
4. After login, your browser redirects to your Redirect URI with `?code=...`
   in the address bar (the page itself may show an error — that's fine,
   you only need the code). Copy that code and paste it into the app.
5. Click **Connect**. You're now logged in for the day.

Once connected, you can:
- Pick **Nifty 50, Bank Nifty, or Fin Nifty**, choose an expiry date, and
  load the live option chain
- See **PCR (Put-Call Ratio)**, **Max Pain**, and **OI buildup** near the
  spot price
- Get a **CE (Call) / PE (Put) lean** that combines options positioning with
  the underlying index's own technical trend — again, a lean based on
  current data, not a prediction

⚠️ **Options-specific risks the dashboard does NOT protect you from:**
theta decay (options lose value as expiry approaches, even if you're
directionally right), high implied volatility crush after events, liquidity
issues in far strikes, and margin requirements for writing options. Learn
these mechanics properly (or paper-trade first) before using real money.

## Roadmap (Phase 1 in progress, rest planned)

This started as a personal screener and is growing toward a more complete
platform. Rough plan, in priority order:

- ✅ **Phase 1 — Data infra**: Upstox as the primary equity data source
  (done — connect once in the Options tab and it's used everywhere),
  realistic transaction costs in backtesting (done). Still open: a proper
  corporate-action (split/bonus) adjustment feed, and including delisted
  stocks in the backtest universe to remove survivorship bias.
- **Phase 2 — NSE/BSE tabs**: separate scanners per exchange, BSE
  Midcap/Smallcap universes, illiquid-stock flagging.
- **Phase 3 — Fundamentals + sector view**: P/E, P/B, ROE, quarterly growth,
  peer comparison, sector heatmap.
- **Phase 4 — Alerts**: Telegram/WhatsApp/email notification when a signal
  changes.
- **Phase 5 — Portfolio/watchlist**: saved watchlist + paper-trading PnL
  tracker.
- **Phase 6 — UI polish**: PDF export, mobile layout.

Each phase is a substantial chunk of work on its own — ask for a specific
one and it can be built out fully rather than all at once.

### 🆕 IPO tab — two optional free API keys

1. **Core IPO details (dates, price band, issue size) — instant, free:**
   Go to [ipoalerts.in](https://ipoalerts.in), sign up, go to **API Keys**
   in the dashboard, and create a key. Takes about 2 minutes, no approval
   wait. Add it to Secrets as `IPOALERTS_API_KEY`.
2. **GMP (Grey Market Premium) — free, but manually issued:**
   Email `ipoguru.in [at] gmail.com` requesting API access (see
   [ipoguru.in](https://www.ipoguru.in/ipo-gmp-details-developer-api)).
   This can take a while since a person reviews each request. Add it to
   Secrets as `IPO_GURU_API_KEY` once you get it.

The IPO tab works fine with just the first key — GMP simply won't show on
the cards until the second key is added. Without either key, it falls back
to labeled sample data so the layout is still visible.

## Known limitations

- Free Yahoo Finance data occasionally has gaps or delays for NSE stocks.
- Full 500-stock scans can be slow / rate-limited — that's a Yahoo Finance
  limit, not something the code can fully avoid.
- Backtest results are for a **single stock's own history** — they don't
  account for brokerage costs, slippage, or taxes, and past performance is
  never a guarantee of future results.
- This is a rule-based heuristic, not machine learning — it won't adapt on
  its own to changing market regimes.

## Ideas to extend it yourself

- Add more indicators (Supertrend, ADX, Fibonacci levels)
- Add stop-loss / target price suggestions based on ATR (Average True Range)
- Save your own watchlist instead of scanning all 500 stocks each time
- Email/Telegram alerts when a stock you follow crosses into "Strong Buy"
