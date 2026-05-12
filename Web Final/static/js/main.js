/* ═══════════════════════════════════════════════════════════════════════════
   TerraAI – Main Frontend Logic
════════════════════════════════════════════════════════════════════════════ */

"use strict";

// ── Utility ───────────────────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast ${type} show`;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 3500);
}

function setLoading(btnEl, loaderEl, loading) {
  if (loading) {
    btnEl.disabled = true;
    loaderEl.style.display = "block";
  } else {
    btnEl.disabled = false;
    loaderEl.style.display = "none";
  }
}

// ── Navbar scroll effect ──────────────────────────────────────────────────────
window.addEventListener("scroll", () => {
  document.getElementById("navbar").classList.toggle("scrolled", window.scrollY > 40);
});

// ── Hamburger menu ────────────────────────────────────────────────────────────
document.getElementById("hamburger")?.addEventListener("click", () => {
  document.querySelector(".nav-links").classList.toggle("open");
});

// ── Sample value buttons ──────────────────────────────────────────────────────
document.querySelectorAll(".sample-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const [N, P, K, temp, hum, ph, rain] = btn.dataset.values.split(",");
    setField("inp-N", N);
    setField("inp-P", P);
    setField("inp-K", K);
    setField("inp-temp", temp);
    setField("inp-hum", hum);
    setField("inp-ph", ph);
    setField("inp-rain", rain);
    showToast(`Sample values loaded for ${btn.textContent.trim()}`);
    document.getElementById("predict-section").scrollIntoView({ behavior: "smooth" });
  });
});

function setField(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = val;
  el.classList.add("filled");
  el.dispatchEvent(new Event("input"));
}

// ── Clear form ────────────────────────────────────────────────────────────────
document.getElementById("clearBtn")?.addEventListener("click", () => {
  ["inp-N","inp-P","inp-K","inp-temp","inp-hum","inp-ph","inp-rain"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) { el.value = ""; el.classList.remove("filled"); }
  });
  document.getElementById("results-section").style.display = "none";
  showToast("Form cleared");
});

// ═══════════════════════════════════════════════════════════════════════════
// WEATHER
// ═══════════════════════════════════════════════════════════════════════════
let weatherData = null;

async function fetchWeather(params) {
  const url = "/weather?" + new URLSearchParams(params);
  const res = await fetch(url);
  if (!res.ok) throw new Error("Weather API error");
  return res.json();
}

function applyWeatherToUI(data) {
  weatherData = data;
  animateValue("wv-temp", data.temperature);
  animateValue("wv-hum", data.humidity);
  animateValue("wv-rain", data.rainfall);
  document.getElementById("wv-city").textContent = data.city || "—";
  document.getElementById("wv-desc").textContent = data.description || "—";

  // Auto-fill prediction form
  setField("inp-temp", data.temperature);
  setField("inp-hum", data.humidity);
  setField("inp-rain", data.rainfall);

  const bar = document.getElementById("weatherFillBar");
  bar.style.display = "flex";

  if (data.mock) showToast("Using demo weather data (add API key for live data)", "warning");
  else showToast(`Weather loaded for ${data.city}`);
}

function animateValue(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseFloat(el.textContent) || 0;
  const end = parseFloat(target);
  const duration = 800;
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = (start + (end - start) * ease).toFixed(1);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = end;
  }
  requestAnimationFrame(step);
}

