# BatteryProject

本项目已按标准 Python 工程结构拆分，核心功能从单一脚本中拆到多个模块，便于维护、复用与测试。

## 目录结构

- data/：实验数据（Excel/CSV）
- output/：图片与结果输出
- src/：源代码包
  - config.py：配置与材料参数
  - simulation.py：仿真统一 facade（实现拆分在 simulation_* 子模块）
  - analysis.py：数据提取与指标计算
  - plotting.py：绘图与结果注入
  - compare.py：Sim-Exp 一站式对标
  - exp_loader.py：实验循环 CSV 加载（中/英文列名自动对齐）
  - utils.py：IO、Excel 解析与导出
  - data_cleaning.py：实验数据清洗/记录层提取
  - parameter_identification.py：老化参数辨识与优化
  - easy_imports.py：Notebook 快捷导入

## 核心模块说明

- analysis.py：RRMSE 计算、容量提取、产热分量、膨胀力估算
- simulation.py：facade，再导出以下子模块的公共符号
  - simulation_dcr.py：DCR + 恒功率分块循环
  - simulation_peak.py：峰值电流/功率搜索
  - simulation_rpt.py：Branch-RPT 诊断
  - simulation_eis.py：生命周期 EIS 工作流
  - simulation_frequency.py：调频工况老化
- plotting.py：BatteryPlotter 与产热/容量注入
- compare.py：compare_all 自动匹配仿真标签与实验 CSV 并出对比图
- exp_loader.py：load_cycling_csv / load_cycling_folder，文件名解析温度倍率
- utils.py：Excel 读取、数据导出、仿真结果注入
- config.py：路径/默认参数/材料参数与熵系数加载
- data_cleaning.py：曲线清洗、record layer 数据提取、实验数据配置化加载
- parameter_identification.py：loss 计算（cycle_line/cycle_line_v2/record）、目标函数构建、BO/GO/MO/DA/BH 优化
- electrolyte_dryout.py：电解液干涸老化耦合
- psd_workflow.py：粒径分布拟合与材料对比研究
- reporting.py：循环指标 Excel 报表导出
- runtime.py：PyBaMM 运行时限制与 notebook 环境配置

## 详细 API 目录

详见 [docs/API.md](docs/API.md)（包含函数清单、参数说明与 Notebook 简化示例）。

Fun_HZ 拆解迁移对照见 [docs/FUN_HZ_MIGRATION.md](docs/FUN_HZ_MIGRATION.md)。

## 与旧版单文件相比的改进

1. **职责清晰**：仿真、分析、绘图、IO 分离，降低耦合。
2. **可复用性强**：功能模块化，可在 Notebook/脚本自由组合。
3. **可维护性更高**：避免重复定义与冲突，修复多处重复代码残留。
4. **稳定性增强**：统一入口、统一配置，减少全局变量污染。

## 快速开始

先安装依赖（依赖以 `pyproject.toml` 为唯一来源）：

```bash
uv sync                 # 推荐；可加 --extra dev / --extra opt / --extra ui
```

或不使用 uv：

```bash
pip install -e ".[dev]"
```

> 在 Notebook 中推荐使用：

```python
from src.easy_imports import *
```

`src.easy_imports` 现会默认应用项目统一的 PyBaMM 运行时限制：

- 将 `pybamm.settings.max_y_value` 提高到 `1e7`
- 将 PyBaMM 日志级别设为 `CRITICAL`

这只会压低日志噪声，不会捕获或吞掉求解异常。若脚本未使用 `easy_imports`，请显式调用：

```python
from src.runtime import configure_notebook_environment

PROJECT_ROOT, WORKSPACE_ROOT, PARAMS_ROOT = configure_notebook_environment(
  project_root=r"D:\Users\hez\Desktop\hithium\BatteryProject"
)
```

频率调节工况示例 Notebook：

- [examples/调频.ipynb](examples/调频.ipynb)
  - 直接演示 `prepare_frequency_scenarios`、`run_frequency_scenarios`、`summary_df` 与结果作图。
  - 默认 `smoke` 模式可快速检查环境；切到 `study` 可复用同一入口跑长周期调频寿命评估。

## 前端操作界面

项目提供两套本地界面：新版 Battery Sim Studio 独立 UI，以及旧版 Streamlit 前端。

### Battery Sim Studio

