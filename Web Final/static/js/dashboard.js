/* ═══════════════════════════════════════════════════════════════════════════
   TerraAI – Dashboard JS
════════════════════════════════════════════════════════════════════════════ */

"use strict";

// ── Tab navigation ────────────────────────────────────────────────────────────
document.querySelectorAll(".dash-nav-item[data-tab]").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    const tab = item.dataset.tab;
    document.querySelectorAll(".dash-nav-item").forEach((i) => i.classList.remove("active"));
    document.querySelectorAll(".dash-tab").forEach((t) => t.classList.remove("active"));
    item.classList.add("active");
    document.getElementById(`tab-${tab}`)?.classList.add("active");
  });
});

// ── Crop profiles data ────────────────────────────────────────────────────────
const CROP_PROFILES = [
  { name:"Rice",        emoji:"🌾", N:80,  P:40,  K:40,  temp:25, hum:82, ph:6.5, rain:200 },
  { name:"Maize",       emoji:"🌽", N:80,  P:40,  K:20,  temp:22, hum:65, ph:6.0, rain:85  },
  { name:"Chickpea",    emoji:"🫘", N:40,  P:67,  K:79,  temp:18, hum:16, ph:7.0, rain:80  },
  { name:"KidneyBeans", emoji:"🫘", N:20,  P:67,  K:20,  temp:20, hum:22, ph:5.7, rain:105 },
  { name:"PigeonPeas",  emoji:"🌿", N:20,  P:67,  K:20,  temp:27, hum:48, ph:5.8, rain:150 },
  { name:"MothBeans",   emoji:"🌱", N:20,  P:40,  K:20,  temp:28, hum:53, ph:6.9, rain:51  },
  { name:"MungBean",    emoji:"🌱", N:20,  P:40,  K:20,  temp:29, hum:85, ph:6.7, rain:48  },
  { name:"Blackgram",   emoji:"🌿", N:40,  P:67,  K:19,  temp:30, hum:65, ph:7.1, rain:67  },
  { name:"Lentil",      emoji:"🫘", N:18,  P:68,  K:19,  temp:24, hum:65, ph:6.9, rain:45  },
  { name:"Pomegranate", emoji:"🍎", N:18,  P:18,  K:40,  temp:21, hum:90, ph:6.5, rain:107 },
  { name:"Banana",      emoji:"🍌", N:100, P:82,  K:50,  temp:27, hum:80, ph:5.8, rain:105 },
  { name:"Mango",       emoji:"🥭", N:20,  P:27,  K:30,  temp:31, hum:50, ph:5.7, rain:95  },
  { name:"Grapes",      emoji:"🍇", N:23,  P:132, K:200, temp:24, hum:82, ph:6.0, rain:70  },
  { name:"Watermelon",  emoji:"🍉", N:99,  P:17,  K:50,  temp:25, hum:85, ph:6.5, rain:50  },
  { name:"Muskmelon",   emoji:"🍈", N:100, P:17,  K:50,  temp:28, hum:92, ph:6.3, rain:25  },
  { name:"Apple",       emoji:"🍎", N:21,  P:134, K:199, temp:22, hum:92, ph:5.9, rain:113 },
  { name:"Orange",      emoji:"🍊", N:20,  P:16,  K:10,  temp:23, hum:92, ph:7.0, rain:110 },
  { name:"Papaya",      emoji:"🍈", N:49,  P:59,  K:50,  temp:34, hum:92, ph:6.7, rain:143 },
  { name:"CoconutTree", emoji:"🥥", N:22,  P:16,  K:30,  temp:27, hum:94, ph:5.9, rain:175 },
  { name:"Cotton",      emoji:"🌸", N:117, P:46,  K:19,  temp:24, hum:80, ph:6.9, rain:80  },
  { name:"Jute",        emoji:"🌿", N:78,  P:46,  K:40,  temp:25, hum:80, ph:6.5, rain:175 },
  { name:"Coffee",      emoji:"☕", N:101, P:28,  K:29,  temp:25, hum:58, ph:6.8, rain:158 },
];