document.getElementById("fetchWeatherBtn")?.addEventListener("click", async () => {
  const city = document.getElementById("cityInput").value.trim();
  if (!city) { showToast("Enter a city name first", "error"); return; }
  const btn = document.getElementById("fetchWeatherBtn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading…';
  try {
    const data = await fetchWeather({ city });
    applyWeatherToUI(data);
  } catch (e) {
    showToast("Could not fetch weather. Check city name.", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-cloud-download-alt"></i> Get Weather';
  }
});

document.getElementById("autoLocationBtn")?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    showToast("Geolocation not supported by your browser", "error");
    return;
  }
  const btn = document.getElementById("autoLocationBtn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Detecting…';
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        const data = await fetchWeather({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        applyWeatherToUI(data);
        document.getElementById("cityInput").value = data.city || "";
      } catch (e) {
        showToast("Could not fetch weather for your location", "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-location-crosshairs"></i> Auto Detect';
      }
    },
    () => {
      showToast("Location access denied. Enter city manually.", "warning");
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-location-crosshairs"></i> Auto Detect';
    }
  );
});

// ── City autocomplete ─────────────────────────────────────────────────────────
const cityInput = document.getElementById("cityInput");
const cityDropdown = document.getElementById("cityDropdown");
let cityDebounce;

cityInput?.addEventListener("input", () => {
  clearTimeout(cityDebounce);
  const q = cityInput.value.trim();
  if (q.length < 2) { cityDropdown.classList.remove("open"); return; }
  cityDebounce = setTimeout(async () => {
    try {
      const res = await fetch(`/cities?q=${encodeURIComponent(q)}`);
      const cities = await res.json();
      cityDropdown.innerHTML = "";
      if (cities.length === 0) { cityDropdown.classList.remove("open"); return; }
      cities.forEach((c) => {
        const div = document.createElement("div");
        div.className = "city-option";
        div.textContent = c;
        div.addEventListener("click", () => {
          cityInput.value = c;
          cityDropdown.classList.remove("open");
        });
        cityDropdown.appendChild(div);
      });
      cityDropdown.classList.add("open");
    } catch (_) {}
  }, 250);
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".city-search-wrap")) cityDropdown.classList.remove("open");
});

cityInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    cityDropdown.classList.remove("open");
    document.getElementById("fetchWeatherBtn").click();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// CROP PREDICTION
// ═══════════════════════════════════════════════════════════════════════════

// Store last prediction inputs so /explain can reuse them
let _lastInputs = {};

document.getElementById("predictBtn")?.addEventListener("click", async () => {
  const fields = {
    N:           document.getElementById("inp-N")?.value,
    P:           document.getElementById("inp-P")?.value,
    K:           document.getElementById("inp-K")?.value,
    temperature: document.getElementById("inp-temp")?.value,
    humidity:    document.getElementById("inp-hum")?.value,
    ph:          document.getElementById("inp-ph")?.value,
    rainfall:    document.getElementById("inp-rain")?.value,
  };

  for (const [key, val] of Object.entries(fields)) {
    if (val === "" || val === null || val === undefined) {
      showToast(`Please fill in the ${key} field`, "error");
      return;
    }
  }

  // Save inputs for per-crop explain calls
  _lastInputs = { ...fields };

  const btn = document.getElementById("predictBtn");
  const loader = document.getElementById("predictLoader");
  setLoading(btn, loader, true);
  btn.querySelector("span").textContent = "Predicting…";

  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, "error"); return; }

    // Save to sessionStorage so dashboard can read it
    try {
      sessionStorage.setItem("terraai_last_prediction", JSON.stringify({
        recommendations: data.recommendations,
        inputs: _lastInputs,
      }));
    } catch (_) {}

    renderResults(data);
    document.getElementById("results-section").style.display = "block";
    setTimeout(() => {
      document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });
    }, 100);
    showToast(`Best crop: ${data.best_crop} (${data.best_confidence}%)`);
  } catch (e) {
    showToast("Prediction failed. Is the server running?", "error");
  } finally {
    setLoading(btn, loader, false);
    btn.querySelector("span").textContent = "Predict Best Crop";
  }
});

