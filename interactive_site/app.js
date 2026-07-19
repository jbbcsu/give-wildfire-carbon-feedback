const LABELS = {
  baseline: "Baseline",
  "feedback-residual-medium": "Residual medium",
  "feedback-residual-high": "Residual high",
  "feedback-resfire-half-gross": "High-end half-gross",
  "feedback-resfire-gross": "High-end gross",
};

const PRESETS = {
  "feedback-residual-medium": {
    fireScale: 1,
    netPersistence: 0.18,
    missingShare: 0.18,
    damageAmplifier: 1,
  },
  "feedback-residual-high": {
    fireScale: 1,
    netPersistence: 0.35,
    missingShare: 0.35,
    damageAmplifier: 1,
  },
  "feedback-resfire-half-gross": {
    fireScale: 1,
    netPersistence: 0.65,
    missingShare: 0.72,
    damageAmplifier: 1,
  },
  "feedback-resfire-gross": {
    fireScale: 1,
    netPersistence: 0.88,
    missingShare: 0.92,
    damageAmplifier: 1,
  },
};

const state = {
  summary: [],
  samples: [],
  sectoral: [],
  fireScale: [],
};

const $ = (id) => document.getElementById(id);

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted && ch === '"' && next === '"') {
      cell += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (!quoted && ch === ",") {
      row.push(cell);
      cell = "";
    } else if (!quoted && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((v) => v.length)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const headers = rows.shift();
  return rows.map((values) => {
    const obj = {};
    headers.forEach((h, i) => {
      const raw = values[i] ?? "";
      const n = Number(raw);
      obj[h] = raw !== "" && Number.isFinite(n) ? n : raw;
    });
    return obj;
  });
}

async function loadCsv(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Could not load ${path}`);
  return parseCsv(await res.text());
}

function money(value) {
  return `$${value.toFixed(2)}`;
}

function pct(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function scenarioRows(dr) {
  const order = [
    "baseline",
    "feedback-residual-medium",
    "feedback-residual-high",
    "feedback-resfire-half-gross",
    "feedback-resfire-gross",
  ];
  return order
    .map((scenario) => state.summary.find((d) => d.scenario === scenario && d.dr_label === dr))
    .filter(Boolean);
}

function getRow(scenario, dr) {
  return state.summary.find((d) => d.scenario === scenario && d.dr_label === dr);
}

function getBaselineSamples(dr) {
  return state.samples
    .filter((d) => d.scenario === "baseline" && d.dr_label === dr)
    .map((d) => d.scc_2020usd_per_tco2);
}

function getFirePath(scenario) {
  return state.fireScale.filter((d) => d.scenario === scenario);
}

function readControls() {
  return {
    dr: $("discountSelect").value,
    scenario: $("scenarioSelect").value,
    fireScale: Number($("fireScale").value),
    netPersistence: Number($("netPersistence").value),
    missingShare: Number($("missingShare").value),
    damageAmplifier: Number($("damageAmplifier").value),
  };
}

function resetControlsToPreset() {
  const scenario = $("scenarioSelect").value;
  const preset = PRESETS[scenario];
  $("fireScale").value = preset.fireScale;
  $("netPersistence").value = preset.netPersistence;
  $("missingShare").value = preset.missingShare;
  $("damageAmplifier").value = preset.damageAmplifier;
  update();
}

function controlMultiplier(c) {
  const preset = PRESETS[c.scenario];
  const netRatio = c.netPersistence / preset.netPersistence;
  const missingRatio = c.missingShare / preset.missingShare;
  return c.fireScale * netRatio * missingRatio * c.damageAmplifier;
}

function estimate(c) {
  const baseline = getRow("baseline", c.dr);
  const anchor = getRow(c.scenario, c.dr);
  const mult = controlMultiplier(c);
  const deltaMean = anchor.delta_mean_scc * mult;
  const deltaMedian = anchor.delta_median_scc * mult;
  const estimatedMean = baseline.mean_scc + deltaMean;
  const estimatedMedian = baseline.median_scc + deltaMedian;
  const pctDelta = (deltaMean / baseline.mean_scc) * 100;
  const path = getFirePath(c.scenario);
  const fire2100Base = path.find((d) => d.year === 2100)?.feedback_fire_gtco2 ?? 0;
  const stock2100Base = path.find((d) => d.year === 2100)?.atmospheric_co2_c_stock_increase_pct ?? 0;
  return {
    baseline,
    anchor,
    mult,
    deltaMean,
    deltaMedian,
    estimatedMean,
    estimatedMedian,
    pctDelta,
    fire2100: fire2100Base * mult,
    stock2100Pct: stock2100Base * mult,
  };
}

function updateOutputs(c, e) {
  $("fireScaleOut").textContent = `${c.fireScale.toFixed(2)}x`;
  $("netPersistenceOut").textContent = c.netPersistence.toFixed(2);
  $("missingShareOut").textContent = c.missingShare.toFixed(2);
  $("damageAmplifierOut").textContent = `${c.damageAmplifier.toFixed(2)}x`;

  $("estimateMean").textContent = money(e.estimatedMean);
  $("estimateDelta").textContent = `${e.deltaMean >= 0 ? "+" : ""}${money(e.deltaMean)}`;
  $("estimatePct").textContent = pct(e.pctDelta);
  $("fire2100").textContent = `${e.fire2100.toFixed(2)} GtCO2/yr`;

  const warnings = [];
  if (c.scenario.includes("resfire")) {
    warnings.push("Stress-test anchor: useful for mechanism checks, not double-counting safe.");
  }
  if (c.netPersistence > 0.65) {
    warnings.push("High net persistence assumes weak regrowth or long atmospheric residence.");
  }
  if (c.missingShare > 0.65) {
    warnings.push("High missing share raises double-counting risk with AFOLU/LULUCF or aggregate pathways.");
  }
  if (e.stock2100Pct > 1) {
    warnings.push("This pushes added atmospheric CO2-C above 1% of the baseline 2100 atmospheric stock.");
  }
  $("riskNote").textContent = warnings.length
    ? warnings.join(" ")
    : "Current settings remain in the residual-style diagnostic range. Still treat the result as a calibrated approximation.";
}

function renderScenarioTable() {
  const dr = $("discountSelect").value;
  const tbody = $("scenarioTable").querySelector("tbody");
  tbody.innerHTML = "";
  scenarioRows(dr).forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${LABELS[row.scenario] ?? row.scenario}</td>
      <td>${money(row.mean_scc)}</td>
      <td>${money(row.median_scc)}</td>
      <td>${money(row.p05_scc)}</td>
      <td>${money(row.p95_scc)}</td>
      <td class="delta">${row.delta_mean_scc >= 0 ? "+" : ""}${money(row.delta_mean_scc)}</td>
      <td class="delta">${pct(row.pct_delta_mean_scc)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function clearCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || canvas.width;
  const h = Math.round(w * (canvas.height / canvas.width));
  canvas.width = Math.round(w * ratio);
  canvas.height = Math.round(h * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

function drawAxes(ctx, x, y, w, h, opts = {}) {
  ctx.strokeStyle = "#d7cdbf";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x, y + h);
  ctx.lineTo(x + w, y + h);
  ctx.stroke();
  ctx.fillStyle = "#59635e";
  ctx.font = "12px Avenir, sans-serif";
  if (opts.xlabel) ctx.fillText(opts.xlabel, x + w - 110, y + h + 28);
}

function histogram(values, bins, maxValue) {
  const counts = Array.from({ length: bins }, () => 0);
  values.forEach((v) => {
    if (v < 0 || v > maxValue) return;
    const i = Math.min(bins - 1, Math.floor((v / maxValue) * bins));
    counts[i] += 1;
  });
  return counts;
}

function drawDistribution(e, c) {
  const canvas = $("distributionChart");
  const { ctx, w, h } = clearCanvas(canvas);
  const pad = { l: 54, r: 24, t: 28, b: 54 };
  const plot = { x: pad.l, y: pad.t, w: w - pad.l - pad.r, h: h - pad.t - pad.b };
  const maxValue = c.dr === "1.5%" ? 1000 : 650;
  const bins = 34;
  const baseline = getBaselineSamples(c.dr);
  const shifted = baseline.map((v) => v + e.deltaMean);
  const h0 = histogram(baseline, bins, maxValue);
  const h1 = histogram(shifted, bins, maxValue);
  const maxCount = Math.max(...h0, ...h1, 1);
  drawAxes(ctx, plot.x, plot.y, plot.w, plot.h, { xlabel: "2020 USD/tCO2" });

  const barW = plot.w / bins;
  h0.forEach((count, i) => {
    const bh = (count / maxCount) * plot.h;
    ctx.fillStyle = "rgba(31, 107, 91, 0.45)";
    ctx.fillRect(plot.x + i * barW, plot.y + plot.h - bh, barW - 1, bh);
  });
  h1.forEach((count, i) => {
    const bh = (count / maxCount) * plot.h;
    ctx.fillStyle = "rgba(200, 78, 45, 0.45)";
    ctx.fillRect(plot.x + i * barW + barW * 0.22, plot.y + plot.h - bh, barW * 0.56, bh);
  });

  const meanX0 = plot.x + (e.baseline.mean_scc / maxValue) * plot.w;
  const meanX1 = plot.x + (e.estimatedMean / maxValue) * plot.w;
  ctx.strokeStyle = "#1f6b5b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(meanX0, plot.y);
  ctx.lineTo(meanX0, plot.y + plot.h);
  ctx.stroke();
  ctx.strokeStyle = "#c84e2d";
  ctx.beginPath();
  ctx.moveTo(meanX1, plot.y);
  ctx.lineTo(meanX1, plot.y + plot.h);
  ctx.stroke();

  ctx.fillStyle = "#182321";
  ctx.font = "13px Avenir, sans-serif";
  ctx.fillText("Baseline", plot.x + 4, plot.y + 16);
  ctx.fillStyle = "#c84e2d";
  ctx.fillText("Adjusted wildfire", plot.x + 92, plot.y + 16);
  ctx.fillStyle = "#59635e";
  ctx.fillText(`Display truncated at ${money(maxValue)}`, plot.x, plot.y + plot.h + 28);
}

function drawFirePath(e, c) {
  const canvas = $("firePathChart");
  const { ctx, w, h } = clearCanvas(canvas);
  const pad = { l: 58, r: 26, t: 28, b: 54 };
  const plot = { x: pad.l, y: pad.t, w: w - pad.l - pad.r, h: h - pad.t - pad.b };
  const path = getFirePath(c.scenario).map((d) => ({
    year: d.year,
    fire: d.feedback_fire_gtco2 * e.mult,
    stock: d.atmospheric_co2_c_stock_increase_pct * e.mult,
  }));
  const years = path.map((d) => d.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxFire = Math.max(...path.map((d) => d.fire), 0.1);

  drawAxes(ctx, plot.x, plot.y, plot.w, plot.h, { xlabel: "year" });
  ctx.strokeStyle = "#ece2d4";
  ctx.lineWidth = 1;
  for (let i = 1; i <= 4; i += 1) {
    const gy = plot.y + plot.h - (plot.h * i) / 4;
    ctx.beginPath();
    ctx.moveTo(plot.x, gy);
    ctx.lineTo(plot.x + plot.w, gy);
    ctx.stroke();
  }

  ctx.strokeStyle = "#c84e2d";
  ctx.lineWidth = 3;
  ctx.beginPath();
  path.forEach((d, i) => {
    const x = plot.x + ((d.year - minYear) / (maxYear - minYear)) * plot.w;
    const y = plot.y + plot.h - (d.fire / maxFire) * plot.h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#182321";
  ctx.font = "13px Avenir, sans-serif";
  ctx.fillText("Added wildfire CO2, GtCO2/yr", plot.x, plot.y + 16);
  ctx.fillStyle = "#59635e";
  ctx.fillText(`${minYear}`, plot.x, plot.y + plot.h + 28);
  ctx.fillText(`${maxYear}`, plot.x + plot.w - 34, plot.y + plot.h + 28);
  ctx.fillText(`${maxFire.toFixed(2)} GtCO2/yr`, plot.x + 8, plot.y + 38);
  ctx.fillText(`2100 stock increment: ${e.stock2100Pct.toFixed(3)}%`, plot.x + 8, plot.y + 58);
}

function update() {
  const c = readControls();
  const e = estimate(c);
  updateOutputs(c, e);
  renderScenarioTable();
  drawDistribution(e, c);
  drawFirePath(e, c);
}

async function init() {
  [state.summary, state.samples, state.sectoral, state.fireScale] = await Promise.all([
    loadCsv("assets/data/scc_summary.csv"),
    loadCsv("assets/data/all_scc_samples.csv"),
    loadCsv("assets/data/sectoral_scc_summary.csv"),
    loadCsv("assets/data/fire_scale_check_deterministic.csv"),
  ]);

  $("scenarioSelect").addEventListener("change", resetControlsToPreset);
  $("discountSelect").addEventListener("change", update);
  ["fireScale", "netPersistence", "missingShare", "damageAmplifier"].forEach((id) => {
    $(id).addEventListener("input", update);
  });
  $("resetButton").addEventListener("click", resetControlsToPreset);
  window.addEventListener("resize", update);
  resetControlsToPreset();
}

init().catch((err) => {
  console.error(err);
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<div class="load-error">Could not load data files: ${err.message}</div>`,
  );
});
