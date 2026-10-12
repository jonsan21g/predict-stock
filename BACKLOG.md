# Wave Rider: Product Backlog & Engineering Roadmap

This document serves as the master backlog of completed capabilities, planned enhancements, and proposed feature ideas for the **Wave Rider (Wave Trader)** quantitative trading engine.

---

## 🏛️ Epic Taxonomy & Segregation Principles

To maintain modularity and architectural integrity, features are organized across **6 Core Epics** corresponding directly to Phases 1 through 6:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EPIC TAXONOMY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  EPIC 1: INGESTION FOUNDATION & ASSET UNIVERSE (Phase 1)                     │
│  EPIC 2: SMART MONEY INGESTION PIPELINE (Phase 2 - Primary Capital Footprint)│
│  EPIC 3: SOCIAL FEEDBACK LOOPS & FEATURE PIPELINE (Phase 3 - Crowd Reaction) │
│  EPIC 4: DAY-1 WAVE DETECTOR & WALKFORWARD BACKTESTER (Phase 4)              │
│  EPIC 5: MACHINE LEARNING CLASSIFIER & PROBABILITY ENGINE (Phase 5)         │
│  EPIC 6: INTERACTIVE DASHBOARD, LIVE DUEL & CLOUD DEPLOYMENT (Phase 6)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 🧭 Boundary Definition: Epic 2 (Smart Money) vs. Epic 3 (Sentiment & Buzz)

A key architectural distinction is drawn between **Primary Capital Footprints** (Epic 2) and **Second-Order Market Reactions** (Epic 3):

* **Epic 2: Smart Money (First-Party Footprints & Motive)**:
  - *Definition*: Direct, regulatory, or institutional data showing where capital and asymmetric information originate.
  - *Scope*: SEC Form 4 insider filings, Congressional STOCK Act filings, Congressional Committee assignments, US Federal Contract awards (USASpending.gov), and Institutional 13F whale filings.
  - *Question Answered*: *"Did someone with regulatory power or inside access deploy real money?"*

* **Epic 3: Social Buzz, Sentiment & Feature Pipeline (Second-Order Crowd Reaction)**:
  - *Definition*: Public dissemination, crowd psychology, and technical translation of market information.
  - *Scope*: Discussion velocity on Reddit/X/StockTwits, virality amplifiers (e.g., the "Pelosi Effect" retail rush), news sentiment polarity, and quantitative technical feature engineering (RVOL, CRR, Bollinger Band Width, EMA alignment).
  - *Question Answered*: *"How is the retail crowd and the tape reacting to this information right now?"*

---

## 📋 Epic-by-Epic Feature Backlog

### Epic 1: Ingestion Foundation & Asset Universe (Phase 1)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `ING-01` | **27 Fortress Equities Universe** | ✅ **Done** | Curated 27 liquid US Tech, Semiconductor & Memory titans across 5 sectors. | `data/watchlist.json` |
| `ING-02` | **Price Fetcher & Multi-Tier Cache** | ✅ **Done** | Daily historical OHLCV bars + pre-market quotes via `yfinance` with Parquet/JSON caching. | `src/fetchers/price_fetcher.py` |
| `ING-03` | **Dynamic Universe Expansion** | 💡 Proposed | Support for custom user watchlists or sub-sectors (e.g., Cyber Security, Nuclear Energy for AI). | Low effort |

---

### Epic 2: Smart Money Ingestion Pipeline (Phase 2 - Primary Capital Footprint)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `SM-01` | **Congressional STOCK Act Scraper** | ✅ **Done** | Scrapes and parses public House and Senate trade disclosures with 12h disk caching. | `src/fetchers/politician_data.py` |
| `SM-02` | **SEC Form 4 Corporate Insider Parser** | ✅ **Done** | Parses C-suite open-market purchases and detects cluster buying (2+ insiders in 30 days). | `src/fetchers/insider_data.py` |
| `SM-03` | **Congressional Committee Relevance Matching** | ✅ **Done** *(Item 1)* | Matches politician committee assignments (Armed Services, Science & Tech, Energy & Commerce) to tech/semiconductor tickers with a $2.5\times$ conviction multiplier. | `src/fetchers/politician_data.py` |
| `SM-04` | **US Federal Government Contract Awards** | ✅ **Done** *(Item 3)* | Ingests DoD, DoE, and NASA federal tech/compute contracts via official `api.usaspending.gov` API ($0 cost). | `src/fetchers/contracts_data.py` |
| `SM-05` | **Quiver Quantitative Tracker Feed** | 💬 **In Discussion** *(Item 4)* | Scrapes or ingests Quiver Quant's aggregated political, lobbying, and institutional tracker feeds. | Evaluates against direct sources |
| `SM-06` | **Institutional 13F Whale Tracking** | 💡 Proposed | Quarterly tracking of top tech hedge funds (e.g. Coatue, Whale Rock, Citadel) via SEC EDGAR. | Medium effort |

---

