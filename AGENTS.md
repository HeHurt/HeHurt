# Hithium 电池仿真项目 — Agent Harness

## 项目概述
基于 PyBaMM 的电池电化学仿真平台，用于 Hithium 电芯的性能预测、老化建模与实验对标。

**北极星（2026-07-03 确立）**：从「完成单点仿真任务」转向「建设 AI Agent 驱动的电池仿真工作流」。
一切新能力按三个标准设计：AI 可调用（headless 入口而非 notebook）、可校验（机器可判的验收判据）、
可检索（registry 而非散落文件）。路线：① 数据 registry（已上线，见「数据 registry」节）→
② spec→run 仿真运行时（对齐 COMSOL 侧 `runs/<时间戳>_<case>/` 惯例）→
③ 决策原语工具化（calibrate / identifiability / discriminate）→ ④ run 历史沉淀与检索。

## 架构与技术栈
- **仿真引擎**: PyBaMM (DFN 模型为主)
- **求解器**: IDAKLUSolver (首选)，fallback CasadiSolver
- **老化模型**: SEI + LAM + 裂纹 + 锂析出 (OKane2022 基础)
- **绘图**: matplotlib + scienceplots (`plt.style.use("science")`)
- **字体**: Calibri + Microsoft YaHei
- **数据导出**: openpyxl (带条件格式色阶)
- **语言**: Python 3.10+，中文交流，技术术语保留英文

---

## Harness 分域指导表

子目录 AGENTS.md 提供分域指导。在该区域工作前，先阅读对应文件。

| 区域 | Harness 文件 | 要点 |
|------|-------------|------|
| 核心仿真代码 | `BatteryProject/src/AGENTS.md` | 函数签名规范、测试要求、模块导出 |
| 参数文件 | `params/AGENTS.md` | 参数文件结构、温度依赖函数、防污染规则 |
| Notebook 工作区 | `work/MIC_1175Ah/AGENTS.md` (各电芯目录同构) | Notebook 模板、importlib.reload、作图规范 |
| 计划与规格 | `.plans/AGENTS.md` | spec/plan 沉淀流程、任务分解模板 |

---

## 项目结构

### 核心模块 (`BatteryProject/src/`)
- `notebook.py` / `notebook_api.py` — 新 notebook 推荐入口（`setup_notebook` + 收窄 API）
- `simulation.py` — 仿真 facade；实现拆分在 `simulation_dcr / _peak / _eis / _frequency / _rpt / _pulse_lifecycle / _regional_parallel / _common.py`
- `parameter_identification.py` — 参数辨识（BO/GA 多优化器）；`uq_calibration.py` — MCMC 后验/可辨识性地基
- `electrolyte_dryout.py` — 电解液干涸；`swelling_coupling.py` — 膨胀力-孔隙率耦合
- `plotting.py` / `analysis.py` / `compare.py` — 绘图、指标、Sim-Exp 一站式对标
- `exp_loader.py` / `data_cleaning.py` / `lifecycle_exp.py` — 实验数据加载与清洗
- `data_registry.py` — 实验数据 registry CLI（见「数据 registry」节）
- `easy_imports.py` — legacy 便捷导入（旧 notebook 用，新代码勿扩展）
- `api/` — Studio 后端（FastAPI + SQLite）；Phase 2 已完成，`JOB_TYPES` 注册 10 类(cycle / calendar_aging / frequency / pulse / lifecycle_heat / psd / regional_coupled_aging / peak_current / eis / rate_benchmark)，统一走 `_run_workflow_job` 消费 spec→run 运行时

### 参数文件 (`params/`)
- 每个文件导出 `get_hithium_params(t_factor, temperature)` 函数；`params/__init__.py` 提供 `load_cell_params` registry
- 锂电：`paramsMIC.py` (1175Ah) / `params280.py` / `params314.py` / `params314_5plus3.py` / `params587.py` / `params50方壳.py` / `params64150.py`
- 锂电（续）：`params650.py` / `params1300CW363.py` (1199Ah) / `paramsLDSCW368.py` (1362Ah) / `paramsLDSCW501.py` (1362Ah)
- 软包/其他：`paramsCW362_pouch.py` / `paramsCW391_pouch.py` / `paramsNa.py`（钠电）
- 同目录 `.csv` 为 OCP/扩散等查表数据

