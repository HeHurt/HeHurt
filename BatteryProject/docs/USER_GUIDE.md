# BatteryProject User Guide

本指南按任务组织，面向新 notebook 和日常仿真工作。完整函数细节见 [API_REFERENCE.md](API_REFERENCE.md) 和 [API.md](API.md)。

## 通用第一格

```python
from src.notebook import setup_notebook, load_params

ctx = setup_notebook(cell="MIC", style="science")
get_hithium_params = load_params("MIC")
```

常用 cell key：

- `MIC` / `1175Ah`
- `280`
- `314`
- `587`

## 峰值电流 map

模板：

- `examples/峰值电流.ipynb`

入口：

```python
from src.notebook_api import run_peak_current
```

核心输出：

- 峰值充电电流
- 峰值放电电流
- 等效峰值功率
- 首点电压

## 循环老化

模板：

- `examples/workflows/循环老化.ipynb`

MIC 0.25P 对标旧实例位于
`work/MIC_1175Ah/202607_何争_0p25P循环老化对标历史实例V1/02_模型/`。

入口：

```python
from src.notebook_api import run_dcr_and_power_test, get_discharge_capacity
```

建议：

- 每个温度循环内重新创建 `pybamm.ParameterValues("OKane2022")` 后再 update 参数。
- 先跑 smoke 配置，再扩大到完整循环数。

## 实验对标

模板：

- `examples/compare_demo.ipynb`
- `examples/analysis_demo.ipynb`
- `examples/exp_loader_demo.ipynb`

入口：

```python
from src.notebook_api import compare_all, calc_rrmse, BatteryPlotter
from src.exp_loader import load_cycling_csv, load_cycling_folder
```

典型流程：

1. 读取实验 CSV 或 folder。
2. 从仿真解中提取容量、能量、膨胀或电压曲线。
3. 用 `compare_all` 或 `BatteryPlotter` 生成对比图。
4. 用 `calc_rrmse` 做误差量化。

## 调频工况

模板：

- `examples/workflows/调频.ipynb`

入口：

```python
from src.workflows.frequency import FrequencyWorkflowSpec, run_frequency_workflow
```

建议：

- 先使用 notebook 中的 `smoke` 配置检查路径和参数。
- 结果表和图表 artifact 优先从 `run_frequency_workflow` 的标准输出目录获取。

## 插入脉冲

模板：

- `examples/workflows/插入脉冲.ipynb`

入口：

```python
from src.workflows.pulse import PulseWorkflowSpec, run_pulse_workflow
```

建议：

- 将客户工况保留在 notebook 顶部配置区。
- 通用 step 构造、批量运行和电压曲线提取放在库层复用。

## Studio

Studio 是当前推荐 UI：

```bash
uv run python run_studio.py --port 8601
```

访问：

- <http://127.0.0.1:8601/>

注意：

- `api/` 是 Studio backend，不是稳定公共 API。
- 旧 Streamlit 前端见 [legacy_frontend.md](legacy_frontend.md)。
