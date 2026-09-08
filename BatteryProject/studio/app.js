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
  importedDataset: null,
  datasetSeries: null,
  extrapolation: null,
  savedConfig: null,
  projectMetadata: {
    project_name: "Demo_Project",
    cell_type: "NCM/Graphite",
    created_at: null,
  },
  runtime: {
    pybamm_version: "--",
  },
  toastTimer: null,
  pollTimer: null,
  pollFailures: 0,
  simTimeH: null,
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
  history: '<path d="M3.5 12a8.5 8.5 0 1 0 2.5-6L3.5 8.5"></path><path d="M3.5 3.5v5h5"></path><path d="M12 7.5V12l3 2"></path>',
  close: '<path d="m6 6 12 12"></path><path d="m18 6-12 12"></path>',
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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatMetric(value, options = {}) {
  if (value === null || value === undefined || value === "") return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  const digits = options.digits ?? 3;
  const suffix = options.suffix || "";
  if (digits === 0) return `${Math.round(number)}${suffix}`;
  return `${number.toFixed(digits).replace(/\.?0+$/, "")}${suffix}`;
}

function downloadUrl(url) {
  const link = document.createElement("a");
  link.href = url;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function formatProjectTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).replace("T", " ").slice(0, 16);
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
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
    const error = new Error(payload.error || payload.detail || `API 请求失败: ${response.status}`);
    error.status = response.status;
    throw error;
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

function collectProjectConfigPayload() {
  return {
    project_name: state.projectMetadata.project_name,
    project_metadata: state.projectMetadata,
    simulation_request: collectSimulationRequest(),
    current_job_id: state.currentJobId,
    dataset: state.importedDataset,
    ui: {
      route: state.route,
      saved_from: "Battery Sim Studio",
    },
  };
}

function renderProjectInfo() {
  document.getElementById("projectNameText").textContent = state.projectMetadata.project_name || "Demo_Project";
  document.getElementById("cellTypeValue").textContent = state.projectMetadata.cell_type || "NCM/Graphite";
  document.getElementById("projectCreatedAt").textContent = formatProjectTime(state.projectMetadata.created_at);
  document.getElementById("pybammVersion").textContent = state.runtime.pybamm_version || "--";
}

function applyProjectConfig(config, runtime = {}) {
  const metadata = config?.project_metadata || {};
  state.projectMetadata = {
    project_name: metadata.project_name || config?.project_name || state.projectMetadata.project_name || "Demo_Project",
    cell_type: metadata.cell_type || state.projectMetadata.cell_type || "NCM/Graphite",
    created_at: metadata.created_at || state.projectMetadata.created_at,
  };
  state.runtime = {
    ...state.runtime,
    ...runtime,
  };
  renderProjectInfo();
}

function applySimulationRequest(request = {}) {
  const setValue = (selector, value) => {
    const element = document.querySelector(selector);
    if (element && value !== undefined && value !== null) element.value = String(value);
  };
  const setChecked = (selector, value) => {
    const element = document.querySelector(selector);
    if (element && value !== undefined && value !== null) element.checked = Boolean(value);
  };
  setValue("#modelSelect", request.model);
  setValue("#parameterSet", request.parameter_set);
  setValue("#cycleMode", request.rate_unit);
  setValue("#chargeRate", request.charge_rate);
  setValue("#dischargeRate", request.discharge_rate);
  setValue("#chargeCutoff", request.charge_cutoff_v);
  setValue("#dischargeCutoff", request.discharge_cutoff_v);
  setValue("#temperatureC", request.temperature_c);
  setValue("#cycleCount", request.cycles);
  setValue("#restMinutes", request.rest_minutes);
  setChecked("#dcrEnabled", request.dcr_enabled);
  setValue("#dcrSoc", request.dcr_soc !== undefined ? Number(request.dcr_soc) * 100 : undefined);
  setValue("#dcrRate", request.dcr_rate);
  setValue("#dcrDuration", request.dcr_duration_s);
  setValue("#dcrEvery", request.dcr_every_cycles);
  setChecked("#agingEnabled", request.aging_enabled);
  const aging = request.aging_options || {};
  setValue("#agingSei", aging.SEI);
  setValue("#agingSeiFilm", aging["SEI film resistance"]);
  setValue("#agingSeiPorosity", aging["SEI porosity change"]);
  setValue("#agingSeiCracks", aging["SEI on cracks"]);
  setValue("#agingPlating", aging["lithium plating"]);
  setValue("#agingPlatingPorosity", aging["lithium plating porosity change"]);
  setValue("#agingMechanics", aging["particle mechanics"]);
  setValue("#agingStressDiffusion", aging["stress-induced diffusion"]);
  setValue("#agingLam", aging["loss of active material"]);
  document.querySelector("#dcrOptions")?.style.setProperty(
    "display",
    document.querySelector("#dcrEnabled")?.checked ? "" : "none"
  );
  syncAgingControls();
  updateCurrentPreview();
  drawConditionChart();
}

const AGING_CONTROL_SELECTORS = [
  "#agingSei",
  "#agingSeiFilm",
  "#agingSeiPorosity",
  "#agingSeiCracks",
  "#agingPlating",
  "#agingPlatingPorosity",
  "#agingMechanics",
  "#agingStressDiffusion",
  "#agingLam",
];

function syncAgingControls() {
  const enabled = Boolean(document.querySelector("#agingEnabled")?.checked);
  AGING_CONTROL_SELECTORS.forEach((selector) => {
    const element = document.querySelector(selector);
    if (element) element.disabled = !enabled;
  });
  updateAccelNote();
}

// 路由 → 视图：多个导航项可共享一个视图
const ROUTE_VIEWS = {
  simulation: "simulation",
  results: "simulation",
  projects: "projects",
  new: "projects",
  open: "projects",
  import: "projects",
  "data-import": "data",
  "data-browser": "data",
  "data-clean": "data",
  "data-analysis": "data",
  tasks: "tasks",
  bench: "bench",
};

// 尚未实现的模块：显示占位页
const PLACEHOLDER_ROUTES = {
  identify: {
    name: "参数识别",
    desc: "基于实验数据自动标定模型参数（BO/GA 优化器），展示参数边界、后验不确定性与相关性。依赖 Sim–Exp 对标工作台。",
  },
  sensitivity: {
    name: "敏感性分析",
    desc: "扫描关键参数对容量衰减 / 内阻 / 峰值功率的影响，定位高杠杆参数，评估外推风险。",
  },
  optimize: {
    name: "优化设计",
    desc: "面向目标（能量密度 / 倍率 / 寿命）的多参数设计空间探索与 Pareto 权衡。",
  },
  equivalent: {
    name: "等效电路模型",
    desc: "Thevenin / DP 等等效电路参数提取与辨识，用于 BMS 标定与状态估计。",
  },
  material: {
    name: "材料参数库",
    desc: "材料级参数（OCP / 扩散系数 / 电导率）的统一管理、版本化与复用。",
  },
  database: {
    name: "电芯数据库",
    desc: "Hithium 各电芯型号参数（params/*.py）的统一浏览与对比。",
  },
  report: {
    name: "报告导出",
    desc: "一键生成仿真报告（PDF），包含图表、参数版本与结果血缘信息。",
  },
};

// P0 信任修复：占位模块统一标注「规划中」，纯视觉控件禁用（承诺 <= 能力）
const PROJECT_PARAMETER_SETS = new Set(["hithium280", "hithium314", "hithium587", "mic1175"]);

function decoratePlaceholders() {
  document.querySelectorAll(".nav-item, .module-tabs a").forEach((item) => {
    const route = item.getAttribute("href")?.replace("#", "");
    if (route && PLACEHOLDER_ROUTES[route]) {
      const badge = document.createElement("span");
      badge.className = "badge-planning";
      badge.textContent = "规划中";
      item.appendChild(badge);
    }
  });
  const markDead = (button, title) => {
    if (!button || button.disabled) return;
    button.disabled = true;
    button.title = title;
    button.setAttribute("aria-disabled", "true");
    button.insertAdjacentHTML("beforeend", '<em class="badge-planning">规划中</em>');
  };
  const textButtons = [...document.querySelectorAll(".top-actions .text-button")];
  markDead(textButtons.find((b) => b.textContent.includes("帮助文档")), "帮助文档 · 规划中");
  markDead(document.querySelector('.top-actions button[aria-label="通知"]'), "通知中心 · 规划中");
  markDead(document.querySelector(".top-actions .avatar"), "用户中心 · 规划中");
  markDead([...document.querySelectorAll(".export-strip .btn")].find((b) => b.textContent.includes("生成报告")), "报告导出 · 规划中");
  markDead([...document.querySelectorAll(".model-panel .btn")].find((b) => b.textContent.includes("参数编辑器")), "参数编辑器 · 规划中");
}

// 项目参数加速口径（1 仿真圈 = 50 等效圈）：仅 project 参数集 + 老化启用时提示
function updateAccelNote() {
  const note = document.getElementById("accelNote");
  if (!note) return;
  const parameterSet = document.getElementById("parameterSet")?.value || "chen2020";
  const agingEnabled = document.getElementById("agingEnabled")?.checked ?? true;
  note.hidden = !(PROJECT_PARAMETER_SETS.has(parameterSet) && agingEnabled);
}