### 顶层目录地图
- `data_raw/` / `data_processed/` — 实验数据（按电芯分目录）；索引见根目录 `datasets.json`
- `datasets.json` — 数据 registry（git 跟踪，由 `data_registry.py` 维护）
- `work/` — 按电芯/体系组织的任务交付区；新任务以 `YYYYMM_何争_任务名称Vn` 为完整可上传单元
- `COMSOL/runs/` / `COMSOL/results/` / `COMSOL/scripts/` / `COMSOL/models/` / `COMSOL/logs/` — COMSOL/MATLAB 闭环工作目录（见下方 COMSOL 规范）
- `archive/` — 归档的 legacy 脚本与旧 notebook
- `tools/` — 预处理与运维脚本（`git_dlp_clean.py`、`0_preprocess_*.py` 等）
- `skills/` — Codex 项目 skill 池真源（junction 机制见「共享基础设施」）

### Notebook 工作区 (`work/`)
| 目录 | 电芯型号 | 主要内容 |
|------|---------|---------|
| `work/MIC_1175Ah/` | MIC 1175Ah | 峰值电流、CW363对标、欧盟循环、电解液干涸 |
| `work/314Ah/` | 314Ah | 老化建模、竞品分析、可靠性对标、不同温度/倍率 |
| `work/280Ah/` | 280Ah | CW254 对标 |
| `work/587Ah/` | 587Ah | 常规循环、脉冲插入、调频 |
| `work/cross_cell/` | 跨电芯 | 多电芯对比与共用工况任务包 |
| `work/AI_virtual_cell/` | — | 定容能效、COMSOL迁移、PSD |
| `work/RTE机理/` | — | RTE 机理研究资料 |
| `work/patent_disclosures/` | — | 专利交底书产出 |

（`work/cylindrical/`、`work/sodium/` 目前是空骨架，待启用。）

### 新任务与交付包工作流

- 新任务必须先执行 `python tools/task_delivery.py new-task ...`，在 `work/<cell>/` 下创建
  `YYYYMM_何争_任务名称Vn/`；负责人默认何争，首版必须显式为 V1。
- 从 `BatteryProject/examples/` 选择 canonical Notebook，由 `new-task --template` 复制到任务包
  `02_模型/` 后再修改；禁止为单次任务直接修改 examples 原件。
- 整合 canonical Notebook 时必须保留旧文件能力并集：只把重复仿真、解析和导出代码下沉到
  `BatteryProject/src/`，不得删减分析章节、图表、实验对标、诊断或导出入口；先做 feature parity
  矩阵，未验证通过不得视为完成整合。
- 原始运行、中间结果和日志写入 `BatteryProject/output/runs/<workflow>/<run_id>/`，不得再新建
  `work/**/notebooks/output`、`outputs` 或 `results/output`。
- `.codex`、Codex scratch、聊天附件临时目录只允许短期工具中转，禁止作为仿真数据、结果或交付物
  的保存位置；任务结束前必须把有效文件归档到对应版本任务包，工具中转文件应清理。
- 验证后的 run 使用 `python tools/task_delivery.py publish-task ...` 复制并固化到任务包
  `04_输出结果/`；发布不移动、不覆盖原始 run。
- 一个任务包至少包含任务说明、仿真报告、模型、输入数据、输出结果和复现说明，完成后可整包上传。
- 已上传版本冻结；正式返修创建 V2/V3，不覆盖旧版。跨电芯任务放在 `work/cross_cell/`。
- 完整流程与命令见 `docs/TASK_DELIVERY_WORKFLOW.md`。

---

## 数据 registry（datasets.json）

**Agent 查实验数据必须先查 registry，不要直接翻 `data_raw/` 猜文件名。**

- 扫描/更新：`python BatteryProject/src/data_registry.py scan`
- 查询：`python BatteryProject/src/data_registry.py ls --cell MIC --temp 25 --test 倍率充电`
- 覆盖概览：`python BatteryProject/src/data_registry.py summary`

