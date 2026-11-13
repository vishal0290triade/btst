"""
Quantitative BTST / STBT Backtest & Options Simulation Engine
for Nifty 50 (^NSEI) and Bank Nifty (^NSEBANK).
"""

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

IST = timezone(timedelta(hours=5, minutes=30))
BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "backtest_results.json"

INDICES = ["^NSEI", "^NSEBANK", "^INDIAVIX"]
HEAVYWEIGHTS = [
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "RELIANCE.NS",
    "INFY.NS",
    "TCS.NS",
]

BANKNIFTY_WEIGHTS = {
    "HDFCBANK.NS": 0.29,
    "ICICIBANK.NS": 0.24,
    "SBIN.NS": 0.11,
    "AXISBANK.NS": 0.10,
    "KOTAKBANK.NS": 0.10,
}

NIFTY_WEIGHTS = {
    "HDFCBANK.NS": 0.120,
    "RELIANCE.NS": 0.090,
    "ICICIBANK.NS": 0.080,
    "INFY.NS": 0.060,
    "TCS.NS": 0.040,
    "AXISBANK.NS": 0.030,
    "SBIN.NS": 0.030,
    "KOTAKBANK.NS": 0.025,
}


def fetch_yahoo_chart(symbol: str, range_str: str = "10y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV bars from Yahoo Finance v8 chart endpoint in IST."""
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_str}&interval={interval}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result")
    if not result:
        raise ValueError(f"No chart result for {symbol} ({range_str}, {interval})")

    item = result[0]
    timestamps = item.get("timestamp", [])
    quote = item.get("indicators", {}).get("quote", [{}])[0]
    if not timestamps or not quote:
        raise ValueError(f"Empty OHLCV for {symbol}")

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "Open": quote.get("open"),
            "High": quote.get("high"),
            "Low": quote.get("low"),
            "Close": quote.get("close"),
            "Volume": quote.get("volume"),
        }
    )
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)]
    df["Volume"] = df["Volume"].fillna(0.0).astype(float)

    dt_ist = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(IST)
    df["Datetime"] = dt_ist
    df["Date"] = dt_ist.dt.date

    if interval == "1d":
        df = df.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    else:
        df = df.drop_duplicates(subset=["Datetime"], keep="last").sort_values("Datetime").reset_index(drop=True)

    return df


def compute_clv(df: pd.DataFrame) -> pd.Series:
    """Close Location Value in [0, 1]; returns 0.5 if High == Low."""
    span = df["High"] - df["Low"]
    clv = np.where(span > 0, (df["Close"] - df["Low"]) / span, 0.5)
    return pd.Series(np.clip(clv, 0.0, 1.0), index=df.index)


def build_heavyweight_clv(daily_data: dict[str, pd.DataFrame], weights: dict[str, float], dates: pd.Series) -> pd.Series:
    """Compute date-aligned weighted average CLV across available heavyweights."""
    num = pd.Series(0.0, index=dates.index)
    den = pd.Series(0.0, index=dates.index)

    for ticker, w in weights.items():
        if ticker not in daily_data:
            continue
        sub = daily_data[ticker][["Date"]].copy()
        sub["clv"] = compute_clv(daily_data[ticker])
        mapped = dates.map(sub.set_index("Date")["clv"])
        valid = mapped.notna()
        num = num + np.where(valid, mapped * w, 0.0)
        den = den + np.where(valid, w, 0.0)

    return pd.Series(np.where(den > 0, num / den, np.nan), index=dates.index)


def summarize_return_series(returns: pd.Series) -> dict:
    """Compute performance and tail statistics for a return series (in decimal)."""
    r = returns.dropna().astype(float)
    n = int(len(r))
    if n == 0:
        return {"count": 0}

    cum_ret = float((np.prod(1.0 + r) - 1.0) * 100.0)
    years = n / 252.0
    cagr = float(((1.0 + cum_ret / 100.0) ** (1.0 / years) - 1.0) * 100.0) if years > 0 and cum_ret > -100 else 0.0
    ann_vol = float(r.std(ddof=1) * math.sqrt(252.0) * 100.0) if n > 1 else 0.0
    sharpe = float((r.mean() / r.std(ddof=1)) * math.sqrt(252.0)) if n > 1 and r.std(ddof=1) > 0 else 0.0
    win_rate = float((r > 0).mean() * 100.0)

    return {
        "count": n,
        "cumulative_return_pct": round(cum_ret, 2),
        "cagr_pct": round(cagr, 2),
        "ann_volatility_pct": round(ann_vol, 2),
        "sharpe_ratio": round(sharpe, 2),
        "win_rate_pct": round(win_rate, 2),
        "mean_pct": round(float(r.mean() * 100.0), 4),
        "median_pct": round(float(r.median() * 100.0), 4),
        "p01_pct": round(float(np.percentile(r, 1) * 100.0), 3),
        "p05_pct": round(float(np.percentile(r, 5) * 100.0), 3),
        "p95_pct": round(float(np.percentile(r, 95) * 100.0), 3),
        "p99_pct": round(float(np.percentile(r, 99) * 100.0), 3),
    }


