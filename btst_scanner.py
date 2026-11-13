"""
3:15 PM Live BTST / STBT Diagnostic Scanner for Nifty 50 and Bank Nifty.
Reuses Yahoo Finance fetchers and constituent weights from fetch_and_backtest.py.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import numpy as np
import pandas as pd

from fetch_and_backtest import (
    BASE_DIR,
    IST,
    BANKNIFTY_WEIGHTS,
    NIFTY_WEIGHTS,
    compute_clv,
    fetch_yahoo_chart,
)


def evaluate_index_live(
    symbol: str,
    label: str,
    weights: dict[str, float],
    vix_spot: float,
    is_nifty_weekly: bool,
) -> dict:
    """Fetch latest daily and 15m data for an index and its constituents and score BTST/STBT."""
    df_d = fetch_yahoo_chart(symbol, range_str="3mo", interval="1d")
    df_15m = fetch_yahoo_chart(symbol, range_str="5d", interval="15m")

    df_d["SMA20"] = df_d["Close"].rolling(20).mean()
    latest_d = df_d.iloc[-1]
    latest_date = latest_d["Date"]
    sma20 = float(latest_d["SMA20"])

    # Use today's/latest session 15m bars if available, else fall back to daily bar
    day_15m = df_15m[df_15m["Date"] == latest_date].sort_values("Datetime")
    if day_15m.empty:
        # Take the most recent session present in 15m data
        latest_15m_date = df_15m["Date"].iloc[-1]
        day_15m = df_15m[df_15m["Date"] == latest_15m_date].sort_values("Datetime")
        session_date = latest_15m_date
    else:
        session_date = latest_date

    spot = float(day_15m["Close"].iloc[-1]) if not day_15m.empty else float(latest_d["Close"])
    sess_open = float(day_15m["Open"].iloc[0]) if not day_15m.empty else float(latest_d["Open"])
    sess_high = float(day_15m["High"].max()) if not day_15m.empty else float(latest_d["High"])
    sess_low = float(day_15m["Low"].min()) if not day_15m.empty else float(latest_d["Low"])

    clv = (spot - sess_low) / (sess_high - sess_low) if sess_high > sess_low else 0.5
    clv = float(np.clip(clv, 0.0, 1.0))
    r_intra = (spot / sess_open - 1.0) * 100.0

    # Intraday VWAP or TWAP fallback when index 15m volume is 0
    typ_price = (day_15m["High"] + day_15m["Low"] + day_15m["Close"]) / 3.0
    if day_15m["Volume"].sum() > 0:
        vwap = float((typ_price * day_15m["Volume"]).sum() / day_15m["Volume"].sum())
        vwap_label = "VWAP"
    else:
        vwap = float(typ_price.mean())
        vwap_label = "TWAP"

    # 2:30 PM - 3:25 PM late surge + 3:00 PM - 3:30 PM institutional range
    day_15m = day_15m.copy()
    day_15m["hm"] = day_15m["Datetime"].dt.hour * 100 + day_15m["Datetime"].dt.minute
    late_bars = day_15m[day_15m["hm"] >= 1430]
    if not late_bars.empty:
        late_surge_pct = (spot / float(late_bars["Open"].iloc[0]) - 1.0) * 100.0
    else:
        late_surge_pct = 0.0

    last30_bars = day_15m[day_15m["hm"] >= 1500]
    if not last30_bars.empty:
        sl_low = float(last30_bars["Low"].min())
        sl_high = float(last30_bars["High"].max())
    else:
        sl_low = sess_low
        sl_high = sess_high

    # Heavyweight sync CLV
    hw_details = []
    hw_num = 0.0
    hw_den = 0.0
    for ticker, w in weights.items():
        try:
            hdf = fetch_yahoo_chart(ticker, range_str="5d", interval="15m")
            h_day = hdf[hdf["Date"] == session_date]
            if h_day.empty:
                h_day = hdf[hdf["Date"] == hdf["Date"].iloc[-1]]
            h_high = float(h_day["High"].max())
            h_low = float(h_day["Low"].min())
            h_close = float(h_day["Close"].iloc[-1])
            h_clv = (h_close - h_low) / (h_high - h_low) if h_high > h_low else 0.5
            hw_num += h_clv * w
            hw_den += w
            hw_details.append((ticker.replace(".NS", ""), round(h_clv * 100, 1)))
        except Exception:
            continue

    hw_clv = hw_num / hw_den if hw_den > 0 else 0.5

    # Composite Score [-100, +100]
    score_clv = (clv - 0.5) * 60.0                          # +/- 30
    score_trend = 20.0 if spot > sma20 else -20.0           # +/- 20
    score_vwap = 15.0 if spot > vwap else -15.0             # +/- 15
    score_late = float(np.clip(late_surge_pct / 0.40, -1.0, 1.0) * 15.0)  # +/- 15
    score_hw = (hw_clv - 0.5) * 40.0                        # +/- 20

    raw_score = score_clv + score_trend + score_vwap + score_late + score_hw

    exhaustion_flag = abs(r_intra) > 1.25
    if exhaustion_flag:
        # Dampen score toward 0 on overextended >1.25% intraday moves
        raw_score *= 0.65

    score = round(float(np.clip(raw_score, -100.0, 100.0)), 1)

    weekday = pd.Timestamp(session_date).dayofweek  # 4 == Friday
    is_friday = weekday == 4

    if score >= 55:
        signal = "STRONG BTST (Bullish)"
        bias = "BULL"
    elif score >= 30:
        signal = "MODERATE BTST (Bullish)"
        bias = "BULL"
    elif score <= -55:
        signal = "STRONG STBT (Bearish)"
        bias = "BEAR"
    elif score <= -30:
        signal = "MODERATE STBT (Bearish)"
        bias = "BEAR"
    else:
        signal = "NO TRADE / NEUTRAL"
        bias = "NEUTRAL"

    if bias == "NEUTRAL":
        structure = "Stay in Cash (no directional edge)"
        stop_loss = "-"
        exit_rule = "-"
    elif bias == "BULL":
        if is_friday or vix_spot >= 16.0 or (is_nifty_weekly and score < 55):
            structure = "Bull Call Debit Spread (Buy ATM CE + Sell ~0.25d OTM CE)"
        else:
            structure = "Slightly ITM Call (~0.60-0.65 Delta CE)"
        stop_loss = f"Break below 3:00-3:30 PM Low ({sl_low:,.2f})"
        exit_rule = "Book 50-100% at 9:15-9:20 AM gap open"
    else:
        if is_friday or vix_spot >= 16.0 or (is_nifty_weekly and score > -55):
            structure = "Bear Put Debit Spread (Buy ATM PE + Sell ~0.25d OTM PE)"
        else:
            structure = "Slightly ITM Put (~0.60-0.65 Delta PE)"
        stop_loss = f"Break above 3:00-3:30 PM High ({sl_high:,.2f})"
        exit_rule = "Book 50-100% at 9:15-9:20 AM gap-down open"

    return {
        "label": label,
        "symbol": symbol,
        "session_date": str(session_date),
        "spot": round(spot, 2),
        "sma20": round(sma20, 2),
        "trend": "ABOVE 20-DMA" if spot > sma20 else "BELOW 20-DMA",
        "vwap_label": vwap_label,
        "vwap": round(vwap, 2),
        "clv_pct": round(clv * 100.0, 1),
        "r_intra_pct": round(r_intra, 2),
        "late_surge_pct": round(late_surge_pct, 2),
        "hw_sync_pct": round(hw_clv * 100.0, 1),
        "exhaustion_warning": "YES (>1.25% move)" if exhaustion_flag else "No",
        "score": score,
        "signal": signal,
        "structure": structure,
        "stop_loss": stop_loss,
        "exit_rule": exit_rule,
        "hw_details": hw_details,
        "is_friday": is_friday,
    }


def save_reports(now_ist: datetime, vix_spot: float, nifty: dict, banknifty: dict) -> tuple[Path, Path]:
    """Write Markdown and JSON scan summaries under reports/ for CI/CD tracking."""
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "latest_scan.json"
    md_path = reports_dir / "latest_scan.md"

    payload = {
        "generated_at_ist": now_ist.isoformat(),
        "india_vix": round(vix_spot, 2),
        "indices": {
            "nifty_50": nifty,
            "bank_nifty": banknifty,
        },
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    lines = [
        "## BTST / STBT Automated Scan Report",
        f"- **Run Time (IST):** `{now_ist.strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **India VIX:** `{vix_spot:.2f}`",
        "",
        "| Metric | Nifty 50 (`^NSEI`) | Bank Nifty (`^NSEBANK`) |",
        "| :--- | :--- | :--- |",
        f"| **Session Date** | `{nifty['session_date']}` | `{banknifty['session_date']}` |",
        f"| **Spot / 20-DMA** | `{nifty['spot']:,.2f}` ({nifty['trend']}: `{nifty['sma20']:,.2f}`) | `{banknifty['spot']:,.2f}` ({banknifty['trend']}: `{banknifty['sma20']:,.2f}`) |",
        f"| **Intraday Benchmark** | `{nifty['vwap']:,.2f}` ({nifty['vwap_label']}) | `{banknifty['vwap']:,.2f}` ({banknifty['vwap_label']}) |",
        f"| **CLV / Day Body / Late Surge** | `{nifty['clv_pct']:.1f}%` / `{nifty['r_intra_pct']:+.2f}%` / `{nifty['late_surge_pct']:+.2f}%` | `{banknifty['clv_pct']:.1f}%` / `{banknifty['r_intra_pct']:+.2f}%` / `{banknifty['late_surge_pct']:+.2f}%` |",
        f"| **Heavyweight Sync** | `{nifty['hw_sync_pct']:.1f}%` | `{banknifty['hw_sync_pct']:.1f}%` |",
        f"| **BTST Score & Signal** | **`{nifty['score']:+.1f} / 100`** — {nifty['signal']} | **`{banknifty['score']:+.1f} / 100`** — {banknifty['signal']} |",
        f"| **Recommended Structure** | {nifty['structure']} | {banknifty['structure']} |",
        f"| **Stop-Loss** | {nifty['stop_loss']} | {banknifty['stop_loss']} |",
        f"| **Morning Exit** | {nifty['exit_rule']} | {banknifty['exit_rule']} |",
        "",
        "### Heavyweight Constituent CLV Breakdown",
        f"- **Nifty 50:** " + ", ".join(f"`{k}: {v:.0f}%`" for k, v in nifty["hw_details"]),
        f"- **Bank Nifty:** " + ", ".join(f"`{k}: {v:.0f}%`" for k, v in banknifty["hw_details"]),
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="3:15 PM BTST / STBT Live Scanner")
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Write reports/latest_scan.md and reports/latest_scan.json",
    )
    args = parser.parse_args()

    now_ist = datetime.now(IST)
    vix_df = fetch_yahoo_chart("^INDIAVIX", range_str="1mo", interval="1d")
    vix_spot = float(vix_df["Close"].iloc[-1])

    nifty = evaluate_index_live("^NSEI", "Nifty 50", NIFTY_WEIGHTS, vix_spot, is_nifty_weekly=True)
    banknifty = evaluate_index_live("^NSEBANK", "Bank Nifty", BANKNIFTY_WEIGHTS, vix_spot, is_nifty_weekly=False)

    print("=" * 84)
    print(f"  BTST / STBT LIVE SCANNER  |  Run Time (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}  |  India VIX: {vix_spot:.2f}")
    print("=" * 84)

    for res in (nifty, banknifty):
        print(f"\n[{res['label']} ({res['symbol']})]  Session: {res['session_date']}  |  Weekend Hold: {'YES (Fri)' if res['is_friday'] else 'No'}")
        print(f"  Spot          : {res['spot']:,.2f}   ({res['trend']}: 20-DMA = {res['sma20']:,.2f})")
        print(f"  Intraday {res['vwap_label']:<4} : {res['vwap']:,.2f}   ({'ABOVE' if res['spot'] > res['vwap'] else 'BELOW'})")
        print(f"  Session CLV   : {res['clv_pct']:.1f}%   |  Day Body: {res['r_intra_pct']:+.2f}%   |  2:30-3:25 Surge: {res['late_surge_pct']:+.2f}%")
        print(f"  Heavywt Sync  : {res['hw_sync_pct']:.1f}%   |  Exhaustion Flag: {res['exhaustion_warning']}")
        hw_str = ", ".join(f"{name}:{val:.0f}%" for name, val in res["hw_details"])
        print(f"  Constituents  : {hw_str}")
        print("-" * 84)
        print(f"  BTST SCORE    : {res['score']:+.1f} / 100  ==>  {res['signal']}")
        print(f"  Structure     : {res['structure']}")
        print(f"  Morning Exit  : {res['exit_rule']}")
        print(f"  Stop-Loss     : {res['stop_loss']}")
    print("=" * 84)

    if args.save_report:
        md_path, json_path = save_reports(now_ist, vix_spot, nifty, banknifty)
        print(f"Saved reports: {md_path} and {json_path}")


if __name__ == "__main__":
    main()