规则：
- 新实验数据放入 `data_raw/<电芯>/` 后必须跑一次 `scan` 登记。
- 机器推断字段（temperature_C/rate/test_type/soh_pct/sample_id）status=`auto`；
  人工核实后把 status 改为 `curated` 并补全 signals/source/quality，此后重扫不再覆盖该条目的工况字段。
- 无效/垃圾文件把 status 改为 `ignore`（保留条目，不要删）。
- 文件移动路径即换 id，会生成新条目；移动前先想清楚。

---

## Legacy 文件归档状态（2026-07-03 更新）

历史 legacy 脚本已集中到 `archive/legacy_scripts/`（原 `工具/`、`MIC/` 顶层目录已不存在）：

| 文件 | 状态 | 说明 |
|---|---|---|
| `archive/legacy_scripts/MIC/宫工-徐恒-不同CW/Fun_NC.py` | ⚠️ `[LEGACY-PARTIAL]` | 干涸主链已迁入 `src/electrolyte_dryout.py`；**待迁**清单见 `docs/FUN_NC_TODO.md` |
| `archive/legacy_scripts/314/...`（model.py / model_params.py） | ✅ 已归档 | 早期 280/314 原型；已由 `params/` + `src/` 取代 |
| `Fun_HZ.py`（文件已删除） | ✅ | 曾全量迁入 `BatteryProject/src/`；迁移记录见 `docs/FUN_HZ_MIGRATION.md` |

> **规则**：以上文件禁止添加新功能；新代码一律放在 `BatteryProject/src/` 下对应模块。

---

## 常用工作流
1. **OCV 对标**: 0.005C 充放电仿真 vs 实验数据
2. **峰值电流**: `run_peak_current()` 多温度扫描 → Excel map 导出
3. **倍率对标**: 多倍率充放电仿真 vs 实验，计算 RRMSE
4. **老化预测**: 长循环仿真 + DCR/容量/功率 fade 曲线
5. **DCR 测试**: `perform_dcr_test()` 脉冲 DCR 与功率

---

## Pre-Commit 验证协议

> **解释器**：本机 `python` 指向 WorkBuddy 自带 3.13（**无 pytest / flake8 / pybamm**）。
> 项目真实环境是系统 Python 3.11，下列命令中的 `python` 一律替换为：
> `C:/Users/hez/AppData/Local/Programs/Python/Python311/python.exe`（pytest 9.0.3 / flake8 7.3.0 / pybamm 26.4.2）。
> `.venv` 与 `.venv-liionpack` 都没有装 pytest，不能用来跑测试。

修改 `BatteryProject/src/` 下的代码后，必须按顺序完成：

1. **Lint**: `python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503` — 必须通过
2. **单元测试**: `python -m pytest BatteryProject/tests/ -q` — 必须全部通过
3. **烟雾测试** (涉及仿真逻辑时): 在 Notebook 中用最小配置验证（单温度、单SOC、1个循环）

修改 `params/` 参数文件后：
1. 确认 `get_hithium_params(1, 298.15)` 可正常调用
2. 确认返回字典包含 `"Nominal cell capacity [A.h]"` 键

**如果任何验证失败，先修复再继续。不要跳过。**

---

## 反馈协议

当 Agent 犯错被纠正时：

1. 判断错误类型：
   - **harness 空白** → 更新对应的 AGENTS.md 文件填补规则
   - **一次性失误** → 当场修正即可
   - **反复出现的模式** → 加入对应 AGENTS.md 的「禁止事项」段落
2. 确保后续会话能读取到更新后的指导

这形成棘轮效应：harness 在每次 review 后只会变得更好。

---

