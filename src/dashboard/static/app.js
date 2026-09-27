// app.js - Wave Rider Dashboard Client Script
let currentMode = "eod";
let allRadarData = [];
let activeCategory = "ALL";
let deepDiveChart = null;
let backtestChart = null;

document.addEventListener("DOMContentLoaded", () => {
  loadRadar();
});

function setMode(mode) {
  currentMode = mode;
  document.getElementById("btn-eod").classList.toggle("active", mode === "eod");
  document.getElementById("btn-pm").classList.toggle("active", mode === "premarket");
  loadRadar(true);
}

function refreshRadar() {
  loadRadar(true);
}

function showTab(tabId) {
  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

  if (tabId === "radar") {
    document.querySelectorAll(".nav-tab")[0].classList.add("active");
    document.getElementById("tab-radar").classList.add("active");
  } else if (tabId === "deepdive") {
    document.querySelectorAll(".nav-tab")[1].classList.add("active");
    document.getElementById("tab-deepdive").classList.add("active");
    const currentTicker = document.getElementById("select-ticker").value || "NVDA";
    loadDeepDive(currentTicker);
  } else if (tabId === "backtest") {
    document.querySelectorAll(".nav-tab")[2].classList.add("active");
    document.getElementById("tab-backtest").classList.add("active");
    if (!document.getElementById("kpi-return").textContent.includes("+")) {
      executeBacktest();
    }
  } else if (tabId === "duel") {
    document.querySelectorAll(".nav-tab")[3].classList.add("active");
    document.getElementById("tab-duel").classList.add("active");
    loadDuelState();
  }
}