// ── Render crop profiles tab ──────────────────────────────────────────────────
function renderCropProfiles() {
  const grid = document.getElementById("cropProfilesGrid");
  if (!grid) return;
  grid.innerHTML = CROP_PROFILES.map((c) => `
    <div class="crop-profile-card">
      <div class="cp-header">
        <span class="cp-emoji">${c.emoji}</span>
        <span class="cp-name">${c.name}</span>
      </div>
      <div class="cp-params">
        <div class="cp-param"><span class="cp-param-label">Nitrogen (N)</span><span class="cp-param-value">${c.N} kg/ha</span></div>
        <div class="cp-param"><span class="cp-param-label">Phosphorus (P)</span><span class="cp-param-value">${c.P} kg/ha</span></div>
        <div class="cp-param"><span class="cp-param-label">Potassium (K)</span><span class="cp-param-value">${c.K} kg/ha</span></div>
        <div class="cp-param"><span class="cp-param-label">Temperature</span><span class="cp-param-value">${c.temp}°C</span></div>
        <div class="cp-param"><span class="cp-param-label">Humidity</span><span class="cp-param-value">${c.hum}%</span></div>
        <div class="cp-param"><span class="cp-param-label">pH</span><span class="cp-param-value">${c.ph}</span></div>
        <div class="cp-param"><span class="cp-param-label">Rainfall</span><span class="cp-param-value">${c.rain}mm</span></div>
      </div>
    </div>
  `).join("");
}
renderCropProfiles();

// ═══════════════════════════════════════════════════════════════════════════
// CHARTS  — fixed-height wrappers prevent infinite expansion
// ═══════════════════════════════════════════════════════════════════════════
const CHART_DEFAULTS = {
  color:     "rgba(255,255,255,0.7)",
  gridColor: "rgba(255,255,255,0.06)",
  font:      { family: "Inter, sans-serif", size: 11 },
};
Chart.defaults.color = CHART_DEFAULTS.color;
Chart.defaults.font  = CHART_DEFAULTS.font;

// Guard: only create each chart once
let _radarChart = null;
let _confChart  = null;

function initCharts() {
  // ── Radar chart ────────────────────────────────────────────────────────────
  const radarCtx = document.getElementById("soilRadarChart")?.getContext("2d");
  if (radarCtx && !_radarChart) {
    _radarChart = new Chart(radarCtx, {
      type: "radar",
      data: {
        labels: ["Nitrogen", "Phosphorus", "Potassium", "Temp", "Humidity", "pH", "Rainfall"],
        datasets: [
          {
            label: "Rice",
            data: [80, 40, 40, 25, 82, 65, 67],
            borderColor: "#00e676",
            backgroundColor: "rgba(0,230,118,0.1)",
            pointBackgroundColor: "#00e676",
            pointRadius: 3,
          },
          {
            label: "Cotton",
            data: [117, 46, 19, 24, 80, 69, 27],
            borderColor: "#40c4ff",
            backgroundColor: "rgba(64,196,255,0.1)",
            pointBackgroundColor: "#40c4ff",
            pointRadius: 3,
          },
          {
            label: "Coffee",
            data: [101, 28, 29, 25, 58, 68, 53],
            borderColor: "#ff9100",
            backgroundColor: "rgba(255,145,0,0.1)",
            pointBackgroundColor: "#ff9100",
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,   // wrapper div controls height
        animation: { duration: 600 },
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 12, padding: 16, font: { size: 11 } },
          },
        },
        scales: {
          r: {
            grid:        { color: CHART_DEFAULTS.gridColor },
            angleLines:  { color: CHART_DEFAULTS.gridColor },
            pointLabels: { font: { size: 10 }, color: "rgba(255,255,255,0.6)" },
            ticks:       { display: false, backdropColor: "transparent" },
            suggestedMin: 0,
            suggestedMax: 140,
          },
        },
      },
    });
  }

  // ── Confidence line chart ──────────────────────────────────────────────────
  const confCtx = document.getElementById("confChart")?.getContext("2d");
  if (confCtx && !_confChart) {
    const confData = [98.2,96.8,95.4,94.1,93.7,92.5,91.8,90.3,89.6,88.9,
                      87.4,86.2,85.7,84.3,83.1,82.6,81.4,80.9,79.5,78.3,77.1,76.4];
    _confChart = new Chart(confCtx, {
      type: "line",
      data: {
        labels: CROP_PROFILES.map((c) => c.name),
        datasets: [{
          label: "Avg Confidence %",
          data: confData,
          borderColor: "#00e676",
          backgroundColor: "rgba(0,230,118,0.08)",
          fill: true,
          tension: 0.4,
          pointBackgroundColor: "#00e676",
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600 },
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid:  { color: CHART_DEFAULTS.gridColor },
            ticks: { maxRotation: 45, font: { size: 9 } },
          },
          y: {
            grid: { color: CHART_DEFAULTS.gridColor },
            min: 70, max: 100,
          },
        },
      },
    });
  }
}

// Init charts once DOM is ready
initCharts();

// ═══════════════════════════════════════════════════════════════════════════
// DYNAMIC CROP INSIGHT PANEL
// ═══════════════════════════════════════════════════════════════════════════

// Cache: crop name → { explanation, gemini_powered }
const _insightCache = {};

// Last prediction data stored from sessionStorage (set by main.js after predict)
let _predictionData = null;