## 关键规则（全局）
- **全程用中文答复**（技术术语、代码、标识符保留英文）
- 每次换温度必须重新 `pybamm.ParameterValues("OKane2022")` + `params.update()`，防止参数污染
- 修改 src 后 Notebook 需 `importlib.reload()` 并重新绑定函数符号
- `var_pts` 标准配置: `{"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}`
- 本机工作区文件可能受加密软件保护；对 `D:\Users\hez\Desktop\hithium` 下的工程文件默认直接走白名单读取，不再先用 PowerShell、ripgrep 或普通第三方进程试读：`.py/.csv/.xlsx` 优先用 Python，`.ipynb` 或 Python 仍无法解密的高密级文件直接用 `Code.exe` Node bridge；Spreadsheet/文档工具读取加密文件前先通过 Python/`Code.exe` 生成明文中转副本。
- DLP 保护的 Office 二进制容器（尤其 `.pptx/.docx/.xlsx`）禁止使用 `Code.exe` 的 UTF-8/文本读取桥；该桥可能直接返回 `%TSD-Header-###%` 密文且会破坏二进制内容。必须先用白名单 Python 按 bytes 读取并写入 `C:\Users\hez\AppData\Local\Temp\codex-hithium\` 明文中转副本，确认文件头为 `PK\x03\x04` 且 `zipfile.is_zipfile(...) == True`，再交给 Presentations/Documents/Spreadsheets 工具。若 Python 仍读到 TSD 密文，则改走对应 Office 应用的原生 COM 打开/另存通道，不得回退到 `Code.exe` 文本桥。
- 以后通过 PowerPoint 或其他 Office 应用保存/导出 PDF 时，默认只交付一个明文正式 PDF：Office 原生导出文件仅作为内部中转，由白名单 Python 读取其解密后的 bytes，并把该明文内容作为最终 PDF 写到用户指定路径；不得同时保留或交付一个 DLP 正式版和一个明文副本。PDF 解析、页数/加密检查、渲染和视觉 QA 均针对最终文件；交付前必须从非白名单读取视角复核文件头为 `%PDF-`、不是 `%TSD-Header-###%`。若指定目录的 DLP 策略会在落盘时重新加密，必须明确告知用户，不能把仍带 TSD 外壳的文件称为明文 PDF。
- PowerPoint COM 自动化不得无条件调用 `Application.Quit()`：PowerPoint 可能复用用户已打开的应用实例，`Quit()` 会关闭所有无关演示文稿。必须只关闭本次由 Agent 打开的 `Presentation`；仅当任务开始前不存在 PowerPoint 进程、且关闭目标文件后确认没有任何其他演示文稿时，才允许退出应用。任务前后应记录已有 PowerPoint 进程/文稿，禁止影响用户正在编辑的窗口。
- 在编写代码前先描述方案并等待批准；需求不明确时先提问
- 单次任务修改超过 7 个文件时，先分解为更小任务

---

## 共享基础设施（Codex）

> 本节是 Codex 在本项目中的机器/工程级单一真源。Claude Code 已封禁、GitHub Copilot 已停用，
> 相关项目资产于 2026-07-31 外移；恢复方法见本节末尾。

### 1. 本机 DLP 文件加密（Trend Micro）
受保护文件头含 `%TSD-Header-###%`，非白名单进程（PowerShell / ripgrep / git.exe）
读取会得到密文/乱码。
- **判断**：文件前几字节含 `%TSD-Header-###%` 即密文。
- **读**：改用白名单 `python`：`python -c "print(open('path', encoding='utf-8').read())"`
  （stdout 不过 DLP）。看到乱码不要反复排查编码，直接换 python。
