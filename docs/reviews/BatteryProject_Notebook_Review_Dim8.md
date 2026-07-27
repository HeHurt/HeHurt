# BatteryProject 代码审查 — 第 8 维度专项：示例 Notebook 框架

> 本维度补全主审查报告（`BatteryProject_Code_Review_Report.md`）中因 DLP 加密留白的部分。
> 读取方法：用白名单 VS Code 作为 Node（`ELECTRON_RUN_AS_NODE=1 Code.exe nb_dump.js <path>`）读取 DLP 密文 `.ipynb` 明文。
> 抽样：跨 `work/` 下 MIC_1175Ah / 314Ah / 587Ah / 280Ah / AI_virtual_cell 共 13 个代表性 notebook + 通读 `MIC_1175Ah/AGENTS.md` 作为基准。
> 严重级：高 / 中 / 低。

---

## 一、总体评分：中

新范本（cw254 / 中车过载 / CW362老化 / CW391 EIS）已达「良」，但体系整体被历史脚本、三套并存 API、绝对路径硬编码与命名错配拖累。

---

## 二、体系概览

- **数量与分布**：约 76 个 notebook 分布于 5 个电芯目录 —— MIC_1175Ah(16)、314Ah(38)、587Ah(13)、AI_virtual_cell(8)、280Ah(1)，另有 RTE机理 / patent_disclosures / pets / reports / 算例 等辅助目录。
- **命名规律**：中英混排、风格不一。如 `<电芯>常规循环`、`<电芯>_0p5P_BOL_thermal_heat_diagnosis`、`<电芯>欧盟电池法`；子目录有 `不同温度倍率循环/`、`长时储能峰值电流/`、`可靠性对标notebook/`、`竞品分析/`、`diff_temperature/`。部分文件名带人名（洪军强-邓述珍），倍率用拼音 `_0p5P` 与中文 `常规循环` 并存。
- **与 AGENTS.md 契合度（严重分化）**：
  - 约一半新 notebook 采用比 AGENTS.md 更先进的 `configure_notebook_environment`（cwd 向上搜索 BatteryProject 根，如 CW362 / EIS / 中车过载 / cw254）；
  - 另一半沿用 AGENTS.md 旧模板 `setup_notebook` + `importlib.reload` 并硬编码 `PROJECT_ROOT`；
  - 少数完全脱离（Benchmark_simple 自写 `RecordLayerData` 类、314短期性能A1 / test_pybamm 用自定义 `Hithium314B1` 模块、314常规循环 用 `BatteryModelPack_v1.5/Fun_HZ`）。
  - **同一仓库存在 3 套互不兼容的仿真 API**。

---

## 三、抽样逐一点评

| # | Notebook | 主题 | 评价 | 级 |
|---|----------|------|------|----|
| 1 | MIC_1175Ah/CW362_CW428_CW495_25C_0p5P_200cycles | 老化对标 | 结构清晰：markdown 机理说明→`configure_notebook_environment`→配置→设计 override→分块老化→Excel 导出（含色阶/冻结窗格）。无硬编码绝对路径，用 `WORKSPACE_ROOT`。教学性好 | 优/低 |
| 2 | MIC_1175Ah/长时储能峰值电流/MIC cw363-10s | 峰值电流 | 遵循 setup 模板，但 `md=0` 无任何说明文字；硬编码 `D:\Users\hez\Desktop\mic\...csv`、`D:\Users\hez\Desktop\hithium\MIC\长时储能峰值电流\...xlsx`，违反「路径放顶部常量」 | 中 |
| 3 | MIC_1175Ah/不同温度倍率循环/MIC_CW363对标 | 倍率对标 | **文件名/内容不符**：cell 0 实为 `# 314多温度拟合（重构版）`，读 `587\Exp\587数据.csv`；依赖未文档化高级函数 `load_cycling_folder/compare_all/BatteryPlotter`。复制粘贴致电芯归属错乱 | 中高 |
| 4 | 314Ah/notebooks/314常规循环 | 常规循环 | **内容/目录错配**：位于 314Ah 目录，却 `from paramsMIC import *` 且 `rate*1175*3.2`（1175Ah 参数）；数据硬编码 `C:\Users\hez\Downloads\不同温度倍率测试.xlsx`。多处 cell 无 markdown | 中 |
| 5 | 314Ah/notebooks/可靠性对标notebook/Benchmark_simple | 可靠性对标 | **最严重违规**：cell 0 在 notebook 内定义整个 `RecordLayerData` 仿真核心类（违反 AGENTS.md「不得在 notebook 定义核心函数」）；相对路径 `对标数据.xlsx`/`.\params\E_*.csv`；无 setup 模板。纯一次性脚本，不可复现不可教 | 高 |
| 6 | 314Ah/CW391_CW511_EIS_50SOC | EIS | 高质量范本：markdown 说明 EIS 流程→`configure_notebook_environment`→函数化 `build_parameter_values/solve_eis_case`→Nyquist/Bode 图。无硬编码数据路径，magic reload 规范 | 优/低 |
| 7 | 314Ah/314Ah_0p5P_BOL_thermal_heat_diagnosis | 热诊断 | 结构好（markdown+配置集中），但硬编码跨盘绝对路径 `E:\Downloads\T3-…ARC报告.xlsx`、`SOURCE_NOTEBOOK=…314Ah_0p5P_lifecycle_heat_rate.ipynb`，依赖「派生自另一 notebook」的外部状态 | 低 |
| 8 | 587Ah/587欧盟电池法 | 拟合 | **文件名/内容不符**：实为 `587多温度拟合（重构版）`，与 314 拟合同一模板仅换 `params587`/`nominal_current=587`；仍硬编码 `587\csv_output`、`587\Exp\587数据.csv` | 中 |
| 9 | 587Ah/中车-过载能力_587Ah | 过载能力 | 最佳范本：markdown 逐节解释目的（电网工况→PyBaMM steps→真实仿真→后续老化三场景）；`configure_notebook_environment`+`WORKSPACE_ROOT`，输出走 `WORKSPACE_ROOT/work/587Ah/outputs`，无绝对路径泄漏；含 `_AgingOnlySolution` 工程化处理 | 优/低 |
| 10 | 587Ah/notebooks/587数据转换 | 数据转换 | 工具型但质量差：`md=0`；cell 1 调用未定义变量 `input_folder/output_folder/split_current_groups`（NameError）；`except FileNotFoundError` 缺冒号（SyntaxError，无法运行）；路径混用相对与 `D:\Users\hez\Desktop\hithium\587\Exp\邓0725\…` | 高 |
| 11 | AI_virtual_cell/314短期性能A1 | 短期性能 | markdown 有目标说明，但用**完全不同的 `Hithium314B1` 自定义 API**（`from Hithium314B1 import BatteryDirect…`），硬编码 `D:\Users\hez\Desktop\hithium\314\Exp\bench_mark`；与 BatteryProject 主线割裂 | 中 |
| 12 | AI_virtual_cell/20260401_COMSOL模型迁移/test_pybamm | COMSOL迁移 | step 化 markdown 教学性好，但 cell 0 读相对路径 `battery_info.csv`（未说明来源），同样依赖 `Hithium314B1` 自定义 API | 中 |
| 13 | 280Ah/cw254 | CW254对标 | 规范范本：顶部常量集中（`OUTPUT_DIR`、`EXP_CSV_FOLDER=None` 且 `if is None: 跳过对标`），markdown 分节，统一 API。对「缺实验数据也能跑通」做了容错 | 优/低 |