// Try to load last prediction from sessionStorage
function loadPredictionData() {
  try {
    const raw = sessionStorage.getItem("terraai_last_prediction");
    if (raw) _predictionData = JSON.parse(raw);
  } catch (_) {}
}
loadPredictionData();

// ── Parameter status helper ───────────────────────────────────────────────────
const PARAM_RANGES = {
  N:    { low: 20,  high: 80,  unit: "kg/ha", label: "Nitrogen"    },
  P:    { low: 20,  high: 80,  unit: "kg/ha", label: "Phosphorus"  },
  K:    { low: 20,  high: 80,  unit: "kg/ha", label: "Potassium"   },
  temp: { low: 15,  high: 35,  unit: "°C",    label: "Temperature" },
  hum:  { low: 30,  high: 80,  unit: "%",     label: "Humidity"    },
  ph:   { low: 5.5, high: 7.5, unit: "",      label: "Soil pH"     },
  rain: { low: 50,  high: 200, unit: "mm",    label: "Rainfall"    },
};

function getParamStatus(key, val) {
  const r = PARAM_RANGES[key];
  if (!r) return { status: "—", color: "#8899aa", pct: 50 };
  const v = parseFloat(val);
  if (isNaN(v)) return { status: "—", color: "#8899aa", pct: 50 };
  if (v < r.low)  return { status: "Low",     color: "#ff9100", pct: 25 };
  if (v > r.high) return { status: "High",    color: "#ff5252", pct: 85 };
                  return { status: "Optimal", color: "#00e676", pct: 60 };
}

// ── Recommendation badge logic ────────────────────────────────────────────────
function getRecommendationBadge(confidence) {
  if (confidence >= 85) return { label: "Highly Suitable",  color: "#00e676", icon: "fa-star" };
  if (confidence >= 65) return { label: "Recommended",      color: "#69f0ae", icon: "fa-thumbs-up" };
  if (confidence >= 45) return { label: "Moderate Match",   color: "#ffab40", icon: "fa-circle-half-stroke" };
                        return { label: "Low Match",         color: "#ff5252", icon: "fa-triangle-exclamation" };
}

function getSoilHealth(N, P, K, ph) {
  let score = 0;
  if (N  >= 20 && N  <= 120) score++;
  if (P  >= 10 && P  <= 130) score++;
  if (K  >= 10 && K  <= 200) score++;
  if (ph >= 5.5 && ph <= 7.5) score++;
  if (score === 4) return { label: "Excellent", color: "#00e676" };
  if (score === 3) return { label: "Good",       color: "#69f0ae" };
  if (score === 2) return { label: "Moderate",   color: "#ffab40" };
                  return { label: "Poor",        color: "#ff5252" };
}