- **写**：先写到 `C:\Users\hez\AppData\Local\Temp\codex-hithium\` 中转，再用 python 读出写入目标
  路径（python 写入会被 DLP 按原级别重新加密）。直接 Edit 受保护 `.py` 会失败。
- **范围**：BatteryProject 下所有 `.py` 和大部分 `.ipynb`；`.md`/`.toml`/`.bat`/
  `run_frontend.py` 是明文，可直接读写。
- **高密级文件（python 也解不开）**：用白名单 VS Code 的 `Code.exe` 当 Node 跑读写明文
  （`Code.exe` 在白名单内）：
  - 读：`$env:ELECTRON_RUN_AS_NODE='1'; & 'D:\软件安装\Microsoft VS Code\Code.exe' -e
    "console.log(require('fs').readFileSync('<路径,\\ 转义>','utf8'))"`
  - 写：同一座桥 `fs.writeFileSync`。**已验证 `.ipynb` 写回会被 DLP 重新加密**
    （`%TSD-Header-###%` 保护级别不丢；但 `.txt` 不会——DLP 按文件类型分类）。
  - 多行/复杂逻辑写成 `.js` 放 `scratch\`，用 `Code.exe <script.js>` 跑（避免内联转义）。
  - 改前先字节拷贝备份（`Copy-Item` 拷的是密文，可还原）。
- **已在 VS Code 打开的 Notebook**：优先使用 `tools/vscode-notebook-bridge/bridge-client.ps1`
  读取和修改，不要直接写磁盘。客户端会按 `-Uri <notebook路径>` 自动选择匹配且存活的 VS Code
  窗口；用 `active-notebook` 读取、`replace-cell` 或 `apply-edits` 修改，修改会立即出现在 Notebook UI，
  需要持久化时加 `-Save`。`Code.exe` 仅作为 Notebook 未打开、未加载或 bridge 不可用时的磁盘级 fallback。

### 2. Git 提交：只存明文（绕过 DLP 密文）
git.exe 非白名单，直接 add 会把密文存进仓库。已配 clean filter 存**明文**：
- **机制**：`.gitattributes` 把 `*.py`/`*.ipynb` 交给 filter `dlp`，filter 调 `python`
  按路径重读拿明文输出给 git。脚本 `tools/git_dlp_clean.py`（自身 `-filter`）。
- **本地配置**（在 `.git/config`，不随仓库分发，换机需重配）：
  - `git config filter.dlp.clean "python tools/git_dlp_clean.py %f"`
  - `git config filter.dlp.required true`
- **闸门**：`.git/hooks/pre-commit` 拒绝仍是密文的 `.py`/`.ipynb`。
- **规则**：不要绕过 filter 塞密文；换机克隆后先重跑上面两条 `git config` 并恢复
  pre-commit hook。解不开的文件 `git rm --cached` 不跟踪，而非提交密文。

### 3. Codex Skill 池
Codex skill 入口通过整目录 junction 指向项目真源。
- **真源**：`D:\Users\hez\Desktop\hithium\skills\`（已纳入 git）。
- **入口 junction**：`…\.codex\skills` → 真源。
- **COMSOL Skill 真源**：`skills\comsol-battery-model-automation\`（普通目录，直接纳入 git；不再使用内层 junction）。
- **不跟踪**：`skills/.system/`（Codex 自带系统 skill，随版本重建）。
- **换机重建**（1 条 mklink）：只需重建 Codex 入口 junction；COMSOL Skill 会随仓库直接存在。
- 新建 skill 直接落进真源目录即可由 Codex 使用。

### 4. 已停用工具资产
Claude Code、GitHub Copilot 与通用 agent 兼容入口已外移到
`D:\Users\hez\Desktop\hithium-外移\disabled-tooling\20260731_claudecode_copilot_V1\`。
后续恢复时按该目录中的 `RESTORE.md` 放回，不要重新手工创建不同版本。

---

## COMSOL with MATLAB / LiveLink for MATLAB 工作规范

### 项目目标
通过 MATLAB 调用 COMSOL，完成脚本化建模、参数化仿真、自动求解、自动后处理和错误复盘，形成“建模脚本化 -> 运行仿真 -> 读取反馈 -> 修复错误 -> 沉淀经验”的闭环自动化工作流。

### 当前前提
COMSOL with MATLAB / LiveLink for MATLAB 已经可以正常连接；除非当前错误明确指向环境、路径、license 或 COMSOL server 问题，不优先排查基础安装。

### 运行原则
- 优先基于已有 `.mph` 文件或 COMSOL Desktop 导出的 `.m` 文件改造。
- 不要凭空编写复杂 COMSOL API；不确定 API 时，优先参考已有导出脚本、COMSOL LiveLink for MATLAB 文档、COMSOL Programming Reference、COMSOL Knowledge Base 和 MATLAB/COMSOL 报错。
- 每次修改后必须运行最小可验证案例，再扩展到参数化或批量仿真。
- 每个大任务维护一份内部运行日志；仅在实际失败时生成错误报告，不为成功运行创建空错误文件。
- 失败后必须读取报错、定位原因、修复并再次验证。
- 每次失败和修复都要追加写入 `COMSOL/logs/lessons_learned.md`，避免重复犯错。

### 文件保护规则
- 不要删除 `.mph`、`.m`、日志、结果文件。
- 不要覆盖成功运行结果。
- 一个大任务从建模到后处理只创建一个中文任务包，命名沿用 `work` 规范：
  `YYYYMM_何争_中文任务名称Vn`。同一任务的后续计算不得反复新增顶层英文时间戳文件夹。
- 正式任务包优先放在对应的 `work/<体系>/` 下；COMSOL 临时运行记录统一收进该任务包的
  `99_内部文件/运行记录/`，不得散落到用户可见的结果目录。
- 保存模型快照前确认目标路径位于当前任务包内，使用 V1/V2 或 baseline/coupled 等明确文件名，
  避免覆盖已成功模型。

### 标准目录
- `COMSOL/models/` 保存 `.mph` 和 COMSOL Desktop 导出的 `.m` 模型文件。
- `COMSOL/scripts/` 保存 MATLAB 自动化脚本。
- `COMSOL/runs/` 仅保留历史任务和无法归属任务包的临时诊断；新正式任务不得按每次运行新增顶层目录。
- `COMSOL/results/` 保存汇总结果。
- `COMSOL/logs/` 保存错误与经验沉淀。

### 标准任务包与精简交付
一个大任务只创建一次如下中文目录；已上传版本冻结，正式返修再创建 V2/V3：

```text
work/<体系>/YYYYMM_何争_中文任务名称V1/
├─ 01_任务说明/
├─ 02_模型/                 # 仅保留需要审核或交付的 .mph
├─ 03_输入数据/
├─ 04_输出结果/
│  ├─ 图表/                 # 最终 PNG/PDF
│  └─ 结果汇总.xlsx          # 优先用一个工作簿收纳指标和必要明细
├─ 05_复现说明/
└─ 99_内部文件/
   ├─ 脚本/
   ├─ 运行记录/
   ├─ JSON/
   └─ 中间数据/