def summarize_trade_setup(ret_series: pd.Series, points_series: pd.Series) -> dict:
    """Compute trade-level statistics for a filtered BTST/STBT setup."""
    valid = ret_series.notna() & points_series.notna()
    r = ret_series[valid].astype(float)
    pts = points_series[valid].astype(float)
    n = int(len(r))
    if n == 0:
        return {"trades": 0}

    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else 999.0

    equity = (1.0 + r).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1.0) * 100.0
    max_dd = float(dd.min())

    return {
        "trades": n,
        "win_rate_pct": round(float((r > 0).mean() * 100.0), 2),
        "mean_gap_pct": round(float(r.mean() * 100.0), 4),
        "median_gap_pct": round(float(r.median() * 100.0), 4),
        "profit_factor": profit_factor,
        "expectancy_points": round(float(pts.mean()), 2),
        "total_points": round(float(pts.sum()), 1),
        "cum_return_pct": round(float((equity.iloc[-1] - 1.0) * 100.0), 2),
        "max_drawdown_pct": round(max_dd, 2),
        "p05_pct": round(float(np.percentile(r, 5) * 100.0), 3),
        "p95_pct": round(float(np.percentile(r, 95) * 100.0), 3),
    }


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return max(0.0, S - K)
    if sigma <= 0:
        return max(0.0, S - K * math.exp(-r * T))
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)


def bs_call_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return norm_cdf(d1)


def find_strike_for_delta(S: float, target_delta: float, T: float, r: float, sigma: float, step: float) -> float:
    """Find nearest discrete strike K with BS call delta closest to target_delta."""
    low_k, high_k = S * 0.85, S * 1.15
    for _ in range(50):
        mid = 0.5 * (low_k + high_k)
        if bs_call_delta(S, mid, T, r, sigma) > target_delta:
            low_k = mid
        else:
            high_k = mid
    exact_k = 0.5 * (low_k + high_k)
    return round(exact_k / step) * step