function renderResults(data) {
  // Best crop banner
  document.getElementById("bcb-emoji").textContent = data.best_emoji;
  document.getElementById("bcb-crop").textContent = data.best_crop;
  document.getElementById("bcb-conf").textContent = `${data.best_confidence}%`;

  // Gemini explanation for the top crop
  updateExplainCard(data.explanation, data.gemini_powered);

  // Top 5 grid — first card is active by default
  const grid = document.getElementById("resultsGrid");
  grid.innerHTML = "";
  data.recommendations.forEach((rec, i) => {
    const card = document.createElement("div");
    card.className = "result-card" + (i === 0 ? " result-card-active" : "");
    card.style.animationDelay = `${i * 0.08}s`;
    card.dataset.crop       = rec.crop;
    card.dataset.confidence = rec.confidence;
    card.dataset.emoji      = rec.emoji;
    card.innerHTML = `
      <div class="result-rank ${i === 0 ? "rank-1" : ""}">${i + 1}</div>
      <div class="result-emoji">${rec.emoji}</div>
      <div class="result-crop">${rec.crop}</div>
      <div class="result-conf-bar">
        <div class="result-conf-fill" style="width:0%" data-target="${rec.confidence}"></div>
      </div>
      <div class="result-conf-text">${rec.confidence}%</div>
      <div class="result-select-hint">Click for AI insight</div>
    `;
    card.addEventListener("click", () => onResultCardClick(card, rec));
    grid.appendChild(card);
  });

  // Animate confidence bars
  requestAnimationFrame(() => {
    document.querySelectorAll(".result-conf-fill").forEach((bar) => {
      bar.style.width = bar.dataset.target + "%";
    });
  });
}

// ── Called when user clicks any result card ───────────────────────────────────
async function onResultCardClick(card, rec) {
  // Mark active
  document.querySelectorAll(".result-card").forEach((c) => c.classList.remove("result-card-active"));
  card.classList.add("result-card-active");

  // Update banner instantly
  document.getElementById("bcb-emoji").textContent = rec.emoji;
  document.getElementById("bcb-crop").textContent  = rec.crop;
  document.getElementById("bcb-conf").textContent  = `${rec.confidence}%`;

  // Show loading state in explain card
  setExplainLoading(true);

  try {
    const res = await fetch("/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        crop:        rec.crop,
        confidence:  rec.confidence,
        ..._lastInputs,
      }),
    });
    const data = await res.json();
    if (data.error) {
      updateExplainCard("Could not generate insight for this crop.", false);
    } else {
      updateExplainCard(data.explanation, data.gemini_powered);
    }
  } catch (e) {
    updateExplainCard("Could not reach the server.", false);
  } finally {
    setExplainLoading(false);
  }
}

// ── Explain card helpers ──────────────────────────────────────────────────────
function updateExplainCard(text, isGemini) {
  const card  = document.getElementById("geminiExplainCard");
  const textEl = document.getElementById("geminiExplainText");
  const badge  = card.querySelector(".gemini-badge");
  if (!text) { card.style.display = "none"; return; }
  textEl.textContent = text;
  if (badge) {
    badge.innerHTML = isGemini
      ? '<i class="fas fa-sparkles"></i> Gemini AI'
      : '<i class="fas fa-robot"></i> AI Insights';
  }
  card.style.display = "flex";
  card.classList.remove("explain-loading");
}