// ── Render the insight panel for a given crop ─────────────────────────────────
async function renderInsightPanel(rec, rank, inputs) {
  const panel       = document.getElementById("insightPanel");
  const nameEl      = document.getElementById("insightCropName");
  const rankEl      = document.getElementById("insightRankBadge");
  const confEl      = document.getElementById("insightConfPill");
  const badgesEl    = document.getElementById("insightBadges");
  const paramsEl    = document.getElementById("insightParams");
  const aiTextEl    = document.getElementById("insightAiText");
  const aiBadgeEl   = document.getElementById("insightAiBadge");

  panel.style.display = "block";

  // Header
  nameEl.textContent = `${rec.emoji || "🌱"} ${rec.crop}`;
  rankEl.textContent = `#${rank}`;
  confEl.textContent = `${rec.confidence}%`;
  confEl.style.background = rec.confidence >= 70
    ? "linear-gradient(135deg,#00e676,#00b248)"
    : rec.confidence >= 45
      ? "linear-gradient(135deg,#ffab40,#ff6d00)"
      : "linear-gradient(135deg,#ff5252,#c62828)";

  // Recommendation + soil health badges
  const recBadge  = getRecommendationBadge(rec.confidence);
  const N  = parseFloat(inputs.N  || 0);
  const P  = parseFloat(inputs.P  || 0);
  const K  = parseFloat(inputs.K  || 0);
  const ph = parseFloat(inputs.ph || 6.5);
  const soilHealth = getSoilHealth(N, P, K, ph);

  badgesEl.innerHTML = `
    <span class="insight-badge" style="background:${recBadge.color}22;border-color:${recBadge.color}55;color:${recBadge.color}">
      <i class="fas ${recBadge.icon}"></i> ${recBadge.label}
    </span>
    <span class="insight-badge" style="background:${soilHealth.color}22;border-color:${soilHealth.color}55;color:${soilHealth.color}">
      <i class="fas fa-layer-group"></i> Soil Health: ${soilHealth.label}
    </span>
  `;

  // Parameter status bars
  const paramMap = [
    { key: "N",    val: inputs.N          },
    { key: "P",    val: inputs.P          },
    { key: "K",    val: inputs.K          },
    { key: "temp", val: inputs.temperature },
    { key: "hum",  val: inputs.humidity   },
    { key: "ph",   val: inputs.ph         },
    { key: "rain", val: inputs.rainfall   },
  ];
  paramsEl.innerHTML = paramMap.map(({ key, val }) => {
    const r   = PARAM_RANGES[key];
    const s   = getParamStatus(key, val);
    const num = parseFloat(val) || 0;
    return `
      <div class="insight-param-row">
        <div class="insight-param-label">${r.label}</div>
        <div class="insight-param-bar-wrap">
          <div class="insight-param-bar">
            <div class="insight-param-fill" style="width:${s.pct}%;background:${s.color}"></div>
          </div>
        </div>
        <div class="insight-param-val">${num}${r.unit}</div>
        <div class="insight-param-status" style="color:${s.color}">${s.status}</div>
      </div>
    `;
  }).join("");

  // AI explanation — show loading, then fetch (with cache)
  const cacheKey = `${rec.crop}_${rec.confidence}`;
  if (_insightCache[cacheKey]) {
    // Instant from cache — no API call
    const cached = _insightCache[cacheKey];
    renderAiText(aiTextEl, aiBadgeEl, cached.explanation, cached.gemini_powered);
    return;
  }

  // Show loading state
  aiTextEl.innerHTML = `<span class="insight-loading"><i class="fas fa-spinner fa-spin"></i> Generating AI insights…</span>`;
  aiBadgeEl.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Thinking…`;

  try {
    const res = await fetch("/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        crop:        rec.crop,
        confidence:  rec.confidence,
        N:           inputs.N,
        P:           inputs.P,
        K:           inputs.K,
        temperature: inputs.temperature,
        humidity:    inputs.humidity,
        ph:          inputs.ph,
        rainfall:    inputs.rainfall,
      }),
    });
    const data = await res.json();
    const explanation   = data.explanation   || "No insight available.";
    const gemini_powered = data.gemini_powered || false;

    // Cache it
    _insightCache[cacheKey] = { explanation, gemini_powered };
    renderAiText(aiTextEl, aiBadgeEl, explanation, gemini_powered);
  } catch (_) {
    aiTextEl.textContent = "Could not generate insight. Check server connection.";
    aiBadgeEl.innerHTML  = `<i class="fas fa-robot"></i> AI Insights`;
  }
}

function renderAiText(textEl, badgeEl, text, isGemini) {
  textEl.textContent  = text;
  badgeEl.innerHTML   = isGemini
    ? `<i class="fas fa-sparkles"></i> Gemini AI`
    : `<i class="fas fa-robot"></i> AI Insights`;
}

// ── Render ranking cards ──────────────────────────────────────────────────────
function renderRankingCards(recommendations, inputs) {
  const section = document.getElementById("rankingSection");
  const grid    = document.getElementById("rankingGrid");
  if (!section || !grid) return;

  section.style.display = "block";
  grid.innerHTML = "";

  recommendations.forEach((rec, i) => {
    const badge = getRecommendationBadge(rec.confidence);
    const card  = document.createElement("div");
    card.className = "dash-rank-card" + (i === 0 ? " dash-rank-card--active" : "");
    card.innerHTML = `
      <div class="drc-rank">#${i + 1}</div>
      <div class="drc-emoji">${rec.emoji || "🌱"}</div>
      <div class="drc-name">${rec.crop}</div>
      <div class="drc-conf">${rec.confidence}%</div>
      <div class="drc-badge" style="color:${badge.color}">
        <i class="fas ${badge.icon}"></i> ${badge.label}
      </div>
    `;
    card.addEventListener("click", () => {
      document.querySelectorAll(".dash-rank-card").forEach((c) => c.classList.remove("dash-rank-card--active"));
      card.classList.add("dash-rank-card--active");
      renderInsightPanel(rec, i + 1, inputs);
      document.getElementById("insightPanel").scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    grid.appendChild(card);
  });

  // Auto-render insight for #1 crop
  renderInsightPanel(recommendations[0], 1, inputs);
}

// ── Listen for prediction data from main page (via sessionStorage) ────────────
function checkForNewPrediction() {
  try {
    const raw = sessionStorage.getItem("terraai_last_prediction");
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data && data.recommendations && data.recommendations.length > 0) {
      _predictionData = data;
      renderRankingCards(data.recommendations, data.inputs);
    }
  } catch (_) {}
}

// Check on load and whenever storage changes (e.g. user predicts in another tab)
checkForNewPrediction();
window.addEventListener("storage", checkForNewPrediction);
