"""
Builds a compact index ticker (price + change% + mini sparkline chart) for
Nifty 50 / Bank Nifty, rendered as inline HTML - similar to the ticker strip
at the top of typical broker apps.
"""

import pandas as pd


def make_sparkline_svg(closes: list, width: int = 120, height: int = 36) -> str:
    """Generate a minimal inline SVG line chart from a list of closing prices."""
    if not closes or len(closes) < 2:
        return ""

    lo, hi = min(closes), max(closes)
    rng = (hi - lo) or 1.0
    n = len(closes)

    points = []
    for i, val in enumerate(closes):
        x = (i / (n - 1)) * width
        y = height - ((val - lo) / rng) * height
        points.append(f"{x:.1f},{y:.1f}")

    is_up = closes[-1] >= closes[0]
    color = "#16a34a" if is_up else "#dc2626"
    polyline = " ".join(points)

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"
                  stroke-linejoin="round" stroke-linecap="round" />
    </svg>
    """


def render_index_ticker_html(name: str, df: pd.DataFrame) -> str:
    """Build one ticker card's HTML for an index given its OHLCV history."""
    if df is None or df.empty or len(df) < 2:
        return f"""
        <div class="idx-card">
            <div class="idx-name">{name}</div>
            <div class="idx-price">—</div>
        </div>
        """

    latest_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    change_abs = latest_close - prev_close
    change_pct = (change_abs / prev_close * 100) if prev_close else 0

    is_up = change_abs >= 0
    color = "#16a34a" if is_up else "#dc2626"
    arrow = "▲" if is_up else "▼"

    sparkline_data = df["Close"].tail(30).tolist()
    sparkline_svg = make_sparkline_svg(sparkline_data)

    return f"""
    <div class="idx-card">
        <div class="idx-top">
            <div>
                <div class="idx-name">{name}</div>
                <div class="idx-price">₹{latest_close:,.2f}</div>
                <div class="idx-change" style="color:{color};">
                    {arrow} {abs(change_abs):,.2f} ({abs(change_pct):.2f}%)
                </div>
            </div>
            <div class="idx-spark">{sparkline_svg}</div>
        </div>
    </div>
    """


def render_ticker_row(index_data: dict) -> str:
    """
    index_data: {display_name: DataFrame} - renders all as a horizontal row.
    """
    cards = "".join(render_index_ticker_html(name, df) for name, df in index_data.items())
    return f"""
    <style>
        .idx-row {{ display: flex; gap: 12px; overflow-x: auto; padding: 4px 2px 14px 2px; }}
        .idx-card {{
            min-width: 190px; background: rgba(128,128,128,0.08);
            border: 1px solid rgba(128,128,128,0.15); border-radius: 10px;
            padding: 10px 14px;
        }}
        .idx-top {{ display: flex; justify-content: space-between; align-items: center; }}
        .idx-name {{ font-size: 12px; opacity: 0.7; font-weight: 600; }}
        .idx-price {{ font-size: 19px; font-weight: 700; margin-top: 2px; }}
        .idx-change {{ font-size: 12px; font-weight: 600; margin-top: 2px; }}
    </style>
    <div class="idx-row">{cards}</div>
    """
