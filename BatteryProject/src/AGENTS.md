# BatteryProject/src — 核心仿真代码 Harness

## 这个区域是什么
所有仿真逻辑的 Python 模块。Notebook 通过 `import src.xxx` 使用。

## 函数签名规范

### simulation.py
```python
def run_peak_current(model, param, var_pts, temperature=298.15,
                     nominal=164, t_period=60, x0=1,
                     charge_soc_list=None, discharge_soc_list=None,
                     search_ratios=None) -> dict:
    """返回 {'charge_soc', 'charge_peak_current', 'discharge_soc', 'discharge_peak_current', ...}"""

def perform_dcr_test(sol, params, model, solver, var_pts,
                     current=1175, C1=0.25, C2=0.5, t=10,
                     charge_time=None) -> tuple:
    """返回 (avg_dcr, discharge_dcr, charge_dcr, discharge_power, charge_power)"""

def run_dcr_and_power_test(rate_range, model, solver, var_pts,
                           get_hithium_params, get_discharge_capacity_func,
                           total_cycles=50, cycles_per_block=10,
                           temperature=298.15, nominal_current=1175,
                           nominal_voltage=3.2) -> dict:
```

### experiment_utils.py
```python
def build_power_step(direction, power_w, cutoff_voltage_v,
                     nominal_capacity_ah, period_minutes=0.5,
                     reference_voltage_v=3.2, safety_factor=1.25,
                     min_duration_hours=2.0) -> str:
    """返回 PyBaMM experiment 字符串"""
```

## 修改规则
- 新增函数必须有 docstring（至少说明参数和返回值）
- 修改函数签名时，保持向后兼容（用默认参数）
- 在 `easy_imports.py` 中导出新增的公共函数
- 修改后必须运行 `python -m pytest BatteryProject/tests/ -q`

## 测试要求
- 每个仿真函数至少有一个 smoke test（最小配置，1个SOC，1个循环）
- 测试文件在 `BatteryProject/tests/` 下，命名 `test_<module>.py`
- 已有: `test_experiment_utils.py`, `test_peak_current.py`

## 禁止事项
- 不得在函数内部硬编码温度或电芯参数
- 不得修改 `pybamm.ParameterValues` 的全局状态
- 不得在 src 模块中使用 `plt.show()` — 绘图仅在 Notebook 中做