def simulate_options_structures(
    spot: float,
    strike_step: float,
    gap_returns: pd.Series,
    hold_days_list: pd.Series,
    sigma_entry: float,
    dte_entry: int,
    iv_crush: float = 0.0075,
    r: float = 0.065,
) -> dict:
    """Simulate overnight option P&L across empirical Setup C gaps with Theta + morning IV crush."""
    T_entry = dte_entry / 365.0
    sigma_exit = max(0.05, sigma_entry - iv_crush)

    k_otm = find_strike_for_delta(spot, 0.25, T_entry, r, sigma_entry, strike_step)
    k_atm = round(spot / strike_step) * strike_step
    k_itm = find_strike_for_delta(spot, 0.65, T_entry, r, sigma_entry, strike_step)

    c_otm_0 = bs_call_price(spot, k_otm, T_entry, r, sigma_entry)
    c_atm_0 = bs_call_price(spot, k_atm, T_entry, r, sigma_entry)
    c_itm_0 = bs_call_price(spot, k_itm, T_entry, r, sigma_entry)
    spread_0 = c_atm_0 - c_otm_0

    structures = {
        "OTM Call (~0.25 Delta)": {"k_long": k_otm, "k_short": None, "cost": c_otm_0},
        "ATM Call (~0.50 Delta)": {"k_long": k_atm, "k_short": None, "cost": c_atm_0},
        "ITM Call (~0.65 Delta)": {"k_long": k_itm, "k_short": None, "cost": c_itm_0},
        "Bull Call Debit Spread (ATM - OTM)": {"k_long": k_atm, "k_short": k_otm, "cost": spread_0},
    }

    sim_results = {}
    for name, cfg in structures.items():
        pnl_1d = []
        pnl_all = []
        for g_ret, hd in zip(gap_returns, hold_days_list):
            if pd.isna(g_ret) or pd.isna(hd):
                continue
            s_next = spot * (1.0 + float(g_ret))
            days_elapsed = min(int(hd), dte_entry)
            T_exit = max(0.25 / 365.0, (dte_entry - days_elapsed) / 365.0)
            T_exit_1d = max(0.25 / 365.0, (dte_entry - 1) / 365.0)

            val_all = bs_call_price(s_next, cfg["k_long"], T_exit, r, sigma_exit)
            val_1d = bs_call_price(s_next, cfg["k_long"], T_exit_1d, r, sigma_exit)
            if cfg["k_short"] is not None:
                val_all -= bs_call_price(s_next, cfg["k_short"], T_exit, r, sigma_exit)
                val_1d -= bs_call_price(s_next, cfg["k_short"], T_exit_1d, r, sigma_exit)

            pnl_all.append((val_all / cfg["cost"] - 1.0) * 100.0)
            pnl_1d.append((val_1d / cfg["cost"] - 1.0) * 100.0)

        arr_all = np.array(pnl_all)
        arr_1d = np.array(pnl_1d)
        wins = arr_all[arr_all > 0]
        losses = arr_all[arr_all < 0]
        pf = round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) > 0 and losses.sum() != 0 else 999.0

        sim_results[name] = {
            "entry_cost_pts": round(cfg["cost"], 2),
            "k_long": cfg["k_long"],
            "k_short": cfg["k_short"],
            "actual_calendar_dte_win_rate_pct": round(float((arr_all > 0).mean() * 100.0), 2),
            "actual_calendar_dte_mean_roi_pct": round(float(arr_all.mean()), 2),
            "actual_calendar_dte_median_roi_pct": round(float(np.median(arr_all)), 2),
            "actual_calendar_dte_profit_factor": pf,
            "actual_calendar_dte_p05_roi_pct": round(float(np.percentile(arr_all, 5)), 2),
            "overnight_1d_win_rate_pct": round(float((arr_1d > 0).mean() * 100.0), 2),
            "overnight_1d_mean_roi_pct": round(float(arr_1d.mean()), 2),
        }

    return sim_results


def analyze_intraday_60d(symbol: str, df_15m: pd.DataFrame, df_daily: pd.DataFrame) -> dict:
    """Analyze 60-day 15-min late-afternoon (14:30-15:25) momentum & VWAP/TWAP vs next-day open."""
    d = df_15m.copy()
    d["hm"] = d["Datetime"].dt.hour * 100 + d["Datetime"].dt.minute
    d["typ_price"] = (d["High"] + d["Low"] + d["Close"]) / 3.0

    has_volume = (d["Volume"] > 0).sum() > (0.25 * len(d))
    day_records = []

    daily_map = df_daily.set_index("Date")
    sorted_dates = list(daily_map.index)
    next_open_map = {}
    for i in range(len(sorted_dates) - 1):
        next_open_map[sorted_dates[i]] = float(daily_map.loc[sorted_dates[i + 1], "Open"])

    for dt, grp in d.groupby("Date"):
        if dt not in next_open_map:
            continue
        grp = grp.sort_values("Datetime")
        if len(grp) < 10:
            continue

        if has_volume and grp["Volume"].sum() > 0:
            vwap = float((grp["typ_price"] * grp["Volume"]).sum() / grp["Volume"].sum())
            benchmark_type = "VWAP"
        else:
            vwap = float(grp["typ_price"].mean())
            benchmark_type = "TWAP (index 15m volume=0)"

        last_close = float(grp["Close"].iloc[-1])
        # Late window starting at 14:30 IST
        late_grp = grp[grp["hm"] >= 1430]
        if late_grp.empty:
            continue
        late_open = float(late_grp["Open"].iloc[0])
        late_ret = (last_close / late_open - 1.0)
        next_open = next_open_map[dt]
        gap_ret = (next_open / last_close - 1.0)

        day_records.append(
            {
                "Date": str(dt),
                "above_vwap": last_close > vwap,
                "late_ret": late_ret,
                "gap_ret": gap_ret,
                "benchmark_type": benchmark_type,
            }
        )

    res_df = pd.DataFrame(day_records)
    if res_df.empty:
        return {"days": 0}

    bull = res_df[(res_df["above_vwap"]) & (res_df["late_ret"] > 0)]
    bear = res_df[(~res_df["above_vwap"]) & (res_df["late_ret"] < 0)]

    def _stats(sub: pd.DataFrame, invert: bool = False) -> dict:
        if sub.empty:
            return {"days": 0}
        r = -sub["gap_ret"] if invert else sub["gap_ret"]
        return {
            "days": int(len(sub)),
            "win_rate_pct": round(float((r > 0).mean() * 100.0), 2),
            "mean_gap_pct": round(float(r.mean() * 100.0), 4),
            "median_gap_pct": round(float(r.median() * 100.0), 4),
        }

    return {
        "benchmark_used": res_df["benchmark_type"].iloc[0],
        "all_days": _stats(res_df),
        "bull_above_vwap_late_surge": _stats(bull),
        "bear_below_vwap_late_drop_stbt": _stats(bear, invert=True),
    }


