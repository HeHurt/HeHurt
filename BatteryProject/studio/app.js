const state = {
  route: "simulation",
  status: "idle",
  running: false,
  progress: 0,
  cycle: 0,
  elapsedSeconds: 0,
  totalCycles: 3,
  currentJobId: null,
  currentResult: null,
  toastTimer: null,
  pollTimer: null,
};

const parameterNominalCapacity = {
  chen2020: 5,
  okane2022: 5,
  hithium280: 280,
  hithium314: 314,
  hithium587: 587,
  mic1175: 1175,
};

// 1P 基准电压：1P[W] = 标称容量[Ah] × 此电压，与后端 jobs.py 默认 3.2 V 一致
const NOMINAL_VOLTAGE_V = 3.2;

const iconPaths = {
  home: '<path d="M3 10.5 12 3l9 7.5"></path><path d="M5 10v10h14V10"></path><path d="M9 20v-6h6v6"></path>',
  "file-plus": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path><path d="M14 2v6h6"></path><path d="M12 11v6"></path><path d="M9 14h6"></path>',
  folder: '<path d="M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v8A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5Z"></path>',
  upload: '<path d="M12 16V4"></path><path d="m7 9 5-5 5 5"></path><path d="M20 16v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3"></path>',
  download: '<path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M20 18v2H4v-2"></path>',
  table: '<rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M3 10h18"></path><path d="M9 4v16"></path>',
  settings: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"></path><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.03.03a2.1 2.1 0 0 1-2.97 2.97l-.03-.03A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 1.62V21a2.1 2.1 0 0 1-4.2 0v-.05A1.8 1.8 0 0 0 8.8 19.4a1.8 1.8 0 0 0-1.98.36l-.03.03a2.1 2.1 0 0 1-2.97-2.97l.03-.03A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.62-1H3a2.1 2.1 0 0 1 0-4.2h.05A1.8 1.8 0 0 0 4.6 8.8a1.8 1.8 0 0 0-.36-1.98l-.03-.03a2.1 2.1 0 0 1 2.97-2.97l.03.03A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-1.62V3a2.1 2.1 0 0 1 4.2 0v.05A1.8 1.8 0 0 0 15.2 4.6a1.8 1.8 0 0 0 1.98-.36l.03-.03a2.1 2.1 0 0 1 2.97 2.97l-.03.03A1.8 1.8 0 0 0 19.4 9a1.8 1.8 0 0 0 1.62 1H21a2.1 2.1 0 0 1 0 4.2h-.05A1.8 1.8 0 0 0 19.4 15Z"></path>',
  pulse: '<path d="M3 12h4l2-7 4 14 2-7h6"></path>',
  bar: '<path d="M4 20V10"></path><path d="M10 20V4"></path><path d="M16 20v-7"></path><path d="M22 20H2"></path>',
  flask: '<path d="M9 2h6"></path><path d="M10 2v6l-5.6 9.4A3 3 0 0 0 7 22h10a3 3 0 0 0 2.6-4.6L14 8V2"></path><path d="M7 16h10"></path>',
  sliders: '<path d="M4 21v-7"></path><path d="M4 10V3"></path><path d="M12 21v-9"></path><path d="M12 8V3"></path><path d="M20 21v-5"></path><path d="M20 12V3"></path><path d="M2 14h4"></path><path d="M10 8h4"></path><path d="M18 16h4"></path>',
  target: '<circle cx="12" cy="12" r="9"></circle><circle cx="12" cy="12" r="5"></circle><circle cx="12" cy="12" r="1.5"></circle>',
  network: '<rect x="3" y="3" width="6" height="6" rx="1"></rect><rect x="15" y="3" width="6" height="6" rx="1"></rect><rect x="9" y="15" width="6" height="6" rx="1"></rect><path d="M9 6h6"></path><path d="m6 9 5 6"></path><path d="m18 9-5 6"></path>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z"></path>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"></ellipse><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"></path><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"></path>',
  edit: '<path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path>',
  menu: '<path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h16"></path>',
  help: '<circle cx="12" cy="12" r="9"></circle><path d="M9.7 9a2.5 2.5 0 1 1 4.4 1.7c-.9.7-2.1 1.2-2.1 2.8"></path><path d="M12 17h.01"></path>',
  sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.9 4.9 1.4 1.4"></path><path d="m17.7 17.7 1.4 1.4"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m4.9 19.1 1.4-1.4"></path><path d="m17.7 6.3 1.4-1.4"></path>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"></path><path d="M10 21h4"></path>',
  user: '<circle cx="12" cy="8" r="4"></circle><path d="M4 21a8 8 0 0 1 16 0"></path>',
  data: '<rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M8 8h8"></path><path d="M8 12h8"></path><path d="M8 16h5"></path>',
  wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.5 5.5l-5.4 5.4a2 2 0 1 0 2.8 2.8l5.4-5.4a4 4 0 0 0 5.5-5.5l-2.9 2.9-2.8-2.8Z"></path>',
  atom: '<circle cx="12" cy="12" r="1.5"></circle><path d="M20.2 12c0 2-3.7 3.6-8.2 3.6S3.8 14 3.8 12 7.5 8.4 12 8.4s8.2 1.6 8.2 3.6Z"></path><path d="M16.1 19.1c-1.7 1-4.9-1.4-7.2-5.3S6.3 6 8 5s4.9 1.4 7.2 5.3 2.6 7.8.9 8.8Z"></path><path d="M7.9 19.1c-1.7-1-.9-4.9 1.4-8.8S14.8 4 16.5 5 17.4 9.9 15.1 13.8s-5.5 6.3-7.2 5.3Z"></path>',
  play: '<path d="m8 5 12 7-12 7Z"></path>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="1"></rect>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"></path><path d="M17 21v-8H7v8"></path><path d="M7 3v5h8"></path>',
  more: '<circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle>',
  branch: '<circle cx="6" cy="6" r="2"></circle><circle cx="18" cy="18" r="2"></circle><circle cx="6" cy="18" r="2"></circle><path d="M8 6h4a4 4 0 0 1 4 4v6"></path><path d="M6 8v8"></path>',
  wave: '<path d="M3 16c3 0 3-8 6-8s3 8 6 8 3-8 6-8"></path>',
  repeat: '<path d="m17 2 4 4-4 4"></path><path d="M3 11V9a3 3 0 0 1 3-3h15"></path><path d="m7 22-4-4 4-4"></path><path d="M21 13v2a3 3 0 0 1-3 3H3"></path>',
  pin: '<path d="M12 17v5"></path><path d="M7 9a5 5 0 1 1 10 0c0 3.5-5 8-5 8S7 12.5 7 9Z"></path><circle cx="12" cy="9" r="1.5"></circle>',
  "chevron-up": '<path d="m18 15-6-6-6 6"></path>',
  "chevron-down": '<path d="m6 9 6 6 6-6"></path>',
  chart: '<path d="M3 3v18h18"></path><path d="m7 15 4-4 3 3 5-7"></path>',
  image: '<rect x="3" y="5" width="18" height="14" rx="2"></rect><circle cx="8" cy="10" r="1.5"></circle><path d="m21 15-5-5L5 21"></path>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path><path d="M14 2v6h6"></path>',
};

