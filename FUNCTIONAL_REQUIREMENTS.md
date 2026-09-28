# Wave Rider: Functional Requirements Specification (FRS)
## Systems Engineering & Requirements Traceability Matrix (RTM)

- **Project**: `predict-stock` (Wave Rider Quantitative Momentum & Smart-Money Engine)
- **Standard**: IEEE 830 / ISO/IEC/IEEE 29148 Software Requirements Specification
- **Classification**: Proprietary Quantitative System Specification
- **Target Runtime**: Local Execution (Windows / Python 3.12 / Zero Cloud API Fees)
- **Traceability Status**: 100% Traceable (All 34 Automated Test Cases Mapped)

---

## 1. Introduction & Operational Context

### 1.1 Purpose
This document defines the complete **Functional Requirements Specification (FRS)** for the **Wave Rider** trading engine. It formalizes **WHAT** the system must do across its functional life cycle, defining inputs, outputs, mathematical formulas, state transitions, business rules, edge-case constraints, and validation acceptance criteria.

### 1.2 System Operational Scope
Wave Rider is an automated quantitative screening, pattern classification, backtesting, and paper-trading system designed to capture **3- to 5-day momentum expansions (+3.5% to +6.0%)** in fundamentally sound US technology, semiconductor, and data infrastructure equities, with strict downside risk protection (-2.5% stop-loss or 5-day EMA trail).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       WAVE RIDER SYSTEM PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  [1. Universe Ingestion]  -->  27 US Tech & Memory Leaders (NASDAQ/NYSE)   │
│  [2. Smart Money Ingest]  -->  STOCK Act, Form 4 Insiders, USASpending.gov  │
│  [3. Social & Tape Buzz]  -->  StockTwits Streams & The Pelosi Effect      │
│  [4. Wave Detector]       -->  RVOL >= 1.50x, CRR >= 0.68, Range Breakouts │
│  [5. ML Probability]      -->  Calibrated HistGradientBoosting P(Wave Win) │
│  [6. Execution & Duel]    -->  Dashboard Desk & 5-Day "Player vs. Bot"     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Key Operational Cadences
1. **End-of-Day (EOD) Scan (~22:00 CET / 16:00 EDT)**: Evaluates completed daily candles, computes technical indicators, ingests after-hours regulatory disclosures, trains/predicts wave win probabilities, and outputs the next day's high-conviction watchlist.
2. **Pre-Market (PM) Confirmation (~14:30–15:15 CET / 08:30–09:15 EDT)**: Ingests pre-market quote streams and overnight gaps to confirm or invalidate EOD setups prior to the regular market opening bell.
3. **Regular Market Intraday Daemon (15:30–22:00 CET / 09:30–16:00 EDT)**: Evaluates live positions and scans the universe every 30 minutes (or on-demand) during active market hours.

---

## 2. Master Requirements Traceability Matrix (RTM)

The following matrix provides 100% bidirectional traceability between functional requirements, their physical implementation files, their associated automated test cases, and the terminal command required to execute them.