function setExplainLoading(loading) {
  const card   = document.getElementById("geminiExplainCard");
  const textEl = document.getElementById("geminiExplainText");
  const badge  = card.querySelector(".gemini-badge");
  if (loading) {
    card.style.display = "flex";
    card.classList.add("explain-loading");
    textEl.textContent = "Generating AI insight…";
    if (badge) badge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Thinking…';
  } else {
    card.classList.remove("explain-loading");
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// OCR
// ═══════════════════════════════════════════════════════════════════════════
let ocrExtractedData = {};
const ocrDropZone   = document.getElementById("ocrDropZone");
const ocrFileInput  = document.getElementById("ocrFileInput");
const ocrPreview    = document.getElementById("ocrPreview");
const ocrPreviewImg = document.getElementById("ocrPreviewImg");
const ocrUploadContent = document.getElementById("ocrUploadContent");
const ocrScanBtn    = document.getElementById("ocrScanBtn");
const ocrFillBtn    = document.getElementById("ocrFillBtn");
const ocrStatus     = document.getElementById("ocrStatus");

ocrDropZone?.addEventListener("click", (e) => {
  if (!e.target.closest(".ocr-remove-btn")) ocrFileInput.click();
});

ocrDropZone?.addEventListener("dragover", (e) => {
  e.preventDefault();
  ocrDropZone.classList.add("drag-over");
});
ocrDropZone?.addEventListener("dragleave", () => ocrDropZone.classList.remove("drag-over"));
ocrDropZone?.addEventListener("drop", (e) => {
  e.preventDefault();
  ocrDropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleOcrFile(file);
});

ocrFileInput?.addEventListener("change", () => {
  if (ocrFileInput.files[0]) handleOcrFile(ocrFileInput.files[0]);
});

document.getElementById("ocrRemoveBtn")?.addEventListener("click", (e) => {
  e.stopPropagation();
  ocrPreview.style.display = "none";
  ocrUploadContent.style.display = "block";
  ocrFileInput.value = "";
  ocrScanBtn.disabled = true;
  ocrFillBtn.disabled = true;
  ocrStatus.textContent = "Waiting for upload…";
  ocrStatus.className = "ocr-status";
  resetExtracted();
});

function handleOcrFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    ocrPreviewImg.src = e.target.result;
    ocrPreview.style.display = "block";
    ocrUploadContent.style.display = "none";
    ocrScanBtn.disabled = false;
    ocrStatus.textContent = "Ready to scan";
    ocrStatus.className = "ocr-status";
  };
  reader.readAsDataURL(file);
}

function resetExtracted() {
  ["N","P","K","ph"].forEach((k) => {
    const el = document.getElementById(`ext-${k}`);
    if (el) { el.textContent = "—"; el.classList.remove("found"); }
  });
  document.getElementById("ocrRawWrap").style.display = "none";
  ocrExtractedData = {};
}

ocrScanBtn?.addEventListener("click", async () => {
  const file = ocrFileInput.files[0];
  if (!file) { showToast("No file selected", "error"); return; }

  const loader = document.getElementById("ocrLoader");
  setLoading(ocrScanBtn, loader, true);
  ocrScanBtn.querySelector("span").textContent = "Scanning…";
  ocrStatus.textContent = "Scanning…";
  ocrStatus.className = "ocr-status scanning";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/ocr", { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, "error");
      ocrStatus.textContent = "Error";
      ocrStatus.className = "ocr-status error";
      return;
    }

    // Normalise keys to lowercase so "N","P","K","ph" all match
    const rawExtracted = data.extracted || {};
    ocrExtractedData = {};
    for (const [k, v] of Object.entries(rawExtracted)) {
      ocrExtractedData[k.toLowerCase()] = v;
    }
    // Also keep original-case keys for display
    const displayExtracted = rawExtracted;
    const keys = Object.keys(displayExtracted);

    if (keys.length === 0 && Object.keys(data.amendments || {}).length === 0) {
      showToast(data.warning || "No values extracted. Try a clearer image.", "warning");
      ocrStatus.textContent = "No values found";
      ocrStatus.className = "ocr-status error";
    } else {
      // ── Update the extracted-values display panel ──────────────────────
      keys.forEach((k) => {
        const el = document.getElementById(`ext-${k}`);
        if (el) { el.textContent = displayExtracted[k]; el.classList.add("found"); }
      });

      // ── AUTO-FILL the prediction form immediately ──────────────────────
      const filledFields = autoFillFormFromOCR(ocrExtractedData);

      // ── Show amendment items if present ───────────────────────────────
      if (data.amendments && Object.keys(data.amendments).length > 0) {
        renderAmendments(data.amendments, data.report_meta);
      }

      ocrFillBtn.disabled = false;
      const totalFound = keys.length + Object.keys(data.amendments || {}).length;
      ocrStatus.textContent = `Extracted ${totalFound} value(s)`;
      ocrStatus.className = "ocr-status done";

      if (filledFields > 0) {
        showToast(`OCR auto-filled ${filledFields} field(s): ${keys.join(", ")}`);
        // Scroll to predict section after short delay so user sees the fill
        setTimeout(() => {
          document.getElementById("predict-section")?.scrollIntoView({ behavior: "smooth" });
        }, 800);
      } else {
        showToast(`OCR extracted: ${keys.join(", ")} — click Auto Fill to apply`);
      }
    }

    if (data.raw_text) {
      document.getElementById("ocrRawText").textContent = data.raw_text;
      document.getElementById("ocrRawWrap").style.display = "block";
    }
  } catch (e) {
    showToast("OCR request failed", "error");
    ocrStatus.textContent = "Failed";
    ocrStatus.className = "ocr-status error";
  } finally {
    setLoading(ocrScanBtn, loader, false);
    ocrScanBtn.querySelector("span").textContent = "Scan Report";
  }
});

