# Hithium 工程系统性评估

- 评估日期：2026-09-08
- 评估范围：仓库全量（23G，`work/` 14G + `data_raw/` 6.5G + `BatteryProject/` 1.9G + `archive/` 368M）
- 评估方式：四路并行只读勘察（核心代码与参数 / 数据资产与 registry / 任务交付与文档 / 工程卫生与仓库治理）
- 工作区状态：`git status` 干净，35 commits，902 个被跟踪文件

> 数据口径说明：本机有 Trend Micro DLP 加密，非白名单进程读取 `.py/.csv` 会得到密文。
> 本报告所有行数/统计均通过白名单工具（Grep / Python 解析 JSON）获得，个别文件的行数可能与
> 编辑器显示不同，已在使用处标注。

---

## 一、总体结论

**综合评分：6.0 / 10 —— 架构先行，治理滞后。**

这个工程最值得肯定的一点是：它不是一堆 notebook 的自然堆积，而是有明确的架构意图。
facade 分层、参数去重、spec→run 运行时、registry 驱动的数据管理，这四件事都是"设计出来的"，
不是长出来的。AGENTS.md 21KB 的 harness 也说明你在持续把经验固化为规则。

但当前的主要矛盾是：**架构资产的完成度明显高于治理资产的完成度**。具体表现为三个
"机制建成、从未使用"：

| 机制 | 建成状态 | 实际使用率 |
|---|---|---|
| 数据 registry curation（`auto`→`curated`） | 已实现，幂等 scan 正确 | **0 / 638 = 0%** |
| 任务包版本冻结（V1 冻结→V2 返修） | 有 V2/V3/V4 包 | **0 个冻结标记**，3 组版本重复 published |
| Pre-commit 验证协议（flake8 + pytest） | 写进 AGENTS.md | **无 CI、无 lint 配置、无 hook** |

以及两个会直接咬人的真实 bug（详见 2.3、2.4）。

### 评分卡

| 维度 | 评分 | 一句话 |
|---|---|---|
| 架构与代码质量 | 7.0 | facade 拆分干净无环，参数去重到位；超长函数与测试缺口是主要欠账 |
| 数据资产健康度 | 4.0 | registry 是合格的文件清单，还不是可信元数据（curation 0%、温度识别率 46.9%） |
| 任务交付与流程 | 7.5 | 六要素齐全率 82.5%，命名合规率 85%；冻结机制缺位 |
| 工程卫生与仓库治理 | 5.0 | .gitignore 写得很好，但 .git 膨胀 12.5×、无 README、无 CI |
| 文档与可复现性 | 4.0 | 知识高度集中在 AGENTS.md；3 处悬空引用；新人无法一键重建环境 |

---

## 二、核心代码与参数体系

### 2.1 做得好的地方

**架构分层是真实资产。** `src/simulation.py`（160 行）是纯 facade，9 个子模块依赖方向单一：

```
simulation_common ← {dcr, eis, frequency, pulse_lifecycle, rpt}
simulation_rpt    ← {eis, frequency, pulse_lifecycle, regional_lifecycle}
regional_parallel ← regional_lifecycle
```

无回边、无循环依赖。这个拆分经得起加新工况的考验。

**参数去重已落地。** `params/common.py:117` 的 `build_lfp_cell_params` 被 13 个 LFP 参数文件复用，
Arrhenius 温度依赖在 `common.py:32` 只有一处实现，没有复制粘贴。CSV 查表走
`PARAMS_DIR = Path(__file__).resolve().parent` + `lru_cache`（`common.py:10`），不依赖 CWD。
这两点比大多数同类工程强。

**Phase 2 spec→run 改造基本完成。** `api/jobs.py:1372` 的 `JOB_TYPES` 已注册 10 类
（cycle / calendar_aging / frequency / pulse / lifecycle_heat / psd / regional_coupled_aging /
peak_current / eis / rate_benchmark），`PLANNED_JOB_TYPES` 已清空（:1366），统一走
`_run_workflow_job`（:1271）。对照 AGENTS.md 北极星路线图，第②步"spec→run 仿真运行时"已经落地。

**代码卫生基线不错。** src / api / tests / params 全库 0 个 TODO/FIXME/HACK，0 个裸 except；
`studio_db.py` 全用 `?` 占位符（无 SQL 注入面）；`public_app.py:81-133` 有 HMAC token + 限流。

### 2.2 代码规模