function setRoute(route) {
  state.route = route || "simulation";
  const view = ROUTE_VIEWS[state.route] || (PLACEHOLDER_ROUTES[state.route] ? "placeholder" : "simulation");
  document.querySelectorAll(".main-content > .view").forEach((node) => {
    node.hidden = node.dataset.view !== view;
  });
  if (view === "placeholder") {
    const routeMeta = PLACEHOLDER_ROUTES[state.route] || {};
    document.getElementById("placeholderTitle").textContent = `${routeMeta.name || "功能"} · 规划中`;
    const desc = document.getElementById("placeholderDesc");
    if (desc) desc.textContent = routeMeta.desc || "";
  }
  document.querySelector(".app-shell").dataset.route = state.route;
  document.querySelectorAll(".nav-item, .module-tabs a").forEach((item) => {
    const target = item.getAttribute("href")?.replace("#", "");
    item.classList.toggle("active", target === state.route || (state.route === "simulation" && target === "simulation"));
  });
  if (view === "projects") loadProjectsView();
  if (view === "data") loadDataView();
  if (view === "tasks") loadTaskCenter();
  if (view === "bench") loadBenchView();
}

function createPreviewRows(rows = null) {
  const displayRows = rows || [
    ["1", "3.102", "11.42", "10.83", "94.83"],
    ["2", "3.098", "11.40", "10.81", "94.82"],
    ["3", "3.094", "11.37", "10.78", "94.81"],
    ["...", "...", "...", "...", "..."],
    ["498", "2.351", "8.53", "7.95", "93.20"],
    ["499", "2.347", "8.51", "7.93", "93.17"],
    ["500", "2.342", "8.49", "7.90", "93.05"],
  ];
  document.getElementById("previewRows").innerHTML = rows
    ? displayRows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")
    : displayRows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("");
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
  updateAccelNote();
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

function drawDataPreviewCharts() {
  const cycles = [1, 100, 200, 300, 400, 500];
  const smallSpec = {
    width: 300,
    height: 112,
    margin: { top: 8, right: 10, bottom: 24, left: 34 },
    xDomain: [0, 500],
    xTicks: [0, 250, 500],
    xlabel: "循环",
  };
  drawLineChart("previewRetentionChart", {
    ...smallSpec,
    yDomain: [92, 101],
    yTicks: [92, 96, 100],
    lines: [{ className: "chart-blue", points: cycles.map((cycle, index) => [cycle, [100, 98.9, 97.3, 95.8, 94.3, 93.05][index]]) }],
  });
  drawLineChart("previewCapacityChart", {
    ...smallSpec,
    yDomain: [2.2, 3.2],
    yTicks: [2.2, 2.7, 3.2],
    lines: [{ className: "chart-blue", points: cycles.map((cycle, index) => [cycle, [3.102, 2.98, 2.82, 2.66, 2.5, 2.342][index]]) }],
  });
  drawLineChart("previewEfficiencyChart", {
    ...smallSpec,
    yDomain: [92.5, 95.2],
    yTicks: [92.5, 94, 95.2],
    lines: [{ className: "chart-blue", points: cycles.map((cycle, index) => [cycle, [94.83, 94.62, 94.29, 93.88, 93.46, 93.05][index]]) }],
  });
}

function renderTimePlaceholder(id, message, options = {}) {
  const svg = document.getElementById(id);
  if (!svg) return;
  const width = options.width || 270;
  const height = options.height || 190;
  drawLineChart(id, {
    width,
    height,
    xDomain: [0, 1],
    yDomain: options.yDomain || [0, 1],
    xTicks: [],
    yTicks: options.yTicks || [],
    xlabel: options.xlabel || "时间 (h)",
    lines: [],
  });
  svg.insertAdjacentHTML(
    "beforeend",
    `<text class="tick-label" x="${width / 2}" y="${height / 2}" text-anchor="middle">${message}</text>`
  );
}

function drawCharts() {
  drawConditionChart();
  drawDataPreviewCharts();
  renderTimePlaceholder("voltageChart", "运行仿真后显示");
  renderTimePlaceholder("currentChart", "运行仿真后显示");
  renderTimePlaceholder("temperatureChart", "运行仿真后显示");
  renderTimePlaceholder("agingChart", "运行仿真后显示充放电曲线演化", { width: 360, xlabel: "容量 (Ah)" });
  renderCyclePlaceholder("capacityChart", "容量衰减", "运行仿真后显示", {
    yDomain: [0, 100],
    yTicks: [0, 50, 100],
  });
  renderCyclePlaceholder("resistanceChart", "DCR", "勾选「DCR 仿真」后运行", {
    yDomain: [0, 1],
    yTicks: [0, 0.5, 1],
    ylabel: "DCR (mΩ)",
  });
  renderCyclePlaceholder("efficiencyChart", "能量效率", "运行仿真后显示", {
    yDomain: [80, 100],
    yTicks: [80, 90, 100],
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
  document.getElementById("simTime").textContent = state.simTimeH === null ? "-- h" : `${state.simTimeH.toFixed(2)} h`;
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
    .map((row) => `<tr><td>${escapeHtml(row.time)}</td><td>${escapeHtml(row.level)}</td><td>${escapeHtml(row.message)}</td></tr>`)
    .join("");
}

async function startRunSimulation() {
  if (state.running) {
    showToast("仿真已经在运行中");
    return;
  }
  const request = collectSimulationRequest();
  state.currentResult = null;
  state.simTimeH = null;
  state.pollFailures = 0;
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
    state.pollFailures = 0;
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
    state.pollFailures += 1;
    // 临时网络抖动不立刻判失败：404（任务已不存在）或连续 3 次失败才停止轮询
    if (error.status !== 404 && state.pollFailures < 3) return;
    clearInterval(state.pollTimer);
    state.pollTimer = null;
    state.running = false;
    state.status = "failed";
    updateRunStatus();
    showToast(error.message);
  }
}

async function resumeCurrentJob() {
  if (!state.currentJobId) return;
  try {
    const status = await apiFetch(`/api/jobs/${state.currentJobId}`);
    applyJobStatus(status);
    if (["running", "queued"].includes(status.status)) {
      state.pollFailures = 0;
      clearInterval(state.pollTimer);
      state.pollTimer = setInterval(pollJobStatus, 1200);
      showToast("已恢复跟踪正在运行的仿真任务");
    } else if (status.status === "completed") {
      state.currentResult = await apiFetch(`/api/jobs/${state.currentJobId}/results`);
      renderSimulationResult(state.currentResult);
    }
  } catch (error) {
    console.warn("恢复仿真任务失败", error);
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

const JOB_STATUS_LABELS = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  canceled: "已停止",
};

function renderJobsRows(jobs) {
  const body = document.getElementById("jobsRows");
  if (!jobs.length) {
    body.innerHTML = '<tr><td colspan="6">暂无任务记录</td></tr>';
    return;
  }
  body.innerHTML = jobs
    .map((job) => {
      const jobId = escapeHtml(job.job_id);
      const name = job.name ? escapeHtml(job.name) : "";
      const idCell = name
        ? `<div class="job-id-cell"><code>${jobId}</code><button class="icon-button ghost" type="button" data-action="rename-job" data-job-id="${jobId}" title="重命名"><span class="icon" data-icon="edit"></span></button></div>`
        : `<div class="job-id-cell"><code>${jobId}</code><button class="icon-button ghost" type="button" data-action="rename-job" data-job-id="${jobId}" title="重命名"><span class="icon" data-icon="edit"></span></button></div>`;
      const actions = [];
      if (job.status === "completed") {
        actions.push(`<button class="btn outline compact" type="button" data-action="load-job" data-job-id="${jobId}">查看结果</button>`);
        actions.push(`<button class="btn outline compact" type="button" data-action="job-csv" data-job-id="${jobId}">CSV</button>`);
      } else if (job.status === "running" || job.status === "queued") {
        actions.push(`<button class="btn outline compact" type="button" data-action="track-job" data-job-id="${jobId}">跟踪</button>`);
      }
      actions.push(`<button class="icon-button ghost danger" type="button" data-action="delete-job" data-job-id="${jobId}" title="删除任务" aria-label="删除"><span class="icon" data-icon="close"></span></button>`);
      return `<tr>
        <td>${idCell}${name ? `<div class="job-name">${name}</div>` : ""}</td>
        <td>${escapeHtml(JOB_STATUS_LABELS[job.status] || job.status)}</td>
        <td>${Number(job.progress || 0).toFixed(0)}%</td>
        <td>${escapeHtml(job.current_cycle ?? 0)} / ${escapeHtml(job.total_cycles ?? 0)}</td>
        <td>${escapeHtml(String(job.updated_at || "").replace("T", " ").slice(0, 19))}</td>
        <td class="job-actions">${actions.join("") || "--"}</td>
      </tr>`;
    })
    .join("");
}

async function renameJobPrompt(jobId) {
  // 优先用当前 name,无则空(留空=清除)
  const resp = await apiFetch("/api/jobs");
  const cur = (resp.jobs || []).find((j) => j.job_id === jobId);
  const currentName = cur?.name || "";
  const next = window.prompt("重命名任务(≤80 字符,留空=清除)", currentName);
  if (next === null) return;
  await apiFetch(`/api/jobs/${jobId}/rename`, {
    method: "POST",
    body: JSON.stringify({ name: next }),
  });
  showToast("已重命名");
  await refreshJobsModal();
}

async function deleteJobConfirm(jobId) {
  if (!window.confirm(`确认删除任务 ${jobId.slice(0, 8)}…(含结果与 run 目录)?该操作不可撤销。`)) return;
  await apiFetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  showToast("已删除");
  await refreshJobsModal();
}

async function refreshJobsModal() {
  try {
    const payload = await apiFetch("/api/jobs");
    renderJobsRows(payload.jobs || []);
  } catch (error) {
    showToast(`任务列表刷新失败: ${error.message}`);
  }
}

async function openJobsModal() {
  const modal = document.getElementById("jobsModal");
  modal.hidden = false;
  const body = document.getElementById("jobsRows");
  body.innerHTML = '<tr><td colspan="6">加载中...</td></tr>';
  try {
    const payload = await apiFetch("/api/jobs");
    renderJobsRows(payload.jobs || []);
  } catch (error) {
    body.innerHTML = `<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`;
  }
}

function closeJobsModal() {
  const modal = document.getElementById("jobsModal");
  if (modal) modal.hidden = true;
}

async function loadJobResult(jobId) {
  state.currentJobId = jobId;
  setRoute("simulation");
  const status = await apiFetch(`/api/jobs/${jobId}`);
  applyJobStatus(status);
  state.currentResult = await apiFetch(`/api/jobs/${jobId}/results`);
  renderSimulationResult(state.currentResult);
  closeJobsModal();
  showToast("已加载历史任务结果");
}

async function loadProjectsView() {
  const body = document.getElementById("projectsRows");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="5">加载中...</td></tr>';
  try {
    const payload = await apiFetch("/api/projects");
    const projects = payload.projects || [];
    if (!projects.length) {
      body.innerHTML = '<tr><td colspan="5">暂无项目，点击右上角「新建项目」创建</td></tr>';
      return;
    }
    const current = state.projectMetadata.project_name;
    body.innerHTML = projects
      .map((project) => {
        const name = escapeHtml(project.project_name);
        const isCurrent = project.project_name === current;
        const action = isCurrent
          ? '<strong>当前项目</strong>'
          : `<button class="btn outline compact" type="button" data-action="switch-project" data-project-name="${name}">设为当前</button>`;
        return `<tr>
          <td>${name}</td>
          <td>${escapeHtml(project.cell_type)}</td>
          <td>${escapeHtml(formatProjectTime(project.created_at))}</td>
          <td>${escapeHtml(formatProjectTime(project.updated_at))}</td>
          <td>${action}</td>
        </tr>`;
      })
      .join("");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function switchProject(projectName) {
  const saved = await apiFetch("/api/project/switch", {
    method: "POST",
    body: JSON.stringify({ project_name: projectName }),
  });
  const config = saved.config || {};
  applyProjectConfig(config, saved.runtime);
  if (config.simulation_request) applySimulationRequest(config.simulation_request);
  applySavedDataset(config.dataset);
  state.currentResult = null;
  state.simTimeH = null;
  clearInterval(state.pollTimer);
  state.pollTimer = null;
  state.currentJobId = config.current_job_id || null;
  if (state.currentJobId) {
    await resumeCurrentJob();
  } else {
    state.status = "idle";
    state.running = false;
    state.progress = 0;
    state.cycle = 0;
    state.elapsedSeconds = 0;
    updateRunStatus();
  }
  await loadProjectsView();
  showToast(`已切换到项目 ${config.project_name || projectName}`);
}

const benchState = { jobs: [], datasets: [] };

async function loadBenchView() {
  await Promise.all([loadBenchJobs(), loadBenchDatasets()]);
  fillBenchRunSelects();
}

async function loadBenchJobs() {
  try {
    const payload = await apiFetch("/api/bench/jobs");
    benchState.jobs = payload.jobs || [];
    const fmt = (job) => `${job.job_id.slice(0, 8)} · ${job.job_type} · ${job.updated_at || ""}`;
    ["benchJob", "benchRunA", "benchRunB"].forEach((id) => {
      const select = document.getElementById(id);
      if (!select) return;
      select.innerHTML = '<option value="">选择任务…</option>' + benchState.jobs.map((job) => `<option value="${escapeHtml(job.job_id)}">${escapeHtml(fmt(job))}</option>`).join("");
    });
  } catch (error) {
    showToast(`任务列表加载失败：${error.message}`);
  }
}

async function loadBenchDatasets() {
  try {
    const payload = await apiFetch("/api/data");
    benchState.datasets = payload.datasets || [];
    const select = document.getElementById("benchDataset");
    if (!select) return;
    select.innerHTML = '<option value="">选择数据集…</option>' + benchState.datasets.map((d) => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.file_name)} (${escapeHtml(d.rows)} 行)</option>`).join("");
  } catch (error) {
    showToast(`数据集加载失败：${error.message}`);
  }
}

function fillBenchRunSelects() {
  if (!benchState.jobs.length) return;
  ["benchJob", "benchRunA", "benchRunB"].forEach((id) => {
    const select = document.getElementById(id);
    if (select && !select.options.length) {
      select.innerHTML = '<option value="">选择任务…</option>' + benchState.jobs.map((job) => `<option value="${escapeHtml(job.job_id)}">${escapeHtml(job.job_id.slice(0, 8))} · ${escapeHtml(job.job_type)}</option>`).join("");
    }
  });
}

async function runBench() {
  const jobId = document.getElementById("benchJob")?.value;
  const datasetId = document.getElementById("benchDataset")?.value;
  const threshold = document.getElementById("benchThreshold")?.value || "5";
  if (!jobId || !datasetId) {
    showToast("请选择仿真任务与实验数据集");
    return;
  }
  showToast("正在计算对标指标");
  const payload = await apiFetch(`/api/bench/sim-exp?job_id=${encodeURIComponent(jobId)}&dataset_id=${encodeURIComponent(datasetId)}&threshold=${encodeURIComponent(threshold)}`);
  renderBenchResult(payload);
  document.getElementById("benchResultPane").hidden = false;
}

function renderBenchResult(payload) {
  const metrics = document.getElementById("benchMetrics");
  const parts = [];
  const addMetric = (label, block) => {
    if (!block) return;
    parts.push(`<div class="bench-metric"><strong>${label} RRMSE</strong><span>${Number(block.rrmse_pct).toFixed(2)}%</span><small>RMSE ${Number(block.rmse).toFixed(4)}</small></div>`);
  };
  addMetric("容量保持率", payload.retention);
  addMetric("能效", payload.efficiency);
  const range = payload.sim_cycle_range ? `重叠仿真区间 ${payload.sim_cycle_range[0]}–${payload.sim_cycle_range[1]} 圈` : "";
  metrics.innerHTML = parts.join("") + (range ? `<div class="bench-metric note">${range}</div>` : "");

  const chart = echartsBox("benchChart");
  if (chart) {
    const series = [];
    const anomalyAreas = [];
    const addBlock = (block, label, color) => {
      if (!block) return;
      series.push({ name: `实测${label}`, type: "scatter", symbolSize: 5, color, data: block.cycle.map((c, i) => [c, block.exp[i]]) });
      series.push({ name: `仿真${label}`, type: "line", showSymbol: false, color, data: block.sim_full.cycle.map((c, i) => [c, block.sim_full.values[i]]) });
    };
    addBlock(payload.retention, "保持率", "#2563eb");
    addBlock(payload.efficiency, "能效", "#0aa777");
    (payload.anomalies || []).forEach((w) => {
      anomalyAreas.push({ xAxis: w.start_cycle, itemStyle: { color: "rgba(239,68,68,0.10)" } });
      anomalyAreas.push({ xAxis: w.end_cycle, itemStyle: { color: "rgba(239,68,68,0.10)" } });
    });
    chart.setOption({
      ...ECHARTS_BASE,
      legend: { top: 0 },
      xAxis: ECHARTS_CYCLE_XAXIS,
      yAxis: { type: "value", name: "%", scale: true },
      series,
      ...(anomalyAreas.length ? { markArea: {} } : {}),
    }, true);
    if (anomalyAreas.length) {
      series.forEach((item) => { item.markArea = { silent: true, itemStyle: { color: "rgba(239,68,68,0.10)" }, data: anomalyAreas }; });
      chart.setOption({ series }, true);
    }
  }

  const anomalyTable = document.getElementById("benchAnomalyTable");
  const anomalies = payload.anomalies || [];
  anomalyTable.innerHTML = anomalies.length
    ? `<div class="table-wrap"><table><thead><tr><th>起始圈</th><th>结束圈</th><th>RMSE</th><th>RRMSE (%)</th><th>级别</th></tr></thead><tbody>` +
      anomalies.map((w) => `<tr><td>${w.start_cycle}</td><td>${w.end_cycle}</td><td>${w.rmse}</td><td>${w.rrmse_pct}</td><td><span class="status-badge ${w.severity === "高" ? "status-missing" : "status-auto"}">${w.severity}</span></td></tr>`).join("") +
      `</tbody></table></div>`
    : '<p class="small-note">重叠区间不足或无异常。</p>';

  const manifest = payload.manifest || {};
  const manifestRows = [
    ["workflow_id", manifest.workflow_id],
    ["job_type", manifest.job_type],
    ["cell", manifest.cell],
    ["run_mode", manifest.run_mode],
    ["PyBaMM 版本", manifest.pybamm_version],
    ["参数来源", manifest.parameter_source],
  ].filter(([, v]) => v !== undefined);
  document.getElementById("benchManifest").innerHTML = manifestRows.length
    ? `<div class="table-wrap"><table><thead><tr><th>字段</th><th>值</th></tr></thead><tbody>` +
      manifestRows.map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join("") + `</tbody></table></div>`
    : '<p class="small-note">该任务为旧格式(cycle),无 manifest 字段。</p>';
}

async function runBenchCurves() {
  const jobA = document.getElementById("benchRunA")?.value;
  const jobB = document.getElementById("benchRunB")?.value;
  if (!jobA || !jobB || jobA === jobB) {
    showToast("请选择两个不同的 Run");
    return;
  }
  showToast("正在对比两个 Run 的曲线");
  const payload = await apiFetch(`/api/bench/runs-curve?job_a=${encodeURIComponent(jobA)}&job_b=${encodeURIComponent(jobB)}`);
  const pane = document.getElementById("benchCurvePane");
  pane.hidden = false;

  const metrics = document.getElementById("benchCurveMetrics");
  metrics.innerHTML = (payload.pairs || []).length
    ? (payload.pairs || []).map((pair) =>
        `<div class="bench-metric"><strong>${escapeHtml(pair.name)}</strong><span>RRMSE ${pair.rrmse_pct}%</span><small>RMSE ${pair.rmse}</small></div>`).join("")
    : '<div class="bench-metric note">两个 Run 无可比曲线(仅 cycle 类有逐圈指标)。</div>';

  const chart = echartsBox("benchCurveChart");
  if (chart) {
    const series = [];
    (payload.pairs || []).forEach((pair) => {
      series.push({ name: `Run A · ${pair.name}`, type: "line", showSymbol: false, data: pair.x.map((x, i) => [x, pair.y_a[i]]) });
      series.push({ name: `Run B · ${pair.name}`, type: "line", showSymbol: false, lineStyle: { type: "dashed" }, data: pair.x.map((x, i) => [x, pair.y_b[i]]) });
    });
    chart.setOption({ ...ECHARTS_BASE, legend: { top: 0 }, xAxis: ECHARTS_CYCLE_XAXIS, yAxis: { type: "value", scale: true }, series }, true);
  }

  const fmtMeta = (meta) => (meta && meta.job_type) ? `${meta.job_type} · ${meta.cell} · ${meta.run_mode} · PyBaMM ${meta.pybamm_version || "--"}` : "旧格式(无 manifest)";
  document.getElementById("benchCurveMeta").innerHTML =
    `<div class="bench-metrics"><div class="bench-metric"><strong>Run A</strong><span style="font-size:13px">${escapeHtml(fmtMeta(payload.meta_a))}</span></div>` +
    `<div class="bench-metric"><strong>Run B</strong><span style="font-size:13px">${escapeHtml(fmtMeta(payload.meta_b))}</span></div></div>`;
}

async function runBenchRuns() {
  const jobA = document.getElementById("benchRunA")?.value;
  const jobB = document.getElementById("benchRunB")?.value;
  if (!jobA || !jobB) {
    showToast("请选择两个 Run");
    return;
  }
  if (jobA === jobB) {
    showToast("请选择两个不同的 Run");
    return;
  }
  const payload = await apiFetch(`/api/bench/runs?job_a=${encodeURIComponent(jobA)}&job_b=${encodeURIComponent(jobB)}`);
  const pane = document.getElementById("benchDiffPane");
  const rows = payload.differences || [];
  pane.innerHTML = `<h4>参数版本差异</h4>` + (rows.length
    ? `<div class="table-wrap"><table><thead><tr><th>字段</th><th>Run A</th><th>Run B</th></tr></thead><tbody>` +
      rows.map((row) => `<tr><td>${escapeHtml(row.field)}</td><td>${escapeHtml(row.job_a ?? "--")}</td><td>${escapeHtml(row.job_b ?? "--")}</td></tr>`).join("") +
      `</tbody></table></div>`
    : '<p class="small-note">两个 Run 的参数版本完全一致。</p>');
  pane.hidden = false;
}

const taskState = {
  jobTypes: [],
  selectedType: null,
  jobId: null,
  status: null,
  pollTimer: null,
};

async function loadTaskCenter() {
  try {
    const payload = await apiFetch("/api/job-types");
    taskState.jobTypes = payload.job_types || [];
    renderTaskTypeList();
    if (taskState.selectedType) selectTaskType(taskState.selectedType);
  } catch (error) {
    document.getElementById("taskTypeList").innerHTML = `<div class="task-type-item disabled">${escapeHtml(error.message)}</div>`;
  }
}

function renderTaskTypeList() {
  const list = document.getElementById("taskTypeList");
  if (!list) return;
  list.innerHTML = taskState.jobTypes
    .map((item) => {
      const stateLabel = item.available ? escapeHtml(item.job_type) : "规划中";
      return `<button type="button" class="task-type-item${item.available ? "" : " disabled"}" data-task-type="${escapeHtml(item.job_type)}" ${item.available ? "" : "disabled"}>
        <strong>${escapeHtml(item.label)}</strong><small>${stateLabel}</small>
      </button>`;
    })
    .join("");
}

function selectTaskType(jobType) {
  const item = taskState.jobTypes.find((t) => t.job_type === jobType);
  if (!item) return;
  taskState.selectedType = jobType;
  document.querySelectorAll(".task-type-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.taskType === jobType);
  });
  document.getElementById("taskTypeTitle").textContent = item.label;
  document.getElementById("taskTypeDesc").textContent = item.available
    ? `${jobType} · 已接入 Studio 运行时`
    : `${jobType} · 后端尚未接入，规划中`;
  const planned = document.getElementById("taskPlannedNote");
  if (planned) planned.hidden = item.available;
  const form = document.getElementById("taskForm");
  form.innerHTML =
    item.available && item.schema.length
      ? item.schema.map((field) => renderTaskField(field)).join("")
      : '<p class="small-note">该类型暂无可用配置项，等待后端接入。</p>';
  document.getElementById("taskMonitorPane").hidden = true;
  if (taskState.pollTimer) {
    clearInterval(taskState.pollTimer);
    taskState.pollTimer = null;
  }
  taskState.status = null;
}

function renderTaskField(field) {
  const id = `taskf_${field.name}`;
  const unit = field.unit ? `<em>${escapeHtml(field.unit)}</em>` : "";
  const desc = field.desc ? `<small class="field-desc">${escapeHtml(field.desc)}</small>` : "";
  if (field.type === "checkbox") {
    return `<label class="check-row task-check"><input type="checkbox" id="${id}" data-task-field="${escapeHtml(field.name)}" ${field.default ? "checked" : ""}> ${escapeHtml(field.label)}</label>`;
  }
  if (field.type === "select") {
    const options = (field.options || [])
      .map((opt) => `<option value="${escapeHtml(String(opt))}" ${String(opt) === String(field.default) ? "selected" : ""}>${escapeHtml(String(opt))}</option>`)
      .join("");
    return `<label class="field"><span>${escapeHtml(field.label)}</span><select id="${id}" data-task-field="${escapeHtml(field.name)}">${options}</select>${desc}</label>`;
  }
  const step = field.step || "any";
  const min = field.min !== undefined ? ` min="${field.min}"` : "";
  const max = field.max !== undefined ? ` max="${field.max}"` : "";
  const inputType = field.type === "number" ? "number" : "text";
  return `<label class="field"><span>${escapeHtml(field.label)}</span><div class="unit-input"><input id="${id}" type="${inputType}" value="${escapeHtml(String(field.default ?? ""))}" data-task-field="${escapeHtml(field.name)}" step="${step}"${min}${max}>${unit}</div>${desc}</label>`;
}

function collectTaskRequest() {
  const item = taskState.jobTypes.find((t) => t.job_type === taskState.selectedType);
  const request = { job_type: taskState.selectedType };
  (item?.schema || []).forEach((field) => {
    const node = document.getElementById(`taskf_${field.name}`);
    if (!node) return;
    if (field.type === "checkbox") {
      request[field.name] = node.checked;
    } else if (field.type === "number") {
      request[field.name] = Number(node.value);
    } else {
      request[field.name] = node.value;
    }
  });
  return request;
}

async function runTask() {
  if (taskState.status === "running" || taskState.status === "queued") {
    showToast("已有任务在运行");
    return;
  }
  const request = collectTaskRequest();
  showToast("正在提交任务");
  const status = await apiFetch("/api/jobs", { method: "POST", body: JSON.stringify(request) });
  taskState.jobId = status.job_id;
  applyTaskStatus(status);
  document.getElementById("taskMonitorPane").hidden = false;
  if (taskState.pollTimer) clearInterval(taskState.pollTimer);
  taskState.pollTimer = setInterval(pollTaskStatus, 1500);
}

async function pollTaskStatus() {
  if (!taskState.jobId) return;
  try {
    const status = await apiFetch(`/api/jobs/${taskState.jobId}`);
    applyTaskStatus(status);
    if (["completed", "failed", "canceled"].includes(status.status)) {
      clearInterval(taskState.pollTimer);
      taskState.pollTimer = null;
      if (status.status === "completed") {
        const result = await apiFetch(`/api/jobs/${taskState.jobId}/results`);
        renderTaskResult(result);
        showToast("任务完成，结果已刷新");
      } else if (status.status === "failed") {
        showToast(status.error || "任务失败，请查看日志");
      } else {
        showToast("任务已停止");
      }
    }
  } catch (error) {
    clearInterval(taskState.pollTimer);
    taskState.pollTimer = null;
    showToast(error.message);
  }
}

async function stopTask() {
  if (!taskState.jobId) return;
  const status = await apiFetch(`/api/jobs/${taskState.jobId}/stop`, { method: "POST" });
  clearInterval(taskState.pollTimer);
  taskState.pollTimer = null;
  applyTaskStatus(status);
  showToast("已请求停止任务");
}

function applyTaskStatus(status) {
  taskState.status = status.status;
  const labels = { queued: "排队中", running: "运行中", completed: "已完成", failed: "失败", canceled: "已停止" };
  document.getElementById("taskRunStatus").textContent = labels[status.status] || status.status;
  document.getElementById("taskJobId").textContent = status.job_id || "--";
  document.getElementById("taskProgressText").textContent = `${Number(status.progress || 0).toFixed(0)}%`;
  document.getElementById("taskElapsed").textContent = fmtClock(Number(status.elapsed_s || 0));
  document.querySelector('[data-action="task-stop"]').disabled = !(status.status === "running" || status.status === "queued");
  const rows = status.logs || [];
  document.getElementById("taskLogRows").innerHTML = (rows.length ? rows : [{ time: "--", level: "INFO", message: "等待任务日志" }])
    .slice(-6)
    .map((row) => `<tr><td>${escapeHtml(row.time)}</td><td>${escapeHtml(row.level)}</td><td>${escapeHtml(row.message)}</td></tr>`)
    .join("");
}

function renderCalibrationResult(result) {
  const best = result.best_params || {};
  const bounds = result.bounds || {};
  const sensitivity = result.sensitivity || [];
  const history = result.loss_history || [];
  const cards = `<div class="bench-metrics">
    <div class="bench-metric"><strong>优化器</strong><span style="font-size:14px">${escapeHtml(result.method || "--")}</span><small>${escapeHtml(result.message || "")}</small></div>
    <div class="bench-metric"><strong>最优 fitness</strong><span>${Number(result.best_fitness ?? 0).toExponential(3)}</span><small>1/损失</small></div>
    <div class="bench-metric"><strong>耗时</strong><span style="font-size:14px">${escapeHtml(result.elapsed_s ?? "--")} s</span><small>t_factor=${escapeHtml(result.t_factor)} · ${escapeHtml(result.cycles)} 圈/评估</small></div>
  </div>`;
  let curveHtml = "";
  if (history.length >= 2) {
    curveHtml = `<h4>损失收敛曲线</h4><div id="calibLossChart" class="echart-box" style="height: 240px"></div>`;
  }
  let tableHtml = "";
  if (Object.keys(best).length) {
    tableHtml = `<h4>标定结果与可辨识性</h4><div class="table-wrap"><table>
      <thead><tr><th>参数</th><th>最优值</th><th>下界</th><th>上界</th><th>±1% 敏感度</th><th>可辨识性</th></tr></thead><tbody>` +
      Object.keys(best).map((name) => {
        const b = bounds[name] || {};
        const s = sensitivity.find((row) => row.param === name);
        const sens = s ? s.sensitivity : 0;
        const identifiable = sens > 0.0001 ? "较好" : sens > 1e-6 ? "一般" : "弱(平坦方向)";
        return `<tr><td class="registry-path" title="${escapeHtml(name)}">${escapeHtml(name)}</td>
          <td>${escapeHtml(Number(best[name]).toExponential(4))}</td>
          <td>${escapeHtml(Number(b.low ?? 0).toExponential(3))}</td>
          <td>${escapeHtml(Number(b.high ?? 0).toExponential(3))}</td>
          <td>${escapeHtml(Number(sens).toExponential(3))}</td>
          <td><span class="status-badge ${sens > 0.0001 ? "status-curated" : "status-ignore"}">${identifiable}</span></td></tr>`;
      }).join("") + `</tbody></table></div>`;
  }
  const html = cards + curveHtml + tableHtml;
  setTimeout(() => {
    if (history.length >= 2) {
      const chart = echartsBox("calibLossChart");
      if (chart) {
        chart.setOption({
          ...ECHARTS_BASE,
          tooltip: { trigger: "axis" },
          legend: { top: 0 },
          grid: { left: 60, right: 20, top: 34, bottom: 34 },
          xAxis: { type: "category", name: "迭代", data: history.map((h) => h.iter) },
          yAxis: { type: "value", name: "loss", scale: true },
          series: [{ name: "loss", type: "line", showSymbol: true, symbolSize: 5, data: history.map((h) => h.loss) }],
        }, true);
      }
    }
    if (sensitivity.length) {
      const sChart = echartsBox("calibSensChart");
      if (sChart) {
        sChart.setOption({
          ...ECHARTS_BASE,
          tooltip: { trigger: "axis" },
          grid: { left: 60, right: 20, top: 20, bottom: 60 },
          xAxis: { type: "category", name: "参数", data: sensitivity.map((s) => s.param), axisLabel: { rotate: 30, width: 110, overflow: "truncate" } },
          yAxis: { type: "value", name: "±1% 敏感度", scale: true },
          series: [{ name: "敏感度", type: "bar", data: sensitivity.map((s) => s.sensitivity) }],
        }, true);
      }
    }
  }, 30);
  return html;
}

function renderTaskResult(result) {
  const pane = document.getElementById("taskResultPane");
  const jobType = result.job_type || taskState.selectedType || "";
  const summary = result.summary || {};
  let html = "";
  if (jobType === "peak_current" && Array.isArray(summary.results)) {
    html = `<div class="table-wrap"><table>
      <thead><tr><th>方向</th><th>SOC</th><th>峰值电流 (A)</th><th>C-rate</th><th>峰值功率 (kW)</th><th>首点电压 (V)</th></tr></thead><tbody>` +
      summary.results
        .map((row) => `<tr><td>${escapeHtml(row.direction)}</td><td>${escapeHtml(row.soc)}</td><td>${escapeHtml(row.peak_current_A ?? "--")}</td><td>${escapeHtml(row.peak_C_rate ?? "--")}</td><td>${escapeHtml(row.peak_power_kW ?? "--")}</td><td>${escapeHtml(row.first_voltage_V ?? "--")}</td></tr>`)
        .join("") +
      `</tbody></table></div>`;
  } else if (jobType === "cycle") {
    html = `<p class="small-note">循环任务完成：耗时 ${escapeHtml(result.elapsed_s ?? "--")} s。完整曲线请在「结果分析」查看。</p>`;
  } else if (jobType === "calibration") {
    html = renderCalibrationResult(result);
  } else {
    html = `<p class="small-note">${escapeHtml(jobType || "任务")} 完成。run_dir：<code>${escapeHtml(result.run_dir || "--")}</code></p>`;
    if (summary.rows !== undefined) html += `<p class="small-note">结果行数：${escapeHtml(summary.rows)}</p>`;
  }
  pane.innerHTML = html;
}

function currentRegistryFilters() {
  const values = ["regCell", "regTemp", "regRate", "regTest", "regStatus"].map((id) => {
    const node = document.getElementById(id);
    return node ? node.value : "";
  });
  return {
    cell: values[0],
    temp: values[1],
    rate: values[2],
    test: values[3],
    status: values[4],
  };
}

async function loadDataView() {
  const activeTab = document.querySelector(".data-tabs button.active")?.dataset.dataTab || "registry";
  if (activeTab === "registry") {
    await Promise.all([loadRegistryFacets(), loadRegistryRows()]);
  } else {
    await loadDatasetsView();
  }
}

async function loadRegistryFacets() {
  try {
    const payload = await apiFetch("/api/registry/facets");
    const facets = payload.facets || {};
    const fill = (id, values, prefix) => {
      const select = document.getElementById(id);
      if (!select) return;
      select.innerHTML =
        `<option value="">${prefix} (全部)</option>` +
        (values || []).map((value) => `<option value="${escapeHtml(String(value))}">${escapeHtml(String(value))}</option>`).join("");
    };
    fill("regCell", facets.cell, "电芯");
    fill("regTemp", facets.temperature_C, "温度 °C");
    fill("regRate", facets.rate, "倍率");
    fill("regTest", facets.test_type, "测试类型");
    fill("regStatus", facets.status, "质量状态");
  } catch (error) {
    showToast(`Registry 维度加载失败：${error.message}`);
  }
}

async function loadRegistryRows() {
  const body = document.getElementById("registryRows");
  const summary = document.getElementById("registrySummary");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="8">加载中…</td></tr>';
  try {
    const filters = currentRegistryFilters();
    const params = new URLSearchParams(
      Object.entries(filters)
        .filter(([, value]) => value !== "")
        .map(([key, value]) => [key, String(value)])
    );
    const payload = await apiFetch(`/api/registry?${params.toString()}`);
    const entries = payload.entries || [];
    if (summary) {
      summary.textContent = `datasets.json 共 ${payload.total ?? 0} 条 · 当前筛选命中 ${payload.count ?? entries.length} 条（quality 由人工审核后置为 curated）`;
    }
    if (!entries.length) {
      body.innerHTML =
        '<tr><td colspan="8">无匹配数据。可调整筛选条件，或在 data_raw/ 下补充实验数据后运行 <code>data_registry.py scan</code> 登记。</td></tr>';
      return;
    }
    const statusLabels = { auto: "自动推断", curated: "人工核实", ignore: "已忽略", missing: "缺失" };
    body.innerHTML = entries
      .map((entry) => {
        const status = entry.status || "auto";
        const label = statusLabels[status] || status;
        return `<tr>
          <td class="registry-path" title="${escapeHtml(entry.path)}">${escapeHtml(entry.path)}</td>
          <td>${escapeHtml(entry.cell || "--")}</td>
          <td>${escapeHtml(entry.temperature_C ?? "--")}</td>
          <td>${escapeHtml(entry.rate || "--")}</td>
          <td>${escapeHtml(entry.test_type || "--")}</td>
          <td>${escapeHtml(entry.soh_pct ?? "--")}</td>
          <td><span class="status-badge status-${escapeHtml(status)}">${label}</span></td>
          <td>${escapeHtml(entry.format || "--")}</td>
        </tr>`;
      })
      .join("");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="8">${escapeHtml(error.message)}</td></tr>`;
    if (summary) summary.textContent = "";
  }
}

function resetRegistryFilters() {
  ["regCell", "regTemp", "regRate", "regTest", "regStatus"].forEach((id) => {
    const select = document.getElementById(id);
    if (select) select.value = "";
  });
  loadRegistryRows();
}

async function loadDatasetsView() {
  const body = document.getElementById("datasetsRows");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="5">加载中...</td></tr>';
  try {
    const payload = await apiFetch("/api/data");
    const datasets = payload.datasets || [];
    if (!datasets.length) {
      body.innerHTML = '<tr><td colspan="5">暂无数据集，点击右上角「导入数据」上传 CSV/Excel</td></tr>';
      return;
    }
    const currentId = state.importedDataset?.id;
    body.innerHTML = datasets
      .map((dataset) => {
        const id = escapeHtml(dataset.id);
        const mark = dataset.id === currentId ? " <strong>(当前)</strong>" : "";
        return `<tr>
          <td>${id}${mark}</td>
          <td>${escapeHtml(dataset.file_name)}</td>
          <td>${escapeHtml(dataset.rows)}</td>
          <td>${escapeHtml(formatProjectTime(dataset.imported_at))}</td>
          <td>
            <button class="btn outline compact" type="button" data-action="use-dataset" data-dataset-id="${id}">设为数据源</button>
            <button class="btn outline compact" type="button" data-action="dataset-csv" data-dataset-id="${id}">CSV</button>
          </td>
        </tr>`;
      })
      .join("");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
  }
}

function renderImportedDataset(payload) {
  const dataset = payload.dataset;
  state.importedDataset = dataset;
  document.getElementById("datasetName").textContent = dataset.file_name;
  document.getElementById("datasetStatus").textContent = "已导入";
  document.getElementById("datasetMeta").textContent = `真实数据 ${dataset.rows} 行 · ${dataset.imported_at}`;
  const source = document.getElementById("dataSource");
  if (source) {
    const value = `dataset:${dataset.id}`;
    let option = [...source.options].find((item) => item.value === value);
    if (!option) {
      option = new Option(dataset.file_name, value);
      source.add(option);
    }
    source.value = value;
  }
  if (payload.preview?.rows) {
    createPreviewRows(payload.preview.rows);
  }
  if (payload.series) {
    state.datasetSeries = payload.series;
    state.extrapolation = null;
    const note = document.getElementById("extrapolateNote");
    if (note) note.hidden = true;
    drawRealPreviewCharts(payload.series);
  }
  const metrics = payload.metrics || {};
  document.getElementById("metricInitialCapacity").textContent = formatMetric(metrics.initial_capacity_ah);
  document.getElementById("metricNominalCapacity").textContent = formatMetric(metrics.nominal_capacity_ah);
  document.getElementById("metricCycle80").textContent = formatMetric(metrics.cycle_to_80, { digits: 0 });
  document.getElementById("metricResistanceGrowth").textContent = formatMetric(metrics.resistance_growth_500_pct, { digits: 2, suffix: "%" });
  document.getElementById("metricMeanEfficiency").textContent = formatMetric(metrics.mean_efficiency_pct, { digits: 2, suffix: "%" });
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function importDataFile(file) {
  if (!file) return;
  showToast("正在导入真实数据文件");
  const contentBase64 = await readFileAsBase64(file);
  const payload = await apiFetch("/api/data/import", {
    method: "POST",
    body: JSON.stringify({
      file_name: file.name,
      content_base64: contentBase64,
    }),
  });
  renderImportedDataset(payload);
  if (!document.querySelector('.view[data-view="data"]')?.hidden) {
    await loadDatasetsView();
  }
  showToast(`已导入 ${payload.dataset.file_name}：${payload.dataset.rows} 行`);
}

async function saveProjectConfig() {
  const payload = collectProjectConfigPayload();
  const saved = await apiFetch("/api/project/config", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.savedConfig = saved.config;
  applyProjectConfig(saved.config, saved.runtime);
  showToast("项目配置已写入本地项目目录");
}

async function updateProjectField(field, value) {
  const nextValue = String(value || "").trim();
  if (!nextValue) return;
  state.projectMetadata = {
    ...state.projectMetadata,
    [field]: nextValue,
  };
  renderProjectInfo();
  await saveProjectConfig();
}

function applySavedDataset(dataset) {
  if (!dataset) return;
  state.importedDataset = dataset;
  document.getElementById("datasetName").textContent = dataset.file_name || "已导入数据";
  document.getElementById("datasetStatus").textContent = "已保存";
  document.getElementById("datasetMeta").textContent = `保存的数据集 · ${dataset.rows || "--"} 行`;
  const source = document.getElementById("dataSource");
  if (source && dataset.id) {
    const value = `dataset:${dataset.id}`;
    let option = [...source.options].find((item) => item.value === value);
    if (!option) {
      option = new Option(dataset.file_name || "已导入数据", value);
      source.add(option);
    }
    source.value = value;
  }
  // 项目恢复时拉取数据集详情，重画真实数据可视化曲线
  if (dataset.id) {
    apiFetch(`/api/data/${dataset.id}`)
      .then((payload) => {
        if (payload.series) {
          state.datasetSeries = payload.series;
          drawRealPreviewCharts(payload.series);
        }
        if (payload.preview?.rows) createPreviewRows(payload.preview.rows);
      })
      .catch(() => {});
  }
}

async function loadProjectConfig() {
  try {
    const saved = await apiFetch("/api/project/config");
    const config = saved.config;
    if (!config) return;
    state.savedConfig = config;
    applyProjectConfig(config, saved.runtime);
    applySavedDataset(config.dataset);
    if (config.simulation_request) applySimulationRequest(config.simulation_request);
    if (config.current_job_id) {
      state.currentJobId = config.current_job_id;
      await resumeCurrentJob();
    }
  } catch (error) {
    console.warn("加载项目配置失败", error);
  }
}

function downloadCsv() {
  if (state.currentJobId && state.currentResult) {
    downloadUrl(`/api/jobs/${state.currentJobId}/export.csv`);
    showToast("正在下载真实仿真 CSV");
    return;
  }
  if (state.importedDataset?.id) {
    downloadUrl(`/api/data/${state.importedDataset.id}/export.csv`);
    showToast("正在下载已导入数据 CSV");
    return;
  }
  showToast("没有可导出的真实数据：请先导入数据或完成仿真");
}

function serializeChartSvg(svg) {
  const clone = svg.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent = `
    .chart-axis{stroke:#7182a4;stroke-width:1.15}
    .grid-line{stroke:#e2e8f0;stroke-width:1}
    .chart-line{stroke:#2563eb;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
    .chart-blue{stroke:#2563eb}.chart-red{stroke:#ef4444}.chart-dashed{stroke-dasharray:5 4}
    .tick-label,.legend-label{font:11px Arial,'Microsoft YaHei',sans-serif;fill:#475569}
  `;
  clone.insertBefore(style, clone.firstChild);
  return new XMLSerializer().serializeToString(clone);
}

function svgToImage(svg) {
  return new Promise((resolve, reject) => {
    const blob = new Blob([serializeChartSvg(svg)], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("图表 SVG 转 PNG 失败"));
    };
    image.src = url;
  });
}

async function exportChartsPng() {
  const figures = [...document.querySelectorAll(".result-charts figure")];
  if (!figures.length) {
    showToast("没有可导出的图表");
    return;
  }
  const scale = 2;
  const chartWidth = 420;
  const chartHeight = 280;
  const gap = 28;
  const padding = 34;
  const titleHeight = 32;
  const width = padding * 2 + figures.length * chartWidth + (figures.length - 1) * gap;
  const height = padding * 2 + titleHeight + chartHeight;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#0f2a4d";
  ctx.font = "600 16px Arial, 'Microsoft YaHei', sans-serif";
  ctx.fillText(`Battery Sim Studio 图表导出 · ${new Date().toLocaleString()}`, padding, 24);

  for (let index = 0; index < figures.length; index += 1) {
    const figure = figures[index];
    const svg = figure.querySelector("svg");
    if (!svg) continue;
    const x = padding + index * (chartWidth + gap);
    const y = padding + titleHeight;
    ctx.fillStyle = "#0f2a4d";
    ctx.font = "600 14px Arial, 'Microsoft YaHei', sans-serif";
    ctx.fillText(figure.querySelector("figcaption")?.textContent || `图表 ${index + 1}`, x, y - 10);
    const image = await svgToImage(svg);
    ctx.drawImage(image, x, y, chartWidth, chartHeight);
  }

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("PNG 生成失败");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `battery_studio_charts_${new Date().toISOString().slice(0, 10)}.png`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast(state.currentResult ? "已导出真实结果图表 PNG" : "已导出当前页面图表 PNG");
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
  const finiteTimes = (series.time_h || []).filter((value) => Number.isFinite(value));
  state.simTimeH = finiteTimes.length ? finiteTimes.at(-1) : null;
  updateRunStatus();
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
  const accel = Number(request.acceleration_factor) || 1;
  let line3 = document.getElementById("summaryLine3");
  if (!line3) {
    line3 = document.createElement("p");
    line3.id = "summaryLine3";
    line3.className = "small-note";
    document.getElementById("summaryLine2").insertAdjacentElement("afterend", line3);
  }
  line3.textContent = accel > 1
    ? `口径提示：共仿真 ${Number(request.cycles) || 0} 仿真圈 ≈ ${((Number(request.cycles) || 0) * accel).toLocaleString("zh-CN")} 等效圈（项目参数退化加速 ×${accel}）`
    : "";
  setResultTab(activeResultTab());
}

// ---------- 结果后处理 tab（性能/机理/热/参数/对比） ----------

function echartsBox(id) {
  if (typeof echarts === "undefined") return null;
  const element = document.getElementById(id);
  if (!element) return null;
  const chart = echarts.getInstanceByDom(element) || echarts.init(element);
  chart.resize();
  return chart;
}

const ECHARTS_BASE = {
  grid: { left: 60, right: 70, top: 56, bottom: 48 },
  tooltip: { trigger: "axis" },
};

const ECHARTS_CYCLE_XAXIS = {
  type: "value",
  name: "循环次数",
  nameLocation: "middle",
  nameGap: 28,
};

function setResultTab(tab) {
  document.querySelectorAll("[data-result-pane]").forEach((pane) => {
    pane.hidden = pane.dataset.resultPane !== tab;
  });
  document.querySelectorAll(".result-tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.resultTab === tab);
  });
  if (tab === "mechanism") renderMechanismChart();
  if (tab === "thermal") renderThermalChart();
  if (tab === "params") renderParamTable();
  if (tab === "compare") populateCompareDatasets();
}

function activeResultTab() {
  return document.querySelector(".result-tabs button.active")?.dataset.resultTab || "performance";
}

const MECHANISM_SERIES_DEFS = [
  ["lli_pct", "LLI (%)", 0],
  ["lam_neg_pct", "LAM 负极 (%)", 0],
  ["lam_pos_pct", "LAM 正极 (%)", 0],
  ["sei_ah", "SEI 损失 (Ah)", 1],
  ["sei_cracks_ah", "裂纹 SEI (Ah)", 1],
  ["plating_ah", "析锂损失 (Ah)", 1],
];

function renderMechanismChart() {
  const chart = echartsBox("mechanismChart");
  if (!chart) return;
  const data = state.currentResult?.degradation_metrics;
  const note = document.getElementById("mechanismNote");
  if (!data || !(data.cycle || []).length) {
    chart.clear();
    if (note) {
      note.textContent = state.currentResult
        ? "该任务无退化数据（老化接口未启用或退化变量缺失）"
        : "运行开启老化接口的仿真后，显示 LLI / LAM / SEI / 析锂逐圈演化";
    }
    return;
  }
  if (note) note.textContent = "逐圈退化机理演化（每圈末值）";
  const series = MECHANISM_SERIES_DEFS.filter(([key]) => Array.isArray(data[key])).map(([key, name, axis]) => ({
    name,
    type: "line",
    yAxisIndex: axis,
    showSymbol: false,
    data: data.cycle.map((cycle, index) => [cycle, data[key][index]]),
  }));
  chart.setOption({
    ...ECHARTS_BASE,
    legend: { top: 0, type: "scroll" },
    xAxis: ECHARTS_CYCLE_XAXIS,
    yAxis: [
      { type: "value", name: "损失 (%)" },
      { type: "value", name: "容量损失 (Ah)" },
    ],
    series,
  }, true);
}

const HEAT_SERIES_LABELS = {
  irrev_chg: "不可逆热-充电",
  irrev_dchg: "不可逆热-放电",
  rev_chg: "可逆热-充电",
  rev_dchg: "可逆热-放电",
  total_chg: "总热-充电",
  total_dchg: "总热-放电",
};

function renderThermalChart() {
  const chart = echartsBox("thermalChart");
  if (!chart) return;
  const data = state.currentResult?.heat_metrics;
  const note = document.getElementById("thermalNote");
  if (!data || !(data.cycle || []).length) {
    chart.clear();
    if (note) {
      note.textContent = state.currentResult
        ? "该任务无产热数据（产热分量计算失败或数据不足）"
        : "运行仿真后显示逐圈平均产热功率分量（不可逆/可逆 × 充/放）";
    }
    return;
  }
  if (note) note.textContent = "逐圈平均产热功率（W）";
  const series = Object.entries(HEAT_SERIES_LABELS)
    .filter(([key]) => Array.isArray(data[key]))
    .map(([key, name]) => ({
      name,
      type: "line",
      showSymbol: false,
      data: data.cycle.map((cycle, index) => [cycle, data[key][index]]),
    }));
  chart.setOption({
    ...ECHARTS_BASE,
    legend: { top: 0, type: "scroll" },
    xAxis: ECHARTS_CYCLE_XAXIS,
    yAxis: { type: "value", name: "平均产热功率 (W)", scale: true },
    series,
  }, true);
}

function formatParamNumber(value) {
  if (value !== 0 && (Math.abs(value) < 1e-3 || Math.abs(value) >= 1e5)) return value.toExponential(3);
  return String(Number(value.toFixed(6)));
}

function renderParamTable() {
  const body = document.getElementById("paramRows");
  if (!body) return;
  const parameters = state.currentResult?.parameters || [];
  if (!parameters.length) {
    body.innerHTML = '<tr><td colspan="2">运行仿真后显示该任务使用的关键参数</td></tr>';
    return;
  }
  body.innerHTML = parameters
    .map((parameter) => {
      const value = typeof parameter.value === "number" ? formatParamNumber(parameter.value) : escapeHtml(parameter.value);
      return `<tr><td>${escapeHtml(parameter.name)}</td><td>${value}</td></tr>`;
    })
    .join("");
}

async function populateCompareDatasets() {
  const select = document.getElementById("compareDataset");
  if (!select) return;
  try {
    const payload = await apiFetch("/api/data");
    const datasets = payload.datasets || [];
    const previous = select.value || state.importedDataset?.id || "";
    select.innerHTML =
      '<option value="">选择实验数据集...</option>' +
      datasets
        .map((dataset) => `<option value="${escapeHtml(dataset.id)}">${escapeHtml(dataset.file_name)}（${escapeHtml(dataset.rows)} 行）</option>`)
        .join("");
    if (previous && [...select.options].some((option) => option.value === previous)) {
      select.value = previous;
    }
  } catch (error) {
    showToast(error.message);
  }
}

async function runCompare() {
  const datasetId = document.getElementById("compareDataset")?.value;
  if (!state.currentJobId || !state.currentResult) {
    showToast("请先运行仿真或从任务历史加载结果");
    return;
  }
  if (!datasetId) {
    showToast("请选择要对比的实验数据集");
    return;
  }
  showToast("正在计算仿真-实测对比");
  const payload = await apiFetch(`/api/jobs/${state.currentJobId}/compare?dataset_id=${encodeURIComponent(datasetId)}`);
  const chart = echartsBox("compareChart");
  if (!chart) return;
  const series = [];
  const rrmseParts = [];
  const addBlock = (block, label) => {
    if (!block) return;
    series.push({
      name: `实测${label}`,
      type: "scatter",
      symbolSize: 5,
      data: block.cycle.map((cycle, index) => [cycle, block.exp[index]]),
    });
    series.push({
      name: `仿真${label}`,
      type: "line",
      showSymbol: false,
      data: block.sim_full.cycle.map((cycle, index) => [cycle, block.sim_full.values[index]]),
    });
    rrmseParts.push(`${label} RRMSE ${block.rrmse_pct.toFixed(2)}%`);
  };
  addBlock(payload.retention, "保持率");
  addBlock(payload.efficiency, "能效");
  chart.setOption({
    ...ECHARTS_BASE,
    legend: { top: 0 },
    xAxis: ECHARTS_CYCLE_XAXIS,
    yAxis: { type: "value", name: "%", scale: true },
    series,
  }, true);
  const rrmseNode = document.getElementById("compareRrmse");
  if (rrmseNode) rrmseNode.textContent = rrmseParts.join(" · ");
}

// ---------- 数据可视化：真实数据集曲线 + 寿命外推 ----------

const previewChartSpec = {
  width: 300,
  height: 112,
  margin: { top: 8, right: 10, bottom: 24, left: 34 },
  xlabel: "循环",
};

function drawRealPreviewCharts(series) {
  if (!series) return;
  const draw = (id, points) => {
    if (points.length < 2) return;
    const xDomain = paddedDomain(points.map((point) => point[0]), [0, 1], 0.02);
    const yDomain = paddedDomain(points.map((point) => point[1]), [0, 1]);
    drawLineChart(id, {
      ...previewChartSpec,
      xDomain,
      yDomain,
      xTicks: ticksForDomain(xDomain, 3),
      yTicks: ticksForDomain(yDomain, 3),
      lines: [{ className: "chart-blue", points }],
    });
  };
  const capacity = finitePairs(series.cycle || [], series.capacity_ah || []);
  draw("previewCapacityChart", capacity);
  const firstValid = capacity.find((point) => point[1] > 0);
  draw("previewRetentionChart", firstValid ? capacity.map(([cycle, value]) => [cycle, (value / firstValid[1]) * 100]) : []);
  draw("previewEfficiencyChart", finitePairs(series.cycle || [], series.efficiency_pct || []));
}

async function runExtrapolation() {
  if (!state.importedDataset?.id) {
    showToast("请先导入或选用实验数据集");
    return;
  }
  showToast("正在计算寿命外推");
  const payload = await apiFetch(`/api/data/${state.importedDataset.id}/extrapolate?target_soh=65`);
  state.extrapolation = payload;
  renderRetentionExtrapolation();
  showToast(`外推完成：预计第 ${payload.predicted_cycle} 圈到 ${payload.target_soh_pct}% SOH`);
}

function renderRetentionExtrapolation() {
  const extra = state.extrapolation;
  if (!extra) return;
  const measured = finitePairs(extra.measured.cycle, extra.measured.retention_pct);
  const extrapolated = finitePairs(extra.extrapolated.cycle, extra.extrapolated.retention_pct);
  if (!measured.length) return;
  const allPoints = measured.concat(extrapolated);
  const xMax = Math.max(...allPoints.map((point) => point[0]));
  const yValues = allPoints.map((point) => point[1]);
  const xDomain = [0, xMax * 1.04];
  const yDomain = [Math.min(...yValues, extra.target_soh_pct) - 3, Math.max(...yValues) + 2];
  const { width, height, margin } = previewChartSpec;
  drawLineChart("previewRetentionChart", {
    ...previewChartSpec,
    xDomain,
    yDomain,
    xTicks: ticksForDomain(xDomain, 3),
    yTicks: ticksForDomain(yDomain, 3),
    lines: [
      { className: "chart-blue", points: measured },
      ...(extrapolated.length > 1 ? [{ color: "#ef4444", dashed: true, points: extrapolated }] : []),
    ],
  });
  const svg = document.getElementById("previewRetentionChart");
  if (svg) {
    const xScale = makeScale(xDomain, [margin.left, width - margin.right]);
    const yScale = makeScale(yDomain, [height - margin.bottom, margin.top]);
    if (extrapolated.length > 1) {
      const x0 = xScale(extrapolated[0][0]);
      const x1 = xScale(extrapolated.at(-1)[0]);
      svg.insertAdjacentHTML(
        "afterbegin",
        `<rect x="${x0.toFixed(1)}" y="${margin.top}" width="${Math.max(0, x1 - x0).toFixed(1)}" height="${height - margin.top - margin.bottom}" fill="#fdeaea"></rect>`
      );
      svg.insertAdjacentHTML(
        "beforeend",
        `<text class="tick-label" x="${((x0 + x1) / 2).toFixed(1)}" y="${margin.top + 10}" text-anchor="middle" style="fill:#b91c1c">外推区间</text>`
      );
    }
    svg.insertAdjacentHTML(
      "beforeend",
      `<path class="chart-dashed" stroke="#b91c1c" fill="none" d="M${margin.left} ${yScale(extra.target_soh_pct).toFixed(1)}H${width - margin.right}"></path>`
    );
  }
  const note = document.getElementById("extrapolateNote");
  if (note) {
    note.hidden = false;
    const r2 = extra.r_squared != null ? `，R²=${Number(extra.r_squared).toFixed(4)}` : "";
    note.textContent = extra.method === "measured-crossing"
      ? `实测数据已达 ${extra.target_soh_pct}% SOH：第 ${extra.predicted_cycle} 圈（无需外推）`
      : `寿命外推（尾段线性拟合${r2}）：预计第 ${extra.predicted_cycle} 圈衰减至 ${extra.target_soh_pct}% SOH，红色虚线为外推段`;
  }
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
    if (action === "import-data") {
      document.getElementById("dataFileInput")?.click();
    }
    if (action === "edit-project") {
      const nextName = window.prompt("编辑当前项目名称", state.projectMetadata.project_name || "Demo_Project");
      if (nextName !== null) {
        try {
          await updateProjectField("project_name", nextName);
        } catch (error) {
          showToast(error.message);
        }
      }
    }
    if (action === "edit-cell-type") {
      const nextType = window.prompt("编辑电芯类型", state.projectMetadata.cell_type || "NCM/Graphite");
      if (nextType !== null) {
        try {
          await updateProjectField("cell_type", nextType);
        } catch (error) {
          showToast(error.message);
        }
      }
    }
    if (action === "save") {
      try {
        await saveProjectConfig();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "export") {
      downloadCsv();
    }
    if (action === "export-charts") {
      try {
        await exportChartsPng();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "preview") {
      drawConditionChart();
      showToast("工况预览已按当前模型容量和输入项更新");
    }
    if (action === "jobs") {
      await openJobsModal();
    }
    if (action === "close-jobs") {
      closeJobsModal();
    }
    if (action === "load-job") {
      try {
        await loadJobResult(actionNode.dataset.jobId);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "track-job") {
      state.currentJobId = actionNode.dataset.jobId;
      closeJobsModal();
      await resumeCurrentJob();
    }
    if (action === "rename-job") {
      try {
        await renameJobPrompt(actionNode.dataset.jobId);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "delete-job") {
      try {
        await deleteJobConfirm(actionNode.dataset.jobId);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "job-csv") {
      downloadUrl(`/api/jobs/${actionNode.dataset.jobId}/export.csv`);
      showToast("正在下载该任务的 CSV");
    }
    if (action === "switch-project") {
      try {
        await switchProject(actionNode.dataset.projectName);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "new-project") {
      const name = window.prompt("新项目名称", "");
      if (name && name.trim()) {
        try {
          await switchProject(name.trim());
        } catch (error) {
          showToast(error.message);
        }
      }
    }
    if (action === "use-dataset") {
      try {
        const payload = await apiFetch(`/api/data/${actionNode.dataset.datasetId}`);
        renderImportedDataset(payload);
        await loadDatasetsView();
        showToast(`已选用数据集 ${payload.dataset.file_name}，保存项目后生效`);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "dataset-csv") {
      downloadUrl(`/api/data/${actionNode.dataset.datasetId}/export.csv`);
      showToast("正在下载数据集 CSV");
    }
    if (action === "extrapolate") {
      try {
        await runExtrapolation();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "run-compare") {
      try {
        await runCompare();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "registry-reset") {
      resetRegistryFilters();
    }
    if (action === "task-run") {
      try {
        await runTask();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "task-stop") {
      try {
        await stopTask();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "bench-run") {
      try {
        await runBench();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "bench-runs") {
      try {
        await runBenchRuns();
      } catch (error) {
        showToast(error.message);
      }
    }
    if (action === "bench-curves") {
      try {
        await runBenchCurves();
      } catch (error) {
        showToast(error.message);
      }
    }
  });

  document.getElementById("taskTypeList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-task-type]");
    if (button && !button.disabled) selectTaskType(button.dataset.taskType);
  });

  document.getElementById("jobsModal")?.addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeJobsModal();
  });

  document.querySelectorAll(".segmented button, .mini-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      button.parentElement.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  document.querySelectorAll(".result-tabs button").forEach((button) => {
    button.addEventListener("click", () => setResultTab(button.dataset.resultTab));
  });

  document.querySelectorAll(".data-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".data-tabs button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      const tab = button.dataset.dataTab;
      document.querySelectorAll(".data-tab-pane").forEach((pane) => {
        pane.hidden = pane.dataset.dataPane !== tab;
      });
      if (tab === "registry") {
        loadRegistryFacets();
        loadRegistryRows();
      } else {
        loadDatasetsView();
      }
    });
  });

  document.querySelectorAll(".registry-select").forEach((select) => {
    select.addEventListener("change", () => loadRegistryRows());
  });

  window.addEventListener("resize", () => {
    if (typeof echarts === "undefined") return;
    ["mechanismChart", "thermalChart", "compareChart"].forEach((id) => {
      const element = document.getElementById(id);
      const chart = element ? echarts.getInstanceByDom(element) : null;
      if (chart) chart.resize();
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

  document.querySelector("#agingEnabled")?.addEventListener("change", syncAgingControls);

  document.getElementById("dataFileInput")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    try {
      await importDataFile(file);
    } catch (error) {
      showToast(error.message);
    }
  });
}

function boot() {
  installIcons();
  createPreviewRows();
  createLogRows();
  drawCharts();
  wireInteractions();
  decoratePlaceholders();
  updateAccelNote();
  updateCurrentPreview();
  setRoute(window.location.hash.replace("#", "") || "simulation");
  updateRunStatus();
  loadProjectConfig();
}

document.addEventListener("DOMContentLoaded", boot);