新版 Studio 使用静态 HTML/CSS/JS + FastAPI 本地后端，项目、数据集与任务索引会写入
`output/studio.sqlite3`，大文件仍保存在 `output/` 对应目录。

推荐用 uv 管理本地 Python 环境：

```bash
uv run python run_studio.py --port 8601
```

或在 Windows 中直接双击：

`run_studio_uv.bat`

如果不使用 uv，也可以直接运行当前 Python 环境：

```bash
python run_studio.py --port 8601
```

启动后访问：

- Studio UI: <http://127.0.0.1:8601/>
- FastAPI docs: <http://127.0.0.1:8601/docs>

### Streamlit 前端

旧版 Streamlit 前端仍可使用：

1. 启动前端（两种方式任选其一）：

```bash
python -m streamlit run frontend.py
```

或：

```bash
python run_frontend.py --port 8501
```

或在 Windows 中直接双击：

`run_frontend.bat`

2. 打开浏览器后可使用四个页签：

- 实验数据：加载 CSV 文件夹并预览 retention/efficiency
- 参数配置：保存循环性能或峰值电流扫描请求
- 运行仿真：执行已保存的请求
- 结果分析：查看指标、图表、CSV 导出与 Sim-Exp 对比

## 示例 Notebook 索引

`examples/` 下提供了**最小可运行**的入门示例（synthetic 数据 / 临时 fixture，无需 `data/`）：

| Notebook | 涉及模块 | 是否跑 PyBaMM | 主要演示 |
| --- | --- | --- | --- |
| [examples/plotting_demo.ipynb](examples/plotting_demo.ipynb) | `plotting` | × | `BatteryPlotter` 注入实验/仿真数据、关键词筛选、颜色按标签共享 |
| [examples/exp_loader_demo.ipynb](examples/exp_loader_demo.ipynb) | `exp_loader` + `data_cleaning` | × | `load_cycling_csv` / `load_cycling_folder` / `parse_condition_from_filename` / `clean_xy_curve` |
| [examples/analysis_demo.ipynb](examples/analysis_demo.ipynb) | `analysis` | √ (2 圈 0.5C) | `calc_rrmse` / `get_discharge_capacity` / `compute_cycle_energies` / `get_all_heat_components` / `calculate_cycle_swelling` |
| [examples/compare_demo.ipynb](examples/compare_demo.ipynb) | `compare` + `exp_loader` | √ (2 圈 × 2 工况) | `compare_all` 自动匹配、`filter_conditions`、`sim_bias`/`exp_bias`、低阶 `compare_retention` |

> 4 个 notebook 已经通过 `jupyter nbconvert --execute` 端到端验证。
> 每个 notebook 的第一个 code cell 会自动定位 `BatteryProject` 根，所以可以从 `BatteryProject/` 或 `examples/` 目录启动。

## Notebook 简化示例（MIC多温度拟合）

已在 docs/API.md 中提供最小替换示例，用于将重复的 Excel 解析与曲线注入逻辑替换为统一 API。
示例 Notebook：[../MIC/不同温度倍率循环/MIC多温度拟合.ipynb](../MIC/不同温度倍率循环/MIC多温度拟合.ipynb)

## 测试

进入 `BatteryProject/` 目录运行（`pyproject.toml` 已把 `testpaths` 指向 `tests`）：

```bash
python -m pytest -q
```

若需要覆盖率报告，请确保已安装 `pytest-cov`：

```bash
python -m pytest --cov=src --cov-report=term-missing -q
```

## 老化参数辨识示例

已提供可直接运行的示例脚本（基于合成数据闭环验证）：

```python
python examples/aging_identification_demo.py --cycles 3 --n-iter 2 --init-points 1
```

脚本路径：`examples/aging_identification_demo.py`

说明：
- 默认先用模型生成 synthetic 实验数据，再执行 BO 参数辨识。
- 你可将 `make_synthetic_experiment_data` 替换为真实数据读取（结合 `src/data_cleaning.py`）。

## 调频工况示例

如果需要把 Notebook 中的调频场景批量运行逻辑直接沉淀到库层，请优先使用：

- `src.simulation.prepare_frequency_scenarios`
- `src.simulation.run_frequency_scenarios`
- `src.simulation.summarize_frequency_results`

示例入口：

- [examples/调频.ipynb](examples/调频.ipynb)

## 备注

- data/ 中请放置实验数据文件
- output/ 会存放绘图与导出结果