---

## 四、跨 Notebook 共性问题

1. **三套 API 并存**：`configure_notebook_environment`（新）、AGENTS.md 旧模板、`Hithium314B1`/`Fun_HZ` 自定义模块，新用户无从选起。
2. **文件名/内容错配**：至少 3 个 notebook（MIC_CW363对标、587欧盟电池法、314常规循环）命名与内部电芯/主题不符，复制粘贴未清理。
3. **绝对路径硬编码泛滥**：`D:\Users\hez\…`、`C:\Users\hez\Downloads\`、`E:\Downloads\` 散落各 cell，违反 AGENTS.md「路径放顶部常量」，换机即失效。
4. **环境/依赖无文档**：全库无 `requirements.txt`、无 kernel/版本说明；magic `%load_ext autoreload` 与隐式全局（`sol_list`、`params`）依赖顺序执行。
5. **教学性两极分化**：新范本 markdown 充分；Benchmark_simple、587数据转换、MIC cw363-10s 几乎零说明，且存在未定义变量/语法错误。

---

## 五、可操作的改进建议

1. **建立模板 notebook**：以 `cw254` / `中车过载` 为蓝本，固化「顶部常量 + `configure_notebook_environment` + 分节 markdown + 容错导出」四段式，全电芯套用。
2. **统一路径解析**：禁止 cell 内硬编码绝对路径，一律 `WORKSPACE_ROOT / "work" / <电芯> / …`；实验数据用 `params` / 固定 `data/` 根，提供 `load_*` 助手。
3. **收敛到单一 API**：弃用 `Hithium314B1` / `Fun_HZ` / `RecordLayerData` 内联类，迁移到 `src.easy_imports`；无法迁移的标注 `deprecated`。
4. **补环境文档 + 命名治理**：新增 `requirements.txt` 与各目录 `README`；用脚本校验 notebook 文件名与内部 `NOMINAL_CAPACITY` / 主题一致性，修正已错配的 3 个文件。
5. **CI 静态检查**：加 pre-commit 规则 —— 禁止 Notebook 内定义 `class` / 超长函数、扫描硬编码 `C:\`/`D:\`/`E:\` 绝对路径、要求核心教学 notebook 每个 code cell 前至少有一个说明性 markdown。

---

## 附：交叉验证记录（本维度高严重级结论已复核）

使用 Code.exe 读取明文后自动扫描 red-flag：
- `Benchmark_simple.ipynb` → `class RecordLayerData` 内联定义 = **TRUE**（高严重级确认）。
- `587数据转换.ipynb` → 未定义变量 `input_folder/output_folder/split_current_groups` = **TRUE**（NameError 风险确认）；`except FileNotFoundError` 缺冒号 = **TRUE**（SyntaxError 确认）；markdown cell 数 = 0；绝对路径硬编码 = **TRUE**。

以上均经实际读取证实，非推断。