def analyze_index(
    symbol: str,
    label: str,
    df_daily: pd.DataFrame,
    df_15m: pd.DataFrame,
    daily_all: dict[str, pd.DataFrame],
    weights: dict[str, float],
    vix_median: float,
    strike_step: float,
    dte_sim: int,
) -> dict:
    df = df_daily.copy()
    df["CLV"] = compute_clv(df)
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["R_intra"] = df["Close"] / df["Open"] - 1.0
    df["HW_CLV"] = build_heavyweight_clv(daily_all, weights, df["Date"])

    df["Next_Open"] = df["Open"].shift(-1)
    df["Next_Date"] = df["Date"].shift(-1)
    df["Overnight_Ret"] = df["Next_Open"] / df["Close"] - 1.0
    df["Gap_Points"] = df["Next_Open"] - df["Close"]
    df["C2C_Ret"] = df["Close"].shift(-1) / df["Close"] - 1.0
    df["Weekday"] = pd.to_datetime(df["Date"]).dt.dayofweek
    df["Hold_Days"] = (pd.to_datetime(df["Next_Date"]) - pd.to_datetime(df["Date"])).dt.days

    # Align evaluation sample where SMA20 and Next_Open are valid
    eval_df = df.dropna(subset=["SMA20", "Overnight_Ret"]).copy()

    decomposition = {
        "date_start": str(eval_df["Date"].iloc[0]),
        "date_end": str(eval_df["Date"].iloc[-1]),
        "trading_days": int(len(eval_df)),
        "overnight_only": summarize_return_series(eval_df["Overnight_Ret"]),
        "intraday_only": summarize_return_series(eval_df["R_intra"]),
        "buy_and_hold": summarize_return_series(eval_df["C2C_Ret"]),
    }

    cond_base = pd.Series(True, index=eval_df.index)
    cond_a = (eval_df["CLV"] >= 0.85) & (eval_df["R_intra"] > 0.0)
    cond_b = (
        (eval_df["CLV"] >= 0.85)
        & (eval_df["Close"] > eval_df["SMA20"])
        & (eval_df["R_intra"] >= 0.0015)
        & (eval_df["R_intra"] <= 0.0125)
    )
    cond_c = cond_b & (eval_df["HW_CLV"] >= 0.75)
    cond_d = eval_df["R_intra"] > 0.015
    cond_e = (eval_df["CLV"] <= 0.15) & (eval_df["Close"] < eval_df["SMA20"]) & (eval_df["HW_CLV"] <= 0.25)

    setups = {
        "Baseline (Every Night Long)": summarize_trade_setup(eval_df.loc[cond_base, "Overnight_Ret"], eval_df.loc[cond_base, "Gap_Points"]),
        "Setup A (CLV>=0.85 & Green Day)": summarize_trade_setup(eval_df.loc[cond_a, "Overnight_Ret"], eval_df.loc[cond_a, "Gap_Points"]),
        "Setup B (Trend + CLV>=0.85 + Non-Exhaustion)": summarize_trade_setup(eval_df.loc[cond_b, "Overnight_Ret"], eval_df.loc[cond_b, "Gap_Points"]),
        "Setup C (Institutional Sync BTST)": summarize_trade_setup(eval_df.loc[cond_c, "Overnight_Ret"], eval_df.loc[cond_c, "Gap_Points"]),
        "Setup D (Exhaustion Days R_intra>1.5%)": summarize_trade_setup(eval_df.loc[cond_d, "Overnight_Ret"], eval_df.loc[cond_d, "Gap_Points"]),
        "Setup E (Bearish STBT / Put BTST)": summarize_trade_setup(-eval_df.loc[cond_e, "Overnight_Ret"], -eval_df.loc[cond_e, "Gap_Points"]),
    }

    # Weekday analysis (0=Mon .. 4=Fri)
    day_names = {0: "Mon->Tue", 1: "Tue->Wed", 2: "Wed->Thu", 3: "Thu->Fri", 4: "Fri->Mon"}
    weekday_stats = {}
    for wd, wd_label in day_names.items():
        sub_all = eval_df[eval_df["Weekday"] == wd]
        sub_c = eval_df[(eval_df["Weekday"] == wd) & cond_c]
        weekday_stats[wd_label] = {
            "unconditional": summarize_trade_setup(sub_all["Overnight_Ret"], sub_all["Gap_Points"]),
            "setup_c": summarize_trade_setup(sub_c["Overnight_Ret"], sub_c["Gap_Points"]),
        }

    # Options simulation on Setup C gaps
    latest_spot = float(df["Close"].iloc[-1])
    options_sim = simulate_options_structures(
        spot=latest_spot,
        strike_step=strike_step,
        gap_returns=eval_df.loc[cond_c, "Overnight_Ret"],
        hold_days_list=eval_df.loc[cond_c, "Hold_Days"],
        sigma_entry=vix_median / 100.0,
        dte_entry=dte_sim,
    )

    intraday_60d = analyze_intraday_60d(symbol, df_15m, df)

    return {
        "symbol": symbol,
        "label": label,
        "latest_close": round(latest_spot, 2),
        "latest_date": str(df["Date"].iloc[-1]),
        "decomposition": decomposition,
        "setups": setups,
        "weekday_analysis": weekday_stats,
        "intraday_60d": intraday_60d,
        "options_simulation": {
            "reference_spot": round(latest_spot, 2),
            "assumed_iv_pct": round(vix_median, 2),
            "iv_crush_pct_pts": 0.75,
            "dte_entry_days": dte_sim,
            "structures": options_sim,
        },
    }