| 项 | 数值 |
|---|---|
| `src/` | 44 个 .py（36 + workflows 12）/ 19,649 行 |
| `api/` | 8 个模块 / 3,620 行（+ `run_studio.py` 452 行） |
| `tests/` | 40 文件 + conftest / 258 个 test_ / 6,518 行 |
| `params/` | 22 个 .py（16 电芯参数 + common + `__init__` + 4 工具脚本） |
| 最长函数 | 274 行（`simulation_regional_lifecycle.py:480 run_regional_dfn_power_cycles`） |

### 2.3 P0：`params/__init__.py` registry 有 4 条悬空引用

`params/__init__.py:38/57/59/61` 注册了 `paramsMICCW500`、`paramsCW428_pouch`、
`paramsCW495_pouch`、`paramsCW511_pouch`，**四个文件磁盘上都不存在** →
`load_cell_params("CW511")` 必然 ImportError。

反向漏注册 3 个已存在且活跃的参数模块：`params1300CW363`、`paramsLDSCW368`、`paramsLDSCW501`。
而 `BatteryProject/output/runs/` 里 `cw363_soc_ocv`、`cw368_1300_multirate`、`cw501_benchmark`
正是当前活跃的 workflow —— **主力电芯在 registry 里没有映射**。

`tests/test_params_registry.py` 只有 33 行 / 4 个用例，没覆盖全部 key，所以这个 bug 一直没被抓住。

### 2.4 P0：Studio `/stop` 端点丢失

`run_studio.py:387` 残留 `job_manager.stop_job(job_id)` 的函数体，但装饰器和
`def stop_job(...)` 签名已缺失，整段变成 `delete_job` 内部的不可达死代码
（:368-384 还重复定义了 rename/delete 路由）。`JobManager.stop_job`（`jobs.py:1591`）没有任何
HTTP 入口 —— **前端"停止任务"按钮实际无效**。

### 2.5 测试缺口

完全零测试的模块（8 个）：

- `src/`：config.py(324)、reporting.py(197)、runtime.py(88)、workflow_runtime.py(55)
- `api/`：calibration.py(300)、studio_db.py(312)、worker.py(180)、run_studio.py(452)

`api/jobs.py` 1,696 行只有 64 行 / 8 个用例。相对地，`tests/` 的 258 个用例大部分集中在
仿真核心路径 —— 覆盖是"偏科"的，不是"不足"。

### 2.6 其他

- **中等**：`sys.path` 运行时污染（`params/__init__.py:19-22`、`tests/conftest.py:10-13`）；
  测试导入根不一致（`test_regional_lifecycle.py:7` 用 `BatteryProject.src.` 而多数用 `src.`）。
- **中等**：api 层 `/api/*` 无鉴权（依赖 127.0.0.1）；`jobs.py:1580/1586/1615` 直接
  `job_root / job_id`，job_id 无白名单校验（路径穿越面）。
- **轻微**：`print` 调试残留 15 处；`except Exception` 37 处（其中 6 处 `pass` 静默吞异常）；
  `src/workflows/calendar_aging_half_soc.py.bak_20260807`（352 行）死代码入库；
  `params/heat_power_compare.py:78` 硬编码 `C:/HithiumSSD/...`；
  `params587calander.py` 文件名拼写错误且未走 `build_lfp_cell_params`。
- **依赖声明脱节**：根 `pyproject.toml` 只有 9 行，仅声明 `sim-cli-core`、`sim-plugin-comsol`；
  实际 import 的 pybamm / scipy / pandas / fastapi / matplotlib 全部未声明。无 `[tool.pytest]`、
  无 ruff/mypy 配置、**无任何 CI**（无 `.github/`）。

---

## 三、数据资产与 registry

### 3.1 机制是对的，但停在第一步

`datasets.json` version=1，638 条目，18 字段 schema 完整；`data_registry.py:213-216` 实现了幂等
scan 且人工字段重扫不覆盖（MANUAL_FIELDS），默认 status=`auto`。设计挑不出毛病。

**但 638 条 status 全部是 `auto`，`curated` = 0。** `git log` 里能查到
`feat(data): add curated registry workflow` 的提交 —— 流程建好了，一次都没用过。
人工字段 `source`/`quality` 638/638 为 null，`notes` 非空 0 条，`signals` 全空。

后果：**registry 现在只是文件清单，不是可信元数据**，AGENTS.md 里"按 quality/source 筛选"的
能力完全不可用。

