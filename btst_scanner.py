"""
3:15 PM Live BTST / STBT Diagnostic Scanner & Persistent Paper Trading Engine
for Nifty 50 (^NSEI) and Bank Nifty (^NSEBANK).
"""

import argparse
from datetime import datetime
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_and_backtest import (
    BASE_DIR,
    BANKNIFTY_WEIGHTS,
    IST,
    NIFTY_WEIGHTS,
    bs_call_price,
    fetch_yahoo_chart,
    find_strike_for_delta,
)

REPORTS_DIR = BASE_DIR / "reports"
PAPER_TRADES_JSON = REPORTS_DIR / "paper_trades.json"
PAPER_TRADES_CSV = REPORTS_DIR / "paper_trades.csv"
PAPER_TRADES_MD = REPORTS_DIR / "paper_trades_summary.md"

INDEX_CONFIG = {
    "^NSEI": {
        "label": "Nifty 50",
        "short": "NIFTY",
        "weights": NIFTY_WEIGHTS,
        "is_weekly": True,
        "strike_step": 50.0,
        "dte_entry": 4,
        "lot_size": 75,
    },
    "^NSEBANK": {
        "label": "Bank Nifty",
        "short": "BANKNIFTY",
        "weights": BANKNIFTY_WEIGHTS,
        "is_weekly": False,
        "strike_step": 100.0,
        "dte_entry": 15,
        "lot_size": 30,
    },
}


def bs_put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """European put price via put-call parity."""
    return bs_call_price(S, K, T, r, sigma) - S + K * math.exp(-r * max(T, 0.0))


def value_structure(
    option_type: str,
    spot: float,
    k_long: float | None,
    k_short: float | None,
    T: float,
    sigma: float,
    r: float = 0.065,
) -> float:
    """Value a single option or vertical debit spread at given spot, time T, and IV."""
    if option_type == "NONE" or k_long is None:
        return 0.0
    if option_type in ("CE", "CE_SPREAD"):
        val = bs_call_price(spot, k_long, T, r, sigma)
        if k_short is not None:
            val -= bs_call_price(spot, k_short, T, r, sigma)
        return max(val, 0.0)
    if option_type in ("PE", "PE_SPREAD"):
        val = bs_put_price(spot, k_long, T, r, sigma)
        if k_short is not None:
            val -= bs_put_price(spot, k_short, T, r, sigma)
        return max(val, 0.0)
    return 0.0


def price_paper_structure(
    bias: str,
    score: float,
    spot: float,
    vix_spot: float,
    is_friday: bool,
    cfg: dict,
    r: float = 0.065,
) -> dict:
    """Select option structure, strikes, and entry Black-Scholes premium."""
    if bias == "NEUTRAL":
        return {
            "trade_taken": False,
            "structure": "Stay in Cash (no directional edge)",
            "option_type": "NONE",
            "k_long": None,
            "k_short": None,
            "dte_entry": cfg["dte_entry"],
            "lot_size": cfg["lot_size"],
            "entry_premium_pts": 0.0,
        }

    step = cfg["strike_step"]
    dte = cfg["dte_entry"]
    T = dte / 365.0
    sigma = max(0.08, vix_spot / 100.0)
    use_spread = is_friday or vix_spot >= 16.0 or (cfg["is_weekly"] and abs(score) < 55.0)
    k_atm = round(spot / step) * step

    if bias == "BULL":
        if use_spread:
            k_long = float(k_atm)
            k_short = float(find_strike_for_delta(spot, 0.25, T, r, sigma, step))
            if k_short <= k_long:
                k_short = k_long + step
            opt_type = "CE_SPREAD"
            structure = f"Bull Call Debit Spread ({int(k_long)}/{int(k_short)} CE)"
        else:
            k_long = float(find_strike_for_delta(spot, 0.65, T, r, sigma, step))
            k_short = None
            opt_type = "CE"
            structure = f"Slightly ITM Call ({int(k_long)} CE)"
    else:
        if use_spread:
            k_long = float(k_atm)
            k_short = float(find_strike_for_delta(spot, 0.75, T, r, sigma, step))
            if k_short >= k_long:
                k_short = k_long - step
            opt_type = "PE_SPREAD"
            structure = f"Bear Put Debit Spread ({int(k_long)}/{int(k_short)} PE)"
        else:
            k_long = float(find_strike_for_delta(spot, 0.35, T, r, sigma, step))
            k_short = None
            opt_type = "PE"
            structure = f"Slightly ITM Put ({int(k_long)} PE)"

    entry_prem = value_structure(opt_type, spot, k_long, k_short, T, sigma, r)
    return {
        "trade_taken": True,
        "structure": structure,
        "option_type": opt_type,
        "k_long": k_long,
        "k_short": k_short,
        "dte_entry": dte,
        "lot_size": cfg["lot_size"],
        "entry_premium_pts": round(entry_prem, 2),
    }


