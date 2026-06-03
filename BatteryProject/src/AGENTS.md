# BatteryProject/src — 核心仿真代码 Harness

## 这个区域是什么
所有仿真逻辑的 Python 模块。Notebook 通过 `import src.xxx` 使用。

## simulation 子模块划分
原 ``simulation.py`` 已按职责拆分；``simulation.py`` 现在只是一个 facade，
统一再导出下述子模块的公共符号，旧的 `from src.simulation import ...` 调用不变。

| 子模块 | 职责 |
|---|---|
| ``simulation_common`` | ``_make_parameter_values`` / 解的轻量化（不直接对外，但被其它子模块复用） |
| ``simulation_dcr``    | ``perform_dcr_test`` / ``run_dcr_and_power_test`` / ``run_and_plot_all`` |
| ``simulation_peak``   | ``peak_current_condition`` / ``run_peak_current`` 及其搜索 helper |
| ``simulation_rpt``    | ``build_rpt_steps`` / ``run_branch_rpt`` / ``snapshot_degradation_variables`` |
| ``simulation_frequency`` | ``build_frequency_day_steps`` / ``run_frequency_scenario`` |

新增仿真逻辑时：**先想清楚归属再选文件**；公共 helper 落在 ``simulation_common``；
最终在 ``simulation.py`` 的 ``__all__`` 中追加新名字以保持 facade 完整。

## 函数签名规范

### simulation_peak.py
```python
def run_peak_current(model, param, var_pts, temperature=298.15,
                     nominal=164, t_period=60, x0=1,
                     charge_soc_list=None, discharge_soc_list=None,
                     search_ratios=None, mode="A") -> dict:
    """返回 dict，键含:
    - 'mode'
    - 'charge_soc' / 'discharge_soc'
    - 'charge_peak_current' / 'discharge_peak_current'  (A，3.2V 基准下的等效)
    - 'charge_peak_power' / 'discharge_peak_power'      (W)
    - 'charge_first_voltage' / 'discharge_first_voltage' (脉冲首点电压)
    """
```

### simulation_dcr.py
```python
def perform_dcr_test(sol, params, model, solver, var_pts,
                     current=1175, C1=0.25, C2=0.5, t=10,
                     charge_time=None, target_soc=0.5) -> dict:
    """返回 dict，键:
    'dcr_mean', 'dcr_discharge', 'dcr_charge',
    'power_discharge', 'power_charge',
    'solution', 'charge_time'

    实际预充时长 = charge_time * target_soc（小时），target_soc ∈ [0, 1]。
    """

def run_dcr_and_power_test(rate_range, model, solver, var_pts,
                           get_hithium_params, get_discharge_capacity_func=None,
                           total_cycles=50, cycles_per_block=10,
                           temperature=298.15, nominal_current=1175,
                           nominal_voltage=3.2, target_soc=0.5,
                           parallel=False, max_workers=None,
                           keep_only_last_cycle_solution=False,
                           return_solutions=True, showprogress=True) -> dict:
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
- 新增/搬移到 ``simulation_*.py`` 的公共符号要同步加进 ``simulation.py`` 的 ``__all__``
- 修改后必须运行 `python -m pytest BatteryProject/tests/ -q`

## 测试要求
- 每个仿真函数至少有一个 smoke test（最小配置，1个SOC，1个循环）
- 测试文件在 `BatteryProject/tests/` 下，命名 `test_<module>.py`
- 已有: `test_experiment_utils.py`（覆盖 DCR / target_soc / 并行 / `_compress_solution_to_last_cycle`）、`test_peak_current.py`、`test_analysis.py`、`test_data_cleaning.py`、`test_exp_loader.py`、`test_psd_workflow.py`
- mock simulation 内部符号时，**patch 真实存在的模块**（例如 ``patch.object(src.simulation_dcr.pybamm, ...)``），不是 facade ``src.simulation``

## 禁止事项
- 不得在函数内部硬编码温度或电芯参数
- 不得修改 `pybamm.ParameterValues` 的全局状态
- 不得在 src 模块中使用 `plt.show()` — 绘图仅在 Notebook 中做
