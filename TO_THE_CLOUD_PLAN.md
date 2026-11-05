# Wave Rider: "To-The-Cloud" Engineering & Migration Plan (`to-the-cloud`)
## Zero-Cost Hybrid Cloud Architecture (GitHub Pages + Precision GitHub Actions + Live Browser Feed)

- **Plan Identifier**: `to-the-cloud`
- **Project**: `predict-stock` (Wave Rider Quantitative Momentum & Smart-Money Engine)
- **Target Execution Window**: End of Week 5 (Post Friday, Nov 6, 2026, 23:00 CET)
- **Cost Mandate**: **\$0.00 / month Forever** (No credit card required, no sleeping containers, no VM maintenance)
- **Traceability Scope**: Updates `FUNCTIONAL_REQUIREMENTS.md` (`FR-07`, `FR-09`), `DESIGN_SPECIFICATION.md`, `ARCHITECTURE.md` (`ADR-06`), `BACKLOG.md`, `SYSTEM_VERIFICATION_REPORT.md`, and `README.md`.

---

## 🔍 Part 1: Self-Critique of the Initial Plan (7 Flaws Identified & Fixed)

Before finalizing this blueprint, the initial draft was audited against real-world cloud failure modes and the project's IEEE specification standards. Seven critical weaknesses were identified and engineered out:

| # | Flaw in Initial Draft | Why It Would Have Failed or Degraded UX | Engineered Solution in Improved Plan |
|:---:|:---|:---|:---|
| **1** | **Relying on public CORS proxies for live browser prices** | Public CORS proxies (`allorigins`, `corsproxy`) are rate-limited by Yahoo Finance (HTTP 429) and unreliable when polling 50 tickers. | **3-Tier Live Price Waterfall**:<br>1. **Finnhub Free Official API/WebSocket** (native CORS, 60 req/min + live WebSocket, \$0 forever).<br>2. **15-Line Cloudflare Worker Proxy** (100k free req/day, batches all 50 quotes in 1 Yahoo request).<br>3. **GitHub Raw Snapshot Fallback** with timestamp indicator. |
| **2** | **Exporting 50 stock dossiers + 50 backtests every 30 mins** | Running 50 backtests and 50 Smart Money scrapes every 30 mins would take **4–6 mins/run**, burning ~1,800 Action mins/month and risking IP blocks. | **Split Fast vs. Full Export Cadence**:<br>• **Fast Path (Every 30m, <20s)**: Single vectorized `yf.download()` batch call for 50 tickers + `bot_evaluate_turn()` + updates `game.json` & intraday radar.<br>• **Full Path (1x Daily EOD)**: Exports all 50 deep-dive dossiers and backtest bundles. Cuts Action usage by **85%**. |
| **3** | **GitHub Pages CDN Lag (60s) on Player BUY/SELL Orders** | After `workflow_dispatch` commits a trade (~15s), GitHub Pages CDN takes another 45–60s to rebuild. The player would think the trade failed or double-click. | **Optimistic UI Lock + GitHub API Direct State Read**:<br>• Lock order button with a live *"⏳ Executing in Cloud (~15s)..."* progress stepper.<br>• Poll `api.github.com/repos/.../contents/data/game_state.json` directly (bypassing CDN caching) so the scoreboard updates the instant the Action finishes. |
| **4** | **Git Commit Bloat on `main` (350+ commits/month)** | Committing 100+ static JSON files to `main` every 30 minutes pollutes `git log` and bloats the `.git` folder size. | **Orphan `gh-pages` Branch for Static Bundles**:<br>• Keep `main` clean: only commit `data/game_state.json` to `main` when a material action (`BUY`, `SELL`, `MACRO_HOLD`) or state change occurs.<br>• Deploy static UI + heavy JSON snapshots to an orphan `gh-pages` branch (`force_orphan: true`, 1 commit history). |
| **5** | **Split-Brain Conflict (Local PC Daemon vs. Cloud Bot)** | Running `localhost:5050` with the background bot daemon active while GitHub Actions also trades in the cloud causes conflicting `game_state.json` states. | **Execution Authority Guard (`WAVE_RIDER_MODE`)**:<br>• Add `--cloud-sync` / `BOT_EXECUTION_AUTHORITY=cloud` mode so when running locally on your PC, `app.py` can pull live state from GitHub without running a duplicate background trading thread. |
| **6** | **Missing `1y` and `3y` Backtest Lookback Periods** | Initial draft only mentioned exporting `_2y.json`, violating `FR-06-11` which requires `1y`, `2y`, and `3y` lookback options in Tab 3. | **Multi-Horizon Backtest Bundle**:<br>• Export `data/cloud/backtests/<TICKER>.json` containing pre-computed `{"1y": {...}, "2y": {...}, "3y": {...}}` payloads (~12 KB per ticker), preserving 100% `FR-06-11` compliance. |
| **7** | **Broad GitHub PAT Security in Browser `localStorage`** | Using a classic `repo`-scoped token in browser storage grants overly broad access across all user repositories. | **Fine-Grained Single-Repo Token Specification**:<br>• Restrict token strictly to 1 repository (`predict-stock`) with only `Actions: Read/Write` and `Contents: Read`. |