def evaluate_session(
    symbol: str,
    session_date,
    day_15m: pd.DataFrame,
    sma20: float,
    hw_15m_by_date: dict[str, dict],
    vix_spot: float,
) -> dict:
    """Compute all BTST/STBT metrics and paper trade specification for a single session."""
    cfg = INDEX_CONFIG[symbol]
    day_15m = day_15m.sort_values("Datetime").copy()

    spot = float(day_15m["Close"].iloc[-1])
    sess_open = float(day_15m["Open"].iloc[0])
    sess_high = float(day_15m["High"].max())
    sess_low = float(day_15m["Low"].min())

    clv = (spot - sess_low) / (sess_high - sess_low) if sess_high > sess_low else 0.5
    clv = float(np.clip(clv, 0.0, 1.0))
    r_intra = (spot / sess_open - 1.0) * 100.0

    typ_price = (day_15m["High"] + day_15m["Low"] + day_15m["Close"]) / 3.0
    if day_15m["Volume"].sum() > 0:
        vwap = float((typ_price * day_15m["Volume"]).sum() / day_15m["Volume"].sum())
        vwap_label = "VWAP"
    else:
        vwap = float(typ_price.mean())
        vwap_label = "TWAP"

    day_15m["hm"] = day_15m["Datetime"].dt.hour * 100 + day_15m["Datetime"].dt.minute
    late_bars = day_15m[day_15m["hm"] >= 1430]
    late_surge_pct = (spot / float(late_bars["Open"].iloc[0]) - 1.0) * 100.0 if not late_bars.empty else 0.0

    last30_bars = day_15m[day_15m["hm"] >= 1500]
    sl_low = float(last30_bars["Low"].min()) if not last30_bars.empty else sess_low
    sl_high = float(last30_bars["High"].max()) if not last30_bars.empty else sess_high

    hw_details = []
    hw_num = 0.0
    hw_den = 0.0
    for ticker, w in cfg["weights"].items():
        h_day = hw_15m_by_date.get(ticker, {}).get(session_date)
        if h_day is None or h_day.empty:
            continue
        h_high = float(h_day["High"].max())
        h_low = float(h_day["Low"].min())
        h_close = float(h_day["Close"].iloc[-1])
        h_clv = (h_close - h_low) / (h_high - h_low) if h_high > h_low else 0.5
        hw_num += h_clv * w
        hw_den += w
        hw_details.append((ticker.replace(".NS", ""), round(h_clv * 100.0, 1)))

    hw_clv = hw_num / hw_den if hw_den > 0 else 0.5

    score_clv = (clv - 0.5) * 60.0
    score_trend = 20.0 if spot > sma20 else -20.0
    score_vwap = 15.0 if spot > vwap else -15.0
    score_late = float(np.clip(late_surge_pct / 0.40, -1.0, 1.0) * 15.0)
    score_hw = (hw_clv - 0.5) * 40.0

    raw_score = score_clv + score_trend + score_vwap + score_late + score_hw
    exhaustion_flag = abs(r_intra) > 1.25
    if exhaustion_flag:
        raw_score *= 0.65

    score = round(float(np.clip(raw_score, -100.0, 100.0)), 1)
    ts_date = pd.Timestamp(session_date)
    is_friday = ts_date.dayofweek == 4

    if score >= 55:
        signal, bias = "STRONG BTST (Bullish)", "BULL"
    elif score >= 30:
        signal, bias = "MODERATE BTST (Bullish)", "BULL"
    elif score <= -55:
        signal, bias = "STRONG STBT (Bearish)", "BEAR"
    elif score <= -30:
        signal, bias = "MODERATE STBT (Bearish)", "BEAR"
    else:
        signal, bias = "NO TRADE / NEUTRAL", "NEUTRAL"

    pricing = price_paper_structure(bias, score, spot, vix_spot, is_friday, cfg)
    if bias == "BULL":
        stop_loss = f"Break below 3:00-3:30 PM Low ({sl_low:,.2f})"
        stop_loss_level = round(sl_low, 2)
        exit_rule = "Book 50-100% at 9:15-9:20 AM gap open"
    elif bias == "BEAR":
        stop_loss = f"Break above 3:00-3:30 PM High ({sl_high:,.2f})"
        stop_loss_level = round(sl_high, 2)
        exit_rule = "Book 50-100% at 9:15-9:20 AM gap-down open"
    else:
        stop_loss = "-"
        stop_loss_level = None
        exit_rule = "-"

    return {
        "trade_id": f"{session_date}_{cfg['short']}",
        "symbol": symbol,
        "label": cfg["label"],
        "entry_date": str(session_date),
        "weekday": ts_date.strftime("%a"),
        "is_friday": is_friday,
        "spot": round(spot, 2),
        "sma20": round(sma20, 2),
        "trend": "ABOVE 20-DMA" if spot > sma20 else "BELOW 20-DMA",
        "vwap_label": vwap_label,
        "vwap": round(vwap, 2),
        "clv_pct": round(clv * 100.0, 1),
        "r_intra_pct": round(r_intra, 2),
        "late_surge_pct": round(late_surge_pct, 2),
        "hw_sync_pct": round(hw_clv * 100.0, 1),
        "india_vix_entry": round(vix_spot, 2),
        "exhaustion_flag": exhaustion_flag,
        "exhaustion_warning": "YES (>1.25% move)" if exhaustion_flag else "No",
        "score": score,
        "signal": signal,
        "bias": bias,
        **pricing,
        "stop_loss": stop_loss,
        "stop_loss_level": stop_loss_level,
        "exit_rule": exit_rule,
        "hw_details": hw_details,
    }


