# BatteryProject API Reference

本文件是精简入口。旧的完整清单位于 [API.md](API.md)，适合查详细函数说明。

## Notebook 入口

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import run_peak_current
```

- `setup_notebook(cell=None, style="science", ...)`: 配置路径、PyBaMM runtime、matplotlib 样式和 autoreload。
- `load_params(cell, reload_module=False)`: 从参数 registry 获取 `get_hithium_params`。
- `src.notebook_api`: 面向新 notebook 的收窄入口。

## 参数 registry

```python
from params import load_cell_params
get_hithium_params = load_cell_params("MIC")
```

常用 key：

- `MIC` / `1175Ah` -> `paramsMIC.py`
- `280` -> `params280.py`
- `314` -> `params314.py`
- `587` -> `params587.py`

兼容入口：

- `from params import get_hithium_params` 仍指向历史 314Ah 参数。
- 直接 import `paramsMIC`、`params280`、`params587` 仍可用于旧 notebook。

## 推荐高频入口

`src.notebook_api` 当前暴露：

- `setup_notebook`
- `load_params`
- `run_peak_current`
- `perform_dcr_test`
- `run_dcr_and_power_test`
- `get_discharge_capacity`
- `calc_rrmse`
- `compare_all`
- `BatteryPlotter`
- `build_power_step`
- `prepare_pulse_lifecycle_scenarios`
- `run_pulse_lifecycle_scenarios`
- `summarize_pulse_lifecycle_results`
- `extract_cycle_voltage_curve`
- `p_rate_to_power_w`
- `DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS`
- `FULL_PULSE_LIFECYCLE_MODEL_OPTIONS`
- `LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS`

## 按任务精确导入

峰值电流：

```python
from src.simulation import run_peak_current
```

DCR / 恒功率循环：

```python
from src.simulation import perform_dcr_test, run_dcr_and_power_test
```

调频：

```python
from src.simulation import (
    prepare_frequency_scenarios,
    run_frequency_scenarios,
    summarize_frequency_results,
)
```

插入脉冲：

```python
from src.simulation import (
    prepare_pulse_lifecycle_scenarios,
    run_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
)
```

实验对标：

```python
from src.compare import compare_all
from src.exp_loader import load_cycling_csv, load_cycling_folder
from src.analysis import calc_rrmse, get_discharge_capacity
from src.plotting import BatteryPlotter
```

## Facade 与 legacy

- `src.simulation` 是仿真 facade，保持旧 import 路径稳定。
- `src.easy_imports` 是 legacy convenience，新 notebook 不再推荐 `from src.easy_imports import *`。
- `docs/API.md` 是完整历史 API 清单，后续可继续拆分为更细的 reference。
