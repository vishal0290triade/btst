## BTST / STBT Automated Scan Report
- **Run Time (IST):** `2026-11-13 23:20:39`
- **India VIX:** `15.49`

| Metric | Nifty 50 (`^NSEI`) | Bank Nifty (`^NSEBANK`) |
| :--- | :--- | :--- |
| **Session Date** | `2026-11-13` | `2026-11-13` |
| **Spot / 20-DMA** | `25,144.30` (ABOVE 20-DMA: `23,642.28`) | `61,034.10` (ABOVE 20-DMA: `56,496.99`) |
| **Intraday Benchmark** | `25,142.17` (TWAP) | `60,998.50` (TWAP) |
| **CLV / Day Body / Late Surge** | `47.0%` / `-0.23%` / `+0.23%` | `48.7%` / `-0.43%` / `+0.15%` |
| **Heavyweight Sync** | `55.1%` | `64.5%` |
| **BTST Score & Signal** | **`+43.9 / 100`** — MODERATE BTST (Bullish) | **`+45.9 / 100`** — MODERATE BTST (Bullish) |
| **Paper Trade Structure** | Bull Call Debit Spread (25150/25450 CE) (`110.35` pts) | Bull Call Debit Spread (61000/62500 CE) (`575.14` pts) |
| **Stop-Loss** | Break below 3:00-3:30 PM Low (25,097.10) | Break below 3:00-3:30 PM Low (60,921.00) |
| **Morning Exit** | Book 50-100% at 9:15-9:20 AM gap open | Book 50-100% at 9:15-9:20 AM gap open |

### Heavyweight Constituent CLV Breakdown
- **Nifty 50:** `HDFCBANK: 60%`, `RELIANCE: 59%`, `ICICIBANK: 89%`, `INFY: 31%`, `TCS: 15%`, `AXISBANK: 36%`, `SBIN: 36%`, `KOTAKBANK: 80%`
- **Bank Nifty:** `HDFCBANK: 60%`, `ICICIBANK: 89%`, `SBIN: 36%`, `AXISBANK: 36%`, `KOTAKBANK: 80%`

---

## Paper Trading Cumulative Summary
- **Retained Dataset:** `120` sessions (`118` settled, `2` open) — see [paper_trades.csv](paper_trades.csv) & [paper_trades_summary.md](paper_trades_summary.md)
- **Active Trades Taken:** `73` (`22W / 51L`, **30.14%** win rate)
- **Cumulative Option P&L:** **`₹-27,506.77`** (`-4.72%` avg ROI/trade)

### Recent 15 Paper Trades

| Date | Index | Score | Structure | Entry Spot | Exit Open | Gap % | Option P&L (INR) | ROI % | Status |
| :--- | :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 2026-11-13 | Nifty 50 | +43.9 | Bull Call Debit Spread (25150/25450 CE) | 25,144.30 | - | - | - | - | OPEN |
| 2026-11-13 | Bank Nifty | +45.9 | Bull Call Debit Spread (61000/62500 CE) | 61,034.10 | - | - | - | - | OPEN |
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
| 2026-11-04 | Bank Nifty | +65.7 | Slightly ITM Call (55400 CE) | 55,913.60 | 57,086.70 | +2.10% | ₹+25,791.39 | +80.81% | WIN |
| 2026-11-03 | Nifty 50 | +91.2 | Slightly ITM Call (23700 CE) | 23,810.85 | 23,734.15 | -0.32% | ₹-5,616.20 | -32.84% | LOSS |
