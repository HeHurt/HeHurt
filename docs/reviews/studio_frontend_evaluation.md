# Battery Sim Studio（`studio/`）前端完整评估报告

评估对象：`BatteryProject/studio/`（内部全功能 Studio，原生 JS SPA）
评估时间：2026-07-22
对比基准：同仓库 `battery-sim-site/`（公开受限版，Next.js/React）

---

## 项目快照

| 文件 | 行数 / 大小 | 说明 |
|------|------------|------|
| `app.js` | 1920 行 / 76 KB | 全部业务逻辑，单文件，全局作用域 |
| `styles.css` | 1792 行 / 28 KB | 全部样式 |
| `index.html` | 429 行 / 32 KB | SPA 外壳 + 全部 DOM 骨架 |
| `vendor/echarts.min.js` | 1.0 MB | 图表库（第三方） |

**关键事实**：无 `package.json`、无构建、无 lint、无测试、无 TypeScript——纯静态文件，靠后端同源代理提供服务。功能涵盖：工况仿真(DFN/SPMe)、项目管理、数据集导入导出、结果后处理(性能/机理/热/参数/对比)、参数识别、敏感性、优化设计、等效电路、材料库、电芯数据库、报告导出。

---

## 六维评分

### 1. 代码质量 — 5 / 10
**优点**
- 事件处理用**全局事件委托**（`document` 级 click + `data-action` + `closest`，行 1706-1709），这是原生 JS 里可维护的写法，避免成百上千个独立监听器。
- 函数命名清晰（63 个函数），`apiFetch` 统一封装、统一错误结构。
- `escapeHtml` 复用良好。

**不足**
- **单文件 1920 行、全局 `state` + 全局函数**，无模块边界、无命名空间。任何一处改动都可能影响全局。
- **两套图表系统并存**：手写 SVG（`drawLineChart` / `renderTimeSeriesChart` / `renderCycleChart` / `drawDataPreviewCharts`）+ echarts（`echartsBox` 用于机理/热/对比）。渲染层不统一，维护两套心智模型。
- **表格渲染三连重复**：`renderJobsRows` / `loadProjectsView` / `loadDatasetsView` 各自重复「加载中…/错误/空态/数据行」骨架，仅字段不同。
- 全局可变状态 `state.xxx =` 散落全文件，无不可变约束，难推理。

### 2. 技术架构 — 4.5 / 10
**优点**
- 轻量、零依赖运行时（除 echarts），适合内网内部工具，部署简单（丢静态文件即可）。
- 基于 `hashchange` 的路由（行 1871）自包含，无框架开销。

**不足**
- 2000 行、11+ 模块的复杂应用用**无框架 + 无构建**的原生 JS，架构选型与规模不匹配。后续每加一个模块，单文件只会更臃肿。
- **echarts 1MB 作为阻塞脚本在 body 末尾同步加载**（行 426），但它只服务于 3 个结果 tab（机理/热/对比），主流程根本用不到。
- 无模块系统（ES Modules 都没用），无代码分割，无 Tree-shaking。
- 与 `battery-sim-site` 形成"同一后端、两套技术栈"的分裂（详见上一轮结论）。

### 3. 性能优化 — 5.5 / 10
**优点**
- 手写 SVG 图表零额外体积，轻量。
- `styles.css` 28KB、首屏无需字体优化（系统字体）。

**不足**
- **1MB echarts 阻塞加载且全量解析执行**，是最大瓶颈——应改为按需动态 `import()`，仅当用户打开机理/热/对比 tab 时再加载。
- 脚本无 `defer`/`async`（虽在 body 末尾，不阻塞 HTML 解析，但阻塞 `load` 与可交互时间）。
- 无构建压缩，`app.js` 76KB 未 minify（尚可，但 echarts 1MB 是硬伤）。
- 轮询固定 1.2s（与公开站一致），无退避。

### 4. 可维护性 — 3 / 10（最弱维度）
**优点**
- 代码风格统一、注释到位（中文）、关键逻辑（如轮询失败重试、SVG 安全跳过）有说明。

**不足**
- **零自动化验证**：无测试、无 lint、无类型检查、无 `package.json`、无 CI。1920 行应用任何改动都是"裸奔"，回归风险极高。
- 单文件 + 全局状态 = 重构成本高、新人上手难。
- 无类型保护：后端 API 契约（job 字段、result 结构）一旦变化，前端静默失效，无编译期报错。
- 这是与 `battery-sim-site`（有 ES、Lint、tsc、2 个测试）落差最大的地方。