def build_paper_trade_record(eval_res: dict) -> dict:
    """Convert an evaluation snapshot into a persistent paper trade ledger record."""
    return {
        "trade_id": eval_res["trade_id"],
        "symbol": eval_res["symbol"],
        "label": eval_res["label"],
        "entry_date": eval_res["entry_date"],
        "weekday": eval_res["weekday"],
        "is_friday": eval_res["is_friday"],
        "entry_spot": eval_res["spot"],
        "sma20": eval_res["sma20"],
        "trend": eval_res["trend"],
        "vwap_label": eval_res["vwap_label"],
        "vwap": eval_res["vwap"],
        "clv_pct": eval_res["clv_pct"],
        "r_intra_pct": eval_res["r_intra_pct"],
        "late_surge_pct": eval_res["late_surge_pct"],
        "hw_sync_pct": eval_res["hw_sync_pct"],
        "india_vix_entry": eval_res["india_vix_entry"],
        "exhaustion_flag": eval_res["exhaustion_flag"],
        "score": eval_res["score"],
        "signal": eval_res["signal"],
        "bias": eval_res["bias"],
        "trade_taken": eval_res["trade_taken"],
        "structure": eval_res["structure"],
        "option_type": eval_res["option_type"],
        "k_long": eval_res["k_long"],
        "k_short": eval_res["k_short"],
        "dte_entry": eval_res["dte_entry"],
        "lot_size": eval_res["lot_size"],
        "entry_premium_pts": eval_res["entry_premium_pts"],
        "stop_loss_level": eval_res["stop_loss_level"],
        "status": "OPEN",
        "exit_date": None,
        "hold_calendar_days": None,
        "exit_open_spot": None,
        "india_vix_exit": None,
        "actual_gap_pts": None,
        "actual_gap_pct": None,
        "exit_premium_pts": None,
        "option_pnl_pts": None,
        "option_roi_pct": None,
        "option_pnl_inr": None,
        "outcome": "OPEN" if eval_res["trade_taken"] else "NO_TRADE_OPEN",
    }