async function loadRadar(refresh = false) {
  const tbody = document.getElementById("radar-tbody");
  tbody.innerHTML = `<tr><td colspan="13" class="loading-cell" style="text-align:center; padding: 24px; color:#94a3b8;">Scanning 27 US Tech & Memory Leaders for Wave Ignition...</td></tr>`;

  try {
    const res = await fetch(`/api/radar?mode=${currentMode}&refresh=${refresh}`);
    const data = await res.json();
    allRadarData = data;

    populateDropdowns(data);
    renderRadarTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="13" style="text-align:center; color:#f43f5e; padding: 20px;">Error loading radar data: ${err}</td></tr>`;
  }
}

function populateDropdowns(data) {
  const selectDeep = document.getElementById("select-ticker");
  const selectBt = document.getElementById("bt-ticker");
  
  if (selectDeep.children.length === 0) {
    data.forEach(item => {
      const opt1 = document.createElement("option");
      opt1.value = item.ticker;
      opt1.textContent = `${item.ticker} — ${item.name || item.ticker}`;
      selectDeep.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = item.ticker;
      opt2.textContent = `${item.ticker} — ${item.name || item.ticker}`;
      selectBt.appendChild(opt2);
    });
  }
}

function filterCategory(cat) {
  activeCategory = cat;
  document.querySelectorAll(".pill").forEach(pill => {
    pill.classList.toggle("active", pill.textContent.includes(cat) || (cat === "ALL" && pill.textContent.includes("All")));
  });
  renderRadarTable();
}

function renderRadarTable() {
  const tbody = document.getElementById("radar-tbody");
  tbody.innerHTML = "";

  const filtered = activeCategory === "ALL" 
    ? allRadarData 
    : allRadarData.filter(d => d.category === activeCategory);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="13" style="text-align:center; padding: 24px; color:#94a3b8;">No stocks in this category.</td></tr>`;
    return;
  }

  filtered.forEach((item, idx) => {
    const tr = document.createElement("tr");

    const isIgnition = item.is_ignition;
    const ignBadge = isIgnition
      ? `<span class="badge-ignition active">⚡ ${item.ignition_type}</span>`
      : `<span class="badge-ignition idle">Consolidating</span>`;

    let scoreClass = "score-low";
    if (item.composite_score >= 70) scoreClass = "score-high";
    else if (item.composite_score >= 50) scoreClass = "score-med";

    const chgSign = item.change_pct >= 0 ? "+" : "";
    const chgColor = item.change_pct >= 0 ? "#10b981" : "#f43f5e";

    const sm = item.smart_money || {};
    let badges = [];
    if (sm.politician_buy) badges.push(`<span title="Recent US Congress Buy">🏛️ Congress</span>`);
    if (sm.insider_cluster) badges.push(`<span title="Executive Cluster Buy">👔 ClusterBuy</span>`);
    else if (sm.insider_buy) badges.push(`<span title="Insider Buy">👔 Insider</span>`);
    if (sm.sentiment_label === "BULLISH") badges.push(`<span title="Positive News Velocity">💬 Bullish</span>`);

    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td class="ticker-cell" onclick="inspectStock('${item.ticker}')">${item.ticker}</td>
      <td style="color:#94a3b8; font-size:12px;">${item.category || "Tech"}</td>
      <td style="font-weight:700;">$${item.current_price.toFixed(2)}</td>
      <td style="color:${chgColor}; font-weight:700;">${chgSign}${item.change_pct.toFixed(2)}%</td>
      <td>${ignBadge}</td>
      <td style="font-weight:700; color:#38bdf8;">${item.wave_probability.toFixed(1)}%</td>
      <td><span class="score-badge ${scoreClass}">${item.composite_score}</span></td>
      <td class="target-val">$${item.target_1 ? item.target_1.toFixed(2) : "-"}</td>
      <td class="target-val">$${item.target_2 ? item.target_2.toFixed(2) : "-"}</td>
      <td class="stop-val">$${item.stop_loss ? item.stop_loss.toFixed(2) : "-"}</td>
      <td>${badges.join(" ") || "-"}</td>
      <td><button class="btn-inspect" onclick="inspectStock('${item.ticker}')">Inspect →</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function inspectStock(ticker) {
  document.getElementById("select-ticker").value = ticker;
  showTab("deepdive");
  loadDeepDive(ticker);
}

async function loadDeepDive(ticker) {
  const container = document.getElementById("deepdive-body");
  container.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding: 40px; color:#94a3b8;">Loading deep-dive for ${ticker}...</div>`;

  try {
    const res = await fetch(`/api/stock/${ticker}`);
    const data = await res.json();

    const chgSign = data.change_pct >= 0 ? "+" : "";
    const chgColor = data.change_pct >= 0 ? "#10b981" : "#f43f5e";

    const checks = data.checks || [];
    const checksHtml = checks.map(c => `
      <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #1e293b; font-size:13px;">
        <span>${c.passed ? "✅" : "❌"} <strong>${c.rule}</strong></span>
        <span style="color:#94a3b8;">${c.detail}</span>
      </div>
    `).join("");

    const sm = data.smart_money || {};
    const pols = sm.politicians && sm.politicians.length > 0 
      ? sm.politicians.map(p => `<li>🏛️ ${p}</li>`).join("")
      : `<li style="color:#94a3b8;">No recent Congress buys in last 45 days.</li>`;

    container.innerHTML = `
      <div class="card-box">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div>
            <h2 style="font-size:22px; font-weight:800; color:#38bdf8;">${data.ticker} <span style="font-size:16px; color:#fff;">$${data.current_price.toFixed(2)}</span></h2>
            <span style="color:${chgColor}; font-weight:700;">${chgSign}${data.change_pct.toFixed(2)}%</span>
          </div>
          <div style="text-align:right;">
            <div style="font-size:12px; color:#94a3b8;">Wave Probability</div>
            <div style="font-size:20px; font-weight:800; color:#10b981;">${data.wave_probability.toFixed(1)}%</div>
          </div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:16px; background:#0f172a; padding:12px; border-radius:8px;">
          <div><span style="font-size:11px; color:#94a3b8;">STOP LOSS (-2.5%)</span><br><strong style="color:#f43f5e;">$${data.stop_loss.toFixed(2)}</strong></div>
          <div><span style="font-size:11px; color:#94a3b8;">TARGET 1 (+3.5%)</span><br><strong style="color:#10b981;">$${data.target_1.toFixed(2)}</strong></div>
          <div><span style="font-size:11px; color:#94a3b8;">TARGET 2 (+6.0%)</span><br><strong style="color:#10b981;">$${data.target_2.toFixed(2)}</strong></div>
        </div>

        <canvas id="deepDiveCanvas" height="150"></canvas>
      </div>

      <div>
        <div class="card-box">
          <h3>⚡ Day-1 Wave Ignition Checklist</h3>
          <div>${checksHtml || "No check data available."}</div>
        </div>

        <div class="card-box">
          <h3>🏛️ US Congressional Activity (STOCK Act)</h3>
          <ul style="list-style:none; padding:0; font-size:13px; display:flex; flex-direction:column; gap:6px;">
            ${pols}
          </ul>
        </div>

        <div class="card-box">
          <h3>👔 SEC Form 4 Insider Conviction</h3>
          <div style="font-size:13px; line-height:1.6;">
            <div>Score: <strong>${sm.insider_score || 0} / 100</strong></div>
            <div>Cluster Buying: <strong>${sm.insider_cluster ? "YES (2+ Insiders)" : "No"}</strong></div>
            <div>Sentiment: <strong>${sm.sentiment_label || "NEUTRAL"}</strong></div>
          </div>
        </div>
      </div>
    `;

    renderDeepDiveChart(data.history, data.target_1, data.target_2, data.stop_loss);
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; color:#f43f5e; padding: 40px;">Failed to load deep-dive: ${err}</div>`;
  }
}

function renderDeepDiveChart(history, t1, t2, sl) {
  const ctx = document.getElementById("deepDiveCanvas").getContext("2d");
  if (deepDiveChart) deepDiveChart.destroy();

  const labels = history.map(h => h.date);
  const closes = history.map(h => h.close);
  const ema5 = history.map(h => h.ema5);

  const t1Line = Array(labels.length).fill(t1);
  const t2Line = Array(labels.length).fill(t2);
  const slLine = Array(labels.length).fill(sl);

  deepDiveChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Price ($)",
          data: closes,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.2
        },
        {
          label: "5 EMA (Trailing Floor)",
          data: ema5,
          borderColor: "#a855f7",
          borderWidth: 1.5,
          borderDash: [4, 4],
          fill: false,
          pointRadius: 0
        },
        {
          label: "Target 1 (+3.5%)",
          data: t1Line,
          borderColor: "#10b981",
          borderWidth: 1.5,
          borderDash: [6, 6],
          fill: false,
          pointRadius: 0
        },
        {
          label: "Stop Loss (-2.5%)",
          data: slLine,
          borderColor: "#f43f5e",
          borderWidth: 1.5,
          borderDash: [6, 6],
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { size: 11 } } }
      },
      scales: {
        x: { ticks: { color: "#94a3b8", maxTicksLimit: 8 }, grid: { color: "#1e293b" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

async function executeBacktest() {
  const ticker = document.getElementById("bt-ticker").value || "NVDA";
  const period = document.getElementById("bt-period").value || "2y";

  const container = document.getElementById("backtest-results");
  container.style.display = "block";

  try {
    const res = await fetch(`/api/backtest?ticker=${ticker}&period=${period}`);
    const data = await res.json();

    document.getElementById("kpi-return").textContent = `${data.strategy_return_pct >= 0 ? "+" : ""}${data.strategy_return_pct.toFixed(2)}%`;
    document.getElementById("kpi-return").style.color = data.strategy_return_pct >= 0 ? "#10b981" : "#f43f5e";
    document.getElementById("kpi-bh").textContent = `vs B&H: ${data.buy_and_hold_return_pct >= 0 ? "+" : ""}${data.buy_and_hold_return_pct.toFixed(1)}%`;

    document.getElementById("kpi-winrate").textContent = `${data.win_rate_pct.toFixed(1)}%`;
    document.getElementById("kpi-wl").textContent = `${data.wins}W / ${data.losses}L (${data.total_trades} Trades)`;

    document.getElementById("kpi-pf").textContent = data.profit_factor.toFixed(2);
    document.getElementById("kpi-exp").textContent = `$${data.expectancy_dollar.toFixed(2)}`;
    document.getElementById("kpi-mdd").textContent = `${data.max_drawdown_pct.toFixed(2)}%`;
    document.getElementById("kpi-hold").textContent = `${data.avg_bars_held} Days`;

    renderBacktestChart(data.equity_curve);

    const tbody = document.getElementById("bt-trades-tbody");
    tbody.innerHTML = "";
    (data.trades || []).forEach(t => {
      const tr = document.createElement("tr");
      const isWin = t.pnl > 0;
      const color = isWin ? "#10b981" : "#f43f5e";
      const sign = isWin ? "+" : "";

      tr.innerHTML = `
        <td>${t.id}</td>
        <td>${t.entry_date}</td>
        <td>${t.exit_date}</td>
        <td>$${t.entry_price.toFixed(2)}</td>
        <td>$${t.exit_price.toFixed(2)}</td>
        <td>${t.shares}</td>
        <td style="color:${color}; font-weight:700;">${sign}$${t.pnl.toFixed(2)}</td>
        <td style="color:${color}; font-weight:700;">${sign}${t.return_pct.toFixed(2)}%</td>
        <td>${t.bars_held}</td>
        <td>${t.exit_reason}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    alert("Backtest failed: " + err);
  }
}

function renderBacktestChart(equityCurve) {
  const ctx = document.getElementById("equityChart").getContext("2d");
  if (backtestChart) backtestChart.destroy();

  const labels = equityCurve.map(pt => pt.date);
  const balances = equityCurve.map(pt => pt.balance);

  backtestChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Account Equity ($)",
          data: balances,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.12)",
          borderWidth: 2,
          fill: true,
          tension: 0.2
        },
        {
          label: "Breakeven ($10,000)",
          data: Array(labels.length).fill(10000),
          borderColor: "#f59e0b",
          borderWidth: 1.5,
          borderDash: [6, 6],
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8" } }
      },
      scales: {
        x: { ticks: { color: "#94a3b8", maxTicksLimit: 10 }, grid: { color: "#1e293b" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#1e293b" } }
      }
    }
  });
}

// =====================================================================
// 5-DAY PLAYER VS. BOT DUEL LOGIC
// =====================================================================
let duelState = null;
let currentOrderAction = "BUY";
let watchlistCache = [];

async function loadDuelState() {
  try {
    const res = await fetch("/api/game");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    duelState = data;
    renderDuelScoreboard(data);
    renderPlayerHoldings(data.player.positions);
    renderBotHoldings(data.bot.positions);
    renderBotDisclosures(data.bot.decision_logs);
    renderMatchAuditLog(data.player.history, data.bot.history);

    // If watchlistCache is empty, populate ticker select from allRadarData or radar fetch
    if (watchlistCache.length === 0) {
      if (allRadarData.length > 0) {
        watchlistCache = allRadarData.map(d => ({ ticker: d.ticker, price: d.current_price, name: d.name }));
        populateOrderTickerSelect();
      } else {
        fetch("/api/radar?mode=eod").then(r => r.json()).then(radar => {
          allRadarData = radar;
          watchlistCache = radar.map(d => ({ ticker: d.ticker, price: d.current_price, name: d.name }));
          populateOrderTickerSelect();
        });
      }
    } else {
      calculateOrderEstimate();
    }
  } catch (err) {
    console.error("Failed to load duel state:", err);
  }
}

function renderDuelScoreboard(data) {
  // Countdown and Lead badge
  const countdownEl = document.getElementById("duel-countdown");
  if (countdownEl) countdownEl.textContent = `${data.countdown} • Target: Friday Oct 2, 2026 at 23:00 CET`;

  const leadBadge = document.getElementById("duel-lead-badge");
  if (leadBadge) {
    leadBadge.textContent = data.lead_label;
    leadBadge.className = "duel-lead-pill " + (data.leader === "PLAYER" ? "lead-player" : (data.leader === "BOT" ? "lead-bot" : "lead-tied"));
  }

  // Player Stats
  const p = data.player;
  document.getElementById("player-equity").textContent = `$${p.net_equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  const pSign = p.total_pnl >= 0 ? "+" : "";
  const pPnlEl = document.getElementById("player-pnl");
  pPnlEl.textContent = `${pSign}$${p.total_pnl.toFixed(2)} (${pSign}${p.total_pnl_pct.toFixed(2)}%)`;
  pPnlEl.className = "equity-pnl " + (p.total_pnl >= 0 ? "pnl-green" : "pnl-red");

  document.getElementById("player-cash").textContent = `$${p.cash.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  document.getElementById("player-stocks").textContent = `$${p.stock_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  document.getElementById("player-positions-count").textContent = p.positions.length;

  // Bot Stats
  const b = data.bot;
  document.getElementById("bot-equity").textContent = `$${b.net_equity.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  const bSign = b.total_pnl >= 0 ? "+" : "";
  const bPnlEl = document.getElementById("bot-pnl");
  bPnlEl.textContent = `${bSign}$${b.total_pnl.toFixed(2)} (${bSign}${b.total_pnl_pct.toFixed(2)}%)`;
  bPnlEl.className = "equity-pnl " + (b.total_pnl >= 0 ? "pnl-green" : "pnl-red");

  document.getElementById("bot-cash").textContent = `$${b.cash.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  document.getElementById("bot-stocks").textContent = `$${b.stock_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  document.getElementById("bot-positions-count").textContent = b.positions.length;
}

function populateOrderTickerSelect() {
  const sel = document.getElementById("order-ticker");
  if (!sel) return;
  sel.innerHTML = "";
  watchlistCache.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.ticker;
    opt.textContent = `${item.ticker} — $${item.price.toFixed(2)} (${item.name || item.ticker})`;
    sel.appendChild(opt);
  });
  calculateOrderEstimate();
}

function setOrderAction(action) {
  currentOrderAction = action;
  document.getElementById("order-type-buy").classList.toggle("active", action === "BUY");
  document.getElementById("order-type-sell").classList.toggle("active", action === "SELL");

  const submitBtn = document.getElementById("btn-submit-order");
  if (action === "BUY") {
    submitBtn.textContent = "🚀 Execute BUY Order";
    submitBtn.className = "btn-execute-order btn-buy";
  } else {
    submitBtn.textContent = "💸 Execute SELL Order";
    submitBtn.className = "btn-execute-order btn-sell";
  }
  calculateOrderEstimate();
}

function onOrderTickerChange() {
  calculateOrderEstimate();
}

function getSelectedStock() {
  const sel = document.getElementById("order-ticker");
  if (!sel || !sel.value) return null;
  const ticker = sel.value;
  return watchlistCache.find(s => s.ticker === ticker) || { ticker: ticker, price: 100.0 };
}

function calculateOrderEstimate() {
  const stock = getSelectedStock();
  if (!stock) return;

  const sharesInput = document.getElementById("order-shares");
  const shares = parseInt(sharesInput.value) || 0;
  const estPrice = stock.price || 100.0;
  const totalValue = shares * estPrice;

  document.getElementById("order-est-price").textContent = `$${estPrice.toFixed(2)}`;
  document.getElementById("order-est-total").textContent = `$${totalValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

  const currentCash = duelState ? duelState.player.cash : 30000.0;
  const remEl = document.getElementById("order-est-remaining");

  if (currentOrderAction === "BUY") {
    const remaining = currentCash - totalValue;
    remEl.textContent = `$${remaining.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    remEl.style.color = remaining >= 0 ? "#94a3b8" : "#f43f5e";
  } else {
    const remaining = currentCash + totalValue;
    remEl.textContent = `$${remaining.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    remEl.style.color = "#10b981";
  }
}

function applyQuickAllocation(fraction) {
  const stock = getSelectedStock();
  if (!stock) return;
  const price = stock.price || 100.0;

  if (currentOrderAction === "BUY") {
    const cash = duelState ? duelState.player.cash : 30000.0;
    const targetBudget = cash * fraction;
    const shares = Math.max(1, Math.floor(targetBudget / price));
    document.getElementById("order-shares").value = shares;
  } else {
    const pos = (duelState?.player?.positions || []).find(p => p.ticker === stock.ticker);
    const held = pos ? pos.shares : 0;
    const shares = Math.max(1, Math.floor(held * fraction));
    document.getElementById("order-shares").value = shares;
  }
  calculateOrderEstimate();
}

async function submitPlayerOrder() {
  const stock = getSelectedStock();
  if (!stock) {
    alert("Please select a stock.");
    return;
  }
  const ticker = stock.ticker;
  const shares = parseInt(document.getElementById("order-shares").value) || 0;

  if (shares <= 0) {
    alert("Please enter a valid share count (> 0).");
    return;
  }

  const btn = document.getElementById("btn-submit-order");
  btn.disabled = true;
  btn.textContent = "Processing Order...";

  try {
    const res = await fetch("/api/game/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: currentOrderAction, ticker: ticker, shares: shares })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.error || "Order execution failed");

    await loadDuelState();
    alert(`Order Filled: ${currentOrderAction} ${shares} ${ticker} @ $${result.price.toFixed(2)}`);
  } catch (err) {
    alert("Order Error: " + err.message);
  } finally {
    btn.disabled = false;
    setOrderAction(currentOrderAction);
  }
}

function quickSell(ticker, fraction) {
  const pos = (duelState?.player?.positions || []).find(p => p.ticker === ticker);
  if (!pos) return;
  const sharesToSell = Math.max(1, Math.floor(pos.shares * fraction));
  const sel = document.getElementById("order-ticker");
  if (sel) sel.value = ticker;
  setOrderAction("SELL");
  document.getElementById("order-shares").value = sharesToSell;
  calculateOrderEstimate();
  submitPlayerOrder();
}

function renderPlayerHoldings(positions) {
  const tbody = document.getElementById("player-holdings-tbody");
  if (!positions || positions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="loading-cell" style="text-align:center; padding: 20px; color:#94a3b8;">No open positions. Starting bankroll is 100% liquid cash.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  positions.forEach(p => {
    const tr = document.createElement("tr");
    const pnlSign = p.unrealized_pnl >= 0 ? "+" : "";
    const pnlColor = p.unrealized_pnl >= 0 ? "#10b981" : "#f43f5e";

    tr.innerHTML = `
      <td><strong>${p.ticker}</strong></td>
      <td>${p.shares}</td>
      <td>$${p.avg_price.toFixed(2)}</td>
      <td>$${p.current_price.toFixed(2)}</td>
      <td>$${p.market_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td style="color:${pnlColor}; font-weight:700;">
        ${pnlSign}$${p.unrealized_pnl.toFixed(2)} (${pnlSign}${p.unrealized_pnl_pct.toFixed(2)}%)
      </td>
      <td>
        <div class="row-actions">
          <button class="btn-micro btn-sell-half" onclick="quickSell('${p.ticker}', 0.5)">Sell 50%</button>
          <button class="btn-micro btn-sell-all" onclick="quickSell('${p.ticker}', 1.0)">Sell 100%</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderBotHoldings(positions) {
  const tbody = document.getElementById("bot-holdings-tbody");
  if (!positions || positions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell" style="text-align:center; padding: 20px; color:#94a3b8;">Bot currently holding $30,000 cash. Scanning for Day-1 Ignition.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  positions.forEach(p => {
    const tr = document.createElement("tr");
    const pnlSign = p.unrealized_pnl >= 0 ? "+" : "";
    const pnlColor = p.unrealized_pnl >= 0 ? "#10b981" : "#f43f5e";

    tr.innerHTML = `
      <td><strong>${p.ticker}</strong></td>
      <td>${p.shares}</td>
      <td>$${p.avg_price.toFixed(2)}</td>
      <td>$${p.current_price.toFixed(2)}</td>
      <td>$${p.market_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td style="color:${pnlColor}; font-weight:700;">
        ${pnlSign}$${p.unrealized_pnl.toFixed(2)} (${pnlSign}${p.unrealized_pnl_pct.toFixed(2)}%)
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderBotDisclosures(logs) {
  const container = document.getElementById("bot-disclosures-feed");
  if (!logs || logs.length === 0) {
    container.innerHTML = `<div class="empty-feed">No Bot actions yet. Once triggered, full rationale and outside catalysts will appear here.</div>`;
    return;
  }

  container.innerHTML = "";
  const reversed = [...logs].reverse();
  reversed.forEach(log => {
    const card = document.createElement("div");
    card.className = "disclosure-card";

    const isBuy = log.action === "BUY";
    const badgeColor = isBuy ? "badge-buy" : "badge-sell";

    card.innerHTML = `
      <div class="disclosure-header">
        <span class="disc-badge ${badgeColor}">${log.action} ${log.shares} ${log.ticker}</span>
        <span class="disc-time">${log.time}</span>
      </div>
      <p class="disc-rationale">"${log.rationale}"</p>
      <div class="disc-meta">
        <span>Fill: $${log.price.toFixed(2)}</span>
        <span>Total: $${log.total_usd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
        ${log.wave_probability ? `<span>P(Wave): ${log.wave_probability.toFixed(1)}%</span>` : ''}
        ${log.composite_score ? `<span>Score: ${log.composite_score}/100</span>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderMatchAuditLog(playerHistory, botHistory) {
  const tbody = document.getElementById("duel-audit-tbody");
  const allTx = [...(playerHistory || []), ...(botHistory || [])];

  if (allTx.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="loading-cell" style="text-align:center; padding: 20px; color:#94a3b8;">No transactions recorded yet in the duel ledger.</td></tr>`;
    return;
  }

  allTx.sort((a, b) => (b.time || "").localeCompare(a.time || ""));

  tbody.innerHTML = "";
  allTx.forEach(tx => {
    const tr = document.createElement("tr");
    const isPlayer = tx.participant === "PLAYER";
    const partBadge = isPlayer
      ? `<span class="pill-participant player-badge">👤 Player</span>`
      : `<span class="pill-participant bot-badge">🤖 Bot</span>`;
    const actionBadge = tx.action === "BUY"
      ? `<span class="order-badge buy-badge">BUY</span>`
      : `<span class="order-badge sell-badge">SELL</span>`;
    const pnlSign = tx.realized_pnl > 0 ? "+" : "";
    const pnlColor = tx.realized_pnl > 0 ? "#10b981" : (tx.realized_pnl < 0 ? "#f43f5e" : "#94a3b8");

    tr.innerHTML = `
      <td>${tx.id}</td>
      <td>${tx.time}</td>
      <td>${partBadge}</td>
      <td>${actionBadge}</td>
      <td><strong>${tx.ticker}</strong></td>
      <td>${tx.shares}</td>
      <td>$${tx.price.toFixed(2)}</td>
      <td>$${tx.total_usd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td style="color:${pnlColor}; font-weight:700;">${pnlSign}$${tx.realized_pnl.toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function triggerBotTurn() {
  const btn = document.querySelector(".btn-bot-turn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "🤖 Evaluating Market...";
  }

  try {
    const res = await fetch("/api/game/bot-turn", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Bot turn failed");

    await loadDuelState();
    if (data.actions_count > 0) {
      alert(`Bot completed evaluation! Executed ${data.actions_count} action(s):\n• ` + data.actions_taken.join("\n• "));
    } else {
      alert("Bot completed evaluation. No position changes needed at this time.");
    }
  } catch (err) {
    alert("Error triggering Bot turn: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "⚡ Trigger Bot Turn";
    }
  }
}

async function resetDuel() {
  if (!confirm("Are you sure you want to reset the 5-Day Duel? Both Player and Bot will be reset to $30,000 cash with all history cleared.")) {
    return;
  }

  try {
    const res = await fetch("/api/game/reset", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Reset failed");
    await loadDuelState();
    alert("Duel successfully reset! Starting clean with $30,000 USD each.");
  } catch (err) {
    alert("Error resetting duel: " + err.message);
  }
}