// ── Core fill logic — called both by auto-fill and by the fill button ─────────
function autoFillFormFromOCR(extracted) {
  // Map: OCR key (lowercase) → form input id
  const map = {
    "n":  "inp-N",
    "p":  "inp-P",
    "k":  "inp-K",
    "ph": "inp-ph",
  };
  let filled = 0;
  for (const [ocrKey, inputId] of Object.entries(map)) {
    const val = extracted[ocrKey];
    if (val !== undefined && val !== null && val !== "") {
      setField(inputId, val);
      // Flash the field green to show it was filled
      const el = document.getElementById(inputId);
      if (el) {
        el.classList.add("ocr-filled-flash");
        setTimeout(() => el.classList.remove("ocr-filled-flash"), 1500);
      }
      filled++;
    }
  }
  return filled;
}

ocrFillBtn?.addEventListener("click", () => {
  const filled = autoFillFormFromOCR(ocrExtractedData);
  if (filled > 0) {
    showToast(`Auto-filled ${filled} field(s) from OCR`);
    document.getElementById("predict-section").scrollIntoView({ behavior: "smooth" });
  } else {
    showToast("No values to fill — scan a report first", "warning");
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// REVERSE COMPATIBILITY
// ═══════════════════════════════════════════════════════════════════════════
document.getElementById("compatBtn")?.addEventListener("click", async () => {
  const crop = document.getElementById("compat-crop")?.value.trim();
  const soil = document.getElementById("compat-soil")?.value.trim();

  if (!crop || !soil) {
    showToast("Enter both crop name and soil type", "error");
    return;
  }

  const btn = document.getElementById("compatBtn");
  const loader = document.getElementById("compatLoader");
  setLoading(btn, loader, true);
  btn.querySelector("span").textContent = "Analyzing…";

  try {
    const res = await fetch("/compatibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crop, soil }),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, "error"); return; }
    renderCompatibility(data);
    document.getElementById("compatResult").style.display = "flex";
    // Trigger improvement insight fetch immediately after compat result
    fetchSoilImprovement(crop, soil, data.score, data.label);
    showToast(`Compatibility: ${data.label} (${data.score}%)`);
  } catch (e) {
    showToast("Compatibility check failed", "error");
  } finally {
    setLoading(btn, loader, false);
    btn.querySelector("span").textContent = "Analyze Compatibility";
  }
});

function renderCompatibility(data) {
  // Score ring
  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (data.score / 100) * circumference;
  const fill = document.getElementById("scoreFill");
  fill.style.stroke = data.color;
  fill.style.strokeDashoffset = circumference;
  requestAnimationFrame(() => { fill.style.strokeDashoffset = offset; });

  document.getElementById("scoreNum").textContent = data.score;
  document.getElementById("scoreNum").style.color = data.color;

  const badge = document.getElementById("compatLabel");
  badge.textContent = data.label;
  badge.style.background    = `${data.color}22`;
  badge.style.color         = data.color;
  badge.style.borderColor   = `${data.color}55`;

  document.getElementById("compat-result-crop").textContent = data.crop;
  document.getElementById("compat-result-soil").textContent = data.soil;

  const tipsEl = document.getElementById("compatTips");
  tipsEl.innerHTML = data.tips
    .map((tip) => `<div class="compat-tip"><i class="fas fa-check-circle"></i><span>${tip}</span></div>`)
    .join("");
}

// ── Soil Improvement Insight ──────────────────────────────────────────────────
// Cache: "crop||soil" → improvement data
const _improvementCache = {};

async function fetchSoilImprovement(crop, soil, score, label) {
  const panel    = document.getElementById("soilImprovePanel");
  const loadBar  = document.getElementById("sipLoadingBar");
  const subtitle = document.getElementById("sipSubtitle");
  const badge    = document.getElementById("sipBadge");

  // Show panel with skeleton loading state
  panel.style.display = "block";
  loadBar.style.display = "block";
  subtitle.textContent = `${crop} on ${soil}`;
  badge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating…';

  // Set all cards to loading skeleton
  ["sipProblem","sipNpk","sipWater","sipAmend","sipTech"].forEach((id) => {
    document.getElementById(id).innerHTML =
      '<span class="sip-skeleton-line"></span><span class="sip-skeleton-line sip-skeleton-line--short"></span>';
  });

  // Scroll to panel
  setTimeout(() => panel.scrollIntoView({ behavior: "smooth", block: "nearest" }), 200);

  // Check cache
  const cacheKey = `${crop.toLowerCase()}||${soil.toLowerCase()}`;
  if (_improvementCache[cacheKey]) {
    loadBar.style.display = "none";
    renderImprovementCards(_improvementCache[cacheKey].improvement, _improvementCache[cacheKey].gemini_powered);
    return;
  }

  try {
    const res = await fetch("/soil-improvement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crop, soil, score, label }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // Cache it
    _improvementCache[cacheKey] = data;
    loadBar.style.display = "none";
    renderImprovementCards(data.improvement, data.gemini_powered);
  } catch (e) {
    loadBar.style.display = "none";
    badge.innerHTML = '<i class="fas fa-robot"></i> AI Insights';
    ["sipProblem","sipNpk","sipWater","sipAmend","sipTech"].forEach((id) => {
      document.getElementById(id).textContent = "Could not generate insight. Please try again.";
    });
  }
}

function renderImprovementCards(imp, isGemini) {
  const badge = document.getElementById("sipBadge");
  badge.innerHTML = isGemini
    ? '<i class="fas fa-sparkles"></i> Gemini AI'
    : '<i class="fas fa-robot"></i> AI Insights';

  const map = {
    sipProblem: imp.problem,
    sipNpk:     imp.npk,
    sipWater:   imp.water,
    sipAmend:   imp.amendments,
    sipTech:    imp.techniques,
  };
  Object.entries(map).forEach(([id, text]) => {
    const el = document.getElementById(id);
    el.textContent = "";
    // Typewriter effect for a premium feel
    typewriterEffect(el, text, 12);
  });
}

function typewriterEffect(el, text, speed = 15) {
  let i = 0;
  el.textContent = "";
  const interval = setInterval(() => {
    el.textContent += text[i];
    i++;
    if (i >= text.length) clearInterval(interval);
  }, speed);
}

// ── Render amendment report data ──────────────────────────────────────────────
const AMENDMENT_LABELS = {
  azomite:      "Azomite (trace minerals)",
  gypsum:       "Gypsum",
  feather_meal: "Feather Meal (12-0-0)",
  sulfur:       "Tiger-90 Elemental Sulfur",
  copper:       "Biomin Copper (4% Cu)",
  zinc:         "Zinc Sulfate",
  borax:        "Borax",
};

function renderAmendments(amendments, meta) {
  // Remove old panel if exists
  document.getElementById("ocrAmendmentPanel")?.remove();

  const panel = document.createElement("div");
  panel.id = "ocrAmendmentPanel";
  panel.className = "ocr-amendment-panel";

  let metaHtml = "";
  if (meta) {
    if (meta.name)       metaHtml += `<span><i class="fas fa-file-alt"></i> ${meta.name.trim()}</span>`;
    if (meta.test_date)  metaHtml += `<span><i class="fas fa-calendar"></i> ${meta.test_date.trim()}</span>`;
    if (meta.area_sqft)  metaHtml += `<span><i class="fas fa-ruler-combined"></i> ${meta.area_sqft} sq ft</span>`;
    if (meta.total_weight) metaHtml += `<span><i class="fas fa-weight-hanging"></i> Total: ${meta.total_weight} lbs</span>`;
  }

  const rows = Object.entries(amendments)
    .map(([key, val]) => `
      <div class="amend-row">
        <span class="amend-name"><i class="fas fa-leaf"></i> ${AMENDMENT_LABELS[key] || key}</span>
        <span class="amend-val">${val} oz</span>
      </div>`)
    .join("");

  panel.innerHTML = `
    <div class="amend-header">
      <i class="fas fa-flask"></i> Amendment Report Detected
    </div>
    ${metaHtml ? `<div class="amend-meta">${metaHtml}</div>` : ""}
    <div class="amend-list">${rows}</div>
  `;

  // Insert after ocr-extracted div
  const extracted = document.getElementById("ocrExtracted");
  extracted.parentNode.insertBefore(panel, extracted.nextSibling);
}

// ═══════════════════════════════════════════════════════════════════════════
// LAND PLANNING & YIELD ESTIMATION
// ═══════════════════════════════════════════════════════════════════════════

let _yieldUnit = "acre";

// Unit toggle
document.querySelectorAll(".yut-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".yut-btn").forEach((b) => b.classList.remove("yut-btn--active"));
    btn.classList.add("yut-btn--active");
    _yieldUnit = btn.dataset.unit;
  });
});

// Quick preset buttons
document.querySelectorAll(".yield-preset-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById("yield-crop").value = btn.dataset.crop;
    document.getElementById("yield-area").value = btn.dataset.area;
    _yieldUnit = "acre";
    document.querySelectorAll(".yut-btn").forEach((b) => b.classList.remove("yut-btn--active"));
    document.getElementById("yutAcre").classList.add("yut-btn--active");
  });
});

