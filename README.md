# Nifty 50 & Bank Nifty BTST / STBT Quantitative Study

Empirical 10-year study (`2016-12-12` to `2026-11-12`) and live 3:15 PM IST diagnostic scanner for **Nifty 50 (`^NSEI`)** and **Bank Nifty (`^NSEBANK`)**.

## Files
- [fetch_and_backtest.py](fetch_and_backtest.py) — Fetches 10y daily + 60d 15m data for `^NSEI`, `^NSEBANK`, `^INDIAVIX`, and 8 heavyweight NSE constituents, runs the overnight/intraday decomposition, signal filter backtests, weekday seasonality, and Black-Scholes options simulations.
- [btst_scanner.py](btst_scanner.py) — Live 3:15 PM IST scanner scoring Nifty 50 and Bank Nifty (`-100` to `+100`) with structure recommendations and stop-loss levels. Supports `--save-report` to write `reports/latest_scan.md` and `reports/latest_scan.json`.
- [backtest_results.json](backtest_results.json) — Full serialized 10-year quantitative output.
- [.github/workflows/btst_automation.yml](.github/workflows/btst_automation.yml) — GitHub Actions workflow for automated daily closing scans and weekly backtest refreshes.

## Quick Usage
```powershell
pip install -r requirements.txt

# Refresh 10-year backtest and options simulation
python fetch_and_backtest.py

# Run live 3:15 PM BTST/STBT scanner (and optionally save Markdown/JSON reports)
python btst_scanner.py --save-report
```

## GitHub Actions Automation
The workflow in [.github/workflows/btst_automation.yml](.github/workflows/btst_automation.yml) runs automatically on GitHub:
- **Mon–Fri at 3:15 PM IST (`45 9 * * 1-5` UTC):** Runs `btst_scanner.py --save-report`, publishes the scan table to the GitHub Actions Job Summary, uploads artifacts, and commits updated `reports/latest_scan.md` and `reports/latest_scan.json`.
- **Fridays at 5:00 PM IST (`30 11 * * 5` UTC):** Refreshes the 10-year `backtest_results.json` via `fetch_and_backtest.py` alongside the report update.
- **Manual Trigger (`workflow_dispatch`):** Run anytime from the **Actions** tab with an optional `run_backtest` toggle.

## Key Empirical Findings (2016–2026)
1. **Overnight vs. Intraday Split:** Overnight Close-to-Open drift delivered `+1,233.62%` (`30.57%` CAGR, `2.65` Sharpe) on Nifty 50 and `+758.41%` (`24.77%` CAGR, `1.80` Sharpe) on Bank Nifty, while intraday Open-to-Close returns were negative (`-77.03%` and `-61.64%`).
2. **Nifty 50 Top Filter:** `Setup B` (`Close > SMA20`, `CLV >= 0.85`, `0.15% <= R_intra <= 1.25%`) achieved `75.85%` win rate, `3.54` Profit Factor, `+31.70` pts expectancy, and `-2.55%` max drawdown across `294` trades. Adding `HW_CLV >= 0.75` (`Setup C`) yielded `75.00%` win rate and `-2.00%` max drawdown across `80` trades.
3. **Bank Nifty Top Filter:** `Setup A` (`CLV >= 0.85` & green day) achieved `68.77%` win rate, `2.21` Profit Factor, `+71.92` pts expectancy, and `-4.46%` max drawdown across `413` trades.
4. **Bearish STBT (`Setup E`):** Negative expectancy over 10 years in both indices (`36.84%` win rate / `0.63` PF on Nifty 50; `43.66%` win rate / `0.68` PF on Bank Nifty).
5. **Options Structures (with Theta + 0.75 vol-pt Morning IV Crush):** Buying `~0.25` Delta OTM Calls loses `-21.92%` mean ROI on Nifty Setup C (`27.5%` win rate), whereas **Bull Call Debit Spreads** (`+5.09%` calendar-DTE / `+8.72%` 1-day ROI, `61.25%` win rate) and **ITM Calls (`~0.65` Delta)** (`+2.16%` calendar-DTE / `+5.62%` 1-day ROI) preserve positive expectancy.
