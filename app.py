"""
NSE Stock Signal Dashboard
Personal-use tool: screens NSE stocks using technical indicators,
shows charts, and backtests the strategy on historical data.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from stock_list import NIFTY_500_SYMBOLS, SYMBOL_TO_ISIN
from data_fetch import fetch_batch, fetch_history, chunked
from signal_engine import analyze_stock
from backtest import backtest_stock
from ai_insight import fetch_news_headlines, generate_insight
from upstox_auth import build_login_url, exchange_code_for_token
from upstox_equity_data import fetch_history_upstox, fetch_batch_upstox
from options_data import get_expiries, get_option_chain, INDEX_INSTRUMENTS, INDEX_YF_SYMBOLS
from options_indicators import chain_to_dataframe, sentiment_summary
from options_signal import build_options_view

st.set_page_config(page_title="NSE Stock Signal Dashboard", layout="wide")

st.title("📈 NSE Stock Signal Dashboard")
st.caption(
    "Technical-indicator based screener for NSE stocks — for personal research only. "
    "This is **not** a price predictor. Signals reflect historical probability, not certainty. "
    "Always do your own research and manage risk."
)

with st.sidebar:
    st.header("🤖 AI Insight (optional)")
    st.caption(
        "Paste your Anthropic API key to get a plain-language explanation of each "
        "signal plus a news sentiment summary on the Stock Detail tab. Your key is "
        "kept only in this browser session - never saved to disk."
    )
    api_key = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...")
    if api_key:
        st.session_state["anthropic_api_key"] = api_key

    st.divider()
    st.header("📡 Equity data source")
    if "upstox_access_token" in st.session_state:
        st.success("Using Upstox (connected via the Options tab) — same reliable source for equity + options data.")
    else:
        st.info(
            "Currently using Yahoo Finance (free, can rate-limit on large scans). "
            "Connect Upstox in the **Options tab** to use it for equity data too — "
            "one consistent, more reliable source."
        )

def _using_upstox() -> bool:
    return "upstox_access_token" in st.session_state

tab_screener, tab_detail, tab_backtest, tab_options = st.tabs(
    ["🔍 Screener", "📊 Stock Detail", "🧪 Backtest", "🎯 Options (CE/PE)"]
)

# ---------------------------------------------------------------------------
# TAB 1: SCREENER
# ---------------------------------------------------------------------------
with tab_screener:
    st.subheader("Scan Nifty 500 stocks for signals")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        universe_choice = st.radio(
            "Universe",
            ["Quick scan (50 stocks)", "Medium scan (150 stocks)", "Full Nifty 500 (slow, ~5-10 min)"],
            horizontal=True,
        )
    with col2:
        filter_signal = st.selectbox(
            "Filter by signal",
            ["All", "Strong Buy / Buy", "Strong Sell / Sell", "Neutral"],
        )
    with col3:
        run_scan = st.button("Run Scan", type="primary")

    if universe_choice.startswith("Quick"):
        symbols_to_scan = NIFTY_500_SYMBOLS[:50]
    elif universe_choice.startswith("Medium"):
        symbols_to_scan = NIFTY_500_SYMBOLS[:150]
    else:
        symbols_to_scan = NIFTY_500_SYMBOLS

    if run_scan:
        results = []
        failed_symbols = []
        progress = st.progress(0, text="Fetching data...")

        use_upstox = _using_upstox()
        if use_upstox:
            plain_symbols = [s.replace(".NS", "") for s in symbols_to_scan]
            access_token = st.session_state["upstox_access_token"]
            batches = list(chunked(plain_symbols, 20))

            for b_idx, batch in enumerate(batches):
                data = fetch_batch_upstox(access_token, batch, days_back=400)
                for sym in batch:
                    df = data.get(sym)
                    if df is None:
                        failed_symbols.append(sym)
                        continue
                    summary = analyze_stock(df)
                    if summary is None:
                        failed_symbols.append(sym)
                        continue
                    results.append({
                        "Symbol": sym,
                        "Close (₹)": summary["close"],
                        "Signal": summary["signal"],
                        "Score": summary["score"],
                        "RSI": summary["rsi"],
                        "Above SMA50": "Yes" if (summary["sma50"] and summary["close"] > summary["sma50"]) else "No",
                        "MACD Bullish": "Yes" if summary["macd_bullish"] else "No",
                        "Volume Spike": "Yes" if summary["vol_spike"] else "No",
                    })
                progress.progress(
                    (b_idx + 1) / len(batches),
                    text=f"(via Upstox) Processed {min((b_idx+1)*20, len(plain_symbols))}/{len(plain_symbols)} stocks "
                         f"({len(results)} succeeded, {len(failed_symbols)} failed so far)...",
                )
        else:
            batches = list(chunked(symbols_to_scan, 15))

            for b_idx, batch in enumerate(batches):
                data = fetch_batch(batch, period="1y")
                for sym in batch:
                    df = data.get(sym)
                    if df is None:
                        failed_symbols.append(sym)
                        continue
                    summary = analyze_stock(df)
                    if summary is None:
                        failed_symbols.append(sym)
                        continue
                    results.append({
                        "Symbol": sym.replace(".NS", ""),
                        "Close (₹)": summary["close"],
                        "Signal": summary["signal"],
                        "Score": summary["score"],
                        "RSI": summary["rsi"],
                        "Above SMA50": "Yes" if (summary["sma50"] and summary["close"] > summary["sma50"]) else "No",
                        "MACD Bullish": "Yes" if summary["macd_bullish"] else "No",
                        "Volume Spike": "Yes" if summary["vol_spike"] else "No",
                    })
                progress.progress(
                    (b_idx + 1) / len(batches),
                    text=f"Processed {min((b_idx+1)*15, len(symbols_to_scan))}/{len(symbols_to_scan)} stocks "
                         f"({len(results)} succeeded, {len(failed_symbols)} failed so far)...",
                )
                time.sleep(0.3)  # brief pause between batches to avoid Yahoo Finance rate limiting

        progress.empty()

        if not results:
            st.warning(
                "No data returned. This is usually Yahoo Finance rate-limiting a large batch — "
                "try 'Quick scan' first, wait a minute, then retry a bigger scan."
            )
        else:
            df_results = pd.DataFrame(results).sort_values("Score", ascending=False)

            if filter_signal == "Strong Buy / Buy":
                df_results = df_results[df_results["Signal"].isin(["Strong Buy", "Buy", "Weak Buy"])]
            elif filter_signal == "Strong Sell / Sell":
                df_results = df_results[df_results["Signal"].isin(["Strong Sell", "Sell", "Weak Sell"])]
            elif filter_signal == "Neutral":
                df_results = df_results[df_results["Signal"] == "Neutral"]

            st.success(f"Scanned {len(results)} stocks successfully. Showing {len(df_results)} after filter.")
            if failed_symbols:
                with st.expander(f"⚠️ {len(failed_symbols)} stocks couldn't be fetched (Yahoo Finance rate limit / no data)"):
                    st.write(", ".join(s.replace(".NS", "") for s in failed_symbols))
                    st.caption("Try re-running the scan in a minute — Yahoo's limits reset over time, and results are cached for 15 minutes.")

            def color_signal(val):
                if "Buy" in val:
                    return "color: #16a34a; font-weight: 600"
                elif "Sell" in val:
                    return "color: #dc2626; font-weight: 600"
                return ""

            try:
                styled = df_results.style.map(color_signal, subset=["Signal"])
            except AttributeError:
                # older pandas versions (<2.1) use applymap instead of map
                styled = df_results.style.applymap(color_signal, subset=["Signal"])

            st.dataframe(
                styled,
                use_container_width=True,
                height=600,
            )

            st.caption(
                "Score ranges from -5 (strong bearish) to +5 (strong bullish), combining trend, "
                "RSI, MACD, and volume signals. This is a probability-weighted heuristic, not a guarantee."
            )
    else:
        st.info("Choose a scan size and click **Run Scan**. Full Nifty 500 scan takes longer due to data fetch limits.")

# ---------------------------------------------------------------------------
# TAB 2: STOCK DETAIL
# ---------------------------------------------------------------------------
with tab_detail:
    st.subheader("Deep dive into a single stock")

    symbol_input = st.selectbox(
        "Select a stock",
        options=[s.replace(".NS", "") for s in NIFTY_500_SYMBOLS],
        index=NIFTY_500_SYMBOLS.index("RELIANCE.NS") if "RELIANCE.NS" in NIFTY_500_SYMBOLS else 0,
    )
    period = st.select_slider("History period", options=["3mo", "6mo", "1y", "2y", "5y"], value="1y")

    if st.button("Load Stock", type="primary"):
        if _using_upstox():
            days_map = {"3mo": 100, "6mo": 200, "1y": 400, "2y": 800, "5y": 1900}
            df = fetch_history_upstox(
                st.session_state["upstox_access_token"], symbol_input,
                days_back=days_map.get(period, 400),
            )
            sym = symbol_input  # used later for news lookup; Upstox path has no ".NS" suffix
        else:
            sym = symbol_input + ".NS"
            df = fetch_history(sym, period=period)

        if df.empty:
            st.error("Could not fetch data for this symbol. Try again or check your connection.")
        else:
            summary = analyze_stock(df)
            df_ind = summary["df"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Close Price", f"₹{summary['close']}")
            c2.metric("Signal", summary["signal"], delta=f"Score: {summary['score']}")
            c3.metric("RSI (14)", summary["rsi"])
            c4.metric("Volume Spike", "Yes ⚡" if summary["vol_spike"] else "No")

            # Candlestick + indicators chart
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                row_heights=[0.55, 0.2, 0.25],
                vertical_spacing=0.03,
                subplot_titles=("Price with SMA & Bollinger Bands", "RSI (14)", "MACD"),
            )

            fig.add_trace(go.Candlestick(
                x=df_ind.index, open=df_ind["Open"], high=df_ind["High"],
                low=df_ind["Low"], close=df_ind["Close"], name="Price",
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["SMA20"], name="SMA20", line=dict(width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["SMA50"], name="SMA50", line=dict(width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["BB_Upper"], name="BB Upper", line=dict(width=1, dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["BB_Lower"], name="BB Lower", line=dict(width=1, dash="dot")), row=1, col=1)

            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["RSI14"], name="RSI"), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["MACD"], name="MACD"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["MACD_Signal"], name="Signal"), row=3, col=1)
            fig.add_trace(go.Bar(x=df_ind.index, y=df_ind["MACD_Hist"], name="Histogram"), row=3, col=1)

            fig.update_layout(height=800, xaxis_rangeslider_visible=False, legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("🤖 AI Insight")
            saved_key = st.session_state.get("anthropic_api_key")
            if not saved_key:
                st.info("Paste your Anthropic API key in the sidebar to unlock a plain-language explanation and news sentiment summary.")
            else:
                if st.button("Generate AI Insight"):
                    with st.spinner("Fetching news and asking Claude..."):
                        headlines = fetch_news_headlines(symbol_input + ".NS")
                        try:
                            insight_text = generate_insight(saved_key, symbol_input, summary, headlines)
                            st.markdown(insight_text)
                            if headlines:
                                with st.expander("Sources used"):
                                    for h in headlines:
                                        st.write(f"- {h['title']} ({h['publisher']})")
                        except Exception as e:
                            st.error(f"Couldn't generate insight: {e}")
                st.caption(
                    "This explanation is generated by Claude based on the technical data and recent "
                    "headlines above. It is commentary, not a prediction or financial advice."
                )

# ---------------------------------------------------------------------------
# TAB 3: BACKTEST
# ---------------------------------------------------------------------------
with tab_backtest:
    st.subheader("Backtest the signal strategy on historical data")
    st.caption(
        "This checks: historically, when the score hit a Buy/Sell threshold, what actually "
        "happened to price N days later? Past performance never guarantees future results."
    )

    bt_symbol = st.selectbox(
        "Stock to backtest",
        options=[s.replace(".NS", "") for s in NIFTY_500_SYMBOLS],
        index=NIFTY_500_SYMBOLS.index("RELIANCE.NS") if "RELIANCE.NS" in NIFTY_500_SYMBOLS else 0,
        key="bt_symbol",
    )
    colA, colB, colC = st.columns(3)
    with colA:
        bt_period = st.select_slider("History period", options=["1y", "2y", "5y"], value="2y", key="bt_period")
    with colB:
        forward_days = st.slider("Check outcome after N days", min_value=1, max_value=20, value=5)
    with colC:
        run_bt = st.button("Run Backtest", type="primary")

    cost_pct = st.slider(
        "Round-trip transaction cost (%) — brokerage + STT + slippage",
        min_value=0.0, max_value=1.0, value=0.3, step=0.05,
        help="Deducted from every simulated trade's return so the win rate reflects real costs, "
             "not just the raw price move. ~0.3% is a reasonable default for NSE delivery trades "
             "via a discount broker.",
    )

    if run_bt:
        if _using_upstox():
            days_map = {"1y": 400, "2y": 800, "5y": 1900}
            df = fetch_history_upstox(
                st.session_state["upstox_access_token"], bt_symbol,
                days_back=days_map.get(bt_period, 800),
            )
        else:
            sym = bt_symbol + ".NS"
            df = fetch_history(sym, period=bt_period)

        if df.empty or len(df) < 220:
            st.error("Not enough historical data for a reliable backtest. Try a longer period.")
        else:
            result = backtest_stock(df, forward_days=forward_days, cost_pct=cost_pct)

            if result is None:
                st.error("Backtest failed - insufficient data.")
            else:
                st.markdown(
                    f"**Tested on {result['total_days_tested']} trading days** "
                    f"(after deducting {result['cost_pct_applied']}% round-trip cost per trade)"
                )

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("### 🟢 Buy Signal Days")
                    bs = result["buy_signals"]
                    if bs["count"] > 0:
                        st.metric("Signals triggered", bs["count"])
                        st.metric(f"Win rate (price up after {forward_days}d)", f"{bs['win_rate']}%")
                        st.metric("Avg return", f"{bs['avg_return']}%")
                    else:
                        st.info("No buy signals triggered in this period.")

                with c2:
                    st.markdown("### 🔴 Sell Signal Days")
                    ss = result["sell_signals"]
                    if ss["count"] > 0:
                        st.metric("Signals triggered", ss["count"])
                        st.metric(f"Win rate (price down after {forward_days}d)", f"{ss['win_rate']}%")
                        st.metric("Avg return", f"{ss['avg_return']}%")
                    else:
                        st.info("No sell signals triggered in this period.")

                with c3:
                    st.markdown("### ⚪ Baseline")
                    st.metric(f"Avg {forward_days}-day return (any random day)", f"{result['baseline_avg_return_pct']}%")
                    st.caption("Compare this to the buy/sell signal returns above — if the strategy isn't beating this by much, the edge is weak.")

                st.divider()
                st.caption(
                    "⚠️ This backtest only checks ONE stock's history and doesn't account for transaction "
                    "costs, slippage, or taxes. A strategy that worked in the past may not work going forward. "
                    "Use this to build intuition, not as a guarantee."
                )

# ---------------------------------------------------------------------------
# TAB 4: OPTIONS (CE/PE)
# ---------------------------------------------------------------------------
with tab_options:
    st.subheader("Options chain analysis — Calls (CE) vs Puts (PE)")
    st.warning(
        "⚠️ **Options are high-risk and leveraged.** Even a correct direction call can lose money "
        "if time runs out or volatility drops (theta/IV decay). This tab shows current market "
        "positioning (PCR, Max Pain, OI) — it does not predict where price will go. Never risk more "
        "than you can afford to lose, and understand lot sizes, margin, and expiry mechanics before trading."
    )

    if "upstox_access_token" not in st.session_state:
        st.markdown("#### Step 1: Connect your Upstox account")
        st.caption(
            "Options data needs a broker API — Upstox has a free developer tier. "
            "[Register an app here](https://developer.upstox.com) to get an API Key + API Secret "
            "(set any redirect URI you control, e.g. `https://127.0.0.1:5000/callback` — it doesn't "
            "need to be a live server, you'll just copy the code from the browser's address bar)."
        )

        colx, coly = st.columns(2)
        with colx:
            up_api_key = st.text_input("Upstox API Key", key="up_api_key")
            up_api_secret = st.text_input("Upstox API Secret", type="password", key="up_api_secret")
        with coly:
            up_redirect_uri = st.text_input("Redirect URI (must match your app registration)", key="up_redirect_uri")

        if up_api_key and up_redirect_uri:
            login_url = build_login_url(up_api_key, up_redirect_uri)
            st.markdown(f"[**Click here to log in to Upstox →**]({login_url})")
            st.caption(
                "After logging in, your browser will redirect to your redirect URI with `?code=...` "
                "in the address bar. Copy just that code value and paste it below."
            )

        auth_code = st.text_input("Paste the authorization code here", key="up_auth_code")
        if st.button("Connect", type="primary"):
            if not (up_api_key and up_api_secret and up_redirect_uri and auth_code):
                st.error("Fill in API Key, API Secret, Redirect URI, and the authorization code.")
            else:
                try:
                    token_data = exchange_code_for_token(up_api_key, up_api_secret, up_redirect_uri, auth_code)
                    st.session_state["upstox_access_token"] = token_data["access_token"]
                    st.success("Connected! Token is valid until ~3:30 AM tonight (Upstox policy).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    else:
        st.success("✅ Connected to Upstox")
        if st.button("Disconnect"):
            del st.session_state["upstox_access_token"]
            st.rerun()

        access_token = st.session_state["upstox_access_token"]

        colA, colB = st.columns(2)
        with colA:
            index_choice = st.selectbox("Index", list(INDEX_INSTRUMENTS.keys()))
        instrument_key = INDEX_INSTRUMENTS[index_choice]
        yf_symbol = INDEX_YF_SYMBOLS[index_choice]

        try:
            expiries = get_expiries(access_token, instrument_key)
        except Exception as e:
            expiries = []
            st.error(f"Couldn't fetch expiries: {e}")

        with colB:
            expiry_choice = st.selectbox("Expiry date", expiries) if expiries else None

        if expiry_choice and st.button("Load Option Chain", type="primary"):
            try:
                raw_chain = get_option_chain(access_token, instrument_key, expiry_choice)
            except Exception as e:
                raw_chain = []
                st.error(f"Couldn't fetch option chain: {e}")

            if raw_chain:
                chain_df = chain_to_dataframe(raw_chain)
                spot = raw_chain[0].get("underlying_spot_price")

                view = build_options_view({}, chain_df, spot, yf_symbol)
                sent = view["options_sentiment"]

                st.markdown(f"### {index_choice} — Spot: ₹{spot}")

                c1, c2, c3 = st.columns(3)
                c1.metric("Overall Lean", view["lean"])
                c2.metric("PCR (Put/Call OI)", sent["pcr"])
                c3.metric("Max Pain Strike", sent["max_pain"])

                st.markdown("**Why this lean:**")
                for r in view["reasons"]:
                    st.write(f"- {r}")
                if not view["reasons"]:
                    st.write("- Signals are mixed / not strong enough to lean either way.")

                col_r, col_s = st.columns(2)
                with col_r:
                    st.markdown("#### 🔴 Resistance (highest Call OI)")
                    for s in sent["resistance_strikes"]:
                        st.write(f"Strike {s['strike']} — OI: {s['call_oi']:,}")
                with col_s:
                    st.markdown("#### 🟢 Support (highest Put OI)")
                    for s in sent["support_strikes"]:
                        st.write(f"Strike {s['strike']} — OI: {s['put_oi']:,}")

                st.divider()
                st.markdown("#### Option chain near spot price")
                near_df = chain_df[(chain_df["strike"] >= spot * 0.95) & (chain_df["strike"] <= spot * 1.05)]
                display_cols = ["strike", "call_oi", "call_oi_chg", "call_iv", "call_ltp",
                                 "put_ltp", "put_iv", "put_oi_chg", "put_oi"]
                st.dataframe(near_df[display_cols], use_container_width=True, height=400)

                if view["underlying_trend"]:
                    st.caption(
                        f"Underlying's own technical signal (from the Screener logic): "
                        f"**{view['underlying_trend']['signal']}** (RSI: {view['underlying_trend']['rsi']})"
                    )

                st.divider()
                st.caption(
                    "⚠️ PCR, Max Pain, and OI show where option writers are currently positioned — "
                    "they describe the present, not the future. Prices can and do move against these "
                    "levels. This is not trade advice."
                )
            else:
                st.warning("No option chain data returned for this expiry.")