function iconMarkup(name) {
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${iconPaths[name] || iconPaths.chart}</svg>`;
}

function installIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((node) => {
    node.innerHTML = iconMarkup(node.dataset.icon);
  });
}

function fmtClock(seconds) {
  const sec = Math.max(0, Math.floor(seconds));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function showToast(message) {
  const toast = document.querySelector(".toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2200);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload.error || `API 请求失败: ${response.status}`);
  }
  return payload;
}

function readNumber(selector, fallback) {
  const value = Number.parseFloat(document.querySelector(selector)?.value);
  return Number.isFinite(value) ? value : fallback;
}

function collectSimulationRequest() {
  return {
    model: document.querySelector("#modelSelect")?.value || "dfn",
    parameter_set: document.querySelector("#parameterSet")?.value || "chen2020",
    rate_unit: document.querySelector("#cycleMode")?.value || "C",
    charge_rate: readNumber("#chargeRate", 0.5),
    discharge_rate: readNumber("#dischargeRate", 0.5),
    charge_cutoff_v: readNumber("#chargeCutoff", 4.2),
    discharge_cutoff_v: readNumber("#dischargeCutoff", 2.5),
    temperature_c: readNumber("#temperatureC", 25),
    cycles: Math.max(1, Math.round(readNumber("#cycleCount", 1))),
    run_mode: "production",
    dcr_enabled: Boolean(document.querySelector("#dcrEnabled")?.checked),
    dcr_soc: readNumber("#dcrSoc", 50) / 100,
    dcr_rate: readNumber("#dcrRate", 0.5),
    dcr_duration_s: readNumber("#dcrDuration", 10),
    dcr_every_cycles: Math.max(1, Math.round(readNumber("#dcrEvery", 100))),
    aging_enabled: Boolean(document.querySelector("#agingEnabled")?.checked),
    aging_options: {
      SEI: document.querySelector("#agingSei")?.value || "none",
      "SEI film resistance": document.querySelector("#agingSeiFilm")?.value || "none",
      "SEI porosity change": document.querySelector("#agingSeiPorosity")?.value || "false",
      "SEI on cracks": document.querySelector("#agingSeiCracks")?.value || "false",
      "lithium plating": document.querySelector("#agingPlating")?.value || "none",
      "lithium plating porosity change": document.querySelector("#agingPlatingPorosity")?.value || "false",
      "particle mechanics": document.querySelector("#agingMechanics")?.value || "none",
      "stress-induced diffusion": document.querySelector("#agingStressDiffusion")?.value || "false",
      "loss of active material": document.querySelector("#agingLam")?.value || "none",
    },
    rest_minutes: Math.max(0, Math.round(readNumber("#restMinutes", 5))),
  };
}

function setRoute(route) {
  state.route = route || "simulation";
  document.querySelector(".app-shell").dataset.route = state.route;
  document.querySelectorAll(".nav-item, .module-tabs a").forEach((item) => {
    const target = item.getAttribute("href")?.replace("#", "");
    item.classList.toggle("active", target === state.route || (state.route === "simulation" && target === "simulation"));
  });
}

function createPreviewRows() {
  const rows = [
    ["1", "3.102", "11.42", "10.83", "94.83"],
    ["2", "3.098", "11.40", "10.81", "94.82"],
    ["3", "3.094", "11.37", "10.78", "94.81"],
    ["...", "...", "...", "...", "..."],
    ["498", "2.351", "8.53", "7.95", "93.20"],
    ["499", "2.347", "8.51", "7.93", "93.17"],
    ["500", "2.342", "8.49", "7.90", "93.05"],
  ];
  document.getElementById("previewRows").innerHTML = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
    .join("");
}

function createLogRows() {
  renderLogs([]);
}

function linePath(points, x, y) {
  return points.map((point, index) => `${index ? "L" : "M"}${x(point[0]).toFixed(1)} ${y(point[1]).toFixed(1)}`).join(" ");
}

function areaPath(points, x, y, baseY) {
  return `${linePath(points, x, y)} L${x(points.at(-1)[0]).toFixed(1)} ${baseY} L${x(points[0][0]).toFixed(1)} ${baseY} Z`;
}

function makeScale(domain, range) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  return (value) => r0 + ((value - d0) / (d1 - d0)) * (r1 - r0);
}

function coolwarm(t) {
  // coolwarm 近似：蓝 -> 浅灰 -> 红，t∈[0,1] 映射循环序号
  const u = Math.max(0, Math.min(1, t));
  const stops = [[59, 76, 192], [221, 221, 221], [180, 4, 38]];
  const [a, b, f] = u < 0.5 ? [stops[0], stops[1], u / 0.5] : [stops[1], stops[2], (u - 0.5) / 0.5];
  const mix = (i) => Math.round(a[i] + (b[i] - a[i]) * f);
  return `rgb(${mix(0)},${mix(1)},${mix(2)})`;
}

function drawColorbar(svgId, { width, height, margin, vmin, vmax }) {
  // 在图右侧画 coolwarm 渐变 colorbar（循环号），需在 drawLineChart 之后调用（它会清空 svg）
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const barW = 9;
  const barX = width - margin.right + 14;
  const barY = margin.top;
  const barH = height - margin.top - margin.bottom;
  const gid = `${svgId}-cbGrad`;
  const stops = [0, 0.25, 0.5, 0.75, 1]
    .map((s) => `<stop offset="${s}" stop-color="${coolwarm(s)}"></stop>`)
    .join("");
  // y1=1(底) -> y2=0(顶)：底部=低循环(蓝)，顶部=高循环(红)
  let html = `<defs><linearGradient id="${gid}" x1="0" y1="1" x2="0" y2="0">${stops}</linearGradient></defs>`;
  html += `<rect x="${barX}" y="${barY}" width="${barW}" height="${barH}" rx="2" fill="url(#${gid})"></rect>`;
  const span = Math.max(1, vmax - vmin);
  const ticks = [vmin, Math.round((vmin + vmax) / 2), vmax];
  ticks.forEach((c) => {
    const ty = barY + barH * (1 - (c - vmin) / span);
    html += `<text class="tick-label" x="${barX + barW + 3}" y="${ty + 3}">${c}</text>`;
  });
  html += `<text class="tick-label" x="${barX + barW / 2}" y="${barY - 4}" text-anchor="middle">循环</text>`;
  svg.insertAdjacentHTML("beforeend", html);
}

function finitePairs(xValues, yValues) {
  const count = Math.min(xValues?.length || 0, yValues?.length || 0);
  const pairs = [];
  for (let index = 0; index < count; index += 1) {
    if (xValues[index] === null || yValues[index] === null || xValues[index] === "" || yValues[index] === "") {
      continue;
    }
    const x = Number(xValues[index]);
    const y = Number(yValues[index]);
    if (Number.isFinite(x) && Number.isFinite(y)) {
      pairs.push([x, y]);
    }
  }
  return pairs;
}

function paddedDomain(values, fallback, padRatio = 0.08) {
  const finite = values.map(Number).filter(Number.isFinite);
  if (!finite.length) return fallback;
  let min = Math.min(...finite);
  let max = Math.max(...finite);
  if (Math.abs(max - min) < 1e-9) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * padRatio;
  return [min - pad, max + pad];
}

function ticksForDomain(domain, count = 4) {
  const [min, max] = domain;
  if (!Number.isFinite(min) || !Number.isFinite(max) || count < 2) return [];
  return Array.from({ length: count }, (_, index) => {
    const value = min + ((max - min) * index) / (count - 1);
    const abs = Math.abs(value);
    if (abs >= 100) return Math.round(value);
    if (abs >= 10) return Number(value.toFixed(1));
    return Number(value.toFixed(2));
  });
}

const resultChartSpec = {
  width: 360,
  height: 240,
  margin: { top: 14, right: 14, bottom: 40, left: 48 },
};

function cycleAxisForPointSets(pointSets, fallbackMax = 100) {
  const finiteCycles = pointSets
    .flat()
    .map((point) => Number(point?.[0]))
    .filter((value) => Number.isFinite(value) && value >= 0);
  const rawMax = Math.max(fallbackMax, finiteCycles.length ? Math.max(...finiteCycles) : 0);
  const axisMax = Math.max(100, Math.ceil(rawMax / 100) * 100);
  const step = Math.max(100, Math.ceil(axisMax / 5 / 100) * 100);
  const ticks = [];
  for (let tick = 0; tick <= axisMax; tick += step) {
    ticks.push(tick);
  }
  if (ticks.at(-1) !== axisMax) ticks.push(axisMax);
  return { xDomain: [0, axisMax], xTicks: ticks };
}

function drawAxes(svg, config) {
  const { width, height, margin, xTicks = [], yTicks = [], xScale, yScale, ylabel } = config;
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const axisX = margin.left;
  const axisY = height - margin.bottom;
  const fragments = [];

  yTicks.forEach((tick) => {
    const y = yScale(tick);
    fragments.push(`<path class="grid-line" fill="none" d="M${axisX} ${y}H${axisX + plotW}"></path>`);
    fragments.push(`<text class="tick-label" x="${axisX - 8}" y="${y + 3}" text-anchor="end">${tick}</text>`);
  });
  xTicks.forEach((tick) => {
    const x = xScale(tick);
    fragments.push(`<text class="tick-label" x="${x}" y="${axisY + 16}" text-anchor="middle">${tick}</text>`);
  });
  fragments.push(`<path class="chart-axis" fill="none" d="M${axisX} ${margin.top}V${axisY}H${axisX + plotW}"></path>`);
  if (ylabel) {
    fragments.push(`<text class="tick-label" x="13" y="${margin.top + plotH / 2}" text-anchor="middle" transform="rotate(-90 13 ${margin.top + plotH / 2})">${ylabel}</text>`);
  }
  svg.insertAdjacentHTML("beforeend", fragments.join(""));
}

function drawLineChart(id, options) {
  const svg = document.getElementById(id);
  if (!svg) return;
  const width = options.width || 270;
  const height = options.height || 190;
  const margin = options.margin || { top: 16, right: 16, bottom: 30, left: 34 };
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const xScale = makeScale(options.xDomain, [margin.left, width - margin.right]);
  const yScale = makeScale(options.yDomain, [height - margin.bottom, margin.top]);
  svg.innerHTML = "";
  drawAxes(svg, { width, height, margin, xScale, yScale, xTicks: options.xTicks, yTicks: options.yTicks, ylabel: options.ylabel });
  options.lines.forEach((line) => {
    const dash = line.dashed ? " chart-dashed" : "";
    const points = line.points ? line.points : line.y.map((value, index) => [line.x[index], value]);
    const styleParts = [];
    if (line.color) styleParts.push(`stroke:${line.color}`);
    if (line.width) styleParts.push(`stroke-width:${line.width}`);
    const style = styleParts.length ? ` style="${styleParts.join(";")}"` : "";
    svg.insertAdjacentHTML(
      "beforeend",
      `<path class="chart-line ${line.className || ""}${dash}" fill="none"${style} d="${linePath(points, xScale, yScale)}"></path>`
    );
    if (line.pointsVisible) {
      points.forEach((point) => {
        svg.insertAdjacentHTML(
          "beforeend",
          `<circle cx="${xScale(point[0])}" cy="${yScale(point[1])}" r="2.4" fill="${line.dot || "#2563eb"}"></circle>`
        );
      });
    }
  });
  if (options.xlabel) {
    svg.insertAdjacentHTML("beforeend", `<text class="tick-label" x="${width / 2}" y="${height - 2}" text-anchor="middle">${options.xlabel}</text>`);
  }
  if (options.legend) {
    const x = width - margin.right - 92;
    const y = margin.top + 76;
    const items = options.legend.map((item, index) => {
      const iy = y + index * 20;
      const dash = item.dashed ? ' stroke-dasharray="5 4"' : "";
      return `<path d="M${x} ${iy}h22" fill="none" stroke="${item.color}" stroke-width="2"${dash}></path><text class="legend-label" x="${x + 30}" y="${iy + 4}">${item.label}</text>`;
    });
    svg.insertAdjacentHTML("beforeend", `<g>${items.join("")}</g>`);
  }
}