| Req ID | Requirement Title | Epic | Implementation File | Test Case ID | Automated Test Function |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`FR-01-01`** | Curated 27 Blue-Chip Universe | Epic 1 | `data/watchlist.json` | `TC-ING-01` | [`tests/test_price_fetcher.py::test_watchlist_structure`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py) |
| **`FR-01-02`** | Daily OHLCV Price Fetcher & Caching | Epic 1 | `src/fetchers/price_fetcher.py` | `TC-ING-02` | [`tests/test_price_fetcher.py::test_daily_history_fetch`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py) |
| **`FR-01-03`** | Pre-Market Quotes & Gap Detection | Epic 1 | `src/fetchers/price_fetcher.py` | `TC-ING-03` | [`tests/test_price_fetcher.py::test_premarket_quote`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py) |
| **`FR-02-01`** | Congressional STOCK Act Parser | Epic 2 | `src/fetchers/politician_data.py` | `TC-SM-01` | [`tests/test_smart_money.py::test_parse_trade_row`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py) |
| **`FR-02-02`** | Congressional Conviction Scoring | Epic 2 | `src/fetchers/politician_data.py` | `TC-SM-02` | [`tests/test_smart_money.py::test_congress_signals_with_mock`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py) |
| **`FR-02-03`** | Committee Relevance & $2.5\times$ Multiplier | Epic 2 | `src/fetchers/politician_data.py` | `TC-SM-03` | [`tests/test_smart_money.py::test_congress_committee_jurisdiction_matching`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py) |
| **`FR-02-04`** | SEC Form 4 Corporate Insider Parser | Epic 2 | `src/fetchers/insider_data.py` | `TC-SM-04` | [`tests/test_smart_money.py::test_insider_transactions_live`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py) |
| **`FR-02-05`** | US Federal Contracts Ingestion (USASpending) | Epic 2 | `src/fetchers/contracts_data.py` | `TC-SM-05` | [`tests/test_contracts.py::test_get_ticker_contract_signals_dell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_contracts.py) |
| **`FR-02-06`** | Federal Contract Scoring Thresholds | Epic 2 | `src/fetchers/contracts_data.py` | `TC-SM-06` | [`tests/test_contracts.py::test_contracts_scoring_thresholds`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_contracts.py) |
| **`FR-03-01`** | Financial News Sentiment Polarity | Epic 3 | `src/fetchers/social_sentiment.py` | `TC-SOC-01` | [`tests/test_social_sentiment.py::test_score_text_sentiment`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py) |
| **`FR-03-02`** | Targeted Politician Buzz Detection | Epic 3 | `src/fetchers/social_sentiment.py` | `TC-SOC-02` | [`tests/test_social_sentiment.py::test_scan_politician_viral_buzz_detection`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py) |
| **`FR-03-03`** | The Pelosi Effect Social Stream Diagnostics | Epic 3 | `src/fetchers/social_sentiment.py` | `TC-SOC-03` | [`tests/test_social_sentiment.py::test_get_ticker_social_sentiment_structure`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py) |
| **`FR-03-04`** | Point-in-Time Technical Indicator Engine | Epic 3 | `src/analysis/features.py` | `TC-FEAT-01` | [`tests/test_features.py::test_compute_technical_indicators`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py) |
| **`FR-03-05`** | Forward Target Labeling ($+3.5\%$ in 5D) | Epic 3 | `src/analysis/features.py` | `TC-FEAT-02` | [`tests/test_features.py::test_create_wave_target`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py) |
| **`FR-03-06`** | Feature Matrix & Sentiment Integration | Epic 3 | `src/analysis/features.py` | `TC-FEAT-03` | [`tests/test_features.py::test_build_feature_matrix`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py) |
| **`FR-04-01`** | Day-1 Wave Ignition Core Verification | Epic 4 | `src/analysis/wave_detector.py` | `TC-DET-01` | [`tests/test_wave_detector.py::test_wave_ignition_valid`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py) |
| **`FR-04-02`** | Ignition Rejection on Volume Failure | Epic 4 | `src/analysis/wave_detector.py` | `TC-DET-02` | [`tests/test_wave_detector.py::test_wave_ignition_rejection_low_volume`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py) |
| **`FR-04-03`** | Anti-Exhaustion Upper BB Guard Rejection | Epic 4 | `src/analysis/wave_detector.py` | `TC-DET-03` | [`tests/test_wave_detector.py::test_wave_ignition_rejection_extended`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py) |
| **`FR-04-04`** | Walkforward Simulation Engine | Epic 4 | `src/backtest/backtester.py` | `TC-BT-01` | [`tests/test_backtest.py::test_wave_backtest_execution`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_backtest.py) |
| **`FR-05-01`** | Calibrated Gradient Boosting Training | Epic 5 | `src/analysis/wave_classifier.py` | `TC-ML-01` | [`tests/test_classifier.py::test_train_wave_model_and_inference`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_classifier.py) |
| **`FR-05-02`** | Composite Confidence Scoring Model | Epic 5 | `src/analysis/wave_classifier.py` | `TC-ML-02` | [`tests/test_classifier.py::test_score_single_stock`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_classifier.py) |
| **`FR-06-01`** | Live Duel State Initialization | Epic 6 | `src/game/duel.py` | `TC-GAME-01` | [`tests/test_game.py::test_initial_game_state`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-02`** | Player Market Order Execution | Epic 6 | `src/game/duel.py` | `TC-GAME-02` | [`tests/test_game.py::test_player_order_buy_and_sell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-03`** | Bankroll Validation & Overspend Guard | Epic 6 | `src/game/duel.py` | `TC-GAME-03` | [`tests/test_game.py::test_player_order_insufficient_cash`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-04`** | Universe Integrity Guard | Epic 6 | `src/game/duel.py` | `TC-GAME-04` | [`tests/test_game.py::test_player_order_invalid_ticker`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-05`** | Shorting Prevention & Oversell Guard | Epic 6 | `src/game/duel.py` | `TC-GAME-05` | [`tests/test_game.py::test_player_order_oversell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-06`** | Autonomous Bot Turn & Catalyst Disclosures | Epic 6 | `src/game/duel.py` | `TC-GAME-06` | [`tests/test_game.py::test_bot_evaluate_turn_with_disclosures`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py) |
| **`FR-06-07`** | Web Dashboard UI Root Endpoint | Epic 6 | `src/dashboard/app.py` | `TC-UI-01` | [`tests/test_interface.py::test_dashboard_index`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-08`** | Dashboard Health Probe | Epic 6 | `src/dashboard/app.py` | `TC-UI-02` | [`tests/test_interface.py::test_dashboard_health`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-09`** | Radar API Endpoint & Premarket Mode | Epic 6 | `src/dashboard/app.py` | `TC-UI-03` | [`tests/test_interface.py::test_dashboard_radar_premarket`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-10`** | Stock Deep-Dive Forensic API | Epic 6 | `src/dashboard/app.py` | `TC-UI-04` | [`tests/test_interface.py::test_dashboard_stock_detail`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-11`** | Backtest Sandbox API | Epic 6 | `src/dashboard/app.py` | `TC-UI-05` | [`tests/test_interface.py::test_dashboard_backtest_api`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-12`** | CLI Runner Premarket Execution | Epic 6 | `src/main.py` | `TC-UI-06` | [`tests/test_interface.py::test_cli_premarket_execution`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-06-13`** | Game State & Order API Endpoints | Epic 6 | `src/dashboard/app.py` | `TC-UI-07` | [`tests/test_interface.py::test_dashboard_game_endpoints`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py) |
| **`FR-07-01`** | Free-Tier Cloud Deployment *(Planned)* | Epic 6 | Render / HF Spaces | `TC-DEP-01` | Deferred / Pre-requisite to Cloud Hosting |
| **`FR-07-02`** | Supabase State Persistence *(Planned)* | Epic 6 | PostgreSQL Client | `TC-DEP-02` | Deferred / Pre-requisite to Cloud Hosting |

---

## 3. Detailed Functional Requirements Specification

---

### Epic 1: Asset Universe & Data Ingestion Foundation

#### `FR-01-01`: 27 Fortress Equities Universe
* **Description**: The system shall constrain its operational trading, scanning, and backtesting universe strictly to 27 pre-screened US liquid technology, semiconductor, and data infrastructure leaders.
* **Preconditions**: `data/watchlist.json` must exist, be valid JSON, and contain exactly 27 equity definitions.
* **Universe Segregation**:
  1. *Pure Memory & Storage (5)*: `MU`, `WDC`, `STX`, `SKHY`, `SNDK`
  2. *Capital Equipment / Picks & Shovels (5)*: `LRCX`, `AMAT`, `KLAC`, `ASML` (ADR), `TXN`
  3. *AI Compute & Enterprise Systems (6)*: `NVDA`, `AMD`, `SMCI`, `DELL`, `INTC`, `TSM` (ADR)
  4. *Connectivity & Custom Silicon (4)*: `AVGO`, `QCOM`, `ARM` (ADR), `MRVL`
  5. *Mega-Cap Anchors & Ballast (7)*: `MSFT`, `AAPL`, `GOOGL`, `AMZN`, `META`, `TSLA`, `SPCX`
* **Verification & Test**: `TC-ING-01` in [`tests/test_price_fetcher.py::test_watchlist_structure`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py).

#### `FR-01-02`: Multi-Tier Historical OHLCV Fetcher & Caching
* **Description**: The system shall fetch daily historical OHLCV data using public yfinance feeds with local disk caching to guarantee zero API fees and sub-second repeated queries.
* **Cache Policy**:
  * Format: Parquet / JSON.
  * Directory: `data/cache/`
  * TTL: 12 hours for historical bars; 15 minutes for current-day intraday data.
* **Outputs**: Pandas DataFrame containing `Open`, `High`, `Low`, `Close`, `Volume`.
* **Verification & Test**: `TC-ING-02` in [`tests/test_price_fetcher.py::test_daily_history_fetch`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py).

#### `FR-01-03`: Pre-Market Quote & Gap Ingestion
* **Description**: The system shall ingest pre-market prices between 14:30–15:15 CET, compute the pre-market gap percentage relative to previous close, and identify candidate gap ignitions:
  $$\text{Gap}_{\%} = \left( \frac{\text{PreMarket Price} - \text{Close}_{t-1}}{\text{Close}_{t-1}} \right) \times 100$$
* **Outputs**: Dictionary with `current_price`, `previous_close`, `gap_pct`, `is_premarket`.
* **Verification & Test**: `TC-ING-03` in [`tests/test_price_fetcher.py::test_premarket_quote`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_price_fetcher.py).

---

### Epic 2: Smart Money Ingestion Pipeline (First-Party Footprints)

#### `FR-02-01`: Congressional STOCK Act Trade Parser
* **Description**: The system shall parse public Congressional stock trade disclosures from House and Senate repositories without paid API subscriptions.
* **Extracted Fields**: Politician Name, Chamber (House/Senate), State, Party, Issuer Ticker, Transaction Type (`BUY` / `SELL`), Trade Size Bracket, Traded Date, Published Date.
* **Verification & Test**: `TC-SM-01` in [`tests/test_smart_money.py::test_parse_trade_row`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py).

#### `FR-02-02`: Congressional Conviction Scoring Model
* **Description**: The system shall compute a quantitative Congressional Conviction Score ($-20$ to $+100$) based on net transaction volume, trade size, and recency within a 90-day quarterly window:
  * Base Buy: $+30\text{ pts}$
  * Trade Size Bonus: $+10\text{ pts}$ for $\$50\text{K}+$, $+15\text{ pts}$ for $\$100\text{K}+$, $+25\text{ pts}$ for $\$500\text{K}+$
  * Politician Cluster Buying (2+ distinct members): $+20\text{ pts}$
  * Net Selling Penalty: $-10\text{ pts}$ (or $-20\text{ pts}$ if high jurisdiction member sells)
* **Verification & Test**: `TC-SM-02` in [`tests/test_smart_money.py::test_congress_signals_with_mock`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py).

#### `FR-02-03`: Congressional Committee Jurisdiction Relevance Matching
* **Description**: The system shall map reporting politicians to official 118th/119th Congressional committee assignments. If a member serves on a committee with direct legislative oversight over semiconductors, defense computing, or telecom, their trade receives a **$2.5\times$ conviction multiplier**.
* **High-Alpha Committees**:
  * *House Energy and Commerce* (Telecommunications, consumer tech, CHIPS Act supply chains) $\rightarrow 2.5\times$
  * *House Armed Services* (Defense microelectronics, cyber warfare, DARPA allocations) $\rightarrow 2.5\times$
  * *House Science, Space, and Technology* (AI research, supercomputing, NSF/NIST grants) $\rightarrow 2.2\times$
  * *House Foreign Affairs* (ITAR semiconductor export controls, Taiwan Strait security) $\rightarrow 2.0\times$
* **Verification & Test**: `TC-SM-03` in [`tests/test_smart_money.py::test_congress_committee_jurisdiction_matching`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py).

#### `FR-02-04`: SEC Form 4 Corporate Insider Parser
* **Description**: The system shall parse SEC Form 4 disclosures, isolating open-market direct cash purchases from routine option grants or planned 10b5-1 sales.
* **Scoring Rules**:
  * Base Open-Market Buy: $+40\text{ pts}$
  * Executive Cluster Buying ($\ge 2$ distinct insiders buying within 30 days): $+30\text{ pts}$
  * C-Suite Buyer Presence (CEO, CFO, COO, President): $+20\text{ pts}$
  * High Dollar Value ($>\$500,000$ cash deployed): $+10\text{ pts}$
* **Outputs**: Dictionary with `insider_score`, `has_cluster_buy`, `total_buy_value_usd`, `c_suite_buyers`, `recent_transactions`.
* **Verification & Test**: `TC-SM-04` in [`tests/test_smart_money.py::test_insider_transactions_live`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_smart_money.py).

#### `FR-02-05`: US Federal Government Contracts Ingestion (USASpending.gov)
* **Description**: The system shall ingest prime federal technology procurement contract awards directly from the official open US Federal API (`api.usaspending.gov/api/v2/search/spending_by_award/`) at $0 runtime cost.
* **Mapping**: Maps 27 tickers to corporate legal entity keywords (e.g. `DELL` $\rightarrow$ `DELL MARKETING L.P.`, `INTC` $\rightarrow$ `INTEL CORP`).
* **Attributes**: Award ID, Recipient Name, Amount ($ USD), Awarding Agency, Sub-Agency, Description, Action Date.
* **Defense Flagging**: Assigns `is_defense_contract = True` if procuring agency includes DoD, DARPA, IARPA, Army, Navy, or Air Force.
* **Verification & Test**: `TC-SM-05` in [`tests/test_contracts.py::test_get_ticker_contract_signals_dell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_contracts.py).

#### `FR-02-06`: Federal Contract Scoring Thresholds
* **Description**: The system shall evaluate the strategic revenue floor of federal contracts on a 0–100 scale:
  * Mega Contractor ($\ge \$500\text{M}$ active commitments): $95\text{ pts}$
  * Major Contractor ($\ge \$100\text{M}$): $80\text{ pts}$
  * Significant Contractor ($\ge \$25\text{M}$): $65\text{ pts}$
  * Moderate Contractor ($\ge \$5\text{M}$): $45\text{ pts}$
  * Any Active Prime Award ($> \$0$): $25\text{ pts}$
  * Defense/DoD Strategic Bonus: $+10\text{ pts}$ (capped at 100).
* **Verification & Test**: `TC-SM-06` in [`tests/test_contracts.py::test_contracts_scoring_thresholds`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_contracts.py).

---

### Epic 3: Social Feedback Loops & Quantitative Feature Pipeline

#### `FR-03-01`: Financial News Sentiment Polarity
* **Description**: The system shall fetch financial headlines and compute keyword-based sentiment polarity scores without paid LLM API calls.
* **Outputs**: `sentiment_score` ($-1.0$ to $+1.0$), `sentiment_label` (`BULLISH`, `BEARISH`, `NEUTRAL`).
* **Verification & Test**: `TC-SOC-01` in [`tests/test_social_sentiment.py::test_score_text_sentiment`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py).

#### `FR-03-02`: Targeted Politician Viral Buzz Detection
* **Description**: The system shall scan public feeds for targeted keywords indicating viral retail herd acceleration: `#pelosi`, `#congress`, `insider buy`, `cluster buy`, `whale`, `copy trade`.
* **Outputs**: `viral_politician_buzz` (boolean), `retail_hype_score` (0–100), `matched_buzz_keywords`.
* **Verification & Test**: `TC-SOC-02` in [`tests/test_social_sentiment.py::test_scan_politician_viral_buzz_detection`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py).

#### `FR-03-03`: The Pelosi Effect In-Depth Diagnostics
* **Description**: The system shall query live StockTwits public symbol streams (`/api/2/streams/symbol/{ticker}.json`) and generate detailed forensic diagnostics on copy-trading herds:
  * `intensity`: `VIRAL_SURGE` (80–100), `HIGH_VELOCITY` (60–79), `MODERATE_INTEREST` (35–59), `QUIET / DORMANT`.
  * `primary_catalyst`: e.g. `PELOSI_CONGRESSIONAL_COPYTRADE`, `C_SUITE_INSIDER_WHALE_ACCUMULATION`.
  * `prominent_figures`: Prominent names cited in stream (e.g. `Nancy Pelosi`, `Paul Pelosi`, `Corporate CEO`).
  * `lifecycle_stage`: `IGNITION_ACCELERATION`, `PEAK_HERD_EXPANSION`, `EMERGING_AWARENESS`.
  * `narrative_summary`: Contextual 2-sentence explanatory paragraph.
  * `verbatim_quotes`: Real trader chat quotes extracted directly from public streams.
* **Verification & Test**: `TC-SOC-03` in [`tests/test_social_sentiment.py::test_get_ticker_social_sentiment_structure`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_social_sentiment.py).

#### `FR-03-04`: Point-in-Time Technical Feature Engineering
* **Description**: The system shall calculate technical indicators strictly on historical bar slices to prevent forward-looking data leakage:
  * **Relative Volume (20-Day)**: $\text{RVOL}_{20} = \frac{\text{Volume}_t}{\text{SMA}_{20}(\text{Volume})}$
  * **Close Range Ratio (CRR)**: $\text{CRR} = \frac{\text{Close}_t - \text{Low}_t}{\text{High}_t - \text{Low}_t}$
  * **Bollinger Band Width**: $\text{BBW} = \frac{\text{Upper BB}_{20,2} - \text{Lower BB}_{20,2}}{\text{SMA}_{20}(\text{Close})}$
  * **EMA Alignment**: $\text{EMA}_5(\text{Close}) > \text{EMA}_{20}(\text{Close})$
* **Verification & Test**: `TC-FEAT-01` in [`tests/test_features.py::test_compute_technical_indicators`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py).

#### `FR-03-05`: Forward Target Labeling
* **Description**: For model training, the system shall compute binary forward wave labels over a 5-day horizon without lookahead bias:
  $$\text{Target} = 1 \iff \left( \max_{1 \le k \le 5}(\text{High}_{t+k}) \ge \text{Close}_t \times 1.035 \right) \land \left( \min_{1 \le k \le 5}(\text{Low}_{t+k}) > \text{Close}_t \times 0.975 \right)$$
* **Verification & Test**: `TC-FEAT-02` in [`tests/test_features.py::test_create_wave_target`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py).

#### `FR-03-06`: Unified Feature Matrix Generation
* **Description**: The system shall merge technical indicators with Smart Money and Social Sentiment scores into an aligned feature vector for ML inference.
* **Verification & Test**: `TC-FEAT-03` in [`tests/test_features.py::test_build_feature_matrix`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_features.py).

---

### Epic 4: Day-1 Wave Ignition & Walkforward Backtesting

#### `FR-04-01`: Day-1 Wave Ignition Core Verification
* **Description**: The system shall classify a bar as an official Day-1 Wave Ignition if and only if **all four core criteria** pass simultaneously:
  1. $\text{RVOL}_{20} \ge 1.50\times$ (Volume Expansion)
  2. $\text{CRR} \ge 0.68$ (Institutional Close in upper 32% of intraday range)
  3. $\text{Close}_t \ge \max_{1 \le i \le 20}(\text{High}_{t-i})$ OR $\text{Close}_t \ge \text{Upper BB}_{20,2}$ (Range Breakout)
  4. $\text{Close}_t \le \text{Upper BB}_{20,2} \times 1.015$ (Anti-Exhaustion Guard: Not extended beyond +1.5% above Upper BB)
* **Outputs**: `is_ignition: True`, `ignition_type`, `checks: [...]`, `target_1` (+3.5%), `target_2` (+6.0%), `stop_loss` (-2.5%).
* **Verification & Test**: `TC-DET-01` in [`tests/test_wave_detector.py::test_wave_ignition_valid`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py).

#### `FR-04-02`: Ignition Rejection on Volume Failure
* **Description**: If $\text{RVOL}_{20} < 1.50\times$, the system must return `is_ignition = False` and log a volume expansion failure, regardless of price breakout.
* **Verification & Test**: `TC-DET-02` in [`tests/test_wave_detector.py::test_wave_ignition_rejection_low_volume`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py).

#### `FR-04-03`: Anti-Exhaustion Guard Rejection
* **Description**: If $\text{Close}_t > \text{Upper BB}_{20,2} \times 1.015$, the system must reject the ignition as an exhausted move (`EXTENDED_EXHAUSTION`) to prevent buying the top.
* **Verification & Test**: `TC-DET-03` in [`tests/test_wave_detector.py::test_wave_ignition_rejection_extended`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_wave_detector.py).

#### `FR-04-04`: Walkforward Simulation Engine
* **Description**: The system shall execute historical backtests applying the exact Wave Rider trade management rules:
  * **Entry**: Next open following Day-1 Ignition.
  * **Scale 1**: Sell 50% of position at Target 1 ($+3.5\%$). Move stop to breakeven ($0.0\%$).
  * **Runner Exit**: Sell remaining 50% at Target 2 ($+6.0\%$) OR when price closes below 5-day EMA.
  * **Stop Loss**: Hard $-2.5\%$ stop.
  * **Time Stop**: Force-exit at market close on Day 5 if neither target nor stop triggered.
* **Metrics**: Win Rate, Profit Factor, Expectancy ($), Max Drawdown (%), Strategy vs. Buy & Hold return.
* **Verification & Test**: `TC-BT-01` in [`tests/test_backtest.py::test_wave_backtest_execution`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_backtest.py).

---

### Epic 5: Machine Learning Classification & Composite Scoring

#### `FR-05-01`: Probability-Calibrated Model Training & Inference
* **Description**: The system shall train a local `HistGradientBoostingClassifier` with `TimeSeriesSplit(n_splits=3)` and `CalibratedClassifierCV(cv=3)` predicting $P(\text{Wave Win})$.
* **Constraints**: 100% CPU execution, model file persisted to disk (`models/wave_model.joblib`), zero cloud dependencies.
* **Verification & Test**: `TC-ML-01` in [`tests/test_classifier.py::test_train_wave_model_and_inference`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_classifier.py).

#### `FR-05-02`: Composite Confidence Scoring Model (0–100)
* **Description**: The system shall compute a unified Composite Score blending ML probability with fundamental Smart Money catalysts:
  $$\text{Composite Score} = \min\left(100, \;\text{round}\Big(P(\text{Wave Win}) \times 70 + \text{Smart Money Bonus}\Big)\right)$$
* **Smart Money Bonus Schedule**:
  * Committee Jurisdiction Match: $+16\text{ pts}$ (or $+10$ for standard Congress buy)
  * Insider Cluster Buy: $+15\text{ pts}$ (or $+8$ for standard insider buy)
  * Federal Contract ($\ge \$500\text{M}$): $+12\text{ pts}$ (or $+8$ for $\ge \$25\text{M}$)
  * Pelosi Effect Active: $+12\text{ pts}$ (or $+8$ for emerging politician buzz)
  * General Bullish Sentiment: $+5\text{ pts}$
* **Verification & Test**: `TC-ML-02` in [`tests/test_classifier.py::test_score_single_stock`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_classifier.py).

---

### Epic 6: Interactive Dashboard & 5-Day Live Trading Duel

#### `FR-06-01`: 5-Day Duel State Management
* **Description**: The system shall maintain the live duel state in `data/game_state.json` between Human Player and Autonomous Bot:
  * Starting Capital: $\$30,000.00\text{ USD}$ each.
  * Start: Monday Sep 28, 2026.
  * End: Friday Oct 2, 2026 at 23:00 CET (21:00 UTC).
* **Verification & Test**: `TC-GAME-01` in [`tests/test_game.py::test_initial_game_state`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-02`: Player Order Execution Desk
* **Description**: The system shall execute market BUY and SELL orders for the player, updating cash balances and maintaining weighted average price (`avg_price`) for positions.
* **Verification & Test**: `TC-GAME-02` in [`tests/test_game.py::test_player_order_buy_and_sell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-03`: Bankroll Overspend Guard
* **Description**: If a BUY order's cost exceeds available cash, the order must be rejected with HTTP 400 and state unchanged.
* **Verification & Test**: `TC-GAME-03` in [`tests/test_game.py::test_player_order_insufficient_cash`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-04`: Allowed Universe Guard
* **Description**: Orders for tickers outside the 27 fortress universe must be rejected with HTTP 400.
* **Verification & Test**: `TC-GAME-04` in [`tests/test_game.py::test_player_order_invalid_ticker`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-05`: Shorting Prevention & Oversell Guard
* **Description**: The system shall forbid short selling. Selling more shares than currently held must be rejected with HTTP 400.
* **Verification & Test**: `TC-GAME-05` in [`tests/test_game.py::test_player_order_oversell`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-06`: Autonomous Bot Decision Engine & Mandatory Disclosures
* **Description**: The autonomous bot shall evaluate candidate setups using strict entry criteria:
  $$\text{Entry Condition} = \Big(\text{is\_ignition} == \text{True}\Big) \;\lor\; \Big(\text{composite\_score} \ge 65\Big) \;\lor\; \Big(P(\text{Wave}) \ge 65.0\%\Big)$$
* **Position Sizing**:
  * Score $\ge 85$: Allocate 50% of available cash.
  * Score $\ge 70$: Allocate 35% of available cash.
  * Score $\ge 65$: Allocate 20% of available cash.
* **Mandatory Disclosure**: The bot must log an audit record citing its exact technical rationale, RVOL, probability, and all external catalysts (Committee oversight, Form 4 purchases, Federal contracts, Pelosi effect).
* **Verification & Test**: `TC-GAME-06` in [`tests/test_game.py::test_bot_evaluate_turn_with_disclosures`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_game.py).

#### `FR-06-07`: Web Dashboard Glassmorphism Shell, Top Banner & Responsive Theme
* **Description**: The system shall serve a responsive, high-performance single-page web application (`index.html`, `style.css`, `app.js`) via `GET /`:
  * **Design System**: Glassmorphic dark aesthetic utilizing semi-transparent frosted glass containers (`rgba(15, 23, 42, 0.75)` with `backdrop-filter: blur(12px)`), slate-900 background (`#090d16`), and high-contrast accent highlights (cyan `#00f2fe`, purple `#4facfe`, emerald `#10b981`, rose `#f43f5e`, gold `#fbbf24`).
  * **Header Controls**: Dynamic operational mode switcher allowing instant toggling between `🌙 End-of-Day (EOD)` and `☀️ Pre-Market (PM)` cadences, and a manual `🔄 Refresh` trigger.
  * **Universe Overview KPI Banner**: 4 persistent metric blocks displaying Tracked Universe (27 Titans), Execution Strategy (3–5 Day Expansion $+3.5\% / +6.0\%$), Risk Floor ($-2.5\%$ Stop / 5 EMA Trail), and Safety Mandate (Zero Bankruptcy Risk).
  * **Navigation Tab Controller**: Top-level tab switcher seamlessly routing between 4 primary functional views without browser reload:
    1. `🌊 Wave Radar`
    2. `🎯 Stock Deep-Dive`
    3. `🧪 Backtest Sandbox`
    4. `⚔️ 5-Day Duel`
  * **Third-Party CDN Libraries**: Bundles Chart.js 4.x for hardware-accelerated canvas chart rendering.
* **Verification & Test**: `TC-UI-01` in [`tests/test_interface.py::test_dashboard_index`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-08`: Dashboard Health Probe API
* **Description**: The system shall expose a lightweight JSON endpoint at `GET /api/health` returning `{"service": "Wave Rider Momentum Engine", "status": "UP"}`. This endpoint facilitates uptime verification, external cron pingers, and container health probes.
* **Verification & Test**: `TC-UI-02` in [`tests/test_interface.py::test_dashboard_health`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-09`: Tab 1 — Wave Radar Grid, Interactive Sorting, High-Contrast Badges & Legend
* **Description**: Tab 1 shall render a ranked, real-time 13-column quantitative screening table populated via `GET /api/radar?mode={eod|premarket}` with advanced sorting, high-contrast status badges, and an explanatory bottom legend:
  * **Category Filter Pills**: Interactive pill buttons allowing instant client-side filtering across all 50 universe stocks: `All (50)`, `Memory & Storage (6)`, `Capital Equipment & EDA (9)`, `AI Compute (10)`, `Datacenter Power & Cooling (5)`, `Connectivity & Silicon (7)`, and `Mega-Cap & Enterprise Cloud (13)`.
  * **Interactive Column Sorting**:
    * Column headers for `Ticker`, `Category`, `Price`, `Change %`, `Wave Prob`, and `Score` shall be interactive click targets.
    * Clicking a sortable column header shall sort the displayed table rows ascending or descending, displaying dynamic direction indicator arrows ($\blacktriangle$ / $\blacktriangledown$).
    * Sorting shall seamlessly preserve active category pill filtering without reloading data from the server.
  * **High-Contrast Smart Money Badge Color-Coding**:
    * Smart Money indicators shall render with distinct background colors, glowing borders, and high-contrast text that stand out against the dark slate table row background:
      * `💼 Insider`: Warm gold/amber background (`rgba(245, 158, 11, 0.18)`), vibrant amber border (`#f59e0b`), and gold text (`#fbbf24`).
      * `📈 Bullish`: Emerald background (`rgba(16, 185, 129, 0.18)`), vibrant green border (`#10b981`), and light-emerald text (`#34d399`).
      * `🏛️ Congress`: Violet/purple background (`rgba(139, 92, 246, 0.18)`), purple border (`#8b5cf6`), and light-purple text (`#a78bfa`).
      * `📜 Contracts`: Cyan/sky background (`rgba(6, 182, 212, 0.18)`), cyan border (`#06b6d4`), and light-cyan text (`#38bdf8`).
  * **Bottom Table Context Legend & Metric Glossary**:
    * A persistent glassmorphism Legend Card positioned directly beneath the radar table shall explain every column, status badge, and quantitative metric across 6 specialized cards:
      * **Day-1 Ignition**:
        * `⚡ IGNITION`: Violent Day-1 momentum breakout. Encompasses Pre-Market session gap ignition (`⚡ PRE_MKT_GAP`, gap $\ge +1.0\%$ overnight on volume) and End-of-Day technical breakouts (`⚡ BREAKOUT_20D`, `⚡ BREAKOUT_BB`, `⚡ VOLUME_EXPANSION` requiring $\text{RVOL} \ge 1.50\times$ and $\text{CRR} \ge 0.68$).
        * `Consolidating`: Asset compressing in healthy base consolidation, pullback support, or flat drift below volume ignition threshold.
      * **Wave Probability ($P(\text{Wave Win})$)**:
        * Calibrated machine-learning prediction ($40\% - 75\%$) that the stock reaches $+3.5\%$ upside in 3–5 trading days before triggering $-2.5\%$ stop loss.
        * *Why 40%–75% Range*: Asymmetric target/stop ratio imposes an unguided random-walk base rate of ~40%–45%. Platt probability calibration (`CalibratedClassifierCV`) aligns outputs with empirical win rates, where financial market noise imposes a ~75% realistic ceiling. Tiers: $\ge 65\%$ (Prime edge / Bot entry trigger), $55\% - 64\%$ (Moderate edge), $< 50\%$ (Negative edge / risk).
      * **Composite Score (0–100)**: Quantitative conviction combining technical momentum with Smart Money bonuses ($\ge 85$: Whale Tier / 50% max allocation; $\ge 70$: Prime Wave Setup / 35% allocation; $\ge 65$: Autonomous Bot Auto-Trigger / 20% allocation; $<65$: Watchlist / Consolidation).
      * **Smart Money Footprint**: Detailed definitions for:
        * 🏛️ `Congress` (STOCK Act purchases within 90 days, $+10$ pts; `Committee Match` with $2.5\times$ weight and $+16$ pts).
        * 💼 `Insider` (SEC Form 4 C-Suite whale buys $\ge \$25\text{K}$, $+8$ pts; `ClusterBuy` $\ge 2$ executives in 30 days, $+15$ pts).
        * 🛡️ `Fed Contract` (Prime US Federal technology awards $\ge \$25\text{M}$, $+8$ pts; Mega-awards $\ge \$500\text{M}$, $+12$ pts).
        * 💬 `Bullish` (FinTwit/news polarity $> +0.25$ with 72h positive sentiment velocity, $+5$ pts).
      * **The Pelosi Effect & Retail Herd Momentum**: Dedicated diagnostic card detailing the self-fulfilling viral copy-trading phenomenon:
        * *Trigger Threshold*: Active when composite `Retail Hype Score >= 60/100` (combining viral catalyst, mention velocity, and Pelosi mention multiplier).
        * *Intensity Tiers*: `VIRAL_SURGE` (80–100: peak retail frenzy), `HIGH_VELOCITY` (60–79: active trigger threshold), `MODERATE_INTEREST` (35–59: emerging buzz), `QUIET / DORMANT` (<35: sub-threshold).
        * *Primary Catalysts*: `PELOSI_CONGRESSIONAL_COPYTRADE` (+20 bonus), `CAPITOL_HILL_DISCLOSURE`, `C_SUITE_INSIDER_WHALE_ACCUMULATION`, `RETAIL_HERD_WHALE_COPYTRADE`.
        * *Lifecycle Stages*: `DORMANT` $\rightarrow$ `EMERGING_AWARENESS` $\rightarrow$ `IGNITION_ACCELERATION` $\rightarrow$ `PEAK_HERD_EXPANSION`.
      * **Execution Brackets**: `Target 1` ($+3.5\%$ profit scale-out), `Target 2` ($+6.0\%$ trend runner), and `Stop Loss` ($-2.5\%$ initial risk floor or trailing 5 EMA).
* **Verification & Test**: `TC-UI-03` in [`tests/test_interface.py::test_dashboard_radar_premarket`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-10`: Tab 2 — Stock Deep-Dive 4-Pillar Forensic Suite & Multi-Overlay Chart
* **Description**: Tab 2 shall render an exhaustive forensic diagnostic view for any of the 27 universe stocks via `GET /api/stock/<ticker>`:
  * **Interactive Ticker Selector**: Dropdown selector enabling on-demand switching or direct routing from Radar action buttons.
  * **4-Pillar Forensic Scorecard Ribbon**:
    1. *Technical Pillar*: RVOL ratio, Close Range Ranking (CRR), 20D High status, Upper Bollinger Band proximity, and 5/20 EMA trend alignment.
    2. *Smart Money Pillar*: Congressional conviction score, Committee jurisdiction overlap match, and Form 4 C-Suite whale purchase indicators.
    3. *Federal Contracts Pillar*: 90-day awarded contract value ($) and prime awardee flags from USASpending.
    4. *Sentiment Velocity & Pelosi Effect*: Financial news polarity score, Pelosi social chatter velocity score, and live community quote feed.
  * **Multi-Overlay Technical Chart**: Interactive Chart.js canvas plotting 60 trading days of historical closes overlaid with:
    * 5-day Exponential Moving Average (Purple line)
    * 20-day Exponential Moving Average (Blue line)
    * Target 1 level $+3.5\%$ (Green dashed horizontal line)
    * Target 2 level $+6.0\%$ (Cyan dashed horizontal line)
    * Stop Loss level $-2.5\%$ (Red dashed horizontal line)
  * **Tabular Audit Data Grids**:
    * *Congressional Filings Table*: Filing date, politician name, chamber (House/Senate), committee, transaction type, dollar bracket, and transaction date.
    * *Form 4 Insider Buys Table*: Filing date, insider name, executive title, transaction type, shares purchased, execution price, and total dollar value.
    * *USASpending Contracts Table*: Award date, recipient name, awarding agency, dollar value, and contract description.
    * *Day-1 Ignition Checklist*: Detailed table displaying all 4 core ignition rules with individual pass/fail status and exact numeric criteria.
* **Verification & Test**: `TC-UI-04` in [`tests/test_interface.py::test_dashboard_stock_detail`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-11`: Tab 3 — Backtest Sandbox & Walkforward Equity Visualizer
* **Description**: Tab 3 shall provide an on-demand historical simulation laboratory powered by `GET /api/backtest`:
  * **Parameter Form**: Ticker selector across the 27 universe stocks and Lookback Period selector (`1y`, `2y`, `3y`).
  * **6 KPI Metric Cards**:
    1. *Strategy Return %* (with comparative Buy & Hold benchmark)
    2. *Win Rate %* (with exact Wins / Losses tally)
    3. *Profit Factor* (Gross Profit / Gross Loss)
    4. *Expectancy* ($ net return per trade)
    5. *Max Drawdown %* (Peak-to-trough equity decline)
    6. *Average Hold Period* (Holding duration in days, subject to 5-day time exit)
  * **Equity Curve Canvas**: Chart.js visualization displaying hypothetical account growth starting from a $10,000 baseline.
  * **Historical Trade Ledger**: Chronological table logging every simulated execution: trade index, entry date, exit date, entry fill, exit fill, share quantity, net P&L ($), return %, holding duration (days), and precise exit reason (`TARGET_1`, `TARGET_2`, `STOP_LOSS`, `5_EMA_TRAIL`, `5D_TIME_STOP`).
* **Verification & Test**: `TC-UI-05` in [`tests/test_interface.py::test_dashboard_backtest_api`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-12`: CLI Runner Premarket Execution
* **Description**: The system shall support a headless terminal pre-market scanner via `python -m src.main --mode premarket` that fetches live gap data, computes composite conviction, and outputs a formatted ANSI terminal table for headless operational verification.
* **Verification & Test**: `TC-UI-06` in [`tests/test_interface.py::test_cli_premarket_execution`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

#### `FR-06-13`: Tab 4 — Live Duel Desk, Mark-to-Market Scoreboard & 15s Auto-Polling
* **Description**: Tab 4 shall host the active 5-Day "Player vs. Bot" Paper Trading Duel (`GET /api/game`):
  * **Banner & Countdown Strip**: Real-time countdown timer to match expiration (Friday Oct 2, 2026, 23:00 CET), Dynamic Leader Badge (`⚖️ Tied`, `🏆 Human Player Leading`, `🤖 Autonomous Bot Leading`), and Autonomous Bot Status Pill.
  * **Dual Live Scoreboard Cards**: Parallel cards for Human Player and Autonomous Bot displaying:
    * Net Account Equity ($)
    * Total P&L ($ and %)
    * Available Buying Power ($ cash)
    * Invested Market Value ($ in open stocks)
    * Active Positions Count
  * **Order Execution Desk**: Interactive trading terminal featuring Action toggle (`BUY` / `SELL`), Stock selector, Shares input with dynamic real-time "Total Order Value" calculation, and instant order submission (`POST /api/game/order`).
  * **Live Open Positions Table**: Displays all currently held stocks, quantity, average cost basis, real-time market price, unrealized P&L ($ and %), and a one-click `Sell All` liquidator.
  * **Order History Ledger**: Chronological ledger of all completed market orders with ISO timestamps.
  * **Autonomous Bot Audit Stream**: Transparent decision log displaying the bot's evaluation history, executed trades, and mandatory outside-catalyst disclosures (technical breakout, RVOL, Congressional backing, insider accumulation, federal contracts).
  * **15-Second Background Polling Loop**: Client-side JavaScript timer (`setInterval(loadDuelState, 15000)`) automatically re-fetching game state and updating mark-to-market valuations without requiring browser refreshes.
  * **Administrative Controls**: `⚡ Trigger Bot Turn` (`POST /api/game/bot-turn`) for manual evaluation, and `⚠️ Reset Match` (`POST /api/game/reset`) for bankroll re-initialization.
* **Verification & Test**: `TC-UI-07` in [`tests/test_interface.py::test_dashboard_game_endpoints`](file:///c:/Users/jonsa/LLM/predict-stock/tests/test_interface.py).

---

### Epic 7: Cloud Deployment & Persistence *(Planned / Deferred)*

#### `FR-07-01`: Free-Tier Cloud Web Server Deployment
* **Description**: The system shall support containerized/cloud deployment on free-tier platforms (e.g. Render.com with health pinger or Hugging Face Spaces with 16GB RAM) to run 24/7 without local machine dependencies.
* **Constraint**: Zero ongoing subscription or cloud runtime costs.
* **Status**: 💡 Planned / Deferred (`DEP-01`).

#### `FR-07-02`: Supabase State Persistence
* **Description**: The system shall optionally sync `game_state.json` to a free-tier Supabase PostgreSQL table to ensure bankrolls, open positions, and audit logs persist across cloud server restarts.
* **Status**: 💡 Planned / Deferred (`DEP-02`).

---

## 4. Test Execution Guide

All functional requirements can be validated directly via pytest:

```powershell
# 1. Run the entire verification test suite (34 of 34 tests)
python -m pytest tests/ -v

# 2. Run specific Epics
# Epic 1: Ingestion & Universe
python -m pytest tests/test_price_fetcher.py -v

# Epic 2: Smart Money (Congress, Insiders, Contracts)
python -m pytest tests/test_smart_money.py tests/test_contracts.py -v

# Epic 3: Social & Sentiment (Pelosi Effect, Features)
python -m pytest tests/test_social_sentiment.py tests/test_features.py -v

# Epic 4: Wave Detector & Backtester
python -m pytest tests/test_wave_detector.py tests/test_backtest.py -v

# Epic 5: Machine Learning Classifier & Scoring
python -m pytest tests/test_classifier.py -v

# Epic 6: Live Duel & Web Dashboard APIs
python -m pytest tests/test_game.py tests/test_interface.py -v
```
