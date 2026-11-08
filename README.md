# Wave Rider: Quantitative Momentum & Smart-Money Engine

An automated quantitative scanning, classification, and backtesting system designed to identify and exploit **3–5 day momentum expansions** in fundamentally sound, non-speculative US Tech, Semiconductor, and Memory equities.

---

## 🏄‍♂️ What Does This Engine Actually Do? (Explained for Smart High-Schoolers)

Imagine you are standing on the beach watching surfers. 

If a surfer paddles out on a completely flat, windless lake, nothing happens — they just float there bored. But if a surfer sees a massive wave that has already broken into violent white foam and is crashing directly onto the rocks, jumping in right then is a recipe for a trip to the emergency room. 

In the stock market, **most amateur traders get wiped out every single day** because they do the financial equivalent of jumping into crashing white water: they buy a stock *after* it has already surged for four days straight and is trending on TikTok, right before the big institutions take their profits and send the price plunging.

**Wave Rider is built to do the exact opposite.** It is an automated mathematical radar designed to spot a fresh swell *the very second it starts rising* (Day 1), hop on the surfboard, ride the quick momentum push for 3 to 5 days, take the profit, and get off safely before the wave crashes.

Here is how it works under the hood, broken down step-by-step:

---

### 1. The "No-Garbage" Rule: Only 50 Fortress Titans
A lot of people think trading means gambling on penny stocks, meme coins, or dying companies hoping for a 10x lottery ticket. If those companies go bankrupt, your money goes to zero.

Wave Rider has a strict **Fortress Rule**: it is hard-coded to look **strictly at 50 of the most critical technology titans on planet Earth** (like Nvidia, Microsoft, Apple, TSMC, Micron, ASML, Broadcom, and Dell). 
* These companies make the actual microchips, servers, cloud software, and AI computers that the modern world cannot function without.
* They hold billions of real dollars in cash in the bank.
* **Why this matters**: Even if a trade doesn't work out as fast as we hoped, the company isn't going bankrupt overnight. We are trading the strongest balance sheets on planet Earth.

---

### 2. Following the Clues: "Smart Money" Footprints
Big stock moves rarely happen out of thin air. Before a stock jumps +5% or +10%, giant institutions and well-connected people leave footprints in the sand. Wave Rider monitors three specific public disclosures every single day:
1. **US Congressional Trades (The Capitol Hill Radar)**: By US law (the STOCK Act), members of the Senate and House must publicly disclose their stock purchases. If a politician sitting on the Armed Services or Science & Technology Committee suddenly buys \$100,000 of a semiconductor company, that is an asymmetric clue that major government funding or defense contracts might be heading their way.
2. **Corporate Insiders (C-Suite Whales)**: Company executives (CEOs, CFOs, Directors) know their company's order books better than anyone else. If three different top executives take their *own personal money* to buy company stock on the open market in the same month (called a "Cluster Buy"), they believe the stock is undervalued and about to pop.
3. **Federal Government Contracts**: Wave Rider directly tracks official awards from `USASpending.gov` (DoD, NASA, Department of Energy) to see if Uncle Sam just awarded a multi-million-dollar computing contract to a watchlist titan.

---

### 3. The Ignition Trigger: Relative Volume (RVOL)
Anyone can look at a stock chart and see lines moving up and down. But the real secret is **Volume** (how many shares are actually changing hands):
* If a stock creeps up +1% on tiny, sleepy volume, it’s just noise — nobody cares.
* But if a stock jumps through a ceiling while trading **1.5x to 3x its normal volume** ($\text{RVOL} \ge 1.50\times$), that isn't retail teenagers trading on their phones; that is billion-dollar pension funds, university endowments, and hedge funds buying millions of shares with aggressive market orders. 
* Wave Rider calls this **Day-1 Wave Ignition**. That is our signal to pay attention.

---

### 4. The Machine Learning Brain (Probability, Not Fortune-Telling)
Wave Rider does not use a magic crystal ball, and it doesn't use "black box" generative AI that hallucinates stories. 

Instead, it trains a local statistical machine-learning algorithm (`HistGradientBoostingClassifier`) on years of historical market data. It calculates a cold, objective math score from 0 to 100:
$$\text{Question: What are the exact statistical odds } P(\text{Wave Win}) \text{ that this stock gains at least } +3.5\% \text{ over the next 5 days without dropping more than } -2.5\%?$$

If the math probability isn't high enough, the engine simply folds its hand and waits. In trading, **sitting in cash is an active, winning position**.

---

### 5. Asymmetric Risk Management: The Ejector Seat & The Profit Escalator
The number one reason most traders lose money is simple human psychology: **pride**. When a stock goes down, people hold onto it, praying it will come back, turning a tiny -\$50 loss into a catastrophic -\$1,000 disaster. When a stock goes up a tiny bit, they get nervous and sell too early.

Wave Rider forces strict mathematical discipline:
* **The Ejector Seat (-2.5% Stop Loss)**: If we buy a stock at \$100 and it dips to \$97.50 (-2.5%), the engine ejects immediately. No praying, no excuses. A -2.5% loss is easily recovered on the next trade.
* **The Profit Escalator (+3.0% / +6.0%)**:
  1. If the stock rallies to $+3.0\%$, the bot automatically sells **half (50%) of the position** to lock cash profit in the bank.
  2. It immediately activates **Breakeven Runner Armor**: the stop-loss on the remaining half is moved up to entry price $+0.1\%$. That means the trade is now mathematically risk-free — it is literally impossible to lose money on it!
  3. If momentum continues toward $+6.0\%$, the remaining half is liquidated for maximum gain.
  4. If nothing happens after 5 days, the bot exits anyway (Time Stop) because the momentum window has closed.

---

### 6. The 5-Day "Player vs. Bot" Live Duel Desk
To test whether pure quantitative algorithms beat human emotions, Wave Rider features an interactive live paper-trading game:
* Both **You (The Human)** and **The Bot** start with **\$30,000 USD** in simulated capital.
* You can trade whenever you want using your own market instincts.
* The Bot runs completely autonomously in the background, scanning the tape, checking macro filters (like whether the broader Nasdaq $QQQ$ index is healthy), and executing orders with full plain-English explanations.
* Every trade is tracked mark-to-market until the bell rings on Friday night!

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
├── tests/                          # Automated test suite (61 automated unit & integration tests, 100% passing)
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

