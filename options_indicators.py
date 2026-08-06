"""
Options chain analytics: Put-Call Ratio, Max Pain, and Open Interest buildup.

These are standard, widely-used options metrics - not predictions. They
describe where option writers (the "smart money" on the other side of the
trade) currently have their positions concentrated.
"""

import pandas as pd


def chain_to_dataframe(raw_chain: list) -> pd.DataFrame:
    """Flatten the raw Upstox option chain response into a clean DataFrame."""
    rows = []
    for item in raw_chain:
        strike = item.get("strike_price")
        spot = item.get("underlying_spot_price")

        call = item.get("call_options", {}) or {}
        put = item.get("put_options", {}) or {}
        call_md = call.get("market_data", {}) or {}
        put_md = put.get("market_data", {}) or {}
        call_gr = call.get("option_greeks", {}) or {}
        put_gr = put.get("option_greeks", {}) or {}

        rows.append({
            "strike": strike,
            "spot": spot,
            "call_ltp": call_md.get("ltp"),
            "call_oi": call_md.get("oi") or 0,
            "call_prev_oi": call_md.get("prev_oi") or 0,
            "call_volume": call_md.get("volume") or 0,
            "call_iv": call_gr.get("iv"),
            "put_ltp": put_md.get("ltp"),
            "put_oi": put_md.get("oi") or 0,
            "put_prev_oi": put_md.get("prev_oi") or 0,
            "put_volume": put_md.get("volume") or 0,
            "put_iv": put_gr.get("iv"),
        })

    df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
    df["call_oi_chg"] = df["call_oi"] - df["call_prev_oi"]
    df["put_oi_chg"] = df["put_oi"] - df["put_prev_oi"]
    return df


def overall_pcr(df: pd.DataFrame) -> float:
    """Put-Call Ratio using total OI across all strikes. >1 = more puts written (bullish lean per convention), <1 = more calls (bearish lean)."""
    total_call_oi = df["call_oi"].sum()
    total_put_oi = df["put_oi"].sum()
    if total_call_oi == 0:
        return float("nan")
    return round(total_put_oi / total_call_oi, 2)


def max_pain(df: pd.DataFrame) -> float:
    """
    Max Pain strike: the price at which option writers (sellers) would lose
    the least money at expiry. Often acts as a magnet for price near expiry,
    though this is a tendency, not a rule.
    """
    strikes = df["strike"].values
    best_strike = None
    min_total_payout = None

    for candidate in strikes:
        call_payout = ((candidate - df["strike"]).clip(lower=0) * df["call_oi"]).sum()
        put_payout = ((df["strike"] - candidate).clip(lower=0) * df["put_oi"]).sum()
        total = call_payout + put_payout
        if min_total_payout is None or total < min_total_payout:
            min_total_payout = total
            best_strike = candidate

    return float(best_strike) if best_strike is not None else float("nan")


def top_oi_strikes(df: pd.DataFrame, n: int = 3) -> dict:
    """Strikes with highest Call OI (resistance) and Put OI (support)."""
    top_calls = df.nlargest(n, "call_oi")[["strike", "call_oi"]].to_dict("records")
    top_puts = df.nlargest(n, "put_oi")[["strike", "put_oi"]].to_dict("records")
    return {"resistance_strikes": top_calls, "support_strikes": top_puts}


def atm_strikes(df: pd.DataFrame, spot: float, n: int = 5) -> pd.DataFrame:
    """Return the n strikes closest to spot price (for a focused table view)."""
    df2 = df.copy()
    df2["dist"] = (df2["strike"] - spot).abs()
    return df2.nsmallest(n * 2, "dist").sort_values("strike").drop(columns="dist")


def sentiment_summary(df: pd.DataFrame, spot: float) -> dict:
    """
    Combine PCR + OI buildup direction into a simple sentiment lean.
    This is descriptive of current positioning, not a forecast.
    """
    pcr = overall_pcr(df)
    mp = max_pain(df)
    oi_data = top_oi_strikes(df)

    # OI buildup: rising call OI near/above spot = resistance building (bearish lean)
    # rising put OI near/below spot = support building (bullish lean)
    near = df[(df["strike"] >= spot * 0.97) & (df["strike"] <= spot * 1.03)]
    call_oi_chg_near = near["call_oi_chg"].sum() if not near.empty else 0
    put_oi_chg_near = near["put_oi_chg"].sum() if not near.empty else 0

    if pcr > 1.2:
        pcr_lean = "Bullish lean (more puts written than calls)"
    elif pcr < 0.8:
        pcr_lean = "Bearish lean (more calls written than puts)"
    else:
        pcr_lean = "Neutral / balanced"

    return {
        "pcr": pcr,
        "pcr_lean": pcr_lean,
        "max_pain": mp,
        "spot": spot,
        "distance_to_max_pain_pct": round((mp - spot) / spot * 100, 2) if spot else None,
        "call_oi_change_near_spot": int(call_oi_chg_near),
        "put_oi_change_near_spot": int(put_oi_chg_near),
        "resistance_strikes": oi_data["resistance_strikes"],
        "support_strikes": oi_data["support_strikes"],
    }