### 3.2 P0：机器推断质量低，查询会静默漏数据

| 字段 | 识别率 | 缺失 |
|---|---|---|
| `test_type` | 415 / 638 = **65.1%** | 223 条未识别（`AI_virtual_cell` 104/105、`587Ah` 29/35 几乎全灭）|
| `temperature_C` | 299 / 638 = **46.9%** | 339 条未识别（`MIC_1175Ah` 143/227）|
| `rate` | 370 / 638 = **58.0%** | 268 条缺失 |

执行 `ls --temp 25 --test 倍率充电` 会静默漏掉约一半真实数据，**且不报错**。这是最危险的一类
问题：Agent 会以为"没有数据"而得出错误结论。

### 3.3 一致性反而是强项

- `data_processed` 151/151 全部登记，0 ghost 条目
- `data_raw` 磁盘 521 文件 vs 登记 487，差的 34 个全部是非数据扩展名（.png 21 / .ipynb 5 /
  .py 3 / .jpeg 2 / 空文件 1），由 `DATA_EXTENSIONS` 白名单有意过滤，**不是漏扫**
- 0 个 `~$` / `.tmp` / `.bak` / `副本` / `- Copy` 垃圾文件
- 字节级真重复仅 18 组 / 7.4MB（占 6.94GB 的 0.1%）
- registry `updated=2026-07-30` vs `data_raw` 最新 mtime 2026-07-24，无新增漏扫

### 3.4 其他问题

- **中等**：`data_processed/` 只有 5.1MB / 151 文件，vs raw 6.94GB / 521 文件（0.07%）。
  只有 MIC 做了落盘（86 raw → 141 processed）；314Ah 是 248 → **5**，587Ah 30 → **5**，
  AI_virtual_cell 105 → **0**，280Ah 3 → **0**。清洗结果散落在各任务目录里，**换任务即重做**。
- **中等**：`data_raw/` 混入 5 个 `.ipynb`、3 个 `.py`、21 张图片 —— "6.94GB 原始数据"口径失真。
- **轻微**：`data_raw/MIC_1175Ah/03-1175Ah电芯数据/工况放电/` 下的 10 个 `.xlsx` 每个 257–265MB，
  合计 2.66GB（占 raw 38%）。xlsx 不适合该量级，且 `.xlsx` 被 .gitignore 全局忽略 ——
  **这批最大的原始数据实际不受版本保护**。1 个 0 字节空文件 `data_raw/MIC_1175Ah/BB62D500`。

---

## 四、任务交付与文档流程

### 4.1 做得好的地方

**六要素骨架已成型。** 40 个含「何争」的任务目录中，33 个具备完整的
`00_任务说明 / 01_仿真报告 / 02_模型 / 03_输入数据 / 04_输出结果 / 05_复现说明`，
齐全率 **82.5%**；在严格合规命名的 34 个包中达 33/34 = **97%**。

**工具链真实存在且被使用。** `tools/task_delivery.py` 的 `new-task` / `publish-task` 会写
`task_manifest.json` / `source_manifest.json` / `run_manifest.json`，`.gitignore:115-119` 排除
`work/**/04_输出结果/` 但保留四类 manifest —— 设计自洽。

**run 与交付分离执行到位。** `BatteryProject/output/runs/` 已有 31 个 workflow、537M，
绝大多数结果没有回流到 `work/`。

### 4.2 P1：冻结机制缺位

全库 **0 个 UPLOADED / LOCK 冻结标记文件**。冻结只靠 `task_manifest.json` 里一个 `status` 字符串，
且明显失真：`587Ah/无活化…V1` 与 `V2`、`cross_cell/…峰值功率V3` 与 `V4`、
`MIC_LDS/…CW368-1300…V1` 与 `V2` **同时为 published**。33 个 manifest 中 14 个 published、
约 17 个仍停留在 `created`。叠加 `04_输出结果/` 被 gitignore，冻结没有版本库兜底。

### 4.3 命名与结构

| 项 | 数值 |
|---|---|
| 命名合规率 | 34 / 40 = **85%**（若含全部 59 个二级目录则 34/59 = 58%）|
| 六要素齐全率 | 33 / 40 = **82.5%** |
| 空要素实例 | `01_仿真报告` 空 8 处、`04_输出结果` 空 4 处、`02_模型` 空 2 处、`03_输入数据` 空 2 处 |
| 禁用 output 目录 | **8 处 / ≈39M** |
| 返修包 | V2 ×5、V3 ×1、V4 ×1 |