function getNominalCapacity() {
  const parameterSet = document.querySelector("#parameterSet")?.value || "chen2020";
  return parameterNominalCapacity[parameterSet] || 5;
}

function updateNominalCapacity() {
  const capacity = getNominalCapacity();
  const capacityInput = document.querySelector("#nominalCapacity");
  if (capacityInput) capacityInput.value = String(capacity);
  return capacity;
}

function updateCurrentPreview() {
  const capacity = updateNominalCapacity();
  const rateUnit = document.querySelector("#cycleMode")?.value || "C";
  const chargeRate = readNumber("#chargeRate", 0.5);
  const dischargeRate = readNumber("#dischargeRate", chargeRate);
  const peakRate = Math.max(Math.abs(chargeRate), Math.abs(dischargeRate));
  const isPower = rateUnit === "P";
  // 1P 基准功率 = 标称容量 × 标称电压（与后端 jobs.py 的 3.2 V 基准一致）
  const value = isPower ? peakRate * capacity * NOMINAL_VOLTAGE_V : peakRate * capacity;
  const currentInput = document.querySelector("#currentPreview");
  if (currentInput) currentInput.value = value >= 100 ? value.toFixed(0) : value.toFixed(2);
  document.querySelector("#currentPreviewUnit")?.replaceChildren(isPower ? "W" : "A");
  document.querySelector("#chargeRateUnit")?.replaceChildren(rateUnit);
  document.querySelector("#dischargeRateUnit")?.replaceChildren(rateUnit);
  const hint = document.querySelector("#modelHint");
  if (hint) {
    hint.textContent = isPower
      ? `当前参数集标称容量 ${capacity} Ah，1P 基准 ${NOMINAL_VOLTAGE_V} V，${chargeRate}P/${dischargeRate}P 对应 ${currentInput?.value} W。`
      : `当前参数集标称容量 ${capacity} Ah，${chargeRate}C/${dischargeRate}C 对应 ${currentInput?.value} A。`;
  }
  return { capacity, chargeRate, dischargeRate, current: value };
}

