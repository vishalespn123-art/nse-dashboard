"""
Renders IPO data as broker-app-style cards, with GMP shown clearly
labeled as unofficial grey-market data.
"""


def _status_color(status: str) -> str:
    s = (status or "").lower()
    if s == "open":
        return "#16a34a"
    elif s == "upcoming":
        return "#2563eb"
    return "#6b7280"  # closed / listed


def _gmp_color(gmp_price) -> str:
    try:
        val = float(gmp_price)
        if val > 0:
            return "#16a34a"
        elif val < 0:
            return "#dc2626"
    except (TypeError, ValueError):
        pass
    return "#6b7280"


def render_ipo_card(ipo: dict) -> str:
    name = ipo.get("name", "—")
    ipo_type = ipo.get("type", "")
    status = ipo.get("status", "—")
    status_color = _status_color(status)

    open_date = ipo.get("open_date") or "—"
    close_date = ipo.get("close_date") or "—"
    listing_date = ipo.get("listing_date") or "—"
    price_band = ipo.get("price_band") or ipo.get("issue_price") or "—"
    lot_size = ipo.get("lot_size") or "—"
    issue_size = ipo.get("issue_size") or "—"

    gmp = ipo.get("gmp") or {}
    gmp_price = gmp.get("price")
    gmp_pct = gmp.get("percentage")
    gmp_updated = gmp.get("updated_at")
    gmp_color = _gmp_color(gmp_price)
    gmp_display = f"₹{gmp_price} ({gmp_pct}%)" if gmp_price not in (None, "0", 0) else "—"

    sub = ipo.get("subscription") or {}
    sub_total = sub.get("total")
    sub_display = f"{sub_total}x subscribed" if sub_total else ""

    return f"""
    <div class="ipo-card">
        <div class="ipo-top">
            <div>
                <div class="ipo-name">{name}</div>
                <div class="ipo-meta">{ipo_type} · ₹{price_band} · Lot {lot_size} · {issue_size}</div>
            </div>
            <div class="ipo-status" style="background:{status_color}22; color:{status_color};">{status}</div>
        </div>
        <div class="ipo-dates">
            <span>Open: <b>{open_date}</b></span>
            <span>Close: <b>{close_date}</b></span>
            <span>Listing: <b>{listing_date}</b></span>
        </div>
        <div class="ipo-bottom">
            <div class="ipo-gmp" style="color:{gmp_color};">
                GMP: <b>{gmp_display}</b>
                <span class="ipo-gmp-tag">unofficial</span>
            </div>
            <div class="ipo-sub">{sub_display}</div>
        </div>
    </div>
    """


def render_ipo_list(ipos: list) -> str:
    if not ipos:
        return "<div style='opacity:0.6; padding:12px;'>No IPOs found for this filter.</div>"

    cards_html = "".join(render_ipo_card(i) for i in ipos)

    return f"""
    <style>
        .ipo-card {{
            border: 1px solid rgba(128,128,128,0.15); border-radius: 10px;
            padding: 12px 14px; margin-bottom: 10px;
        }}
        .ipo-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }}
        .ipo-name {{ font-weight: 700; font-size: 15px; }}
        .ipo-meta {{ font-size: 11px; opacity: 0.65; margin-top: 2px; }}
        .ipo-status {{
            font-size: 11px; font-weight: 700; padding: 3px 10px;
            border-radius: 999px; white-space: nowrap;
        }}
        .ipo-dates {{
            display: flex; gap: 16px; font-size: 12px; opacity: 0.8;
            margin-top: 10px; flex-wrap: wrap;
        }}
        .ipo-bottom {{
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(128,128,128,0.1);
        }}
        .ipo-gmp {{ font-size: 13px; }}
        .ipo-gmp-tag {{
            font-size: 9px; opacity: 0.6; border: 1px solid currentColor;
            border-radius: 4px; padding: 1px 5px; margin-left: 6px;
        }}
        .ipo-sub {{ font-size: 12px; opacity: 0.7; }}
    </style>
    {cards_html}
    """
