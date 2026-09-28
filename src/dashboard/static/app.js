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
    if (sm.jurisdiction_match) badges.push(`<span class="badge" style="background:#7c3aed; color:#fff;" title="High Congressional Committee Jurisdiction Match">🏛️ Committee Match</span>`);
    else if (sm.politician_buy) badges.push(`<span title="Recent US Congress Buy">🏛️ Congress</span>`);
    if (sm.insider_cluster) badges.push(`<span title="Executive Cluster Buy">👔 ClusterBuy</span>`);
    else if (sm.insider_buy) badges.push(`<span title="Insider Buy">👔 Insider</span>`);
    if (sm.is_pelosi_effect) badges.push(`<span class="badge" style="background:#ea580c; color:#fff;" title="Active Pelosi Effect Viral Retail Herd">🔥 Pelosi Effect</span>`);
    else if (sm.sentiment_label === "BULLISH") badges.push(`<span title="Positive News Velocity">💬 Bullish</span>`);
    if (sm.contracts && sm.contracts.has_major_contract) badges.push(`<span class="badge" style="background:#059669; color:#fff;" title="Prime US Federal Government Contractor ($25M+ Awards)">🛡️ Fed Contract</span>`);

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
  container.innerHTML = `<div style="text-align:center; padding: 60px; color:#94a3b8; font-size:15px;">🔍 Gathering forensic smart-money, government contracts, and wave technicals for <strong>${ticker}</strong>...</div>`;

  try {
    const res = await fetch(`/api/stock/${ticker}`);
    const data = await res.json();

    const chgSign = data.change_pct >= 0 ? "+" : "";
    const chgColor = data.change_pct >= 0 ? "#10b981" : "#f43f5e";

    const tech = data.technicals || {};
    const sm = data.smart_money || {};
    const pe = sm.pelosi_effect || {};
    const fed = sm.contracts || {};

    const checks = data.checks || [];
    const checksHtml = checks.map(c => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #1e293b; font-size:13px;">
        <span>${c.passed ? "✅" : "❌"} <strong>${c.rule}</strong></span>
        <span style="color:#94a3b8; font-family:monospace; font-size:12px;">${c.detail}</span>
      </div>
    `).join("");

    const ignBadge = data.is_ignition
      ? `<span class="badge badge-ignition" style="background:#059669; color:#fff; font-size:11px;">🚀 DAY-1 IGNITION (${data.ignition_type})</span>`
      : `<span class="badge" style="background:#1e293b; color:#94a3b8; font-size:11px;">⏳ SETUP FORMING</span>`;

    const scoreClass = data.composite_score >= 80 ? "score-high" : (data.composite_score >= 60 ? "score-med" : "score-low");

    // Pillar 1: Congress Trades Table
    const congressTrades = sm.congress_trades || [];
    let congressTradesHtml = "";
    if (congressTrades.length > 0) {
      congressTradesHtml = `
        <div class="forensic-scroll-box" style="margin-top:10px;">
          <table class="forensic-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Politician</th>
                <th>Chamber / State</th>
                <th>Committees</th>
                <th>Type</th>
                <th>Trade Size</th>
                <th>Jurisdiction</th>
              </tr>
            </thead>
            <tbody>
              ${congressTrades.map(t => {
                const isBuy = t.type === "BUY";
                const typeBadge = isBuy 
                  ? `<span class="badge" style="background:#064e3b; color:#34d399; font-weight:700;">BUY</span>` 
                  : `<span class="badge" style="background:#881337; color:#fb7185; font-weight:700;">SELL</span>`;
                const jurBadge = t.jurisdiction_match 
                  ? `<span class="badge-committee">🎯 High Tech Alpha</span>` 
                  : `<span style="color:#64748b; font-size:11px;">Standard</span>`;
                return `
                  <tr>
                    <td style="white-space:nowrap;">
                      <strong>${t.traded_date || "-"}</strong><br>
                      <span style="font-size:10px; color:#64748b;">Filed: ${t.published_date || "-"}</span>
                    </td>
                    <td><strong style="color:#f8fafc;">${t.politician_name || t.politician}</strong></td>
                    <td style="font-size:11px; color:#94a3b8;">${t.chamber || "Congress"} (${t.party || ""}-${t.state || ""})</td>
                    <td style="font-size:11px; color:#cbd5e1; max-width:180px;">${(t.committees || []).join(", ") || "-"}</td>
                    <td>${typeBadge}</td>
                    <td style="font-weight:600; font-family:monospace; color:#38bdf8;">${t.size || "-"}</td>
                    <td>${jurBadge}</td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      congressTradesHtml = `
        <div style="background:#0f172a; padding:16px; border-radius:8px; border:1px solid #1e293b; color:#94a3b8; font-size:12px; margin-top:10px;">
          No direct STOCK Act purchases or sales reported by members of the US Congress in the past 90 days.
        </div>
      `;
    }

    // Pillar 2: Insider Transactions Table
    const insiderTx = sm.recent_transactions && sm.recent_transactions.length > 0 
      ? sm.recent_transactions 
      : (sm.recent_buys || []);
    let insiderTxHtml = "";
    if (insiderTx.length > 0) {
      insiderTxHtml = `
        <div class="forensic-scroll-box" style="margin-top:10px;">
          <table class="forensic-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Insider</th>
                <th>Title / Role</th>
                <th>Type</th>
                <th>Shares</th>
                <th>Total Value ($)</th>
              </tr>
            </thead>
            <tbody>
              ${insiderTx.map(t => {
                const isBuy = t.type === "BUY";
                const typeColor = isBuy ? "#34d399" : (t.type === "SELL" ? "#fb7185" : "#94a3b8");
                return `
                  <tr>
                    <td style="white-space:nowrap; font-size:11px;">${t.date || "-"}</td>
                    <td><strong style="color:#f8fafc;">${t.insider || "-"}</strong></td>
                    <td style="font-size:11px; color:#94a3b8;">${t.position || "Director / Officer"}</td>
                    <td style="font-weight:700; color:${typeColor};">${t.type}</td>
                    <td style="font-family:monospace;">${(t.shares || 0).toLocaleString()}</td>
                    <td style="font-weight:700; font-family:monospace; color:#38bdf8;">$${(t.value_usd || 0).toLocaleString()}</td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      insiderTxHtml = `
        <div style="background:#0f172a; padding:16px; border-radius:8px; border:1px solid #1e293b; color:#94a3b8; font-size:12px; margin-top:10px;">
          No open-market SEC Form 4 insider transactions recorded in the evaluated window.
        </div>
      `;
    }

    // Pillar 3: Federal Contracts Table
    const fedContracts = fed.recent_contracts || [];
    let fedContractsHtml = "";
    if (fedContracts.length > 0) {
      fedContractsHtml = `
        <div class="forensic-scroll-box" style="margin-top:10px;">
          <table class="forensic-table">
            <thead>
              <tr>
                <th>Action Date</th>
                <th>Award ID</th>
                <th>Recipient Entity</th>
                <th>Amount ($ USD)</th>
                <th>Awarding Agency</th>
                <th>Procurement Scope</th>
              </tr>
            </thead>
            <tbody>
              ${fedContracts.map(c => `
                <tr>
                  <td style="white-space:nowrap; font-size:11px;">${c.action_date || "Active"}</td>
                  <td style="font-family:monospace; font-size:11px; color:#38bdf8;">${c.award_id || "-"}</td>
                  <td style="font-size:11px; color:#f8fafc;">${c.recipient || "-"}</td>
                  <td style="font-weight:700; font-family:monospace; color:#10b981;">$${(c.amount_usd || 0).toLocaleString()}</td>
                  <td style="font-size:11px; color:#cbd5e1;">${c.agency || ""}${c.sub_agency ? ' - ' + c.sub_agency : ''}</td>
                  <td style="font-size:11px; color:#94a3b8; max-width:220px;" title="${c.description || ''}">${(c.description || "Technology Procurement").substring(0, 75)}...</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      fedContractsHtml = `
        <div style="background:#0f172a; padding:16px; border-radius:8px; border:1px solid #1e293b; color:#94a3b8; font-size:12px; margin-top:10px;">
          No prime US Federal Government awards recorded on USASpending.gov in past 24 months.
        </div>
      `;
    }

    // Pillar 4: Pelosi Effect & Retail Stream Details
    const quotesList = pe.verbatim_quotes && pe.verbatim_quotes.length > 0
      ? pe.verbatim_quotes.map(q => `<li style="margin-bottom:6px; color:#cbd5e1;"><em>"${q}"</em></li>`).join("")
      : `<li style="color:#94a3b8;">No direct copy-trading quotes captured.</li>`;

    const buzzBadges = (sm.buzz_keywords || []).map(k => `
      <span class="badge" style="background:#0f172a; border:1px solid #334155; color:#38bdf8; font-size:10px; margin-right:4px;">#${k}</span>
    `).join("");

    const headlinesList = (sm.recent_headlines || []).slice(0, 3).map(h => `
      <li style="margin-bottom:4px; font-size:12px;">
        <span style="color:#cbd5e1;">${h.title}</span> 
        <span class="badge" style="font-size:9px; background:${h.sentiment === 'BULLISH' ? '#064e3b' : (h.sentiment === 'BEARISH' ? '#881337' : '#1e293b')}; color:#fff;">${h.sentiment}</span>
      </li>
    `).join("");

    // Assemble the complete Deep-Dive HTML
    container.innerHTML = `
      <!-- 1. Hero Stock Header Banner -->
      <div class="deepdive-hero">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; margin-bottom:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px; flex-wrap:wrap;">
              <h2 style="font-size:28px; font-weight:800; color:#38bdf8; margin:0;">${data.ticker}</h2>
              <span style="font-size:18px; font-weight:700; color:#f8fafc;">${data.name || data.ticker}</span>
              <span class="badge" style="background:#1e293b; color:#94a3b8; font-size:11px;">${data.category || "Tech"}</span>
              ${data.role ? `<span class="badge" style="background:#0f172a; border:1px solid #334155; color:#38bdf8; font-size:11px;">${data.role}</span>` : ''}
            </div>
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <span style="font-size:26px; font-weight:800; color:#fff;">$${data.current_price.toFixed(2)}</span>
              <span style="font-size:16px; font-weight:700; color:${chgColor};">${chgSign}${data.change_pct.toFixed(2)}%</span>
              <span style="font-size:12px; color:#94a3b8;">As of Bar Date: <strong>${data.date}</strong></span>
              ${tech.high ? `<span style="font-size:12px; color:#64748b;">(Day Range: $${tech.low.toFixed(2)} - $${tech.high.toFixed(2)})</span>` : ''}
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
            <div style="text-align:right;">
              <div style="font-size:11px; color:#94a3b8; text-transform:uppercase;">Day-1 Wave Ignition</div>
              <div style="margin-top:2px;">${ignBadge}</div>
            </div>
            <div style="text-align:right; background:#0f172a; padding:8px 14px; border-radius:8px; border:1px solid #1e293b;">
              <div style="font-size:11px; color:#94a3b8; text-transform:uppercase;">P(Wave Win)</div>
              <div style="font-size:20px; font-weight:800; color:#10b981;">${data.wave_probability.toFixed(1)}%</div>
            </div>
            <div style="text-align:right; background:#0f172a; padding:8px 14px; border-radius:8px; border:1px solid #1e293b;">
              <div style="font-size:11px; color:#94a3b8; text-transform:uppercase;">Composite Score</div>
              <div style="font-size:20px; font-weight:800; color:#38bdf8;"><span class="score-badge ${scoreClass}">${data.composite_score}</span></div>
            </div>
          </div>
        </div>

        <!-- Actionable Bracket Bar -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px; background:#0f172a; padding:14px; border-radius:8px; border:1px solid #1e293b;">
          <div>
            <span style="font-size:11px; color:#94a3b8; font-weight:600;">🛑 STOP LOSS (-2.5%)</span>
            <div style="font-size:18px; font-weight:800; color:#f43f5e; margin-top:2px;">$${data.stop_loss.toFixed(2)}</div>
            <span style="font-size:10px; color:#64748b;">Hard Risk Floor</span>
          </div>
          <div>
            <span style="font-size:11px; color:#94a3b8; font-weight:600;">📉 5 EMA TRAIL FLOOR</span>
            <div style="font-size:18px; font-weight:800; color:#c084fc; margin-top:2px;">$${tech.ema5 ? tech.ema5.toFixed(2) : "-"}</div>
            <span style="font-size:10px; color:#64748b;">Trailing Protection</span>
          </div>
          <div>
            <span style="font-size:11px; color:#94a3b8; font-weight:600;">🎯 TARGET 1 (+3.5%)</span>
            <div style="font-size:18px; font-weight:800; color:#10b981; margin-top:2px;">$${data.target_1.toFixed(2)}</div>
            <span style="font-size:10px; color:#64748b;">Scale 50% Profit</span>
          </div>
          <div>
            <span style="font-size:11px; color:#94a3b8; font-weight:600;">🚀 TARGET 2 (+6.0%)</span>
            <div style="font-size:18px; font-weight:800; color:#34d399; margin-top:2px;">$${data.target_2.toFixed(2)}</div>
            <span style="font-size:10px; color:#64748b;">Runner Target</span>
          </div>
          <div>
            <span style="font-size:11px; color:#94a3b8; font-weight:600;">⚖️ REWARD / RISK</span>
            <div style="font-size:18px; font-weight:800; color:#38bdf8; margin-top:2px;">1.4x / 2.4x</div>
            <span style="font-size:10px; color:#64748b;">T1 / T2 R-Multiples</span>
          </div>
        </div>
      </div>

      <!-- 2. The 4 Pillars Institutional Scorecard -->
      <div class="pillar-scorecard-grid">
        <!-- Pillar 1 -->
        <div class="pillar-kpi-card" style="border-top:3px solid #7c3aed;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:12px; font-weight:700; color:#c084fc;">🏛️ CAPITOL HILL & COMMITTEES</span>
              <span style="font-size:16px; font-weight:800; color:#fff;">${sm.congress_score || 0} <span style="font-size:11px; color:#94a3b8;">/100</span></span>
            </div>
            <div style="font-size:13px; font-weight:700; margin-top:6px; color:${sm.jurisdiction_match ? '#c084fc' : (sm.politician_buy ? '#34d399' : (sm.congress_sell_count > 0 ? '#fb7185' : '#94a3b8'))};">
              ${sm.jurisdiction_match ? '🎯 HIGH JURISDICTION MATCH' : (sm.politician_buy ? '✅ RECENT CONGRESS BUY' : (sm.congress_sell_count > 0 ? '⚠️ NET SELLING DETECTED' : 'No Recent Activity'))}
            </div>
          </div>
          <div style="font-size:11px; color:#94a3b8;">
            ${sm.high_jurisdiction_buyers && sm.high_jurisdiction_buyers.length > 0 ? `Key Member: <strong style="color:#e2e8f0;">${sm.high_jurisdiction_buyers.join(', ')}</strong>` : `${sm.congress_buy_count || 0} Buys / ${sm.congress_sell_count || 0} Sells`}
          </div>
        </div>

        <!-- Pillar 2 -->
        <div class="pillar-kpi-card" style="border-top:3px solid #0284c7;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:12px; font-weight:700; color:#38bdf8;">👔 C-SUITE & INSIDERS</span>
              <span style="font-size:16px; font-weight:800; color:#fff;">${sm.insider_score || 0} <span style="font-size:11px; color:#94a3b8;">/100</span></span>
            </div>
            <div style="font-size:13px; font-weight:700; margin-top:6px; color:${sm.total_buy_value_usd > 1000000 ? '#38bdf8' : (sm.insider_cluster ? '#34d399' : (sm.insider_buy ? '#34d399' : '#94a3b8'))};">
              ${sm.total_buy_value_usd > 1000000 ? '🐋 WHALE C-SUITE BUY' : (sm.insider_cluster ? '👔 EXECUTIVE CLUSTER BUY' : (sm.insider_buy ? '✅ DIRECT CASH PURCHASE' : 'Routine Sales / Neutral'))}
            </div>
          </div>
          <div style="font-size:11px; color:#94a3b8;">
            ${sm.total_buy_value_usd > 0 ? `Total Cash: <strong style="color:#34d399;">$${sm.total_buy_value_usd.toLocaleString()}</strong>` : `${sm.insider_sell_count || 0} Open-Market Sells`}
          </div>
        </div>

        <!-- Pillar 3 -->
        <div class="pillar-kpi-card" style="border-top:3px solid #059669;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:12px; font-weight:700; color:#34d399;">🛡️ FEDERAL CONTRACTS</span>
              <span style="font-size:16px; font-weight:800; color:#fff;">${fed.contract_score || 0} <span style="font-size:11px; color:#94a3b8;">/100</span></span>
            </div>
            <div style="font-size:13px; font-weight:700; margin-top:6px; color:${fed.is_defense_contract ? '#f43f5e' : (fed.has_major_contract ? '#34d399' : '#94a3b8')};">
              ${fed.is_defense_contract ? '🛡️ DoD / DEFENSE STRATEGIC' : (fed.has_major_contract ? '🏛️ PRIME US CONTRACTOR' : 'Commercial / Low Fed')}
            </div>
          </div>
          <div style="font-size:11px; color:#94a3b8;">
            ${fed.total_value_usd > 0 ? `Active: <strong style="color:#34d399;">$${fed.total_value_usd >= 1000000000 ? (fed.total_value_usd / 1000000000).toFixed(2) + 'B' : (fed.total_value_usd / 1000000).toFixed(1) + 'M'} USD</strong>` : 'No direct prime contracts'}
          </div>
        </div>

        <!-- Pillar 4 -->
        <div class="pillar-kpi-card" style="border-top:3px solid #ea580c;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:12px; font-weight:700; color:#fb923c;">🔥 THE PELOSI EFFECT</span>
              <span style="font-size:16px; font-weight:800; color:#fff;">${sm.retail_hype_score || 0} <span style="font-size:11px; color:#94a3b8;">/100</span></span>
            </div>
            <div style="font-size:13px; font-weight:700; margin-top:6px; color:${pe.is_active ? '#fb923c' : (sm.viral_politician_buzz ? '#38bdf8' : '#94a3b8')};">
              ${pe.is_active ? '🔥 ' + (pe.intensity || 'ACTIVE') : (sm.viral_politician_buzz ? '⚡ SMART-MONEY BUZZ' : 'Dormant Streams')}
            </div>
          </div>
          <div style="font-size:11px; color:#94a3b8;">
            ${pe.primary_catalyst ? `Catalyst: <strong style="color:#e2e8f0;">${pe.primary_catalyst}</strong>` : `Sentiment: <strong style="color:#34d399;">${sm.sentiment_label || 'NEUTRAL'}</strong>`}
          </div>
        </div>
      </div>

      <!-- 3. Main Split Grid -->
      <div class="deepdive-main-grid">
        <!-- LEFT COLUMN: Technical Wave Diagnostics & Chart -->
        <div>
          <div class="card-box">
            <h3 style="display:flex; justify-content:space-between; align-items:center;">
              <span>📈 60-Day Momentum Trajectory</span>
              <span style="font-size:12px; color:#94a3b8;">Daily Closes + 5 EMA Trailing Floor</span>
            </h3>
            <canvas id="deepDiveCanvas" height="175"></canvas>
          </div>

          <div class="card-box">
            <h3>⚡ Day-1 Wave Ignition Rule Checklist</h3>
            <div style="display:flex; flex-direction:column; gap:4px;">
              ${checksHtml || "<div style='color:#94a3b8;'>No rule check data available.</div>"}
            </div>
          </div>

          <div class="card-box">
            <h3>📊 Quantitative Feature Snapshot</h3>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">
              <div style="background:#0f172a; padding:10px; border-radius:6px; border:1px solid #1e293b;">
                <span style="font-size:11px; color:#94a3b8;">Relative Volume (20D)</span><br>
                <strong style="color:${tech.rvol_20d >= 1.5 ? '#10b981' : '#f8fafc'}; font-size:16px;">${tech.rvol_20d ? tech.rvol_20d.toFixed(2) + 'x' : '-'}</strong>
              </div>
              <div style="background:#0f172a; padding:10px; border-radius:6px; border:1px solid #1e293b;">
                <span style="font-size:11px; color:#94a3b8;">Close Range Ratio (CRR)</span><br>
                <strong style="color:${tech.crr >= 0.68 ? '#10b981' : '#f8fafc'}; font-size:16px;">${tech.crr ? tech.crr.toFixed(2) : '-'}</strong>
              </div>
              <div style="background:#0f172a; padding:10px; border-radius:6px; border:1px solid #1e293b;">
                <span style="font-size:11px; color:#94a3b8;">Bollinger Band Width</span><br>
                <strong style="color:#38bdf8; font-size:16px;">${tech.bb_width ? tech.bb_width.toFixed(3) : '-'}</strong>
              </div>
              <div style="background:#0f172a; padding:10px; border-radius:6px; border:1px solid #1e293b;">
                <span style="font-size:11px; color:#94a3b8;">Volume vs 20D SMA</span><br>
                <strong style="color:#f8fafc; font-size:14px;">${tech.volume ? (tech.volume / 1000000).toFixed(1) + 'M' : '-'} / ${tech.vol_sma20 ? (tech.vol_sma20 / 1000000).toFixed(1) + 'M' : '-'}</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN: Deep Forensic Smart Money Dossiers -->
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- Pillar 1 Dossier -->
          <div class="card-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <h3 style="margin:0;">🏛️ US Congressional Activity & Committee Oversight (STOCK Act)</h3>
              <span class="badge" style="background:#7c3aed; color:#fff; font-size:11px;">Score: ${sm.congress_score || 0}/100</span>
            </div>
            ${sm.jurisdiction_match ? `
              <div style="background:rgba(124, 58, 237, 0.15); border:1px solid #7c3aed; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
                <strong style="color:#c084fc;">🎯 High Committee Oversight Match:</strong>
                <span style="font-size:12px; color:#e2e8f0;">${(sm.matched_committees || []).join(', ') || 'Tech & Commerce'}. Trade receives a <strong>2.5x conviction multiplier</strong> due to direct legislative jurisdiction over semiconductors and critical tech.</span>
              </div>
            ` : ''}
            <div style="display:flex; gap:16px; font-size:12px; color:#94a3b8; margin-bottom:8px;">
              <span>Buys: <strong style="color:#34d399;">${sm.congress_buy_count || 0}</strong></span>
              <span>Sells: <strong style="color:#fb7185;">${sm.congress_sell_count || 0}</strong></span>
              <span>Total Filings: <strong style="color:#f8fafc;">${sm.congress_total_trades || 0}</strong></span>
            </div>
            ${congressTradesHtml}
          </div>

          <!-- Pillar 2 Dossier -->
          <div class="card-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <h3 style="margin:0;">👔 Corporate C-Suite & SEC Form 4 Insider Conviction</h3>
              <span class="badge" style="background:#0284c7; color:#fff; font-size:11px;">Score: ${sm.insider_score || 0}/100</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; background:#0f172a; padding:10px 14px; border-radius:8px; border:1px solid #1e293b; margin-bottom:10px; font-size:12px;">
              <div>
                <span style="color:#94a3b8;">Total Buy Value:</span> 
                <strong style="color:#34d399; font-size:14px;">$${(sm.total_buy_value_usd || 0).toLocaleString()}</strong>
              </div>
              <div>
                <span style="color:#94a3b8;">Cluster Buying:</span> 
                <strong style="color:${sm.insider_cluster ? '#34d399' : '#94a3b8'};">${sm.insider_cluster ? "YES (2+ Insiders)" : "No"}</strong>
              </div>
              <div>
                <span style="color:#94a3b8;">Unique Buyers:</span> 
                <strong style="color:#f8fafc;">${sm.unique_buyers || 0}</strong>
              </div>
            </div>
            ${sm.c_suite_buyers && sm.c_suite_buyers.length > 0 ? `
              <div style="font-size:12px; margin-bottom:8px;">
                <span style="color:#94a3b8;">C-Suite / Key Buyers:</span> 
                <strong style="color:#38bdf8;">${sm.c_suite_buyers.join(' • ')}</strong>
              </div>
            ` : ''}
            ${insiderTxHtml}
          </div>

          <!-- Pillar 3 Dossier -->
          <div class="card-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <h3 style="margin:0;">🛡️ US Federal Government Prime Contracts (USASpending.gov)</h3>
              <span class="badge" style="background:#059669; color:#fff; font-size:11px;">Score: ${fed.contract_score || 0}/100</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; background:#0f172a; padding:10px 14px; border-radius:8px; border:1px solid #1e293b; margin-bottom:10px; font-size:12px;">
              <div>
                <span style="color:#94a3b8;">Active Awards:</span> 
                <strong style="color:#10b981; font-size:14px;">$${fed.total_value_usd >= 1000000000 ? (fed.total_value_usd / 1000000000).toFixed(2) + 'B' : (fed.total_value_usd / 1000000).toFixed(1) + 'M'} USD</strong>
              </div>
              <div>
                <span style="color:#94a3b8;">Top Single Award:</span> 
                <strong style="color:#38bdf8;">$${(fed.top_award_amount_usd / 1000000).toFixed(1)}M</strong>
              </div>
              <div>
                ${fed.is_defense_contract ? '<span class="badge-defense">🛡️ DoD / Defense Strategic</span>' : '<span style="color:#94a3b8;">Commercial Tech</span>'}
              </div>
            </div>
            ${fed.top_agencies && fed.top_agencies.length > 0 ? `
              <div style="font-size:12px; margin-bottom:8px;">
                <span style="color:#94a3b8;">Procuring Agencies:</span> 
                <strong style="color:#e2e8f0;">${fed.top_agencies.join(', ')}</strong>
              </div>
            ` : ''}
            ${fedContractsHtml}
          </div>

          <!-- Pillar 4 Dossier -->
          <div class="card-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <h3 style="margin:0;">🔥 The Pelosi Effect & Viral Retail Social Streams</h3>
              <span class="badge" style="background:#ea580c; color:#fff; font-size:11px;">Hype Score: ${sm.retail_hype_score || 0}/100</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap;">
              ${pe.is_active ? `<span class="badge-pelosi-viral">🔥 ACTIVE (${pe.intensity || 'VIRAL'})</span>` : (sm.viral_politician_buzz ? `<span class="badge" style="background:#0284c7; color:#fff; font-size:11px;">⚡ Emerging Smart-Money Buzz</span>` : `<span class="badge" style="background:#334155; color:#94a3b8; font-size:11px;">Quiet / Dormant</span>`)}
              ${pe.primary_catalyst ? `<span class="badge" style="background:#0284c7; color:#fff; font-size:10px;">${pe.primary_catalyst}</span>` : ''}
              ${pe.lifecycle_stage ? `<span class="badge" style="background:#7c3aed; color:#fff; font-size:10px;">${pe.lifecycle_stage}</span>` : ''}
              <span class="badge" style="background:#1e293b; color:#34d399; font-size:10px;">Tape: ${sm.sentiment_label || 'NEUTRAL'}</span>
            </div>
            ${pe.prominent_figures && pe.prominent_figures.length > 0 ? `
              <div style="font-size:12px; margin-bottom:6px;">
                <span style="color:#94a3b8;">Prominent Figures Cited:</span> 
                <strong style="color:#f8fafc;">${pe.prominent_figures.join(', ')}</strong>
              </div>
            ` : ''}
            ${pe.narrative_summary ? `
              <p style="font-size:12px; color:#cbd5e1; background:#0f172a; padding:10px 14px; border-radius:6px; border-left:3px solid #f59e0b; margin:8px 0; line-height:1.5;">
                ${pe.narrative_summary}
              </p>
            ` : ''}
            ${pe.verbatim_quotes && pe.verbatim_quotes.length > 0 ? `
              <div style="font-size:12px; margin-top:10px;">
                <strong style="color:#94a3b8;">Live Trader Stream Quotes:</strong>
                <ul style="padding-left:16px; margin:6px 0 0 0; font-size:11px;">
                  ${quotesList}
                </ul>
              </div>
            ` : ''}
            ${buzzBadges ? `
              <div style="margin-top:10px;">
                <span style="font-size:11px; color:#64748b; margin-right:6px;">Buzz Keywords:</span>
                ${buzzBadges}
              </div>
            ` : ''}
            ${headlinesList ? `
              <div style="margin-top:10px; border-top:1px solid #1e293b; padding-top:8px;">
                <span style="font-size:11px; color:#94a3b8; font-weight:700;">Analyzed Financial Headlines:</span>
                <ul style="padding-left:14px; margin:4px 0 0 0;">
                  ${headlinesList}
                </ul>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;

    renderDeepDiveChart(data.history, data.target_1, data.target_2, data.stop_loss);
  } catch (err) {
    container.innerHTML = `<div style="text-align:center; color:#f43f5e; padding: 40px; font-size:15px;">Failed to load deep-dive for ${ticker}: ${err}</div>`;
  }
}

function renderDeepDiveChart(history, t1, t2, sl) {
  const ctx = document.getElementById("deepDiveCanvas").getContext("2d");
  if (deepDiveChart) deepDiveChart.destroy();

  const labels = history.map(h => h.date);
  const closes = history.map(h => h.close);
  const ema5 = history.map(h => h.ema5);
  const ema20 = history.map(h => h.ema20);

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
          backgroundColor: "rgba(56, 189, 248, 0.08)",
          borderWidth: 2,
          fill: true,
          tension: 0.15
        },
        {
          label: "5 EMA (Trailing Floor)",
          data: ema5,
          borderColor: "#c084fc",
          borderWidth: 1.5,
          borderDash: [4, 4],
          fill: false,
          pointRadius: 0
        },
        {
          label: "20 EMA (Trend Anchor)",
          data: ema20,
          borderColor: "#3b82f6",
          borderWidth: 1.2,
          borderDash: [2, 2],
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
          label: "Target 2 (+6.0%)",
          data: t2Line,
          borderColor: "#34d399",
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
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { size: 10 } } }
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

  const botAutoSub = document.getElementById("bot-auto-sub");
  if (botAutoSub) {
    const lastEval = b.last_evaluated_at || "Just Initialized";
    botAutoSub.textContent = `🟢 Auto-Evaluator Active • Last: ${lastEval}`;
  }
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

