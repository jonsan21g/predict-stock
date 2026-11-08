# Wave Rider: "To-The-Cloud" Two-Step Migration Plan (`to-the-cloud`)
## Zero-Cost Hybrid Cloud Architecture (GitHub Pages + Precision Actions + Live Browser Feed)

- **Plan Identifier**: `to-the-cloud` (v2.1 - Two-Step Structure with Integrated Local Documentation)
- **Project**: `predict-stock` (Wave Rider Quantitative Momentum & Smart-Money Engine)
- **Architecture Mandate**: **\$0.00 / month Forever** (Zero subscriptions, zero sleeping containers, zero ongoing cloud costs)
- **Execution Strategy**: **Step 1: Revise & Document Locally** $\longrightarrow$ **Step 2: Bring to the Cloud & Automate**
- **Traceability Scope**: Full IEEE 830 / ISO 29148 synchronization across `FUNCTIONAL_REQUIREMENTS.md`, `DESIGN_SPECIFICATION.md`, `ARCHITECTURE.md`, `BACKLOG.md`, `SYSTEM_VERIFICATION_REPORT.md`, and `README.md`.

---

## 🎯 Architecture Strategy: Two Distinct Steps

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               STEP 1: REVISE & DOCUMENT LOCALLY (Engineering & Full RTM Sync)          │
│                                                                                        │
│  1.1 Capitulation Carve-Out Engine (Integrate verified Drop <= -8% + Green Reversal)   │
│  1.2 Static Cloud Exporter (`src/cloud/static_exporter.py` with fast/full modes)       │
│  1.3 Dual-Mode Frontend (`app.js` runs seamlessly on Flask and Static file bundles)   │
│  1.4 Local Static Server Validation (Test complete SPA on localhost:5055 with NO Flask)│
│  1.5 Local Automated Test Suite (`pytest` regression + new cloud export tests)         │
│  1.6 Local IEEE Documentation Sync (Update FRS/RTM, Design Spec, Architecture ADR-06)  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Step 1 Verified 100% Locally (Code & Docs)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               STEP 2: BRING TO THE CLOUD & AUTOMATE (Deployment & Live Infrastructure) │
│                                                                                        │
│  2.1 GitHub Actions Workflow (`.github/workflows/wave-rider-cloud.yml` on gh-pages)    │
│  2.2 Precision External Scheduler (`cron-job.org` triggering workflow_dispatch)        │
│  2.3 GitHub Pages CDN Activation (Point repo to orphan `gh-pages` branch)             │
│  2.4 Browser Cloud Trading Desk (Single-repo PAT + Finnhub Live Price Stream)          │
│  2.5 Cloud Deployment Audit & Live URL Verification                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ STEP 1: REVISE & DOCUMENT LOCALLY (Engineering & Full RTM Sync)

Before touching remote GitHub Actions or external schedulers, all code, static data pipelines, UI routing, automated tests, and engineering specifications are implemented, verified, and synchronized directly on your local machine.

### 1.1 Integrate Capitulation Reversal Carve-Out in `src/game/duel.py`
* **Problem**: In Week 5, the bot was completely blind to Thursday's extreme sell-off because the Macro Gatekeeper ($QQQ < \text{20-day EMA}$) acted as a blanket curfew, freezing all long entries.
* **Empirical Validation**: Our 3-year 50-stock walkforward backtest proved that **Next-Day Green Confirmation after an $\le -8\%$ crash with a Stop at the crash day's Low (LOD)** generates a **66.9% Win Rate** and a **1.37 Profit Factor** across 157 historical instances during macro downtrends (outperforming unconfirmed knife-catching which lost money with a 0.67–0.82 PF).
* **Implementation**:
  - In `src/game/duel.py`: Inside `bot_evaluate_turn()`, if $QQQ < \text{20-day EMA}$, do *not* immediately exit. Instead, evaluate the **Capitulation Carve-Out**:
    1. Scan for any universe stock that dropped $\le -8.0\%$ on Day $T-1$.
    2. Check if Day $T$ confirms green ($\text{Close}_T > \text{Open}_T$ and $\text{Close}_T > \text{Close}_{T-1}$).
    3. If confirmed, allow a tactical entry with **half allocation** (20–25%) and a structural stop loss set at $\text{Low}_{T-1} \times 0.995$.
    4. If no stock qualifies, fall back to standard `MACRO_HOLD`.

