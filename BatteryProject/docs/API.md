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
- `calculate_rrmse_from_sol(df, x_columns, y_columns, sol_list, labels, charge_or_discharge)`
  - 作用：纯分析——对比仿真/实验电压曲线，返回每条曲线的 RMSE/RRMSE 及绘图数据。
- `plot_and_calculate_rrmse(df, x_columns, y_columns, sol_list, labels, colors, charge_or_discharge)`
  - 作用：实验/仿真曲线对比并输出 RMSE/RRMSE（向后兼容，内部复用 `calculate_rrmse_from_sol`）。
- `get_discharge_capacity(sol)`
  - 返回：`{"discharge_capacity": np.array}`，按圈提取放电容量。
- `get_all_heat_components(sol, label_for_temp=None)`
  - 返回：每圈不可逆/可逆/总热量分量字典（键：`irrev_chg/irrev_dchg/rev_chg/rev_dchg/total_chg/total_dchg`）。
- `calculate_cycle_swelling(sol, params, return_components=False, omega_n=..., omega_p=0, k_stiffness=1e9, preload_force=0)`
  - 返回：默认 `(max_forces, min_forces)`；`return_components=True` 时返回 `(max, min, eoc, reversible_amplitudes)`。
- `compute_cycle_energies(sol)`
  - 返回：`{"discharge_cap", "e_charge", "e_discharge", "efficiency"}`，计算每圈容量/能量/能效。
- `extract_all_metrics_from_sol(sol)`
  - 返回：`(discharge_cap, e_charge, e_discharge, efficiency)` 元组。
- `export_cycle_metrics_report(sol_list, sim_labels_list, cycle_step=50, output_filename=...)`
  - 作用：按工况分组导出循环结果到 Excel（含条件格式色阶）。
- `export_full_metrics_summary(sol_list, sim_labels_list, cycle_step=50, output_filename=...)`
  - 作用：导出完整指标汇总表到 Excel。

## src/simulation.py

- `perform_dcr_test(sol, params, model, solver, var_pts, current=1175, C1=0.25, C2=0.5, t=10, charge_time=None)`
  - 返回：dict，包含键 `dcr_mean`, `dcr_discharge`, `dcr_charge`, `power_discharge`, `power_charge`, `solution`, `charge_time`。
- `run_dcr_and_power_test(rate_range, model, solver, var_pts, get_hithium_params, get_discharge_capacity_func, total_cycles=50, cycles_per_block=10, temperature=298.15, nominal_current=1175, nominal_voltage=3.2)`
  - 返回：包含 DCR、功率、充电时间与 `sol_list` 的字典。
- `peak_current_condition(nominal, temperature, ratio, time=10, mode="A")`
  - 返回：`{"charge_peak": Experiment, "discharge_peak": Experiment}`。
  - `mode="W"` 时，施加功率为 `ratio * nominal * 3.2` W。
- `run_peak_current(model, param, var_pts, temperature=298.15, nominal=164, t_period=60, x0=1, charge_soc_list=None, discharge_soc_list=None, search_ratios=None, mode="A")`
  - 返回：dict，包含 SOC 网格、等效峰值电流（3.2V 基准）、峰值功率、首点电压。
- `run_and_plot_all(rate_range, model, solver, var_pts, get_hithium_params, get_discharge_capacity_func, ...)`
  - 作用：一键完成 DCR/功率仿真并绘制能效曲线。

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

---

## src/exp_loader.py

- `parse_condition_from_filename(filename)`
  - 作用：从文件名解析温度和倍率，返回 `{"temperature": "25°C", "rate": "0.5P", "label": "25°C 0.5P"}`。
- `load_cycling_csv(file_path, channel=0, label=None, encoding="utf-8-sig")`
  - 作用：加载测试设备导出 CSV，自动识别中英文列名，返回统一 dict。
- `load_cycling_folder(folder_path, pattern="*.csv", channel=0, ...)`
  - 作用：批量加载文件夹下所有循环 CSV，返回 `list[dict]`。

## src/compare.py

- `compare_retention(sol_list, sim_labels, exp_data_list, acceleration_factor=50, ...)`
  - 作用：容量保持率 Sim-vs-Exp 对标图。支持 `filter_conditions` 筛选工况、`sim_bias`/`exp_bias` 偏移修正。
- `compare_efficiency(sol_list, sim_labels, exp_data_list, ...)`
  - 作用：能量效率对标图。参数同上。
- `compare_swelling(sol_list, sim_labels, exp_data_list, params, ...)`
  - 作用：膨胀力（最大/最小）对标图。支持 `omega_n`/`k_stiffness`/`preload_force` 物理参数。
- `compare_all(sol_list, sim_labels, exp_folder=None, exp_data_list=None, params=None, ...)`
  - 作用：一站式自动对标（retention + efficiency + swelling），自动匹配工况。

## src/electrolyte_dryout.py

- `DryoutTracker(params, excess_ratio=1.2)`
  - 作用：电解液干涸状态追踪器。初始化时注入干涸参数到 params。
  - 方法：`update(sol, params)` / `plot()` / `summary()` / `get_lam_dryout_pct()`。
- `apply_dryout_to_initial_conditions(model, sol, params)`
  - 作用：将干涸浓度修正应用到初始条件，返回新模型。
- `plot_dryout(history, figsize=...)`
  - 作用：绘制干涸演化 6 子图面板。
- `run_aging_with_dryout(model, params, experiment, solver, var_pts, ...)`
  - 作用：带电解液干涸追踪的循环老化仿真。

## src/experiment_utils.py

- `estimate_power_step_duration_hours(power_w, nominal_capacity_ah, reference_voltage_v=3.2, ...)`
  - 作用：估算恒功率步保守时长（含安全系数）。
- `build_power_step(direction, power_w, cutoff_voltage_v, nominal_capacity_ah, ...)`
  - 作用：生成带显式时长保护的 PyBaMM 恒功率实验字符串。

## src/psd_workflow.py

- `normalize_material_inputs(materials, default_diameters_um=None)`
  - 作用：校验并归一化材料粒径分布输入。
- `compute_area_distribution(diameters_um, vol_pct)`
  - 作用：将激光粒度仪体积百分比转换为面积加权半径分布。
- `fit_single_lognormal_psd(distribution)` / `fit_bimodal_lognormal_psd(distribution)`
  - 作用：用对数正态分布拟合面积加权 PSD。
- `analyze_materials(materials, selected_strategy="bimodal")`
  - 作用：完整分析流程：归一化 → 面积分布 → 拟合。
- `build_material_summary_frame(material_analysis)` → `pd.DataFrame`
- `build_operation_cases(design)` → `list[dict]`：从设计参数生成工况列表。
- `run_material_comparison_study(analysis, design, get_hithium_params)` → dict
  - 作用：对多种材料 PSD 运行对比仿真（single vs PSD 模式）。
- `summarize_study(study_result, cycle_number=2)` → `pd.DataFrame`