function drawConditionChart() {
  const { chargeRate, dischargeRate, current } = updateCurrentPreview();
  const chargeCutoff = readNumber("#chargeCutoff", 4.2);
  const dischargeCutoff = readNumber("#dischargeCutoff", 2.5);
  const restMinutes = Math.max(0, readNumber("#restMinutes", 5));
  const chargeHours = Math.max(0.12, 1 / Math.max(chargeRate, 0.05));
  const restHours = restMinutes / 60;
  const dischargeHours = Math.max(0.12, 1 / Math.max(dischargeRate, 0.05));
  const t0 = 0;
  const t1 = chargeHours * 0.72;
  const t2 = chargeHours;
  const t3 = t2 + restHours;
  const t4 = t3 + dischargeHours;
  const currentScale = Math.max(current, 1);
  const chargeLevel = current / currentScale;
  const dischargeLevel = -current / currentScale;
  drawLineChart("conditionChart", {
    width: 340,
    height: 150,
    margin: { top: 12, right: 12, bottom: 28, left: 28 },
    xDomain: [0, Math.max(1, t4)],
    yDomain: [-1.15, 1.15],
    xTicks: ticksForDomain([0, Math.max(1, t4)], 4),
    yTicks: [-1, 0, 1],
    xlabel: "时间 (h)",
    lines: [
      { className: "chart-blue", points: [[t0, 0], [t0 + 0.02, chargeLevel], [t1, chargeLevel], [t2, chargeLevel * 0.22], [t2, 0], [t3, 0], [t3 + 0.02, dischargeLevel], [t4, dischargeLevel], [t4, 0]] },
    ],
  });
  const svg = document.getElementById("conditionChart");
  svg.insertAdjacentHTML(
    "beforeend",
    `<text class="tick-label" x="34" y="18">电流: ${current.toFixed(1)} A</text><text class="tick-label" x="82" y="48">充电至 ${chargeCutoff}V</text><text class="tick-label" x="172" y="76">静置 ${restMinutes}min</text><text class="tick-label" x="238" y="112">放电至 ${dischargeCutoff}V</text>`
  );
}

