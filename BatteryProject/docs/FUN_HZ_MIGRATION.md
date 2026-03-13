# Fun_HZ 拆解迁移说明

本文给出 `工具/Fun_HZ.py` 到 `BatteryProject/src` 的工程化映射与调用方式。

## 1) 功能拆分结果

- 仿真流程：`src/simulation.py`
  - `perform_dcr_test`
  - `run_dcr_and_power_test`
  - `run_and_plot_all`
  - `peak_current_condition`
  - `run_peak_current`

- 指标/物理分析：`src/analysis.py`
  - `calc_rrmse`
  - `plot_and_calculate_rrmse`
  - `extract_all_metrics_from_sol`
  - `export_full_metrics_summary`
  - `get_discharge_capacity`
  - `get_separated_irreversible_heat`
  - `get_all_heat_components`
  - `calculate_cycle_swelling`

- 绘图：`src/plotting.py`
  - `BatteryPlotter`
  - `Different_cycle_voltage`
  - `plot_efficiency_vs_cycle`
  - `plot_efficiency_vs_cycle_all`
  - `process_sol_list_for_all_heat_components`

- 数据读写/注入：`src/utils.py`
  - `BatteryDataLoader`
  - `load_excel_to_plotter`
  - `load_dat_folder_to_plotter`
  - `process_sol_list_with_custom_extractor`
  - `export_cycle_data`

- 配置与熵系数：`src/config.py`
  - `load_entropy`
  - `ensure_entropy_loaded`

## 2) 推荐导入方式（Notebook）

```python
from src.easy_imports import *
```

该方式已聚合 Fun_HZ 常用能力，适合快速上手和历史 notebook 迁移。

## 3) 精准导入方式（工程代码）

```python
from src.simulation import run_dcr_and_power_test, run_and_plot_all
from src.analysis import get_discharge_capacity, calculate_cycle_swelling
from src.plotting import BatteryPlotter, plot_efficiency_vs_cycle_all
from src.utils import load_excel_to_plotter, export_cycle_data
```

适用于脚本化和团队协作，避免星号导入造成命名污染。

## 4) 历史调用替换示例

### 4.1 DCR + 功率 + 能效一键流程

```python
results = run_and_plot_all(
    rate_range=[0.25, 0.5],
    model=model,
    solver=solver,
    var_pts=var_pts,
    get_hithium_params=get_hithium_params,
    get_discharge_capacity_func=get_discharge_capacity,
    total_cycles=50,
    cycles_per_block=10,
    temperature=298.15,
)
```

### 4.2 容量保持率对比图

```python
plotter = BatteryPlotter()
process_sol_list_with_custom_extractor(plotter, sol_list, sim_labels_list, t_factor=50)
load_excel_to_plotter(plotter, r"D:\\path\\exp.xlsx", sheet_names="all")
plotter.plot(target_sim="all", target_exp="all")
```

### 4.3 全量指标导出（替代 notebook 内部长函数）

```python
_ = export_full_metrics_summary(
  sol_list=sol_list,
  sim_labels_list=sim_labels_list,
  cycle_step=50,
  output_filename="314_Full_Metrics_Summary.xlsx",
)
```

### 4.4 峰值电流

```python
res_peak = run_peak_current(
    model=model,
    param=params,
    var_pts=var_pts,
    temperature=298.15,
    nominal=164,
    t_period=60,
    x0=1,
)
```

## 5) 迁移建议（分两步）

1. **Notebook 先迁入 `easy_imports`**：保持可运行优先。
2. **再按模块细化导入**：将公共逻辑落到 `.py` 脚本，减少 notebook 重复代码。

## 6) 兼容性说明

- `src` 中函数签名尽量与 `Fun_HZ.py` 保持一致。
- 个别函数参数名做了工程化（如 `get_discharge_capacity_func`），语义不变。
- 若你旧 notebook 仍直接 `from Fun_HZ import *`，建议逐步替换为 `from src.easy_imports import *`。
