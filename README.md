# Wave Rider: Quantitative Momentum & Smart-Money Engine

An automated quantitative scanning, classification, and backtesting system designed to identify and exploit **3–5 day momentum expansions** in fundamentally sound, non-speculative US Tech, Semiconductor, and Memory equities.

---

## 🌟 Key Pillars & Architectural Advantages

1. **Zero Bankruptcy Risk Universe**: Focused strictly on **50 market-leading US tech, semiconductor, and data infrastructure equities** (Nvidia, Micron, Western Digital, TSMC, ASML, Microsoft, Dell, Apple, etc.) with fortress balance sheets.
2. **Smart Money Accumulation Footprints**: Integrates official **US Congressional STOCK Act disclosures** and **SEC Form 4 Corporate Insider cluster buys**.
3. **Social & Financial News Velocity**: Measures headline acceleration and domain-specific sentiment polarity.
4. **Day-1 Ignition Timing**: Solves the core flaw of legacy trend-following systems by requiring high Relative Volume ($\text{RVOL} \ge 1.50\times$) and structural range expansion, eliminating late-trend top-chasing.
5. **Calibrated Asymmetry**: Targets $+3.5\%$ (scale 50%) and $+6.0\%$ (runner liquidation) against a $-2.5\%$ stop-loss with dynamic 5-day EMA trailing and a strict 5-day time stop.
6. **100% Local Execution**: Runs entirely on your local CPU. Zero ongoing cloud costs, zero token fees, and zero LLM dependencies at runtime.

---

## 📁 System Architecture

```
predict-stock/
├── data/
│   ├── watchlist.json              # 50 verified US tech, semiconductor & cloud titans across 4 macro sectors
│   └── cache/                      # Multi-tier local cache (parquet & json)
├── src/
│   ├── fetchers/
│   │   ├── price_fetcher.py        # Daily EOD bars + Pre-Market quotes
│   │   ├── politician_data.py      # US Congressional STOCK Act disclosures
│   │   ├── insider_data.py         # SEC Form 4 Corporate Insider purchases
│   │   └── social_sentiment.py     # Financial news buzz & sentiment polarity
│   ├── analysis/
│   │   ├── features.py             # Feature engineering pipeline & forward target
│   │   ├── wave_detector.py        # Day-1 Wave Ignition rule engine
│   │   └── wave_classifier.py      # Calibrated HistGradientBoosting classifier
│   ├── backtest/
│   │   └── backtester.py           # Historical walkforward simulation engine
│   ├── dashboard/
│   │   ├── app.py                  # Local Flask web application server
│   │   ├── templates/index.html    # Interactive single-page dashboard
│   │   └── static/                 # Stylesheet & Chart.js client script
│   └── main.py                     # Dual-cadence CLI entrypoint
├── tests/                          # Automated test suite (21 unit & integration tests)
├── ARCHITECTURE.md                 # Full engineering blueprint & ADRs
└── requirements.txt
```

---

## 🚀 Quick Start Guide

### 1. Run the Evening End-of-Day (EOD) Scan
Run after US market close (~22:00 CET / 4:00 PM EST) to produce tomorrow's candidate watchlist:
```bash
python -m src.main --mode eod
```

### 2. Run the Morning Pre-Market (PM) Gap Check
Run before market open (~14:30–15:15 CET / 8:30–9:15 AM EST) to check pre-market quotes, gap percentages, and confirm follow-through:
```bash
python -m src.main --mode premarket
```

### 3. Run a Walkforward Backtest on Any Stock
Simulates bar-by-bar performance without lookahead bias:
```bash
python -m src.main --backtest NVDA --period 2y
python -m src.main --backtest MU --period 2y
```

### 5. Launch the Interactive Local Dashboard
Starts the local web app with the live radar table, interactive price charts with stop/target lines, Congressional/Insider inspection, the 1-click backtest sandbox, and the **5-Day Live Trading Duel**:
```bash
python -m src.dashboard.app
```
Then open your browser at 👉 **`http://localhost:5050`**

### 6. ⚔️ 5-Day Live "Player vs. Bot" Paper Trading Duel
A live paper trading contest running from **Monday Sep 28 to Friday Oct 2, 2026, at 23:00 CET (21:00 UTC)**:
- **Starting Bankrolls**: $30,000 USD each (Player and Bot).
- **Playing Field**: Strictly the 27 US Tech & Memory universe (long-only, no shorting, live market pricing).
- **Goal**: Highest Total Net Equity at Friday Oct 2, 23:00 CET.
- **Bot Transparency**: Bot logs full disclosures for every trade, explaining its technical ignition thesis and external catalysts (Congressional filings, SEC Form 4 insider clusters, sentiment).

**Run or interact via CLI:**
```bash
# View the live duel scoreboard and open positions
python -m src.main --duel

# Execute a player order (BUY or SELL)
python -m src.main --order BUY NVDA 10
python -m src.main --order SELL NVDA 5

# Trigger an autonomous Bot evaluation cycle (can be run hourly via cron)
python -m src.main --bot-turn

# Reset the duel to a clean $30,000 starting line
python -m src.main --reset-duel
```
Or use the **`⚔️ 5-Day Duel`** tab directly inside the Web Dashboard at `http://localhost:5050`.

### 7. Static Cloud Exporter & Local Port 5055 Review
Compile the dynamic application into a zero-cost, self-contained static Single Page Application (SPA) with pre-rendered REST JSON payloads:
```bash
# 1. Export static bundle in fast mode (<20s)
python -m src.main --export-static --export-mode fast

# 2. Or export full 50-stock dossiers and multi-horizon backtests
python -m src.main --export-static --export-mode full

# 3. Serve and review locally without Flask on port 5055
python -m http.server 5055 --directory dist
```
Then open your browser at 👉 **`http://localhost:5055`** to preview the exact static cloud experience.

### 8. Requirements Traceability Matrix (RTM) & Test Suite
Executes all 61 automated unit and integration tests across data fetchers, smart money, feature pipeline, ignition rules, ML classifier, duel game engine, capitulation carve-out, and cloud deployment:
```bash
# Run complete test suite (61 of 61 tests passing)
pytest

# Run IEEE 830 / 1016 Requirements Traceability Matrix compliance report (50 / 50 verified)
python -m src.main --verify-rtm
```

---

## 🎯 Tracked Universe (27 Tickers)

- **Pure Memory & Storage (5)**: `MU`, `WDC`, `STX`, `SKHY`, `SNDK`
- **Capital Equipment (Picks & Shovels) (5)**: `LRCX`, `AMAT`, `KLAC`, `ASML` (ADR), `TXN`
- **AI Compute & Systems (6)**: `NVDA`, `AMD`, `SMCI`, `DELL`, `INTC`, `TSM` (ADR)
- **Connectivity & Custom Silicon (4)**: `AVGO`, `QCOM`, `ARM` (ADR), `MRVL`
- **Mega-Cap Anchors & High-Beta Momentum (7)**: `MSFT`, `AAPL`, `GOOGL`, `AMZN`, `META`, `TSLA`, `SPCX`

---

## 📖 In-Depth Documentation
For complete technical specifications, mathematical equations, and Architecture Decision Records (ADRs), read **[ARCHITECTURE.md](ARCHITECTURE.md)**.