### Epic 3: Social Feedback Loops & Quantitative Feature Pipeline (Phase 3)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `SOC-01` | **Financial News & Sentiment Tracker** | ✅ **Done** | Scrapes financial headlines, computes sentiment polarity, and measures discussion velocity. | `src/fetchers/social_sentiment.py` |
| `SOC-02` | **Point-in-Time Feature Engineering** | ✅ **Done** | Computes RVOL, CRR, Bollinger Band Width, EMA alignment, and forward target labeling without lookahead bias. | `src/analysis/features.py` |
| `SOC-03` | **Targeted Politician Viral Buzz ("Pelosi Effect")** | ✅ **Done** *(Item 2)* | Real-time StockTwits streams and targeted news monitoring for politician/insider copy-trading herd velocity. | `src/fetchers/social_sentiment.py` |
| `SOC-04` | **X (Twitter) Influencer Tracker Scraper** | 💬 **In Discussion** *(Item 4 alt)* | Monitors public tweets/alerts from `@PelosiTracker_`, `@UnusualWhales`, and `@QuiverQuant` without paid API keys. | Requires resilient public scraping |
| `SOC-05` | **Options Market Whale Sweeps (Unusual Options)** | 💬 **In Discussion** *(Item 4 alt)* | Detects heavy out-of-the-money call option sweeps and high call/put volume ratios preceding wave ignition. | Requires free options data source |

---

### Epic 4: Day-1 Wave Detector & Walkforward Backtesting (Phase 4)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `DET-01` | **Day-1 Wave Ignition Rules** | ✅ **Done** | Enforces $\text{RVOL} \ge 1.50\times$, $\text{CRR} \ge 0.68$, range breakouts, and anti-exhaustion guard. | `src/analysis/wave_detector.py` |
| `DET-02` | **Walkforward Simulation Engine** | ✅ **Done** | Multi-year historical backtest with +3.5% scale 50%, +6.0% runner, -2.5% stop, 5 EMA trail, and 5-day time stop. | `src/backtest/backtester.py` |
| `DET-03` | **Dynamic Volatility Stops (ATR-Based Stops)** | 💡 Proposed | Option to set stop loss dynamically at $1.5 \times \text{ATR}_{14}$ instead of a fixed $-2.5\%$ stop. | Low effort |
| `DET-05` | **Break-Even Trailing Stop at +3.0% (The SPCX Rule)** | ✅ **Done** | Lock stop-loss at entry + 0.1% once a position reaches +3.0% gain to eliminate round-trip losses on runners. | [`WEEK_2_LEARNINGS.md`](file:///c:/Users/jonsa/LLM/predict-stock/WEEK_2_LEARNINGS.md) |
| `DET-06` | **Portfolio Risk Concentration Limits (Max 4 Positions, Max 2 Semis)** | ✅ **Done** | Limit concurrent holdings to 4 fortress positions and cap semiconductor exposure to prevent correlated basket drawdowns. | [`src/game/duel.py`](file:///c:/Users/jonsa/LLM/predict-stock/src/game/duel.py) |
| `DET-07` | **Multi-Tranche Partial Scaling (50% at +3.0%) & Ratchet Exit** | ✅ **Done** | Automatically harvest 50% profits at +3.0% and dynamic trailing ratchet floor locks gains before market pullbacks occur. | [`src/game/duel.py`](file:///c:/Users/jonsa/LLM/predict-stock/src/game/duel.py) |

---

### Epic 5: Machine Learning Classifier & Probability Scoring (Phase 5)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `ML-01` | **Calibrated Gradient Boosting Classifier** | ✅ **Done** | Locally trained `HistGradientBoostingClassifier` predicting $P(\text{Wave Win})$. | `src/analysis/wave_classifier.py` |
| `ML-02` | **Composite Scoring Model (0–100)** | ✅ **Done** | Blends technical breakout probability with Smart Money multiplier into a single rank. | Real-time radar ranking |
| `ML-03` | **Smart Money Weight Fine-Tuning** | 💡 Proposed | Recalibrate ML feature weights once Committee and Federal Contract features are active. | Dependent on Epic 2 |

---

### Epic 6: Interactive Dashboard, Live Duel & Cloud Deployment (Phase 6)

| ID | Feature | Status | Description | Notes / Effort |
| :--- | :--- | :--- | :--- | :--- |
| `UI-01` | **Interactive Glassmorphism Web App** | ✅ **Done** | Single-page UI at `localhost:5050` with live radar, candlestick charts, and backtest sandbox. | `src/dashboard/app.py` |
| `UI-02` | **5-Day Live "Player vs. Bot" Duel** | ✅ **Done** | \$30k starting bankroll, live order execution desk, transparent bot disclosures, countdown to Oct 2. | `src/game/duel.py` |
| `UI-03` | **Dual Execution Bot (Autonomous + Manual)** | ✅ **Done** | Background daemon thread (30m market, 60m off-hours) + 4 manual trigger mechanisms. | Dashboard + CLI + `.bat` |
| `DEP-01` | **Cloud Web Server Deployment (Render / Hugging Face)** | 💬 **In Discussion** | Deploying app 24/7 on free cloud tier (Render.com with pinger vs. Hugging Face Spaces 16GB RAM). | Zero ongoing cost |
| `DEP-02` | **State Persistence across Reboots (Supabase)** | 💬 **In Discussion** | Syncing `game_state.json` to a free Supabase PostgreSQL database to ensure state survives cloud reboots. | Permanent persistence |