function drawAgingChart() {
  const svg = document.getElementById("agingChart");
  const width = 360;
  const height = 190;
  const margin = { top: 12, right: 58, bottom: 32, left: 36 };
  const xScale = makeScale([0, 3.8], [margin.left, width - margin.right]);
  const yScale = makeScale([2, 4.5], [height - margin.bottom, margin.top]);
  svg.innerHTML = "";
  drawAxes(svg, { width, height, margin, xScale, yScale, xTicks: [0, 0.8, 1.6, 2.4, 3.8], yTicks: [2, 3, 4, 4.5] });
  for (let i = 0; i < 36; i += 1) {
    const t = i / 35;
    const cutoff = 2.85 + 0.62 * (1 - t) + 0.16 * Math.sin(t * Math.PI);
    const points = [];
    for (let j = 0; j <= 44; j += 1) {
      const x = (j / 44) * cutoff;
      const y = 4.28 - 0.26 * Math.log1p(x * 1.7) - 0.05 * t - 1.75 / (1 + Math.exp(-(x - cutoff + 0.24) * 14));
      points.push([x, y]);
    }
    const hue = 220 - t * 195;
    const color = `hsl(${hue}, 88%, ${54 + t * 4}%)`;
    svg.insertAdjacentHTML("beforeend", `<path class="chart-line" fill="none" d="${linePath(points, xScale, yScale)}" stroke="${color}" opacity="0.82"></path>`);
  }
  const red = [[0, 4.22], [0.25, 3.98], [0.75, 3.85], [1.25, 3.55], [1.65, 3.05], [1.82, 2.55]];
  svg.insertAdjacentHTML("beforeend", `<path class="chart-line chart-red" fill="none" d="${linePath(red, xScale, yScale)}"></path>`);
  const barX = width - 36;
  const grad = '<defs><linearGradient id="cycleGrad" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#2455e8"></stop><stop offset="0.55" stop-color="#f4d443"></stop><stop offset="1" stop-color="#e11d48"></stop></linearGradient></defs>';
  svg.insertAdjacentHTML("afterbegin", grad);
  svg.insertAdjacentHTML("beforeend", `<rect x="${barX}" y="22" width="14" height="126" fill="url(#cycleGrad)"></rect><text class="tick-label" x="${barX + 28}" y="30">500</text><text class="tick-label" x="${barX + 28}" y="149">1</text><text class="tick-label" x="${barX - 7}" y="14">循环序号</text><text class="tick-label" x="180" y="184" text-anchor="middle">容量 (Ah)</text>`);
}

function drawResultChart(id, title, yDomain, blue, red, options = {}) {
  const { width, height, margin } = resultChartSpec;
  const { xDomain, xTicks } = cycleAxisForPointSets([blue, red], options.maxCycle || 1000);
  drawLineChart(id, {
    width,
    height,
    margin,
    xDomain,
    yDomain,
    xTicks,
    yTicks: options.yTicks,
    ylabel: options.ylabel,
    xlabel: "循环次数",
    lines: [
      { className: "chart-blue", points: blue, pointsVisible: true, dot: "#2563eb" },
      { className: "chart-red", points: red, pointsVisible: true, dot: "#ef4444" },
    ],
    legend: [
      { label: "仿真", color: "#2563eb" },
      { label: "实验", color: "#ef4444" },
    ],
  });
  const svg = document.getElementById(id);
  if (options.threshold) {
    const xScale = makeScale(xDomain, [margin.left, width - margin.right]);
    const yScale = makeScale(yDomain, [height - margin.bottom, margin.top]);
    const y = yScale(options.threshold.value);
    svg.insertAdjacentHTML("beforeend", `<path d="M${xScale(xDomain[0])} ${y}H${xScale(xDomain[1])}" fill="none" stroke="#8b98aa" stroke-width="1" stroke-dasharray="5 4"></path><text class="tick-label" x="${xScale(xDomain[0]) + 8}" y="${y - 5}">${options.threshold.label}</text>`);
  }
}