### 1.2 Build Static Cloud Exporter in `src/cloud/static_exporter.py`
* **Create `src/cloud/static_exporter.py`**:
  - `export_cloud_bundle(output_dir="dist", mode="fast") -> Dict[str, Any]`:
    - Copies HTML/CSS/JS frontend assets into `dist/`.
    - Generates `dist/api/health.json`, `dist/api/game.json`, `dist/api/radar_eod.json`, `dist/api/radar_premarket.json`, `dist/api/radar_intraday.json`.
    - When `mode == "full"` (or if missing), compiles all 50 stock dossiers (`dist/api/stock/<TICKER>.json`) and multi-horizon backtest bundles (`dist/api/backtest/<TICKER>.json` containing `1y`, `2y`, and `3y` pre-computed results).
* **Update `src/main.py` CLI**:
  - Add `--export-static` and `--export-mode {fast|full}` CLI arguments.

### 1.3 Upgrade Frontend to Dual-Mode Architecture
* **File**: `src/dashboard/static/app.js` & `src/dashboard/templates/index.html`
* **Dual-Mode API Routing**:
  - Detects if running on Flask (`/api/...`) versus Static Cloud (`./api/...json`).
  - Implements the **3-Tier Live Browser Price Waterfall**:
    1. *Tier 1*: Finnhub Free Official WebSocket/REST API (native CORS, 60 req/min, free forever).
    2. *Tier 2*: Batch Yahoo proxy via Cloudflare Worker (`?symbols=NVDA,STX,TSLA,...`).
    3. *Tier 3*: Static snapshot fallback with timestamp indicator.
  - Live recomputation in browser: Mark-to-Market Net Equity, Unrealized P&L, High-Water Mark Trailing Stops, and Duel Leaderboard.

### 1.4 Local Static Server Validation (Zero-Flask Proof)
* Run a local static file server directly on the exported `dist/` bundle:
  ```powershell
  python -m http.server 5055 --directory dist
  ```
* Verify in the browser at `http://localhost:5055`:
  - Tab 1 (Live Wave Radar): All 50 stocks load from static JSON.
  - Tab 2 (Deep Dive): Candlestick charts, technical indicators, and checklist badges render cleanly.
  - Tab 3 (Backtest Sandbox): Multi-horizon switches (`1y`, `2y`, `3y`) update metrics instantly.
  - Tab 4 (Duel Trading Desk): Scoreboard, active positions, and trade history display correctly.

### 1.5 Local Automated Test Suite Verification
* Create `tests/test_cloud_deployment.py`:
  - `test_static_exporter_fast_and_full_bundles` (`TC-DEP-01`): Verifies all required JSON keys and directory structures.
  - `test_capitulation_carveout_execution` (`TC-CARVE-01`): Verifies bot triggers carve-out only when confirmation criteria are met.
* Run full test suite:
  ```powershell
  pytest
  ```
* Guarantee: **100% of unit and integration tests must pass before proceeding to Step 1.6.**