// Main calculate button
document.getElementById("yieldBtn")?.addEventListener("click", async () => {
  const crop = document.getElementById("yield-crop")?.value.trim();
  const area = parseFloat(document.getElementById("yield-area")?.value);

  if (!crop) { showToast("Enter a crop name", "error"); return; }
  if (!area || area <= 0) { showToast("Enter a valid land area", "error"); return; }

  const btn    = document.getElementById("yieldBtn");
  const loader = document.getElementById("yieldLoader");
  setLoading(btn, loader, true);
  btn.querySelector("span").textContent = "Calculating…";

  try {
    const res = await fetch("/yield-estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crop, area, unit: _yieldUnit }),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, "error"); return; }
    renderYieldResults(data);
    showToast(`Yield estimate ready for ${data.crop}`);
  } catch (e) {
    showToast("Estimation failed. Is the server running?", "error");
  } finally {
    setLoading(btn, loader, false);
    btn.querySelector("span").textContent = "Calculate Estimates";
  }
});

function renderYieldResults(data) {
  const est = data.estimates;

  // Show cards
  document.getElementById("yieldResultsCard").style.display = "block";
  document.getElementById("yieldInsightPanel").style.display = "block";

  // Header
  document.getElementById("yieldResultCrop").textContent =
    `${getCropEmoji(data.crop)} ${data.crop}`;
  document.getElementById("yieldResultArea").textContent =
    `${data.area} ${data.unit}${data.area !== 1 ? "s" : ""} · ${est.area_ha} ha`;

  // Stat tiles — animate numbers
  animateCounter("ysv-seed",   est.seed_req,  1);
  animateCounter("ysv-water",  est.water_req, 0);
  animateCounter("ysv-yield",  est.yield_est, 1);
  document.getElementById("ysv-yield-unit").textContent = est.yield_unit;
  document.getElementById("ysv-season").textContent     = est.season;

  // NPK bars
  const maxNPK = Math.max(est.N_kg, est.P_kg, est.K_kg, 1);
  setNpkBar("npkFillN", "npkValN", est.N_kg, maxNPK, "#00e676");
  setNpkBar("npkFillP", "npkValP", est.P_kg, maxNPK, "#40c4ff");
  setNpkBar("npkFillK", "npkValK", est.K_kg, maxNPK, "#ff9100");

  // AI insight
  const insightPanel  = document.getElementById("yieldInsightPanel");
  const insightText   = document.getElementById("yieldInsightText");
  const insightBadge  = document.getElementById("yieldInsightBadge");
  const insightSub    = document.getElementById("yieldInsightSub");
  const insightLoader = document.getElementById("yieldInsightLoading");

  insightSub.textContent = `${data.crop} · ${data.area} ${data.unit}${data.area !== 1 ? "s" : ""}`;
  insightLoader.style.display = "block";
  insightText.textContent = "";
  insightBadge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating…';

  // Typewriter after short delay so stats animate first
  setTimeout(() => {
    insightLoader.style.display = "none";
    insightBadge.innerHTML = data.gemini_powered
      ? '<i class="fas fa-sparkles"></i> Gemini AI'
      : '<i class="fas fa-robot"></i> AI Insights';
    typewriterEffect(insightText, data.insight, 10);
  }, 400);

  // Scroll to results
  setTimeout(() => {
    document.getElementById("yieldResultsCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, 200);
}

function setNpkBar(fillId, valId, value, max, color) {
  const fill = document.getElementById(fillId);
  const val  = document.getElementById(valId);
  val.textContent = value + " kg";
  fill.style.background = color;
  fill.style.width = "0%";
  requestAnimationFrame(() => {
    fill.style.width = Math.round((value / max) * 100) + "%";
  });
}

function animateCounter(id, target, decimals = 0) {
  const el = document.getElementById(id);
  if (!el) return;
  const duration = 900;
  const start    = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3);
    el.textContent = (target * ease).toFixed(decimals);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target.toFixed(decimals);
  }
  requestAnimationFrame(step);
}

const CROP_EMOJIS = {
  rice:"🌾",maize:"🌽",wheat:"🌿",cotton:"🌸",sugarcane:"🎋",banana:"🍌",
  tomato:"🍅",potato:"🥔",coffee:"☕",grapes:"🍇",chickpea:"🫘",lentil:"🫘",
  jute:"🌿",papaya:"🍈",mango:"🥭",watermelon:"🍉",muskmelon:"🍈",orange:"🍊",
  apple:"🍎",pomegranate:"🍎",coconuttree:"🥥",pigeonpeas:"🌿",mothbeans:"🌱",
  mungbean:"🌱",blackgram:"🌿",kidneybeans:"🫘",
};
function getCropEmoji(name) {
  return CROP_EMOJIS[name.toLowerCase()] || "🌱";
}

// ── Smooth scroll for nav links ───────────────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener("click", (e) => {
    const target = document.querySelector(a.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth" });
      document.querySelector(".nav-links")?.classList.remove("open");
    }
  });
});