def fetch_market_bundle() -> dict:
    """Fetch daily (6mo) and 15m (60d) data once for indices, VIX, and all heavyweights."""
    vix_daily = fetch_yahoo_chart("^INDIAVIX", range_str="6mo", interval="1d")
    vix_by_date = {
        str(row["Date"]): {"open": float(row["Open"]), "close": float(row["Close"])}
        for _, row in vix_daily.iterrows()
    }

    daily_by_sym = {}
    intraday_by_sym = {}
    open_by_sym_date = {}

    for sym in INDEX_CONFIG:
        dfd = fetch_yahoo_chart(sym, range_str="6mo", interval="1d")
        dfd["SMA20"] = dfd["Close"].rolling(20).mean()
        daily_by_sym[sym] = dfd

        df15 = fetch_yahoo_chart(sym, range_str="60d", interval="15m")
        grouped = {str(dt): grp.sort_values("Datetime") for dt, grp in df15.groupby("Date")}
        intraday_by_sym[sym] = grouped

        opens = {str(row["Date"]): float(row["Open"]) for _, row in dfd.iterrows()}
        for dt_str, grp in grouped.items():
            opens[dt_str] = float(grp["Open"].iloc[0])
        open_by_sym_date[sym] = opens

    all_hw_tickers = sorted({t for cfg in INDEX_CONFIG.values() for t in cfg["weights"]})
    hw_15m_by_date: dict[str, dict] = {}
    for ticker in all_hw_tickers:
        try:
            hdf = fetch_yahoo_chart(ticker, range_str="60d", interval="15m")
            hw_15m_by_date[ticker] = {str(dt): grp.sort_values("Datetime") for dt, grp in hdf.groupby("Date")}
        except Exception:
            hw_15m_by_date[ticker] = {}

    return {
        "vix_daily": vix_daily,
        "vix_by_date": vix_by_date,
        "daily_by_sym": daily_by_sym,
        "intraday_by_sym": intraday_by_sym,
        "open_by_sym_date": open_by_sym_date,
        "hw_15m_by_date": hw_15m_by_date,
    }


def settle_open_trades(ledger: dict[str, dict], bundle: dict) -> int:
    """Settle any OPEN paper trade whose next trading day 9:15 AM open is available."""
    settled_count = 0
    vix_by_date = bundle["vix_by_date"]

    for trade_id, rec in ledger.items():
        if rec.get("status") == "SETTLED":
            continue
        sym = rec["symbol"]
        opens_map = bundle["open_by_sym_date"].get(sym, {})
        future_dates = sorted(d for d in opens_map if d > rec["entry_date"])
        if not future_dates:
            continue

        exit_date = future_dates[0]
        exit_open = opens_map[exit_date]
        entry_spot = float(rec["entry_spot"])
        gap_pts = exit_open - entry_spot
        gap_pct = (exit_open / entry_spot - 1.0) * 100.0
        hold_days = (pd.Timestamp(exit_date) - pd.Timestamp(rec["entry_date"])).days

        vix_exit = vix_by_date.get(exit_date, {}).get("open", rec["india_vix_entry"])
        rec["exit_date"] = exit_date
        rec["hold_calendar_days"] = int(hold_days)
        rec["exit_open_spot"] = round(exit_open, 2)
        rec["india_vix_exit"] = round(float(vix_exit), 2)
        rec["actual_gap_pts"] = round(gap_pts, 2)
        rec["actual_gap_pct"] = round(gap_pct, 4)

        if rec["trade_taken"]:
            dte_rem = max(0.25, float(rec["dte_entry"]) - hold_days)
            T_exit = dte_rem / 365.0
            sigma_exit = max(0.08, float(vix_exit) / 100.0 - 0.0075)
            exit_prem = value_structure(
                rec["option_type"],
                exit_open,
                rec["k_long"],
                rec["k_short"],
                T_exit,
                sigma_exit,
            )
            pnl_pts = exit_prem - float(rec["entry_premium_pts"])
            roi_pct = (pnl_pts / float(rec["entry_premium_pts"]) * 100.0) if rec["entry_premium_pts"] > 0 else 0.0
            pnl_inr = pnl_pts * int(rec["lot_size"])

            rec["exit_premium_pts"] = round(exit_prem, 2)
            rec["option_pnl_pts"] = round(pnl_pts, 2)
            rec["option_roi_pct"] = round(roi_pct, 2)
            rec["option_pnl_inr"] = round(pnl_inr, 2)
            rec["outcome"] = "WIN" if pnl_pts > 0 else "LOSS"
        else:
            rec["exit_premium_pts"] = 0.0
            rec["option_pnl_pts"] = 0.0
            rec["option_roi_pct"] = 0.0
            rec["option_pnl_inr"] = 0.0
            rec["outcome"] = "NO_TRADE"

        rec["status"] = "SETTLED"
        settled_count += 1

    return settled_count