function drawCharts() {
  drawConditionChart();
  drawLineChart("voltageChart", {
    xDomain: [0, 7],
    yDomain: [2, 4.5],
    xTicks: [0, 1.2, 2.5, 6, 7],
    yTicks: [2, 3, 4, 4.5],
    xlabel: "时间 (h)",
    lines: [
      { className: "chart-blue", points: [[0, 3.0], [0.1, 3.5], [0.4, 3.72], [1.7, 4.12], [1.85, 4.22], [2.05, 3.18], [2.23, 3.55], [2.8, 3.85], [5.6, 4.18], [6.8, 4.26]] },
      { className: "chart-red", dashed: true, points: [[2.0, 2.7], [2.12, 3.45], [2.55, 3.78], [4.5, 3.98], [6.7, 4.22]] },
    ],
    legend: [
      { label: "仿真", color: "#2563eb" },
      { label: "数据", color: "#ef4444", dashed: true },
    ],
  });

  drawLineChart("currentChart", {
    xDomain: [0, 4],
    yDomain: [-2, 2],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [-2, -1, 0, 1, 2],
    xlabel: "时间 (h)",
    lines: [
      { className: "chart-blue", points: [[0, 1.65], [1.0, 1.65], [1.02, -1.9], [2.55, -1.9], [2.58, 1.78], [3.5, 1.78], [3.52, 0.02], [4, 0.02]] },
    ],
  });

  drawLineChart("temperatureChart", {
    xDomain: [0, 3],
    yDomain: [24, 32],
    xTicks: [0, 1.2, 2.1, 3],
    yTicks: [24, 26, 28, 30, 32],
    xlabel: "时间 (h)",
    lines: [
      { className: "chart-blue", points: [[0, 25.5], [0.5, 26.5], [1.1, 27.4], [1.55, 28.6], [1.85, 29.3], [2.15, 29.4], [2.3, 28.5], [2.7, 27.7], [3, 27.3]] },
    ],
  });

  drawAgingChart();

  const cycles = [0, 80, 160, 240, 320, 420, 520, 620, 720, 820, 920, 1000];
  const capBlue = cycles.map((cycle, index) => [cycle, 3.35 - 0.00075 * cycle - 0.00000052 * cycle * cycle + (index % 2 ? 0.025 : -0.012)]);
  const capRed = cycles.map((cycle, index) => [cycle, 3.35 - 0.0009 * cycle - 0.00000082 * cycle * cycle + (index % 2 ? -0.012 : 0.018)]);
  drawResultChart("capacityChart", "容量衰减", [1.5, 3.5], capBlue, capRed, {
    yTicks: [1.5, 2, 2.5, 3, 3.5],
    threshold: { value: 2.4, label: "80% 2.40Ah" },
  });

  const resBlue = cycles.map((cycle) => [cycle, 18 + cycle * 0.022]);
  const resRed = cycles.map((cycle, index) => [cycle, 18 + cycle * 0.029 + Math.max(0, index - 8) * 2.1]);
  drawResultChart("resistanceChart", "内阻增长", [15, 60], resBlue, resRed, {
    yTicks: [20, 30, 40, 50, 60],
    ylabel: "DCR (mΩ)",
  });

  const effBlue = cycles.map((cycle, index) => [cycle, 98.5 - cycle * 0.0038 + (index % 2 ? -0.06 : 0.04)]);
  const effRed = cycles.map((cycle, index) => [cycle, 98.9 - cycle * 0.0042 + (index % 2 ? 0.08 : -0.03)]);
  drawResultChart("efficiencyChart", "能量效率", [88, 100], effBlue, effRed, {
    yTicks: [88, 92, 96, 100],
  });
}

function updateRunStatus() {
  const remainingSeconds = state.running
    ? Math.max(0, Math.round(state.elapsedSeconds * (100 - state.progress) / Math.max(state.progress, 1)))
    : null;
  const statusLabels = {
    idle: "待运行",
    queued: "排队中",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
    canceled: "已停止",
  };
  document.getElementById("progressText").textContent = `${state.progress.toFixed(1)}%`;
  document.getElementById("progressBar").style.width = `${state.progress}%`;
  document.getElementById("cycleText").textContent = `${state.cycle} / ${state.totalCycles}`;
  document.getElementById("elapsedTime").textContent = fmtClock(state.elapsedSeconds);
  document.getElementById("remainingTime").textContent = remainingSeconds === null ? "--:--:--" : fmtClock(remainingSeconds);
  document.getElementById("simTime").textContent = `${(state.cycle * 0.345).toFixed(2)} h`;
  document.getElementById("runStatus").textContent = statusLabels[state.status] || state.status;
  document.querySelector('[data-action="stop"]').disabled = !state.running;
  document.querySelector(".status-dot")?.classList.toggle("error", state.status === "failed");
  document.querySelector(".status-dot")?.classList.toggle("done", state.status === "completed");
  document.querySelector(".status-dot")?.classList.toggle("idle", !state.running && state.status !== "completed" && state.status !== "failed");
}

function applyJobStatus(status) {
  state.status = status.status || "idle";
  state.running = state.status === "running" || state.status === "queued";
  state.progress = Number(status.progress || 0);
  state.cycle = Number(status.current_cycle || 0);
  state.totalCycles = Number(status.total_cycles || 1);
  state.elapsedSeconds = Number(status.elapsed_s || 0);
  state.currentJobId = status.job_id || state.currentJobId;
  updateRunStatus();
  renderLogs(status.logs || []);
}

function renderLogs(logs) {
  const rows = logs.length ? logs : [{ time: "--:--:--", level: "INFO", message: "等待创建真实仿真任务" }];
  document.getElementById("logRows").innerHTML = rows
    .slice(-8)
    .map((row) => `<tr><td>${row.time}</td><td>${row.level}</td><td>${row.message}</td></tr>`)
    .join("");
}

async function startRunSimulation() {
  if (state.running) {
    showToast("仿真已经在运行中");
    return;
  }
  const request = collectSimulationRequest();
  state.currentResult = null;
  showToast("正在提交真实 PyBaMM 仿真任务");
  const status = await apiFetch("/api/jobs", {
    method: "POST",
    body: JSON.stringify(request),
  });
  applyJobStatus(status);
  if (status.request?.run_mode === "smoke" && status.cycles_requested > status.total_cycles) {
    showToast(`已创建 smoke run：${status.total_cycles} 圈，避免误跑 ${status.cycles_requested} 圈长任务`);
  } else {
    showToast(`已创建完整运行：${status.total_cycles} 圈`);
  }
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(pollJobStatus, 1200);
}

async function pollJobStatus() {
  if (!state.currentJobId) return;
  try {
    const status = await apiFetch(`/api/jobs/${state.currentJobId}`);
    applyJobStatus(status);
    if (["completed", "failed", "canceled"].includes(status.status)) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      if (status.status === "completed") {
        state.currentResult = await apiFetch(`/api/jobs/${state.currentJobId}/results`);
        renderSimulationResult(state.currentResult);
        showToast("仿真完成，结果已刷新");
      } else if (status.status === "failed") {
        showToast(status.error || "仿真失败，请查看日志");
      } else {
        showToast("仿真任务已停止");
      }
    }
  } catch (error) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
    state.running = false;
    state.status = "failed";
    updateRunStatus();
    showToast(error.message);
  }
}