体积与规范度倒挂：**越大的包越不规范**。

- `MIC_LDS/202608_何争_不同集流体导出方式对电芯性能的影响` —— **1.8G，无版本号**
- `MIC_LDS/202607_何争_LDS CW501模型对标及峰值电流Mapping` —— 39M
- `MIC_LDS/202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真` —— 8.5M（含空格、中英混排）
- `587Ah/202607_何争_587电池全生命周期产热率及1C-30sDCR` —— 36M，无版本号，六要素仅 1/6，
  自建 `notebooks/` `results/` `报告/`
- `RTE机理/CW391+CW511-仿真支持数据 to 何争` —— 277M，无日期无版本

禁用输出目录 8 处 ≈39M（`587Ah/…/results/output` 22M、`…/notebooks/output` 3.3M、
`MIC_LDS/…/06_Codex原始交付归档/outputs` 8.1M 等），直接违反 AGENTS.md:87-88。

另有"包中包"：`cross_cell/…跨电芯ARC…V2/202607_何争_跨电芯ARC…V1/`（3.7M），
同任务两个版本嵌套而非并列。

### 4.4 文档治理：知识过度集中

`docs/` 只有 132K：2 个 md（`DATA_PROCESSING_RULES.md` 14.1K、`TASK_DELIVERY_WORKFLOW.md` 3.3K）
+ reviews 6 篇 + changelogs + planning。

**3 处悬空引用**（AGENTS.md 引了但文件不存在）：

- AGENTS.md:122 → `docs/FUN_NC_TODO.md`
- AGENTS.md:124 → `docs/FUN_HZ_MIGRATION.md`
- AGENTS.md:31 → `work/MIC_1175Ah/AGENTS.md`（`work/` 下只有 `MIC_LDS/AGENTS.md`）

`work/**/*.md` 有 207 个，但 65 个集中在
`AI_virtual_cell/202608_何争_PyBaMM工作流与Codex记忆跨电脑迁移V1/04_输出结果/codex_memory_tree/`
—— 那是历史 rollout 摘要，不是流程知识。

`.plans/` 92K / 23 文件，最新 `2026-08-05`，**已停更 1 个月**。

**结论：核心知识几乎全部压在 AGENTS.md 一个 21KB 文件里。** 这个文件一旦出问题或被误改，
整个 harness 就失效。而且它是面向 Agent 的，不是面向人类 onboarding 的。

### 4.5 可归档项（约 7.3G）

`work/` 最大的 8 个文件全是 COMSOL `.mph` 快照 + 1 个 zip，合计 ≈4.8G：

- 861M `314Ah/…/99_内部文件/历史COMSOL归档/…/314热电耦合充.mph`
- 842M / 482M / 434M / 422M `AI_virtual_cell/202609_何争_扣电与软包力电耦合V1/99_内部文件/历史运行归档/COMSOL_runs/…`
- 656M `314热电耦合放.mph`
- 561M `…/02_模型/扣电_V9_0N_…mph`
- 554M `…PyBaMM工作流与Codex记忆跨电脑迁移V1/04_输出结果/Codex_historical_sessions_evidence.zip`

建议外迁 `archive/`：`AI_virtual_cell/202609_何争_扣电与软包力电耦合V1`（5.5G，99% 是历史
COMSOL 快照，且已有 V2）、`314Ah/…V1`（1.5G，含 `.mph.lock`）、`RTE机理/`（302M，全为
PPT/PDF/原始数据、零标准任务包）。

---

## 五、工程卫生与仓库治理

### 5.1 做得好的地方

`.gitignore` 覆盖面扎实且**经过验证**：`node_modules/`、`.venv/`、`.venv-liionpack/`、`/scratch/`、
`/.codex*`、`.pytest_cache/` 全部命中（实测 `git check-ignore` 均返回 IGNORED）。

归档意识强：全仓未发现散落在外的 legacy 副本，源码目录 0 个空 `__init__.py`，
`tools/`（14 文件）与 `skills/`（101 文件）无同名 `.py` 互相复制。

**未发现任何凭据泄露。** 无 `.env`/`.pem`/`.key`/`credentials`/`id_rsa`；`skills/` 内无
`sk-`/`ghp_`/`AKIA`/`xox`/`AIza` 形态密钥。`tools/vscode-notebook-bridge/` 的 token 是
`crypto.randomBytes(32)` 运行时生成、仅 localhost 使用，属正常设计。