def seed_60d_history(ledger: dict[str, dict], bundle: dict) -> int:
    """Replay the 60-day 15m dataset day by day and insert missing historical entries."""
    added = 0
    vix_by_date = bundle["vix_by_date"]
    vix_fallback = float(bundle["vix_daily"]["Close"].iloc[-1])

    for sym in INDEX_CONFIG:
        dfd = bundle["daily_by_sym"][sym]
        intraday_map = bundle["intraday_by_sym"][sym]
        # Map date string -> daily close series for rolling SMA20 up to session d
        daily_dates = [str(d) for d in dfd["Date"]]
        daily_closes = list(dfd["Close"].astype(float))

        for dt_str in sorted(intraday_map.keys()):
            trade_id = f"{dt_str}_{INDEX_CONFIG[sym]['short']}"
            if trade_id in ledger:
                continue

            day_15m = intraday_map[dt_str]
            if len(day_15m) < 8:
                continue

            # Compute SMA20 using closes strictly prior to dt_str plus dt_str's 15m close
            prior_closes = [c for d, c in zip(daily_dates, daily_closes) if d < dt_str]
            sess_close = float(day_15m["Close"].iloc[-1])
            window = (prior_closes + [sess_close])[-20:]
            if len(window) < 20:
                continue
            sma20 = float(np.mean(window))
            vix_val = vix_by_date.get(dt_str, {}).get("close", vix_fallback)

            eval_res = evaluate_session(sym, dt_str, day_15m, sma20, bundle["hw_15m_by_date"], vix_val)
            ledger[trade_id] = build_paper_trade_record(eval_res)
            added += 1

    return added


def compute_paper_stats(records: list[dict]) -> dict:
    """Summarize cumulative paper trading performance across settled trades."""
    settled_all = [r for r in records if r["status"] == "SETTLED"]
    active = [r for r in settled_all if r["trade_taken"]]
    open_trades = [r for r in records if r["status"] == "OPEN"]

    wins = [r for r in active if r["outcome"] == "WIN"]
    total_pnl_inr = sum(float(r["option_pnl_inr"] or 0.0) for r in active)
    total_opt_pts = sum(float(r["option_pnl_pts"] or 0.0) for r in active)
    avg_roi = float(np.mean([float(r["option_roi_pct"]) for r in active])) if active else 0.0

    by_index = {}
    for sym, cfg in INDEX_CONFIG.items():
        sub = [r for r in active if r["symbol"] == sym]
        sub_wins = [r for r in sub if r["outcome"] == "WIN"]
        sub_pnl = sum(float(r["option_pnl_inr"] or 0.0) for r in sub)
        sub_gap_pts = sum(
            float(r["actual_gap_pts"] or 0.0) * (1.0 if r["bias"] == "BULL" else -1.0)
            for r in sub
        )
        by_index[cfg["label"]] = {
            "trades": len(sub),
            "wins": len(sub_wins),
            "win_rate_pct": round(len(sub_wins) / len(sub) * 100.0, 2) if sub else 0.0,
            "directional_gap_pts": round(sub_gap_pts, 2),
            "option_pnl_inr": round(sub_pnl, 2),
            "avg_roi_pct": round(float(np.mean([float(r["option_roi_pct"]) for r in sub])), 2) if sub else 0.0,
        }

    return {
        "total_sessions_logged": len(records),
        "settled_sessions": len(settled_all),
        "open_sessions": len(open_trades),
        "active_trades_taken": len(active),
        "wins": len(wins),
        "losses": len(active) - len(wins),
        "win_rate_pct": round(len(wins) / len(active) * 100.0, 2) if active else 0.0,
        "total_option_pnl_pts": round(total_opt_pts, 2),
        "total_option_pnl_inr": round(total_pnl_inr, 2),
        "avg_roi_pct": round(avg_roi, 2),
        "by_index": by_index,
    }