---

## 🏗️ Part 2: Improved Target Architecture ("To-The-Cloud")

```text
┌───────────────────────────────────────────────────────────────────────────────────┐
│                    1. PRECISION SCHEDULER & TRIGGER LAYER                         │
│  • cron-job.org (Free): Fires POST /dispatches every 30m (Mon-Fri 14:00-22:00 CET)│
│  • Bypasses GitHub's delayed `on: schedule` queue (Starts runner in ~5-10s)       │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          │ HTTPS POST (workflow_dispatch)
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                    2. CLOUD EXECUTION LAYER (GitHub Actions)                      │
│  • Concurrency Lock: `group: wave-rider-state` (Zero merge collisions)            │
│  • Fast Intraday Mode (30m, <20s):                                                │
│      - Vectorized 50-stock quote fetch -> `bot_evaluate_turn()`                   │
│      - Updates `data/game_state.json` on `main` (if state changed)                │
│      - Publishes `game.json` & `radar_*.json` to `gh-pages`                       │
│  • Full EOD Mode (Daily 22:15 CET, ~60s):                                         │
│      - Refreshes Congress, Form 4, USASpending, StockTwits caches                 │
│      - Compiles 50 `stocks/<TICKER>.json` + 50 `backtests/<TICKER>.json`          │
└───────────────────┬───────────────────────────────────────────┬───────────────────┘
                    │ Atomic State (`main`)                     │ Static Bundle (`gh-pages`)
                    ▼                                           ▼
┌─────────────────────────────────────────┐ ┌───────────────────────────────────────┐
│   `raw.githubusercontent.com/.../main`  │ │   GitHub Pages CDN (`*.github.io`)    │
│   • `data/game_state.json` (Zero cache) │ │   • Glassmorphism SPA (`index.html`)  │
└───────────────────┬─────────────────────┘ │   • 50 Stock Dossiers & Backtests     │
                    │                       └───────────────────┬───────────────────┘
                    └─────────────────────┬─────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│               3. HYBRID LIVE CLIENT LAYER (Browser `app.js`)                      │
│  • Environment Auto-Detector: `LOCAL_FLASK` (`localhost:5050`) vs `CLOUD_PAGES`   │
│  • 15-Second Live Price Overlay:                                                  │
│      - Tier 1: Finnhub Free Real-Time REST/WebSocket (or Cloudflare Worker Proxy) │
│      - Recalculates live Mark-to-Market Equity, P&L, Peaks & Trailing Stops       │
│  • 1-Click Cloud Trading Desk:                                                    │
│      - Dispatches Player `BUY`/`SELL` & `Force Bot Turn` via `workflow_dispatch`  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Part 3: Phased Implementation Work Packages

### Phase 1: Cloud Snapshot Exporter & CLI Extensions
**Files**: `src/cloud/static_exporter.py` *(new)*, `src/main.py` *(update)*

1. **Create `src/cloud/static_exporter.py`**:
   - `export_cloud_bundle(output_dir: str = "dist", mode: str = "fast") -> Dict[str, Any]`:
     - Copies `src/dashboard/templates/index.html` and `src/dashboard/static/{style.css, app.js}` into `dist/`.
     - Exports `dist/api/health.json`, `dist/api/game.json`, `dist/api/radar_eod.json`, `dist/api/radar_premarket.json`, `dist/api/radar_intraday.json`.
     - When `mode == "full"` (or if missing), exports `dist/api/stock/<TICKER>.json` (all 50 tickers) and `dist/api/backtest/<TICKER>.json` (containing `1y`, `2y`, `3y` results for all 50 tickers).
2. **Extend `src/main.py` CLI**:
   - Add `--export-static` and `--export-mode {fast|full}` flags so GitHub Actions can execute:
     ```bash
     python -m src.main --bot-turn --export-static --export-mode fast
     ```

---

### Phase 2: Dual-Mode Frontend & Real-Time Browser Price Engine
**Files**: `src/dashboard/static/app.js`, `src/dashboard/templates/index.html`, `src/dashboard/static/style.css`, `src/cloud/cloudflare_worker_proxy.js` *(optional helper)*

1. **Dual-Mode API Router (`apiFetch(endpoint, options)` in `app.js`)**:
   - Automatically detects if running on Flask (`/api/...`) vs. Static Cloud (`./api/...json`).
   - For `game_state.json`, fetches directly from GitHub API / Raw URL with `?t=${Date.now()}` to bypass GitHub Pages CDN caching.
2. **Live Browser Price Stream (`livePriceEngine` in `app.js`)**:
   - Polls live prices every 15 seconds for all held tickers (Player + Bot) and visible radar rows.
   - Supports **Finnhub API Key** (entered once in UI settings, stored in `localStorage`) OR **Cloudflare Worker Yahoo Finance Batch Proxy** (`?symbols=NVDA,STX,META,...`).
   - Recomputes in real time inside the browser:
     - `current_price`, `market_value`, `unrealized_pnl`, `unrealized_pnl_pct`
     - `peak_price` and dynamic ratcheted `trailing_stop`
     - Player & Bot `net_equity`, `total_pnl`, and `lead_label`
   - Displays a live status badge in the top bar: `🟢 Live Market Feed (Updated 2s ago)`.
3. **Cloud Order & Action Dispatcher (`cloudDispatch(action, payload)` in `app.js`)**:
   - Adds a **"☁️ Cloud Settings"** button in the header where you configure:
     - GitHub Repo (`jonsan21g/predict-stock`)
     - Fine-Grained GitHub PAT (`Actions: Read & Write`)
     - Optional Finnhub Free API Key (for live browser quotes)
   - Routes `submitOrder()`, `triggerBotTurn()`, and `resetDuel()` in Cloud Mode to:
     `POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/wave-rider-cloud.yml/dispatches`
   - Shows a live 15-second progress indicator and automatically refreshes the scoreboard once the workflow completes.

---

### Phase 3: GitHub Actions Workflow & `cron-job.org` Integration
**File**: `.github/workflows/wave-rider-cloud.yml` *(new)*

1. **Workflow Inputs (`workflow_dispatch`)**:
   - `command`: `bot_turn` (default) | `player_order` | `full_eod_export` | `reset_duel`
   - `order_action`: `BUY` | `SELL`
   - `ticker`: e.g. `NVDA`
   - `shares`: e.g. `10`
2. **Concurrency & Caching**:
   - `concurrency: { group: "wave-rider-cloud-lock", cancel-in-progress: false }`
   - `actions/cache@v4` for pip virtualenv and `data/cache/` (keeps intraday runs under 25 seconds).
3. **Two-Target Deployment**:
   - Commits updated `data/game_state.json` and `data/history/*.json` back to `main` **only when modified**.
   - Deploys the compiled `dist/` static dashboard bundle to the `gh-pages` branch using `peaceiris/actions-gh-pages@v4` with `force_orphan: true`.

---

### Phase 4: Automated Test Suite & RTM Verification
**File**: `tests/test_cloud_deployment.py` *(new)*

1. **`test_static_exporter_fast_and_full_bundles` (`TC-DEP-01`)**:
   - Verifies `export_cloud_bundle()` creates `index.html`, `app.js`, `style.css`, `api/game.json`, `api/radar_*.json`, `api/stock/<TICKER>.json`, and `api/backtest/<TICKER>.json` with all required schema keys.
2. **`test_cli_export_and_cloud_order_execution` (`TC-DEP-02`)**:
   - Verifies CLI execution of `--order`, `--bot-turn`, and `--export-static` maintains atomic state integrity in `game_state.json`.
3. **Full Regression**:
   - Verify all existing tests + new cloud deployment tests pass 100% (`pytest`).

---

### Phase 5: Specification & Documentation Synchronization
Every engineering document in the repository will be updated simultaneously so the specification suite remains 100% consistent:

1. **[`FUNCTIONAL_REQUIREMENTS.md`](file:///c:/Users/jonsa/LLM/predict-stock/FUNCTIONAL_REQUIREMENTS.md)**:
   - Update Master RTM table and detailed specs for **`FR-07-01`** (*Hybrid GitHub Pages & Actions Cloud Deployment*) and **`FR-07-02`** (*Git-Backed Atomic State Persistence & Browser Live Price Overlay*).
   - Add **Epic 9 (`FR-09-01` to `FR-09-05`)** documenting the 50-stock universe expansion and Week 3–5 Profit Realization & Ratchet rules in the RTM.
2. **[`DESIGN_SPECIFICATION.md`](file:///c:/Users/jonsa/LLM/predict-stock/DESIGN_SPECIFICATION.md)**:
   - Replace Section 9 (*Future Cloud Architecture Blueprint*) with the production **Hybrid GitHub Pages + Precision `workflow_dispatch` + Live Browser Price Waterfall** design and sequence diagrams.
   - Synchronize universe counts (50 equities) and Week 3–5 game state schemas.
3. **[`ARCHITECTURE.md`](file:///c:/Users/jonsa/LLM/predict-stock/ARCHITECTURE.md)**:
   - Add **`ADR-06`**: *Hybrid Serverless Cloud Topology vs. Sleeping PaaS & IaaS Micro-VMs*.
4. **[`BACKLOG.md`](file:///c:/Users/jonsa/LLM/predict-stock/BACKLOG.md)**:
   - Mark `DEP-01` and `DEP-02` as **✅ Done** under Epic 6.
5. **[`SYSTEM_VERIFICATION_REPORT.md`](file:///c:/Users/jonsa/LLM/predict-stock/SYSTEM_VERIFICATION_REPORT.md)**:
   - Record the updated test suite pass rate and cloud bundle verification audit.
6. **[`README.md`](file:///c:/Users/jonsa/LLM/predict-stock/README.md)**:
   - Add the 5-minute step-by-step setup guide for GitHub Pages, `cron-job.org`, and the Fine-Grained PAT.

---

## 📌 How to Trigger Execution at the End of the Week
Once Week 5 concludes on **Friday, November 6, 2026**, simply say:
> *"Execute plan `to-the-cloud`"*

We will archive Week 5, implement all 5 phases above, run the full verification suite, and get your cloud dashboard live!