### 5.2 P0：`.git` 414MB，膨胀 12.5 倍

| 项 | 数值 |
|---|---|
| 被跟踪文件 | 902 个（35 commits）|
| 被跟踪内容实际大小 | **33 MB** |
| `.git` 体积 | **414 MB**（pack 298M + loose 113M）|
| 膨胀比 | **12.5×** |

`git fsck` 已报出 unreachable tree/blob。典型症状是历史中曾提交大文件后删除、且长期未
`git gc --aggressive`。对比：全仓 23G，git 只管了 33MB —— 这 414MB 基本是纯浪费，
且拖慢每次 clone/backup。

### 5.3 P0：DLP filter 不可移植

`.gitattributes` 声明 `*.py filter=dlp`、`*.ipynb filter=dlp`，但 filter 只定义在本机
`.git/config`（`filter.dlp.clean python tools/git_dlp_clean.py %f`、`filter.dlp.required true`）。

换机后 `.py` / `.ipynb` 的 add/checkout 会**硬失败**或直接写入密文。且
`tools/git_dlp_clean.py` 自身在磁盘上就是 Trend Micro 密文 —— 形成循环依赖。

### 5.4 其他问题

- **中等**：嵌套 Git 仓库 `BatteryProject/battery-sim-site/.git`（1.5M），该目录又被
  `.gitignore:136` 忽略 —— 这段前端历史完全游离于主仓库、无备份。
- **中等**：`*.json` 被全局忽略（`.gitignore:48`）却仍有 100 个 json 被 force-add。
  规则与事实矛盾，新增 json 会静默不入版本控制。`*.png`/`*.csv`/`*.xlsx` 同样一刀切过粗。
- **中等**：`BatteryProject` 1.9G 中 96% 非源码 —— `battery-sim-site/` 747M
  （node_modules 741M + dist 3M）、`.venv/` 625M、`output/` 537M；真实代码
  `src/` 2.2M + `tests/` 1.8M + `studio/` 1.2M ≈ 8M。
- **中等**：`BatteryProject/legacy/` 残留 3 个文件（`frontend.py`、`run_frontend.bat`、
  `run_frontend.py`）且**已被跟踪**，与 AGENTS.md 声称的"legacy 已集中到 archive/"不符。
- **中等**：最大被跟踪文件是带输出的 notebook `BatteryProject/examples/314Ah_LC_non_PCS.ipynb`
  **11.5MB**（另 `swelling_cycling_demo.ipynb` 4.1MB、`plotting_demo.ipynb` 2.2MB）。
  >1MB 的被跟踪文件共 6 个。
- **中等**：`tools/setup-hermes.sh` 第 3/9/10/11/17 行硬编码 `C:\Users\hez\.hermes`
  与 `/mnt/d/Users/hez/Desktop/hithium`。
- **中等**：**无 README / SETUP / Makefile**。根目录只有面向 Agent 的 AGENTS.md，
  新人无法一键重建环境。
- **轻微**：`scratch/` 110M / 210 文件（169 张图，多为 PPT 评审截图）、`.codex_tmp/` 30M / 73 文件、
  `_v2`/`.bak` 后缀文件 21 个（其中 `src/workflows/calendar_aging_half_soc.py.bak_20260807`
  在代码目录，应清）。

### 5.5 敏感度

风险不在密钥，而在 **公司 IP 进入 git 历史且 filter 依赖本机 DLP**：含 314Ah/587Ah/MIC_1175Ah
及 CW391/CW501/CW368 等电芯型号的对标模型、COMSOL 导出 `.java`、`datasets.json`（332KB）。
`datasets.json` 是被跟踪的（force-add），意味着实验数据索引已进 git 历史。

---

## 六、北极星路线图进度

AGENTS.md 北极星：从"完成单点仿真任务"转向"建设 AI Agent 驱动的电池仿真工作流"，
四步路线 ① 数据 registry → ② spec→run 运行时 → ③ 决策原语工具化 → ④ run 历史沉淀与检索。

