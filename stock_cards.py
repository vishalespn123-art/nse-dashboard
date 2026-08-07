"""
Renders screener results as a scrollable list of stock cards - each with
symbol, price, colored change%, and signal badge - similar to the stock
list you'd see in a broker app, instead of a plain data table.
"""

import math


def _is_valid_number(val) -> bool:
    return val is not None and not (isinstance(val, float) and math.isnan(val))


def _signal_badge_color(signal: str) -> str:
    if "Buy" in signal:
        return "#16a34a"
    elif "Sell" in signal:
        return "#dc2626"
    return "#6b7280"


def render_stock_card(row: dict) -> str:
    change_pct = row.get("Change %")
    has_change = _is_valid_number(change_pct)
    is_up = has_change and change_pct >= 0
    change_color = "#16a34a" if is_up else "#dc2626"
    arrow = "▲" if is_up else "▼"
    change_display = f"{arrow} {abs(change_pct):.2f}%" if has_change else "—"

    badge_color = _signal_badge_color(row["Signal"])

    rsi_display = row.get("RSI") if _is_valid_number(row.get("RSI")) else "—"
    score_display = row.get("Score") if _is_valid_number(row.get("Score")) else "—"

    return f"""
    <div class="stock-card">
        <div class="stock-left">
            <div class="stock-symbol">{row['Symbol']}</div>
            <div class="stock-meta">RSI {rsi_display} · Score {score_display}</div>
        </div>
        <div class="stock-right">
            <div class="stock-price">₹{row['Close (₹)']:,.2f}</div>
            <div class="stock-change" style="color:{change_color};">{change_display}</div>
        </div>
        <div class="stock-badge" style="background:{badge_color}22; color:{badge_color};">
            {row['Signal']}
        </div>
    </div>
    """


def render_stock_list(rows: list, max_height_px: int = 600) -> str:
    """rows: list of dicts (each a row from the screener results)."""
    cards_html = "".join(render_stock_card(r) for r in rows)

    return f"""
    <style>
        .stock-list {{
            max-height: {max_height_px}px; overflow-y: auto;
            border: 1px solid rgba(128,128,128,0.15); border-radius: 10px;
        }}
        .stock-card {{
            display: flex; align-items: center; gap: 12px;
            padding: 12px 14px; border-bottom: 1px solid rgba(128,128,128,0.1);
        }}
        .stock-card:last-child {{ border-bottom: none; }}
        .stock-left {{ flex: 1; min-width: 0; }}
        .stock-symbol {{ font-weight: 700; font-size: 14px; }}
        .stock-meta {{ font-size: 11px; opacity: 0.6; margin-top: 2px; }}
        .stock-right {{ text-align: right; min-width: 110px; }}
        .stock-price {{ font-weight: 700; font-size: 14px; }}
        .stock-change {{ font-size: 12px; font-weight: 600; margin-top: 2px; }}
        .stock-badge {{
            font-size: 11px; font-weight: 700; padding: 4px 10px;
            border-radius: 999px; white-space: nowrap;
        }}
    </style>
    <div class="stock-list">{cards_html}</div>
    """
