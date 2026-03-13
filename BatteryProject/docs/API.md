# BatteryProject API 目录

本文件集中说明 src/ 内的可复用接口与典型用法，便于在脚本与 Notebook 中快速查找。

## src/config.py

### 常量
- `PROJECT_DIR`/`WORKSPACE_DIR`/`DATA_DIR`/`OUTPUT_DIR`/`PARAMS_DIR`：路径常量
- `DEFAULT_PLOT_STYLE`/`DEFAULT_FONT_SANS_SERIF`：绘图样式与字体
- `ENTROPY_FILE`/`TARGET_PTS`：熵系数文件与插值点数
- `RATES`/`TEMPERATURES`/`ACCELERATION_FACTOR`/`NOMINAL_CAPACITY`/`DATA_FILE`

### 函数
- `load_entropy(entropy_file=None, target_pts=TARGET_PTS)`
  - 作用：加载熵系数曲线，返回 `(dudt_chg, dudt_dchg)`。
- `ensure_entropy_loaded()`
  - 作用：延迟加载熵系数，若未加载则触发 `load_entropy()`。
- `electrolyte_diffusivity_Nyman2008_arrhenius(c_e, T)`
  - 作用：电解液扩散系数温度修正。
- `electrolyte_conductivity(c_e, T)`
  - 作用：电解液电导率温度修正。
- `LFP_ocp_charge(sto)` / `LFP_ocp_discharge(sto)`
  - 作用：LFP 正极充放电 OCP 曲线。
- `graphite_ocp_charge(sto)` / `graphite_ocp_discharge(sto)`
  - 作用：石墨负极充放电 OCP 曲线。
- `LFP_ocp_Hithium280Ah(sto)` / `graphite_ocp_Hithium280Ah(sto)`
  - 作用：Hithium 280Ah 特化 OCP。
- `LFP_entropic(sto)` / `graphite_entropic(sto)`
  - 作用：正/负极熵系数曲线。
- `plating_exchange_current_density_OKane2020(c_e, c_Li, T)`
  - 作用：镀锂交换电流密度。
- `get_hithium_params(t_factor=1, temperature=298.15)`
  - 作用：生成参数字典，供 PyBaMM 参数更新使用。

## src/analysis.py

- `calc_rrmse(y_true, y_pred)`
  - 返回：`(rmse, rrmse)`。
- `plot_and_calculate_rrmse(df, x_columns, y_columns, sol_list, labels, colors, charge_or_discharge)`
  - 作用：实验/仿真曲线对比并输出 RMSE/RRMSE。
- `get_discharge_capacity(sol)`
  - 返回：`{"discharge_capacity": np.array}`，按圈提取放电容量。
- `get_separated_irreversible_heat(sol)`
  - 返回：`{"charge_heat": ..., "discharge_heat": ...}`，分离充/放电不可逆热。
- `get_all_heat_components(sol, label_for_temp=None)`
  - 返回：每圈不可逆/可逆/总热量分量字典。
- `calculate_cycle_swelling(sol, params)`
  - 返回：`(max_forces, min_forces)`，估算每圈膨胀力。

## src/simulation.py

- `perform_dcr_test(sol, params, model, solver, var_pts, current=1175, C1=0.25, C2=0.5, t=10, charge_time=None)`
  - 返回：`(dcr_mean, dcr_discharge, dcr_charge, power_discharge, power_charge, test_sol, charge_time)`。
- `run_dcr_and_power_test(rate_range, model, solver, var_pts, get_hithium_params, get_discharge_capacity_func, total_cycles=50, cycles_per_block=10, temperature=298.15, nominal_current=1175, nominal_voltage=3.2)`
  - 返回：包含 DCR、功率、充电时间与 `sol_list` 的字典。
- `peak_current_condition(nominal, temperature, ratio, time=10)`
  - 返回：`{"charge_peak": Experiment, "discharge_peak": Experiment}`。
- `run_peak_current(model, param, var_pts, temperature=298.15, nominal=164, t_period=60, x0=1)`
  - 返回：SOC 与峰值电流序列字典。

## src/plotting.py

### `BatteryPlotter`
- `add_exp_data(label, cycle, capacity, retention)`：注入实验曲线
- `add_sim_data(label, cycle, capacity, retention)`：注入仿真曲线
- `plot(...)`：绘制容量/保持率双图