| 步骤 | 状态 | 证据 |
|---|---|---|
| ① 数据 registry | 🟡 机制建成，数据未治理 | 638 条目、幂等 scan 正确；**curation 0%、温度识别率 46.9%** |
| ② spec→run 运行时 | 🟢 基本完成 | `JOB_TYPES` 10 类已注册，`PLANNED_JOB_TYPES` 清空，统一 `_run_workflow_job`；`output/runs/` 31 workflow |
| ③ 决策原语工具化 | 🟡 部分 | `parameter_identification.py` / `uq_calibration.py` 存在；`api/calibration.py`(300 行) **零测试** |
| ④ run 历史沉淀与检索 | 🔴 未启动 | `output/runs/` 有 31 workflow 但无统一索引/检索入口；冻结机制缺位 |

**整体判断：第②步完成得比预期好，第①步卡在"数据治理"而不是"工具"，第④步还没开始。**

---

## 七、优先级行动清单

### P0 — 会直接咬人，建议本周内

1. **修 `params/__init__.py` 的 4 条悬空引用**（删或补文件）+ 注册漏掉的 3 个活跃模块
   （`params1300CW363` / `paramsLDSCW368` / `paramsLDSCW501`）。纯 bug，成本 10 分钟。
   顺手给 `test_params_registry.py` 加一个"遍历所有 key 都能 import"的用例。
2. **补回 Studio `/stop` 端点**，并清理 `run_studio.py:368-387` 的重复路由与不可达代码。
3. **`git gc --aggressive` + `git filter-repo` 瘦身**（414M → 预期 <50M）。
   这是破坏性操作，执行前先做个裸克隆备份。
4. **DLP filter 降级**：把 `filter.dlp.required` 改为 `false`，或在 filter 缺失时降级为 no-op，
   否则换机即硬失败。

### P1 — 解锁能力，建议本月

5. **批量 curation**：对 314Ah / MIC 主力工况把 `curated` 率提到 10–20%，
   即可解锁按 quality/source 筛选。这是投入产出比最高的一项。
6. **补 `data_registry.py` 的推断规则**，目标：test_type / temperature_C / rate 识别率各 ≥85%。
   在此之前，Agent 查 registry 必须交叉验证，不能盲信。
7. **建立冻结机制**：给已上传包加 `UPLOADED` 标记文件（不必改 gitignore），
   并清理 3 组重复 published 的 manifest。
8. **加最小 CI**：flake8（AGENTS.md 已规定 `--max-line-length=120 --ignore=E501,W503`）
   + pytest，先本地 pre-commit hook 也行。规则写进 harness 但没有自动化执行 = 没有规则。

### P2 — 清理与沉淀，季度内

9. **归档 7.3G COMSOL 快照**（`AI_virtual_cell/…扣电与软包力电耦合V1` 5.5G 等）到 `archive/`。
10. **清理 8 处禁用 output 目录**（≈39M）+ `BatteryProject/legacy/` 3 个残留文件
    + `src/workflows/*.py.bak_20260807`。
11. **补根 `README.md`**：环境重建步骤（两个 venv 的分工、pyproject 与实际依赖的落差要写清楚）。
12. **拆分 AGENTS.md**：把 21KB 拆成根 AGENTS.md（索引）+ `docs/` 下的分域细则，
    同时修掉 3 处悬空引用。
13. **处理 `BatteryProject/battery-sim-site/.git` 嵌套仓库** 与 741M node_modules。
14. **补零测试模块的测试**：优先 `api/calibration.py`、`api/studio_db.py`、`src/config.py`、
    `src/reporting.py`。

---

## 附：关键指标速查

| 指标 | 数值 | 评价 |
|---|---|---|
| 总仓库体积 / git 跟踪 | 23G / 33MB | — |
| `.git` 膨胀比 | **12.5×** | 严重 |
| src 行数 / 测试用例 | 19,649 / 258 | 良好 |
| 零测试模块数 | 8 | 中等 |
| params registry 悬空引用 | 4 | 严重 |
| registry 条目 / curated | 638 / **0** | 严重 |
| test_type 识别率 | 65.1% | 严重 |
| 温度识别率 | 46.9% | 严重 |
| registry ↔ 磁盘一致性 | processed 100%、raw 差 34 全为非数据后缀 | 良好 |
| 任务包命名合规率 | 85%（严格口径 58%）| 中等 |
| 六要素齐全率 | 82.5% | 良好 |
| 冻结标记文件 | **0** | 严重 |
| 禁用 output 目录 | 8 处 / 39M | 中等 |
| 文档悬空引用 | 3 | 中等 |
| 硬编码凭据 | 0 | 良好 |
| CI / lint / README | 0 / 0 / 0 | 中等 |
| `git status` 脏文件 | 0 | 良好 |