### 1.6 Local IEEE Documentation & RTM Synchronization
Synchronize the full specification suite to reflect Step 1 local engineering:
1. **[`FUNCTIONAL_REQUIREMENTS.md`](file:///c:/Users/jonsa/LLM/predict-stock/FUNCTIONAL_REQUIREMENTS.md)**:
   - Add **`FR-07-01`**: *Static Cloud Exporter & Decoupled SPA Bundle* (mapped to `TC-DEP-01`).
   - Add **`FR-07-02`**: *Dual-Mode API Routing & Local Static Serving* (mapped to `TC-DEP-02`).
   - Add **`FR-09-06`**: *Capitulation Reversal Carve-Out Rule* (mapped to `TC-CARVE-01`).
   - Update Master RTM Table and traceability matrices.
2. **[`DESIGN_SPECIFICATION.md`](file:///c:/Users/jonsa/LLM/predict-stock/DESIGN_SPECIFICATION.md)**:
   - Document the Static Exporter schema, fast vs full export payloads, directory tree in `dist/`.
   - Document the Dual-Mode client API router sequence diagram and fallback waterfall.
   - Document the Capitulation Carve-Out decision logic flow chart.
3. **[`ARCHITECTURE.md`](file:///c:/Users/jonsa/LLM/predict-stock/ARCHITECTURE.md)**:
   - Add **`ADR-06`**: *Decoupled Static Asset Architecture & Client-Side Data Routing* (documenting why the SPA is decoupled from Flask and how it runs without a backend server).
4. **[`BACKLOG.md`](file:///c:/Users/jonsa/LLM/predict-stock/BACKLOG.md)**:
   - Track `DEP-01` (Static Exporter), `DEP-02` (Dual-Mode Frontend), and `ENG-05` (Capitulation Carve-Out) as **✅ Completed**.
5. **[`SYSTEM_VERIFICATION_REPORT.md`](file:///c:/Users/jonsa/LLM/predict-stock/SYSTEM_VERIFICATION_REPORT.md)**:
   - Record the updated test suite pass rate and local static server verification audit.
6. **[`README.md`](file:///c:/Users/jonsa/LLM/predict-stock/README.md)**:
   - Document the `--export-static` command and local static review on `http://localhost:5055`.

---

## ☁️ STEP 2: BRING TO THE CLOUD & AUTOMATE (Deployment & Live Infrastructure)

Once Step 1 code, tests, and documentation are 100% complete and committed locally, Step 2 brings the system into full cloud automation.

### 2.1 GitHub Actions Workflow (`.github/workflows/wave-rider-cloud.yml`)
* **Triggers**:
  - `workflow_dispatch`: Accepts inputs (`command`, `ticker`, `shares`, `action`).
* **Execution Paths**:
  - **Fast Intraday Mode** (runs in <20s): Fetches 50-stock quotes, runs `bot_evaluate_turn()`, exports fast bundle, commits state changes to `main` only if state changed.
  - **Full EOD Mode** (runs 1x daily at 22:15 CET, ~60s): Refreshes all 50 stock dossiers and backtests.
* **Orphan `gh-pages` Branch**:
  - The compiled `dist/` dashboard is pushed to `gh-pages` with `force_orphan: true`, keeping git history on `main` completely clean.
* **Concurrency Lock**:
  - `concurrency: { group: "wave-rider-cloud-lock", cancel-in-progress: false }` prevents any race conditions or split-brain states.

### 2.2 Precision External Scheduler Setup (`cron-job.org`)
* Configure free jobs on `cron-job.org` calling `workflow_dispatch` via GitHub REST API:
  1. *Market Open Ignition Scan*: Monday–Friday at 15:35 CET (09:35 EST).
  2. *Intraday Surveillance*: Monday–Friday every 30 minutes between 16:00 and 21:30 CET.
  3. *Market Close Session*: Monday–Friday at 22:00 CET (16:00 EST).
  4. *Daily Full EOD Refresh*: Monday–Friday at 22:15 CET (16:15 EST).
* *Advantage*: Starts GitHub Actions within 5–10 seconds, eliminating the 15–45 minute delays of native `on: schedule`.

### 2.3 Activate GitHub Pages CDN
* In GitHub Repository Settings:
  - Source: Deploy from branch `gh-pages` / `/ (root)`.
  - Your cloud dashboard becomes instantly available at:
    `https://jonsan21g.github.io/predict-stock/`

### 2.4 Browser Cloud Trading Desk & Fine-Grained PAT
* Add the **"☁️ Cloud Settings"** modal in `index.html`:
  - Fine-Grained GitHub PAT (scoped strictly to `predict-stock` with `Actions: Read/Write` and `Contents: Read`).
  - Optional free Finnhub API Key for real-time WebSocket/REST price streaming.
* Enables 1-click player trading directly from your phone or browser while your PC is completely turned off.

### 2.5 Cloud Deployment Audit & Live URL Verification
* Trigger test `workflow_dispatch` run in GitHub Actions.
* Verify live URL loads from CDN, shows real-time price feeds, and allows executing paper duel trades remotely.

---

## 🚀 Execution Choice

1. **"Execute Step 1"**: Completes all local engineering (Capitulation Carve-Out, Static Exporter, Dual-Mode UI, local static server validation) AND updates all 6 documentation files locally.
2. **"Execute both steps"**: Proceeds through Step 1 local engineering and documentation, then deploys directly to GitHub Pages and configures the cloud scheduler.