### 5. 用户体验 — 7 / 10
**优点**
- **响应式更彻底**：4 个断点（1480/1240/980/640px）+ 移动端汉堡菜单（`toggle-menu`），比公开站的 3 断点更细。
- 可访问性基础好：`<aside aria-label>`、按钮 `aria-label`、导航 `role="navigation"`、图表区 `role="img"`。
- 交互反馈完整：toast、进度、模态框、stepper 流程指示。

**不足**
- **无 `prefers-reduced-motion`**（公开站有）。
- 无 `<meta description>` / OpenGraph / favicon（内部工具可接受，但公开站做了）。
- 初始视图无骨架屏；图表（尤其 echarts）在首次打开 tab 时可能有短暂空白。
- 部分 SVG 图表缺文本等价描述，屏幕阅读器用户拿不到数据。

### 6. 安全性 — 7.5 / 10
**优点**
- **XSS 面控制得当**：所有 API 数据源的 `innerHTML` 插入（jobs/projects/datasets/logs/preview）都经 `escapeHtml()` 转义；仅有静态文案未转义。
- **无 `eval` / `new Function` / 动态代码执行**。
- **前端不存 token**：无 `localStorage`/`sessionStorage`，无 Bearer 令牌落在客户端（与公开站把 token 放内存 state 相比，这里甚至更低暴露面，可能走后端 cookie/session）。
- echarts 是**本地 vendored** 副本，非运行时 CDN，无供应链注入风险。

**不足**
- 无 CSP / 安全响应头（依赖部署层，源码未体现）。
- vendored echarts 版本未知，长期不更新的第三方库有潜在 CVE 风险。
- 内部工具、低风险场景，但安全基线仍弱于公开站（8 分）主要是缺 CSP 与依赖治理。

---

## 最关键的三个问题（按优先级）

### ① 零自动化验证（可维护性，优先级最高）
1920 行应用无任何测试/lint/TS/CI，改动即"裸奔"。
**方案**：
1. 加 `package.json` + `eslint` + `vitest`（用 jsdom 模拟 DOM）。
2. 先补 3–5 个冒烟测试：API 契约解析、`escapeHtml`、路由切换、仿真提交→轮询→结果闭环。
3. 接入 CI（哪怕本地 `npm test` 门禁也行）。

### ② 1MB echarts 阻塞加载（性能）
全量解析却只服务 3 个 tab。
**方案**：改为动态导入——在 `renderMechanismChart` / `renderThermalChart` / `renderCompareChart` 内 `await import('./vendor/echarts.min.js')`（或拆成独立 chunk），首屏省下 ~1MB 解析成本。

### ③ 单文件全局结构与重复渲染（代码质量/架构）
1920 行单文件 + 两套图表系统 + 三连表格模板。
**方案**：
1. 按模块拆分：`api.js` / `state.js` / `charts-svg.js` / `charts-echarts.js` / `views/*.js`（用原生 ES Modules，`index.html` 加 `type="module"`）。
2. 抽象 `renderTable(rows, columns, emptyText)` 统一三处表格渲染。
3. 选定**单一图表层**（建议 echarts 统一，SVG 仅留轻量预览），消除双系统。

---

## 与 `battery-sim-site/` 的横向对比

| 维度 | `studio/`（内部） | `battery-sim-site/`（公开） | 谁更好 |
|------|------------------|----------------------------|--------|
| 代码质量 | 5 | 7 | 公开站 |
| 技术架构 | 4.5 | 6.5 | 公开站 |
| 性能 | 5.5 | 7 | 公开站（但站有 og.png 1.3MB 问题） |
| 可维护性 | 3 | 6 | 公开站 |
| 用户体验 | 7 | 7.5 | 公开站（响应式略少但更现代） |
| 安全性 | 7.5 | 8 | 公开站（公开站有 CSP 面 + token 治理） |
| **总分** | **≈32/60** | **≈42/60** | 公开站明显领先 |

**结论**：`studio/` 是功能更全但工程成熟度更低的一端——它承载了全部内部能力，却用最"原始"的方式实现，且完全没有测试/lint/类型护栏。`battery-sim-site/` 规模小但工程闭环完整。两者共同的根因仍是上一轮指出的：**同一后端被两套前端重复实现**，核心仿真闭环写了两遍。建议优先消除这个重复（抽共享仿真 SDK），其次给 `studio/` 补齐测试与模块拆分。