### 其他函数
- `Different_cycle_voltage(sol, battery_model, rate, temperature)`
  - 作用：绘制不同循环下的电压曲线。
- `process_sol_list_for_all_heat_components(plotter_instance, sol_list, label_list, acceleration_factor=50)`
  - 作用：注入不可逆/可逆/总热量分量曲线。

## src/utils.py

- `safe_var_access(step, candidates)`
  - 作用：在候选变量名中找到第一个可用变量。
- `BatteryDataLoader.load_data(file_path, sheet_name=0)`
  - 作用：自动识别表头并标准化列名。
- `load_excel_to_plotter(plotter_instance, file_path, sheet_names=None)`
  - 作用：读取 Excel 并注入实验曲线。
- `process_sol_list_with_custom_extractor(plotter_instance, sol_list, label_list, t_factor=50)`
  - 作用：提取放电容量并注入仿真曲线。
- `export_cycle_data(sol, filename="cycle_analysis.xlsx")`
  - 作用：导出每圈充/放电曲线到 Excel。

## src/data_cleaning.py

- `clean_xy_curve(x, y, sort_by_x=True, drop_duplicates=True, smooth_window=None, smooth_polyorder=2)`
  - 作用：清洗二维曲线（数值化、去空、去重、排序、可选平滑）。
- `load_curve_file(file_path, x_col=0, y_col=1, sep=None, header=None, smooth_window=None)`
  - 作用：读取 txt/csv/dat 的二维曲线并清洗。
- `load_record_layer_csv(file_path, cycle_col="cycle", t_col="t", v_col="V")`
  - 作用：按 cycle 分组提取记录层 `[[t, v], ...]`。
- `load_experiment_data(exp_data_path)`
  - 作用：按配置批量加载 `line/cycle_line/cycle_line_v2/record` 实验数据。

## src/parameter_identification.py

- `ParamSpec(scope, scale, low, high)`
  - 作用：定义参数搜索空间（支持 log/line）。
- `params_to_model_input(search_params, change_params, fixed_input_params=None)`
  - 作用：将优化器参数映射为 `{"user":..., "model":...}` 输入。
- `extract_aging_output(sol, cycle_index=None)`
  - 作用：从 PyBaMM 解提取老化拟合输出（容量衰减曲线 + 记录层）。
- `compute_loss(loss_type, exp_data, sim_output, t_factor=50)`
  - 作用：计算 `cycle_line/cycle_line_v2/record/hybrid` 误差。
- `build_aging_objective(simulate_fn, change_params, exp_data, ...)`
  - 作用：构建可直接用于优化器的目标函数（fitness = 1/loss）。
- `run_parameter_optimization(objective, change_params, method="BO", ...)`
  - 作用：执行参数优化（支持 `BO/GO/MO/DA/BH`）。

## src/easy_imports.py

- 作用：聚合常用模块与函数，便于 Notebook 一行导入。

## main.py

- 作用：轻量入口，用于快速加载配置并做基础流程自检。

---

## Notebook 简化示例（MIC多温度拟合）

> 目标：用统一 API 替换手写的 Excel 解析、容量/保持率注入、产热处理等重复逻辑。

### 推荐替换思路
1. **实验数据注入**：用 `load_excel_to_plotter` 统一读取。
2. **仿真容量曲线**：用 `process_sol_list_with_custom_extractor` 注入。
3. **热量曲线**：用 `process_sol_list_for_all_heat_components`（可筛选 `Irrev/Rev/Total`）。

### 最小示例
```python
from src.easy_imports import *

plotter = BatteryPlotter()

# 1) 实验曲线注入
load_excel_to_plotter(plotter, DATA_DIR / "循环数据-20260106.xlsx", sheet_names="all")

# 2) 仿真结果注入（示例：已得到 sol_list/label_list）
process_sol_list_with_custom_extractor(plotter, sol_list, label_list, t_factor=ACCELERATION_FACTOR)

# 3) 产热分量（可选）
process_sol_list_for_all_heat_components(plotter, sol_list, label_list, acceleration_factor=ACCELERATION_FACTOR)

# 4) 统一绘图
plotter.plot(target_exp="all", target_sim="all")
```

### 关联 Notebook
- MIC 多温度拟合：../MIC/不同温度倍率循环/MIC多温度拟合.ipynb
