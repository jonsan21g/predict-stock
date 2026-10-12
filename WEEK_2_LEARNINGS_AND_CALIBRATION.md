# Week 2 Learnings & Parameter Calibration Journal

## 📅 Session 1: Monday, October 5, 2026 (Day 1 of Duel 2)

---

### 1. Case Study: The "Quiet Breakouts" — Cloud & High-Beta Software (`NET` & `ALAB`)

#### A. Tape Observation & Metrics
During the initial 2–4 hours of the trading session, two prominent equities in the 50-stock watchlist exhibited clean, sustained price appreciation:
- **`NET` (Cloudflare)**:
  - Day Change: **+4.27%** (Open \$351.13 $\to$ High \$364.69 $\to$ Current \$363.99).
  - Structure: Clean 30-minute Opening Range Breakout above \$357.99 ORH; held steadily above VWAP (\$358.88); intact long-term uptrend (> 20-day EMA at \$325).
  - Cumulative Volume: ~1.1M shares vs 3.11M 20-day SMA.
  - **Pacing RVOL**: **0.96× – 0.99×** (Failed $\ge 1.40\times$ threshold).
- **`ALAB` (Astera Labs)**:
  - Day Change: **+3.41%** (Open \$354.80 $\to$ High \$360.73 $\to$ Current \$362.29).
  - Structure: Clean 30-minute Opening Range Breakout above \$357.00 ORH; held steadily above VWAP (\$354.52); intact uptrend (> 20-day EMA at \$338).
  - Cumulative Volume: ~1.1M shares vs 4.24M 20-day SMA.
  - **Pacing RVOL**: **0.72× – 0.76×** (Failed $\ge 1.40\times$ threshold).

#### B. Engine Decision
- **Classification**: Both were rejected from ignition (`is_ignition = False`, Composite Score = 45, $P(\text{Wave}) = 42.0\%$).
- **Trigger Failure**: Blocked specifically by the **Week 2 "Be More Sure" Time-of-Day Pacing RVOL Gate** ($\text{RVOL}_{\text{pacing}} \ge 1.40\times$).
- **Capital Deployed**: The Bot correctly chose **`TSLA`** ($\text{RVOL}_{\text{pacing}} = 1.40\times$) and **`SPCX`** ($\text{RVOL}_{\text{pacing}} = 1.51\times$) instead.

---

### 2. The Core Quantitative Dilemma: False Breakout Protection vs. Opportunity Cost

```
                    ┌──────────────────────────────────────────────┐
                    │      INTRADAY VOLUME PACING DILEMMA          │
                    └──────────────────────────────────────────────┘
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
  [STRICT THRESHOLD: ≥ 1.40×]                                [LOWER THRESHOLD: ≥ 1.10×]
  • Filters out Week 1 low-volume traps                      • Catches quiet trend expansions (NET, ALAB)
  • Prevents late-session bleed in choppy names              • Risk of higher false positives in retail chop
  • Misses low-volume high-margin runners (Type II error)    • May dilute capital across weaker momentum
```

1. **Why the $1.40\times$ threshold was introduced**:
   - In Week 1, the bot repeatedly bought false breakouts that lacked institutional sponsorship. Those positions routinely stalled at +0.8% to +1.2%, drifted lower during midday liquidity droughts, and triggered stop-losses.
   - Enforcing $\ge 1.40\times$ volume pacing ensures institutional accumulation.
2. **What `NET` and `ALAB` teach us**:
   - High-multiple cloud, SaaS, and specialized semiconductor names often experience **liquidity-efficient markups**: sellers simply vanish, allowing market makers to mark the stock up +3% to +5% on normal or even slightly below-average volume ($0.8\times – 1.1\times$).
   - A rigid blanket threshold of $1.40\times$ across all 50 stocks treats enterprise software identically to mega-cap retail favorites like `TSLA` (which routinely trades tens of millions of shares).

---

### 3. Monitoring Plan & Future Calibration Roadmap

#### Phase 1: End-of-Day (EOD) Close Verification
- **Test**: Track whether `NET` and `ALAB` hold their gains into the 16:00 EST close or experience afternoon mean-reversion.
- **Criteria**:
  - If `NET` and `ALAB` close near their highs (e.g., Close within top 25% of day's range with positive forward Day-2 follow-through), this validates that low-volume trend breakouts are viable.
  - If they fade toward open/VWAP into the close, it validates that the $1.40\times$ threshold saved the bot from a false breakout.

#### Phase 2: Proposed Dynamic Calibration Models (For Future Testing)

| Candidate Model | Proposed Mechanism | Target Equities |
| :--- | :--- | :--- |
| **Option A: Tiered Sector Thresholds** | Lower pacing requirement to **$1.15\times$** for Cloud/Cyber/SaaS (e.g. `NET`, `NOW`, `PANW`, `CRWD`) while maintaining **$1.40\times$** for Hardware/Mega-caps (`TSLA`, `NVDA`, `AMD`). | Cloud & Cybersecurity |
| **Option B: VWAP-Distance Relaxation** | If a stock breaks ORH_30 AND trades **$\ge +0.75\%$ above rising VWAP** with positive VWAP slope, allow entry at **$1.10\times$ RVOL**. | Strong intraday structure |
| **Option C: Relative Sector Strength Gate** | If stock is outperforming its benchmark sector ETF (e.g., `IGV` / `SMH`) by $\ge +1.5\%$, accept lower absolute volume pacing. | Sector leaders |

---

### 4. Current Operational Directive
- **Hold Baseline Rules Constant for Week 2**: Do not alter live parameters mid-duel to maintain rigorous scientific discipline.
- **Daily Journaling**: Log every "Quiet Breakout" occurrence daily through Friday, October 9, 2026.
- **Weekend Optimization**: Run historical walkforward backtests comparing $\text{RVOL}_{\text{pacing}} \in [1.0\times, 1.2\times, 1.4\times, 1.6\times]$ before deploying any engine modifications for Week 3.