def main() -> None:
    print("Fetching 10y daily and 60d 15m data from Yahoo Finance...")
    daily_all: dict[str, pd.DataFrame] = {}
    for ticker in INDICES + HEAVYWEIGHTS:
        daily_all[ticker] = fetch_yahoo_chart(ticker, range_str="10y", interval="1d")
        print(f"  Daily {ticker}: {len(daily_all[ticker])} rows ({daily_all[ticker]['Date'].iloc[0]} -> {daily_all[ticker]['Date'].iloc[-1]})")

    intraday_indices: dict[str, pd.DataFrame] = {}
    for ticker in ["^NSEI", "^NSEBANK"]:
        intraday_indices[ticker] = fetch_yahoo_chart(ticker, range_str="60d", interval="15m")
        print(f"  15m   {ticker}: {len(intraday_indices[ticker])} rows")

    vix_df = daily_all["^INDIAVIX"]
    vix_median = float(vix_df["Close"].median())
    vix_latest = float(vix_df["Close"].iloc[-1])

    results = {
        "generated_at": datetime.now(IST).isoformat(),
        "india_vix": {
            "latest": round(vix_latest, 2),
            "median_10y": round(vix_median, 2),
            "p25_10y": round(float(vix_df["Close"].quantile(0.25)), 2),
            "p75_10y": round(float(vix_df["Close"].quantile(0.75)), 2),
        },
        "indices": {
            "^NSEI": analyze_index(
                symbol="^NSEI",
                label="Nifty 50",
                df_daily=daily_all["^NSEI"],
                df_15m=intraday_indices["^NSEI"],
                daily_all=daily_all,
                weights=NIFTY_WEIGHTS,
                vix_median=vix_median,
                strike_step=50.0,
                dte_sim=4,  # Typical mid-week weekly contract (~4 DTE)
            ),
            "^NSEBANK": analyze_index(
                symbol="^NSEBANK",
                label="Bank Nifty",
                df_daily=daily_all["^NSEBANK"],
                df_15m=intraday_indices["^NSEBANK"],
                daily_all=daily_all,
                weights=BANKNIFTY_WEIGHTS,
                vix_median=vix_median,
                strike_step=100.0,
                dte_sim=15,  # Monthly contract mid-cycle (~15 DTE)
            ),
        },
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved backtest results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