```

- 用户可见的任务包根目录和 `04_输出结果` 不放 JSON、日志、脚本、session 文件或成百上千个空间场 CSV。
- `config.json` 用于记录仿真输入，audit/verify JSON 用于机器回读验收，summary JSON 用于驱动作图；
  它们都是内部可复现文件，统一放入 `99_内部文件/JSON/`，不作为正式交付物。
- 正式交付默认精简为：最终 `.mph`、最终图、一个结果汇总工作簿和一份简短说明。只有用户明确要求时才额外交付原始 CSV/JSON。

### COMSOL API 安全规则
- 物理参数必须显式带单位，例如 `"10[mm]"`、`"293.15[K]"`、`"1[A]"`。
- 不要硬编码 boundary、domain、edge ID，除非已从模型或导出脚本验证。
- 优先使用 COMSOL Desktop 中的 named selections。
- 先验证 geometry，再 mesh，再 solve。
- 参数扫描前必须先跑通一个 baseline case。
- 调试时优先简化 mesh/physics，批处理时避免不必要绘图和大规模 field data 传输。
- 仅提取任务需要的 metrics；重大 solver 或 physics 修改前保存 model snapshot。

### Solver 调试规则
Solver 失败时按顺序检查：

1. 参数和单位是否合法。
2. geometry 与 selections 是否有效。
3. materials 是否完整分配。
4. boundary conditions 是否缺失或冲突。
5. mesh 是否成功、质量是否可接受。
6. initial values 是否合理。
7. 是否可用 stationary 或 reduced model 做诊断。
8. 放宽 tolerance 只用于诊断，不作为最终修复。

### 错误分类
失败后必须归类为以下之一：

1. Environment/path/license issue.
2. COMSOL server or MATLAB connection issue.
3. API syntax issue.
4. Model tag or feature tag issue.
5. Geometry build issue.
6. Selection/domain/boundary ID issue.
7. Material/parameter/unit issue.
8. Mesh issue.
9. Solver/convergence issue.
10. Memory/performance issue.
11. Postprocessing/export issue.
12. Missing baseline model issue.
13. Unknown issue.

### 任务结束汇报
每次任务结束时必须汇报：

- 修改了哪些文件。
- 执行了哪些命令。
- 仿真是否成功。
- 主要结果是什么。
- 如果失败，失败原因、已尝试修复、下一步建议是什么。