def save_paper_ledger(ledger: dict[str, dict]) -> dict:
    """Persist sorted paper trade ledger to JSON, CSV, and Markdown summary."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    records = sorted(ledger.values(), key=lambda r: (r["entry_date"], r["symbol"]))
    stats = compute_paper_stats(records)

    with open(PAPER_TRADES_JSON, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "trades": records}, f, indent=2)

    pd.DataFrame(records).to_csv(PAPER_TRADES_CSV, index=False)

    md_lines = [
        "# BTST / STBT Paper Trading Ledger & Testing Dataset",
        "",
        f"- **Total Sessions Retained:** `{stats['total_sessions_logged']}` (`{stats['settled_sessions']}` settled, `{stats['open_sessions']}` open)",
        f"- **Active Trades Taken (`|Score| >= 30`):** `{stats['active_trades_taken']}` (`{stats['wins']}W / {stats['losses']}L`, **{stats['win_rate_pct']:.2f}%** win rate)",
        f"- **Cumulative Option P&L:** **`₹{stats['total_option_pnl_inr']:+,.2f}`** (`{stats['total_option_pnl_pts']:+.2f}` option pts | `{stats['avg_roi_pct']:+.2f}%` avg ROI/trade)",
        "",
        "## Performance Breakdown by Index",
        "",
        "| Index | Lot Size | Trades Taken | Wins | Win Rate | Directional Gap Pts | Avg ROI / Trade | Option P&L (INR) |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for sym, cfg in INDEX_CONFIG.items():
        st = stats["by_index"][cfg["label"]]
        md_lines.append(
            f"| {cfg['label']} | {cfg['lot_size']} | {st['trades']} | {st['wins']} | "
            f"{st['win_rate_pct']:.2f}% | {st['directional_gap_pts']:+.2f} | {st['avg_roi_pct']:+.2f}% | "
            f"₹{st['option_pnl_inr']:+,.2f} |"
        )

    md_lines.extend([
        "",
        "## Complete Paper Trade Log (Newest First)",
        "",
        "| Entry Date | Index | Score | Signal | Structure | Entry Spot | Exit Open | Gap % | Entry Prem | Exit Prem | ROI % | P&L (INR) | Status |",
        "| :--- | :--- | ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |",
    ])
    for r in reversed(records):
        exit_spot_s = f"{r['exit_open_spot']:,.2f}" if r["exit_open_spot"] is not None else "-"
        gap_s = f"{r['actual_gap_pct']:+.2f}%" if r["actual_gap_pct"] is not None else "-"
        exit_prem_s = f"{r['exit_premium_pts']:.2f}" if r["exit_premium_pts"] is not None else "-"
        roi_s = f"{r['option_roi_pct']:+.2f}%" if r["option_roi_pct"] is not None else "-"
        pnl_s = f"₹{r['option_pnl_inr']:+,.2f}" if r["option_pnl_inr"] is not None else "-"
        md_lines.append(
            f"| {r['entry_date']} ({r['weekday']}) | {r['label']} | {r['score']:+.1f} | {r['signal']} | "
            f"{r['structure']} | {r['entry_spot']:,.2f} | {exit_spot_s} | {gap_s} | "
            f"{r['entry_premium_pts']:.2f} | {exit_prem_s} | {roi_s} | {pnl_s} | {r['outcome']} |"
        )

    with open(PAPER_TRADES_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    return stats


def save_latest_scan_reports(
    now_ist: datetime,
    vix_spot: float,
    nifty: dict,
    banknifty: dict,
    stats: dict,
    records: list[dict],
) -> tuple[Path, Path]:
    """Write Markdown and JSON scan summaries including paper trading KPIs."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "latest_scan.json"
    md_path = REPORTS_DIR / "latest_scan.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at_ist": now_ist.isoformat(),
                "india_vix": round(vix_spot, 2),
                "indices": {"nifty_50": nifty, "bank_nifty": banknifty},
                "paper_trading_stats": stats,
            },
            f,
            indent=2,
        )

    lines = [
        "## BTST / STBT Automated Scan Report",
        f"- **Run Time (IST):** `{now_ist.strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **India VIX:** `{vix_spot:.2f}`",
        "",
        "| Metric | Nifty 50 (`^NSEI`) | Bank Nifty (`^NSEBANK`) |",
        "| :--- | :--- | :--- |",
        f"| **Session Date** | `{nifty['entry_date']}` | `{banknifty['entry_date']}` |",
        f"| **Spot / 20-DMA** | `{nifty['spot']:,.2f}` ({nifty['trend']}: `{nifty['sma20']:,.2f}`) | `{banknifty['spot']:,.2f}` ({banknifty['trend']}: `{banknifty['sma20']:,.2f}`) |",
        f"| **Intraday Benchmark** | `{nifty['vwap']:,.2f}` ({nifty['vwap_label']}) | `{banknifty['vwap']:,.2f}` ({banknifty['vwap_label']}) |",
        f"| **CLV / Day Body / Late Surge** | `{nifty['clv_pct']:.1f}%` / `{nifty['r_intra_pct']:+.2f}%` / `{nifty['late_surge_pct']:+.2f}%` | `{banknifty['clv_pct']:.1f}%` / `{banknifty['r_intra_pct']:+.2f}%` / `{banknifty['late_surge_pct']:+.2f}%` |",
        f"| **Heavyweight Sync** | `{nifty['hw_sync_pct']:.1f}%` | `{banknifty['hw_sync_pct']:.1f}%` |",
        f"| **BTST Score & Signal** | **`{nifty['score']:+.1f} / 100`** — {nifty['signal']} | **`{banknifty['score']:+.1f} / 100`** — {banknifty['signal']} |",
        f"| **Paper Trade Structure** | {nifty['structure']} (`{nifty['entry_premium_pts']:.2f}` pts) | {banknifty['structure']} (`{banknifty['entry_premium_pts']:.2f}` pts) |",
        f"| **Stop-Loss** | {nifty['stop_loss']} | {banknifty['stop_loss']} |",
        f"| **Morning Exit** | {nifty['exit_rule']} | {banknifty['exit_rule']} |",
        "",
        "### Heavyweight Constituent CLV Breakdown",
        "- **Nifty 50:** " + ", ".join(f"`{k}: {v:.0f}%`" for k, v in nifty["hw_details"]),
        "- **Bank Nifty:** " + ", ".join(f"`{k}: {v:.0f}%`" for k, v in banknifty["hw_details"]),
        "",
        "---",
        "",
        "## Paper Trading Cumulative Summary",
        f"- **Retained Dataset:** `{stats['total_sessions_logged']}` sessions (`{stats['settled_sessions']}` settled, `{stats['open_sessions']}` open) — see [paper_trades.csv](paper_trades.csv) & [paper_trades_summary.md](paper_trades_summary.md)",
        f"- **Active Trades Taken:** `{stats['active_trades_taken']}` (`{stats['wins']}W / {stats['losses']}L`, **{stats['win_rate_pct']:.2f}%** win rate)",
        f"- **Cumulative Option P&L:** **`₹{stats['total_option_pnl_inr']:+,.2f}`** (`{stats['avg_roi_pct']:+.2f}%` avg ROI/trade)",
        "",
        "### Recent 15 Paper Trades",
        "",
        "| Date | Index | Score | Structure | Entry Spot | Exit Open | Gap % | Option P&L (INR) | ROI % | Status |",
        "| :--- | :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]
    for r in reversed(records[-15:]):
        exit_spot_s = f"{r['exit_open_spot']:,.2f}" if r["exit_open_spot"] is not None else "-"
        gap_s = f"{r['actual_gap_pct']:+.2f}%" if r["actual_gap_pct"] is not None else "-"
        pnl_s = f"₹{r['option_pnl_inr']:+,.2f}" if r["option_pnl_inr"] is not None else "-"
        roi_s = f"{r['option_roi_pct']:+.2f}%" if r["option_roi_pct"] is not None else "-"
        lines.append(
            f"| {r['entry_date']} | {r['label']} | {r['score']:+.1f} | {r['structure']} | "
            f"{r['entry_spot']:,.2f} | {exit_spot_s} | {gap_s} | {pnl_s} | {roi_s} | {r['outcome']} |"
        )
    lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="3:15 PM BTST / STBT Live Scanner & Paper Trader")
    parser.add_argument("--save-report", action="store_true", help="Write reports/latest_scan.* and paper_trades.*")
    parser.add_argument("--seed-history", action="store_true", help="Backfill missing 60-day paper trades into ledger")
    parser.add_argument("--settle-only", action="store_true", help="Settle OPEN trades only (do not open new afternoon trades)")
    args = parser.parse_args()

    now_ist = datetime.now(IST)
    bundle = fetch_market_bundle()
    vix_spot = float(bundle["vix_daily"]["Close"].iloc[-1])

    # Load existing persistent ledger
    ledger: dict[str, dict] = {}
    first_init = not PAPER_TRADES_JSON.exists()
    if not first_init:
        with open(PAPER_TRADES_JSON, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for rec in raw.get("trades", []):
                ledger[rec["trade_id"]] = rec

    if args.seed_history or first_init:
        seeded = seed_60d_history(ledger, bundle)
        if seeded:
            print(f"Seeded {seeded} historical 60-day paper trade records into ledger.")

    # Evaluate latest session for Nifty 50 and Bank Nifty
    latest_evals = {}
    for sym in INDEX_CONFIG:
        dfd = bundle["daily_by_sym"][sym]
        intraday_map = bundle["intraday_by_sym"][sym]
        latest_date = sorted(intraday_map.keys())[-1]
        day_15m = intraday_map[latest_date]
        prior_closes = list(dfd[dfd["Date"].astype(str) < latest_date]["Close"].astype(float))
        sess_close = float(day_15m["Close"].iloc[-1])
        sma20 = float(np.mean((prior_closes + [sess_close])[-20:]))
        latest_evals[sym] = evaluate_session(sym, latest_date, day_15m, sma20, bundle["hw_15m_by_date"], vix_spot)

        if not args.settle_only:
            tid = latest_evals[sym]["trade_id"]
            # Insert or update if still OPEN (never overwrite an already SETTLED trade)
            if tid not in ledger or ledger[tid].get("status") != "SETTLED":
                ledger[tid] = build_paper_trade_record(latest_evals[sym])

    newly_settled = settle_open_trades(ledger, bundle)
    if newly_settled:
        print(f"Settled {newly_settled} overnight paper trade(s) at 9:15 AM open.")

    nifty = latest_evals["^NSEI"]
    banknifty = latest_evals["^NSEBANK"]
    records = sorted(ledger.values(), key=lambda r: (r["entry_date"], r["symbol"]))
    stats = compute_paper_stats(records)

    print("=" * 84)
    print(f"  BTST / STBT LIVE SCANNER  |  Run Time (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}  |  India VIX: {vix_spot:.2f}")
    print("=" * 84)
    for res in (nifty, banknifty):
        print(f"\n[{res['label']} ({res['symbol']})]  Session: {res['entry_date']}  |  Weekend Hold: {'YES (Fri)' if res['is_friday'] else 'No'}")
        print(f"  Spot          : {res['spot']:,.2f}   ({res['trend']}: 20-DMA = {res['sma20']:,.2f})")
        print(f"  Intraday {res['vwap_label']:<4} : {res['vwap']:,.2f}   ({'ABOVE' if res['spot'] > res['vwap'] else 'BELOW'})")
        print(f"  Session CLV   : {res['clv_pct']:.1f}%   |  Day Body: {res['r_intra_pct']:+.2f}%   |  2:30-3:25 Surge: {res['late_surge_pct']:+.2f}%")
        print(f"  Heavywt Sync  : {res['hw_sync_pct']:.1f}%   |  Exhaustion Flag: {res['exhaustion_warning']}")
        print("  Constituents  : " + ", ".join(f"{name}:{val:.0f}%" for name, val in res["hw_details"]))
        print("-" * 84)
        print(f"  BTST SCORE    : {res['score']:+.1f} / 100  ==>  {res['signal']}")
        print(f"  Paper Trade   : {res['structure']} (Entry Prem: {res['entry_premium_pts']:.2f} pts, Lot: {res['lot_size']})")
        print(f"  Morning Exit  : {res['exit_rule']}")
        print(f"  Stop-Loss     : {res['stop_loss']}")
    print("-" * 84)
    print(
        f"  PAPER LEDGER  : {stats['total_sessions_logged']} sessions ({stats['settled_sessions']} settled, {stats['open_sessions']} open) | "
        f"Active: {stats['active_trades_taken']} ({stats['win_rate_pct']:.1f}% WR) | P&L: INR {stats['total_option_pnl_inr']:+,.2f}"
    )
    print("=" * 84)

    if args.save_report:
        save_paper_ledger(ledger)
        md_path, json_path = save_latest_scan_reports(now_ist, vix_spot, nifty, banknifty, stats, records)
        print(f"Saved reports: {md_path}, {json_path}, {PAPER_TRADES_CSV}, {PAPER_TRADES_JSON}, {PAPER_TRADES_MD}")


if __name__ == "__main__":
    main()