async function stopRunSimulation() {
  if (!state.currentJobId) {
    state.status = "canceled";
    state.running = false;
    updateRunStatus();
    showToast("没有正在运行的真实任务");
    return;
  }
  const status = await apiFetch(`/api/jobs/${state.currentJobId}/stop`, { method: "POST" });
  clearInterval(state.pollTimer);
  state.pollTimer = null;
  applyJobStatus(status);
  showToast("已请求停止仿真任务");
}

function downloadCsv() {
  if (state.currentJobId && state.currentResult) {
    window.location.href = `/api/jobs/${state.currentJobId}/export.csv`;
    showToast("正在下载真实仿真 CSV");
    return;
  }
  const csv = [
    "cycle,capacity_ah,resistance_mohm,efficiency_pct",
    "1,3.102,18.4,98.7",
    "250,2.912,24.5,97.6",
    "500,2.342,31.2,95.1",
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "battery_sim_results.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("当前还没有真实结果，已导出示例 CSV");
}

async function fetchSimulationSnapshot() {
  if (!state.currentJobId) return null;
  return apiFetch(`/api/jobs/${state.currentJobId}`);
}

function renderTimeSeriesChart(id, yValues, label, options = {}) {
  const time = state.currentResult?.series?.time_h || [];
  const points = finitePairs(time, yValues);
  if (!points.length) return;
  const xValues = points.map((point) => point[0]);
  const yOnly = points.map((point) => point[1]);
  const xDomain = paddedDomain(xValues, [0, 1], 0.02);
  const yDomain = paddedDomain(yOnly, options.fallbackDomain || [0, 1]);
  drawLineChart(id, {
    xDomain,
    yDomain,
    xTicks: ticksForDomain(xDomain, 4),
    yTicks: ticksForDomain(yDomain, 4),
    xlabel: "时间 (h)",
    lines: [
      { className: "chart-blue", points },
    ],
    legend: label ? [{ label, color: "#2563eb" }] : undefined,
  });
}

function renderCycleChart(id, yValues, label, options = {}) {
  const cycles = state.currentResult?.cycle_metrics?.cycle || [];
  const points = finitePairs(cycles, yValues);
  if (!points.length) return;
  const xValues = points.map((point) => point[0]);
  const yOnly = points.map((point) => point[1]);
  const { width, height, margin } = resultChartSpec;
  const { xDomain, xTicks } = cycleAxisForPointSets([points], options.maxCycle || Math.max(...xValues, 1));
  const yDomain = paddedDomain(yOnly, options.fallbackDomain || [0, 1]);
  drawLineChart(id, {
    width,
    height,
    margin,
    xDomain,
    yDomain,
    xTicks,
    yTicks: ticksForDomain(yDomain, 4),
    xlabel: "循环次数",
    lines: [
      { className: "chart-blue", points, pointsVisible: true, dot: "#2563eb" },
    ],
    legend: [{ label, color: "#2563eb" }],
  });
}

function renderCyclePlaceholder(id, title, message, options = {}) {
  const svg = document.getElementById(id);
  if (!svg) return;
  const { width, height, margin } = resultChartSpec;
  const { xDomain, xTicks } = cycleAxisForPointSets([], options.maxCycle || 100);
  const yDomain = options.yDomain || [0, 1];
  drawLineChart(id, {
    width,
    height,
    margin,
    xDomain,
    yDomain,
    xTicks,
    yTicks: options.yTicks || ticksForDomain(yDomain, 4),
    ylabel: options.ylabel,
    xlabel: "循环次数",
    lines: [],
  });
  svg.insertAdjacentHTML(
    "beforeend",
    `<text class="tick-label" x="${width / 2}" y="${height / 2 - 10}" text-anchor="middle">${title}</text><text class="tick-label" x="${width / 2}" y="${height / 2 + 14}" text-anchor="middle">${message}</text>`
  );
}

function renderCycleCurves(curves, series) {
  // 充放电曲线随循环演化：按循环号用 coolwarm 上色，充放电合并到一张图
  if (curves.length) {
    const minCycle = curves[0].cycle || 1;
    const maxCycle = curves[curves.length - 1].cycle || curves.length;
    const span = Math.max(1, maxCycle - minCycle);
    const lines = [];
    const allPoints = [];
    curves.forEach((cv) => {
      const color = coolwarm((cv.cycle - minCycle) / span);
      ["charge", "discharge"].forEach((seg) => {
        const pts = (cv[seg] || []).filter((p) => p && p[0] != null && p[1] != null);
        if (pts.length > 1) {
          lines.push({ color, width: 1.1, points: pts });
          allPoints.push(...pts);
        }
      });
    });
    if (lines.length) {
      const xDomain = paddedDomain(allPoints.map((p) => p[0]), [0, 1]);
      const yDomain = paddedDomain(allPoints.map((p) => p[1]), [2, 4.5]);
      const margin = { top: 12, right: 56, bottom: 32, left: 36 };
      drawLineChart("agingChart", {
        width: 360,
        height: 190,
        margin,
        xDomain,
        yDomain,
        xTicks: ticksForDomain(xDomain, 4),
        yTicks: ticksForDomain(yDomain, 4),
        xlabel: "容量 (Ah)",
        lines,
      });
      drawColorbar("agingChart", { width: 360, height: 190, margin, vmin: minCycle, vmax: maxCycle });
      return;
    }
  }
  // fallback：整段 V vs 通量容量
  const voltageCapacity = finitePairs(series.capacity_ah || [], series.voltage_v || []);
  if (!voltageCapacity.length) return;
  const xDomain = paddedDomain(voltageCapacity.map((point) => point[0]), [0, 1]);
  const yDomain = paddedDomain(voltageCapacity.map((point) => point[1]), [2, 4.5]);
  drawLineChart("agingChart", {
    width: 360,
    height: 190,
    margin: { top: 12, right: 32, bottom: 32, left: 36 },
    xDomain,
    yDomain,
    xTicks: ticksForDomain(xDomain, 4),
    yTicks: ticksForDomain(yDomain, 4),
    xlabel: "容量 (Ah)",
    lines: [{ className: "chart-blue", points: voltageCapacity }],
  });
}

function renderSimulationResult(result) {
  state.currentResult = result;
  const series = result.series || {};
  const metrics = result.cycle_metrics || {};
  const request = result.request || {};
  const maxCycle = Math.max(...(metrics.cycle || [request.cycles || 100]).map((value) => Number(value) || 0), 1);
  renderTimeSeriesChart("voltageChart", series.voltage_v, "真实仿真", { fallbackDomain: [2, 4.5] });
  renderTimeSeriesChart("currentChart", series.current_a, "真实仿真", { fallbackDomain: [-2, 2] });
  renderTimeSeriesChart("temperatureChart", series.temperature_c, "真实仿真", { fallbackDomain: [20, 40] });

  renderCycleCurves(result.cycle_curves || [], series);

  renderCycleChart("capacityChart", metrics.retention_pct || [], "真实仿真", { fallbackDomain: [99, 101], maxCycle });
  renderCycleChart("efficiencyChart", metrics.efficiency_pct || [], "真实仿真", { fallbackDomain: [80, 100], maxCycle });
  const dcr = result.dcr_series;
  const dcrPoints = dcr ? finitePairs(dcr.cycle || [], dcr.dcr_mohm || []) : [];
  if (dcrPoints.length) {
    const { width, height, margin } = resultChartSpec;
    const { xDomain, xTicks } = cycleAxisForPointSets([dcrPoints], maxCycle);
    const yDomain = paddedDomain(dcrPoints.map((p) => p[1]), [0, 1]);
    drawLineChart("resistanceChart", {
      width,
      height,
      margin,
      xDomain,
      yDomain,
      xTicks,
      yTicks: ticksForDomain(yDomain, 4),
      ylabel: "DCR (mΩ)",
      xlabel: "循环次数",
      lines: [{ className: "chart-blue", points: dcrPoints, pointsVisible: true, dot: "#2563eb" }],
      legend: [{ label: "DCR (mΩ)", color: "#2563eb" }],
    });
  } else {
    renderCyclePlaceholder("resistanceChart", "DCR 未计算", "勾选「DCR 仿真」后运行", {
      maxCycle,
      yDomain: [0, 1],
      yTicks: [0, 0.5, 1],
      ylabel: "DCR (mΩ)",
    });
  }

  const summary = result.summary || {};
  const initial = Number(summary.initial_capacity_ah);
  const final = Number(summary.final_capacity_ah);
  const retention = Number(summary.retention_pct);
  document.getElementById("summaryTitle").textContent = `真实仿真摘要 @ ${request.temperature_c ?? "--"}°C`;
  document.getElementById("summaryValue").textContent = Number.isFinite(final) ? final.toFixed(3) : "--";
  document.getElementById("summaryUnit").textContent = "Ah";
  document.getElementById("summaryLine1").textContent = Number.isFinite(initial)
    ? `初始容量: ${initial.toFixed(3)} Ah`
    : "初始容量: --";
  document.getElementById("summaryLine2").textContent = Number.isFinite(retention)
    ? `容量保持率: ${retention.toFixed(2)}%`
    : "容量保持率: --";
}

function wireInteractions() {
  document.addEventListener("click", async (event) => {
    const actionNode = event.target.closest("[data-action]");
    if (!actionNode) return;
    const action = actionNode.dataset.action;
    if (action === "toggle-menu") {
      document.querySelector(".app-shell").classList.toggle("menu-open");
    }
    if (action === "theme") {
      document.body.classList.toggle("light-alt");
      showToast("主题变量已切换");
    }
    if (action === "run") {
      try {
        await startRunSimulation();
      } catch (error) {
        state.status = "failed";
        state.running = false;
        updateRunStatus();
        showToast(error.message);
      }
    }
    if (action === "stop") {
      try {
        await stopRunSimulation();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "save") {
      showToast("项目配置已保存");
    }
    if (action === "export") {
      downloadCsv();
    }
    if (action === "preview") {
      drawConditionChart();
      showToast("工况预览已按当前模型容量和输入项更新");
    }
  });

  document.querySelectorAll(".segmented button, .mini-tabs button, .result-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      button.parentElement.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  window.addEventListener("hashchange", () => {
    setRoute(window.location.hash.replace("#", "") || "simulation");
    document.querySelector(".app-shell").classList.remove("menu-open");
  });

  [
    "#cycleMode",
    "#parameterSet",
    "#chargeRate",
    "#dischargeRate",
    "#chargeCutoff",
    "#dischargeCutoff",
    "#restMinutes",
  ].forEach((selector) => {
    document.querySelector(selector)?.addEventListener("change", updateCurrentPreview);
    document.querySelector(selector)?.addEventListener("input", updateCurrentPreview);
  });

  const dcrToggle = document.querySelector("#dcrEnabled");
  const dcrOptions = document.querySelector("#dcrOptions");
  dcrToggle?.addEventListener("change", () => {
    if (dcrOptions) dcrOptions.style.display = dcrToggle.checked ? "" : "none";
  });
}

function boot() {
  installIcons();
  createPreviewRows();
  createLogRows();
  drawCharts();
  wireInteractions();
  updateCurrentPreview();
  setRoute(window.location.hash.replace("#", "") || "simulation");
  updateRunStatus();
}

document.addEventListener("DOMContentLoaded", boot);
