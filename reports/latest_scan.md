## BTST / STBT Automated Scan Report
- **Run Time (IST):** `2026-11-20 17:45:07`
- **India VIX:** `16.11`

| Metric | Nifty 50 (`^NSEI`) | Bank Nifty (`^NSEBANK`) |
| :--- | :--- | :--- |
| **Session Date** | `2026-11-20` | `2026-11-20` |
| **Spot / 20-DMA** | `25,800.60` (ABOVE 20-DMA: `24,276.78`) | `64,635.20` (ABOVE 20-DMA: `58,324.03`) |
| **Intraday Benchmark** | `25,646.31` (TWAP) | `63,922.43` (TWAP) |
| **CLV / Day Body / Late Surge** | `98.2%` / `+1.71%` / `+0.14%` | `97.9%` / `+3.17%` / `+0.08%` |
| **Heavyweight Sync** | `78.0%` | `87.3%` |
| **BTST Score & Signal** | **`+52.2 / 100`** — MODERATE BTST (Bullish) | **`+53.1 / 100`** — MODERATE BTST (Bullish) |
| **Paper Trade Structure** | Bull Call Debit Spread (25800/26100 CE) (`114.28` pts) | Bull Call Debit Spread (64600/66300 CE) (`641.93` pts) |
| **Stop-Loss** | Break below 3:00-3:30 PM Low (25,763.35) | Break below 3:00-3:30 PM Low (64,567.20) |
| **Morning Exit** | Book 50-100% at 9:15-9:20 AM gap open | Book 50-100% at 9:15-9:20 AM gap open |

### Heavyweight Constituent CLV Breakdown
- **Nifty 50:** `HDFCBANK: 88%`, `RELIANCE: 80%`, `ICICIBANK: 88%`, `INFY: 42%`, `TCS: 61%`, `AXISBANK: 95%`, `SBIN: 68%`, `KOTAKBANK: 96%`
- **Bank Nifty:** `HDFCBANK: 88%`, `ICICIBANK: 88%`, `SBIN: 68%`, `AXISBANK: 95%`, `KOTAKBANK: 96%`

---

## Paper Trading Cumulative Summary
- **Retained Dataset:** `128` sessions (`128` settled, `0` open) — see [paper_trades.csv](paper_trades.csv) & [paper_trades_summary.md](paper_trades_summary.md)
- **Active Trades Taken:** `80` (`23W / 57L`, **28.75%** win rate)
- **Cumulative Option P&L:** **`₹-53,152.49`** (`-5.62%` avg ROI/trade)

### Recent 15 Paper Trades

| Date | Index | Score | Structure | Entry Spot | Exit Open | Gap % | Option P&L (INR) | ROI % | Status |
| :--- | :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2026-11-19 | Nifty 50 | +55.9 | Slightly ITM Call (25400 CE) | 25,514.30 | 25,367.90 | -0.57% | ₹-8,480.46 | -47.11% | LOSS |
| 2026-11-19 | Bank Nifty | +59.3 | Slightly ITM Call (62500 CE) | 63,063.00 | 62,648.65 | -0.66% | ₹-9,644.28 | -26.63% | LOSS |
| 2026-11-18 | Nifty 50 | -14.1 | Stay in Cash (no directional edge) | 25,227.95 | 25,186.80 | -0.16% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-18 | Bank Nifty | -2.3 | Stay in Cash (no directional edge) | 62,038.65 | 62,060.75 | +0.04% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-17 | Nifty 50 | -4.1 | Stay in Cash (no directional edge) | 25,387.40 | 25,323.15 | -0.25% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-17 | Bank Nifty | +50.0 | Slightly ITM Call (61700 CE) | 62,273.25 | 62,231.75 | -0.07% | ₹-2,996.19 | -8.26% | LOSS |
| 2026-11-16 | Nifty 50 | +63.1 | Slightly ITM Call (25150 CE) | 25,291.10 | 25,277.30 | -0.05% | ₹-2,775.24 | -14.52% | LOSS |
| 2026-11-16 | Bank Nifty | +62.2 | Slightly ITM Call (61000 CE) | 61,575.90 | 61,561.00 | -0.02% | ₹-1,987.83 | -5.56% | LOSS |
| 2026-11-13 | Nifty 50 | +43.9 | Bull Call Debit Spread (25150/25450 CE) | 25,144.30 | 25,206.15 | +0.25% | ₹-690.37 | -8.34% | LOSS |
| 2026-11-13 | Bank Nifty | +45.9 | Bull Call Debit Spread (61000/62500 CE) | 61,034.10 | 61,229.90 | +0.32% | ₹+928.65 | +5.38% | WIN |
| 2026-11-12 | Nifty 50 | +61.3 | Bull Call Debit Spread (25300/25600 CE) | 25,299.35 | 25,201.90 | -0.39% | ₹-2,643.42 | -30.86% | LOSS |
| 2026-11-12 | Bank Nifty | +80.6 | Bull Call Debit Spread (61500/63100 CE) | 61,518.50 | 61,300.55 | -0.35% | ₹-2,457.23 | -13.49% | LOSS |
| 2026-11-11 | Nifty 50 | +3.7 | Stay in Cash (no directional edge) | 25,255.05 | 25,213.50 | -0.16% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-11 | Bank Nifty | -3.8 | Stay in Cash (no directional edge) | 60,792.40 | 60,807.90 | +0.03% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-09 | Nifty 50 | +71.4 | Bull Call Debit Spread (25050/25400 CE) | 25,044.65 | 25,337.80 | +1.17% | ₹+7,381.57 | +77.85% | WIN |
