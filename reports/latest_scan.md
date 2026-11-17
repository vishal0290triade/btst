## BTST / STBT Automated Scan Report
- **Run Time (IST):** `2026-11-17 18:03:22`
- **India VIX:** `15.52`

| Metric | Nifty 50 (`^NSEI`) | Bank Nifty (`^NSEBANK`) |
| :--- | :--- | :--- |
| **Session Date** | `2026-11-17` | `2026-11-17` |
| **Spot / 20-DMA** | `25,387.40` (ABOVE 20-DMA: `23,869.03`) | `62,273.25` (ABOVE 20-DMA: `57,106.73`) |
| **Intraday Benchmark** | `25,418.10` (TWAP) | `62,245.05` (TWAP) |
| **CLV / Day Body / Late Surge** | `50.9%` / `+0.44%` / `-0.30%` | `82.0%` / `+1.16%` / `-0.19%` |
| **Heavyweight Sync** | `53.9%` | `57.0%` |
| **BTST Score & Signal** | **`-4.1 / 100`** — NO TRADE / NEUTRAL | **`+50.0 / 100`** — MODERATE BTST (Bullish) |
| **Paper Trade Structure** | Stay in Cash (no directional edge) (`0.00` pts) | Slightly ITM Call (61700 CE) (`1200.99` pts) |
| **Stop-Loss** | - | Break below 3:00-3:30 PM Low (62,207.10) |
| **Morning Exit** | - | Book 50-100% at 9:15-9:20 AM gap open |

### Heavyweight Constituent CLV Breakdown
- **Nifty 50:** `HDFCBANK: 40%`, `RELIANCE: 82%`, `ICICIBANK: 57%`, `INFY: 21%`, `TCS: 35%`, `AXISBANK: 80%`, `SBIN: 76%`, `KOTAKBANK: 65%`
- **Bank Nifty:** `HDFCBANK: 40%`, `ICICIBANK: 57%`, `SBIN: 76%`, `AXISBANK: 80%`, `KOTAKBANK: 65%`

---

## Paper Trading Cumulative Summary
- **Retained Dataset:** `122` sessions (`122` settled, `0` open) — see [paper_trades.csv](paper_trades.csv) & [paper_trades_summary.md](paper_trades_summary.md)
- **Active Trades Taken:** `77` (`23W / 54L`, **29.87%** win rate)
- **Cumulative Option P&L:** **`₹-32,031.56`** (`-4.78%` avg ROI/trade)

### Recent 15 Paper Trades

| Date | Index | Score | Structure | Entry Spot | Exit Open | Gap % | Option P&L (INR) | ROI % | Status |
| :--- | :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2026-11-16 | Nifty 50 | +63.1 | Slightly ITM Call (25150 CE) | 25,291.10 | 25,277.30 | -0.05% | ₹-2,775.24 | -14.52% | LOSS |
| 2026-11-16 | Bank Nifty | +62.2 | Slightly ITM Call (61000 CE) | 61,575.90 | 61,561.00 | -0.02% | ₹-1,987.83 | -5.56% | LOSS |
| 2026-11-13 | Nifty 50 | +43.9 | Bull Call Debit Spread (25150/25450 CE) | 25,144.30 | 25,206.15 | +0.25% | ₹-690.37 | -8.34% | LOSS |
| 2026-11-13 | Bank Nifty | +45.9 | Bull Call Debit Spread (61000/62500 CE) | 61,034.10 | 61,229.90 | +0.32% | ₹+928.65 | +5.38% | WIN |
| 2026-11-12 | Nifty 50 | +61.3 | Bull Call Debit Spread (25300/25600 CE) | 25,299.35 | 25,201.90 | -0.39% | ₹-2,643.42 | -30.86% | LOSS |
| 2026-11-12 | Bank Nifty | +80.6 | Bull Call Debit Spread (61500/63100 CE) | 61,518.50 | 61,300.55 | -0.35% | ₹-2,457.23 | -13.49% | LOSS |
| 2026-11-11 | Nifty 50 | +3.7 | Stay in Cash (no directional edge) | 25,255.05 | 25,213.50 | -0.16% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-11 | Bank Nifty | -3.8 | Stay in Cash (no directional edge) | 60,792.40 | 60,807.90 | +0.03% | ₹+0.00 | +0.00% | NO_TRADE |
| 2026-11-09 | Nifty 50 | +71.4 | Bull Call Debit Spread (25050/25400 CE) | 25,044.65 | 25,337.80 | +1.17% | ₹+7,381.57 | +77.85% | WIN |
| 2026-11-09 | Bank Nifty | +89.5 | Bull Call Debit Spread (59700/61400 CE) | 59,741.25 | 60,471.05 | +1.22% | ₹+6,611.67 | +34.49% | WIN |
| 2026-11-06 | Nifty 50 | +61.4 | Bull Call Debit Spread (25050/25350 CE) | 25,030.35 | 25,073.65 | +0.17% | ₹-1,316.15 | -15.85% | LOSS |
| 2026-11-06 | Bank Nifty | +64.8 | Bull Call Debit Spread (59100/60700 CE) | 59,086.00 | 59,219.95 | +0.23% | ₹+449.48 | +2.51% | WIN |
| 2026-11-05 | Nifty 50 | +68.6 | Slightly ITM Call (24400 CE) | 24,536.60 | 24,518.20 | -0.07% | ₹-3,057.49 | -16.45% | LOSS |
| 2026-11-05 | Bank Nifty | +79.3 | Slightly ITM Call (57300 CE) | 57,773.65 | 57,692.25 | -0.14% | ₹-3,396.06 | -10.48% | LOSS |
| 2026-11-04 | Nifty 50 | +76.7 | Slightly ITM Call (23850 CE) | 23,960.60 | 24,378.05 | +1.74% | ₹+24,189.13 | +144.08% | WIN |
