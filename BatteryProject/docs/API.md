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
  - 注：`plot_and_calculate_rrmse` 已迁至 [src/plotting.py](#srcplottingpy) 章节。
- `get_discharge_capacity(sol)`
  - 返回：`{"discharge_capacity": np.array}`，按圈提取放电容量。
- `get_all_heat_components(sol, label_for_temp=None)`
  - 返回：每圈不可逆/可逆/总热量分量字典（键：`irrev_chg/irrev_dchg/rev_chg/rev_dchg/total_chg/total_dchg`）。
- `calculate_cycle_swelling(sol, params, return_components=False, omega_n=..., omega_p=0, k_stiffness=1e9, preload_force=0, method="engineering", reference="parameter_initial", return_table=False)`
  - `method="engineering"` 保留浓度-厚度估算；`method="pybamm_thickness"` 优先读取 `Cell thickness change [m]`，再乘 `k_stiffness` 并叠加 `preload_force`。
  - `reference` 支持 `cycle_start` / `solution_start` / `parameter_initial`。
  - 返回：默认 `(max_forces, min_forces)`；`return_components=True` 时返回 `(max, min, eoc, reversible_amplitudes)`；`return_table=True` 时返回结构化表。
- `compute_cycle_energies(sol)`
  - 返回：`{"discharge_cap", "e_charge", "e_discharge", "efficiency"}`，计算每圈容量/能量/能效。
- `extract_all_metrics_from_sol(sol)`
  - 返回：`(discharge_cap, e_charge, e_discharge, efficiency)` 元组。
注：`export_cycle_metrics_report` / `export_full_metrics_summary` 已迁至 [src/reporting.py](#srcreportingpy) 章节。

## src/reporting.py

> 与 ``analysis`` 解耦的纯报表模块（pandas + openpyxl 写出，不做计算）。

- `export_cycle_metrics_report(sol_list, sim_labels_list, cycle_step=50, output_filename=...)`
  - 作用：按工况分组导出循环结果到 Excel（含条件格式色阶）。
- `export_full_metrics_summary(sol_list, sim_labels_list, cycle_step=50, output_filename=...)`
  - 作用：导出完整指标汇总表到 Excel。

## src/simulation*.py

`src.simulation` 是 facade，再导出下列子模块的公共符号；下列函数路径同时也可直接从子模块导入：

- `src/simulation_dcr.py`：DCR + 恒功率分块循环
- `src/simulation_peak.py`：峰值电流/功率搜索
- `src/simulation_rpt.py`：Branch-RPT 诊断
- `src/simulation_frequency.py`：频率调节工况老化
- `src/simulation_eis.py`：寿命老化 + SOH 节点 EIS 阻抗谱
- `src/simulation_common.py`：跨子模块复用的公共参数构造（非公共 API）

### simulation_dcr

- `perform_dcr_test(sol, params, model, solver, var_pts, current=1175, C1=0.25, C2=0.5, t=10, charge_time=None, target_soc=0.5)`
  - 返回：dict，包含键 `dcr_mean`, `dcr_discharge`, `dcr_charge`, `power_discharge`, `power_charge`, `solution`, `charge_time`。
  - `target_soc ∈ [0, 1]`：实际预充时长 = `charge_time * target_soc`（小时）。
- `run_dcr_and_power_test(rate_range, model, solver, var_pts, get_hithium_params, get_discharge_capacity_func=None, total_cycles=50, cycles_per_block=10, temperature=298.15, nominal_current=1175, nominal_voltage=3.2, target_soc=0.5, parallel=False, max_workers=None, keep_only_last_cycle_solution=False, return_solutions=True, showprogress=True)`
  - 返回：包含 DCR、功率、充电时间与 `sol_list` 的字典。
  - `parallel=True` 时按 rate 并行（默认 ThreadPool；`return_solutions=False` 时切换为 ProcessPool）。
  - `keep_only_last_cycle_solution=True` 时把每段解压缩到只保留最后一圈，显著降低内存。
  - `get_discharge_capacity_func=None`（默认）时自动绑定 `src.analysis.get_discharge_capacity`；测试需要 mock 时传入自定义可调用即可。
- `run_and_plot_all(rate_range, model, solver, var_pts, get_hithium_params, get_discharge_capacity_func=None, total_cycles=50, cycles_per_block=10, temperature=298.15)`
  - 作用：一键完成 DCR/功率仿真并绘制能效曲线（内部调用 `plot_efficiency_vs_cycle_all`）。

### simulation_peak

- `peak_current_condition(nominal, temperature, ratio, time=10, mode="A")`
  - 返回：`{"charge_peak": Experiment, "discharge_peak": Experiment}`。
  - `mode="W"` 时，施加功率为 `ratio * nominal * 3.2` W。
- `run_peak_current(model, param, var_pts, temperature=298.15, nominal=164, t_period=60, x0=1, charge_soc_list=None, discharge_soc_list=None, search_ratios=None, mode="A")`
  - 返回 dict，键：
    - `mode`
    - `charge_soc` / `discharge_soc`
    - `charge_peak_current` / `discharge_peak_current` (A，3.2 V 基准等效)
    - `charge_peak_power` / `discharge_peak_power` (W)
    - `charge_first_voltage` / `discharge_first_voltage` (脉冲首点电压)

### simulation_rpt

- `build_rpt_steps(current_a) -> list[str]`：构建放电 → 充CV → 放电的标定循环步序。
- `run_branch_rpt(model, solver, starting_solution, temperature_k, current_a, var_pts, get_hithium_params, calculate_cycle_swelling_func=None) -> tuple[Solution, dict]`
  - 从给定 starting state 跑一圈 RPT，返回 `(rpt_sol, summary)`；summary 含 `rpt_charge_capacity_ah`、`rpt_discharge_capacity_ah`、`rpt_*_energy_wh`、`rpt_efficiency`、可选 `rpt_max_force_n` / `rpt_min_force_n`。
- `snapshot_degradation_variables(sol, faraday_const=96485.33212) -> dict`
  - 抽取 throughput、SEI、plating、side reactions、LLI / LAM 标量诊断。
- `should_run_rpt(real_days_elapsed, real_days_total, rpt_every_real_days) -> bool`：调度工具。

### simulation_frequency

- `build_frequency_day_steps(current_a, pulse_seconds, total_pulses_per_day, sample_period_seconds) -> list[str]`
  - 一天对称充放脉冲步序；`total_pulses_per_day` 必须为偶数。
- `prepare_frequency_scenarios(scenarios, current_a, nominal_capacity_ah) -> dict`
  - 输入原始场景列表，自动补齐：`pair_count_per_day`、`charge_ah_per_day`、`discharge_ah_per_day`、`efc_per_day`、`soc_swing_per_half_cycle`、`waveform_hours_per_day`。
  - 返回 `{"scenarios": normalized_scenarios, "scenario_table": DataFrame}`。
- `run_frequency_scenario(scenario, runtime_config, *, model_options, var_pts, current_a, nominal_capacity_ah=None, initial_soc, temperature_k, get_hithium_params, ...) -> dict`
  - 按 `day_acceleration_factor` 加速跑老化，按 `rpt_every_real_days` 节点插入 Branch-RPT。
  - 当 `scenario` 还是 notebook 原始写法、尚未带 `efc_per_day` 等衍生字段时，可通过 `nominal_capacity_ah` 自动补齐，不需要手工预处理。
  - 返回 `{scenario, main_df, rpt_df, final_main_solution, rpt_solutions}`。
- `summarize_frequency_results(results, real_days_covered=None) -> pandas.DataFrame`
  - 把 `run_frequency_scenario` / `run_frequency_scenarios` 的结果汇总成 notebook 常用 summary 表。
  - 默认提取 `final_capacity_retention_pct`、`final_rpt_efficiency_pct`、`final_q_sei_ah`、`final_q_plating_ah`、`final_lli_ah`、`final_lam_neg_ah`。
- `run_frequency_scenarios(scenarios, runtime_config, *, model_options, var_pts, current_a, nominal_capacity_ah, initial_soc, temperature_k, get_hithium_params, calculate_cycle_swelling_func=None, faraday_const=96485.33212, solver_rtol=1e-6, solver_atol=1e-6, parallel=False, max_workers=None, keep_only_last_cycle_solution=False, keep_only_last_rpt_solution=False, return_solutions=None, enabled_only=True) -> dict`
  - 多场景批量入口，内部负责：场景预处理、任务 kwargs 打包、串行/并行调度、结果汇总。
  - 返回 `{"scenarios", "scenario_table", "results", "summary_df"}`。
  - `parallel=True` 且 `return_solutions=False` 时使用 `ProcessPoolExecutor`；若显式要求返回解对象，则退回 `ThreadPoolExecutor`，避免在子进程之间搬运大 `Solution`。
  - `enabled_only=True` 时自动跳过 `enabled=False` 的场景。

### simulation_eis

> 寿命老化跑到指定 SOH 节点后，注入静置并做 EIS 阻抗谱测量与 Nyquist 后处理。

- `build_lifecycle_power_experiment(...)`：构建 EIS 检查点前的严格恒功率寿命实验。
- `build_lifecycle_soh_table(cycle_solutions, ...) -> pd.DataFrame`：从逐圈解构建每圈 SOH 表。
- `pick_soh_checkpoints(soh_table, milestones) -> ...`：挑出最接近目标 SOH 里程碑的唯一检查点。
- `prepare_eis_measurement_state(...)`：在某个寿命检查点准备 EIS 测量所需的电池状态。
- `run_eis_from_checkpoint(...)`：从保存的寿命检查点状态运行 EIS。
- `impedance_to_frame(eis_sol) -> pd.DataFrame`：把 EIS 解转成整洁 DataFrame。
- `summarize_impedance_components(eis_sol) -> dict`：抽取紧凑的 Nyquist 特征。
- `extract_frequency_slices(eis_sol, target_freqs) -> pd.DataFrame`：取若干目标频率最近的阻抗行。
- `format_eis_state_label(...)`：返回 EIS 测量状态的可读描述。
- `run_lifecycle_eis_study(...) -> dict`：一站式入口——寿命老化 + EIS 后处理一次跑完。
- 常量 `DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS`：默认寿命+EIS 模型选项。

## src/swelling_coupling.py

> 膨胀力-孔隙率 单向准稳态耦合（电化学→力→双向耦合，路线 A）。每个老化 block 末尾：用
> `calculate_cycle_swelling` 算 EOC 膨胀力 → 化为模组等效压力 P → 由压力反算孔隙率因子，
> 低地更新 `params` 孔隙率参数，使下一 block 在受压收缩后的孔隙率下仿真；与
> `apply_dryout_to_initial_conditions(..., porosity_factors=...)` 共享同一套孔隙率状态。

### `SwellingCoupler`
- `SwellingCoupler(params, ...)`：初始化时记录初始孔隙率参数与模组刚度/预紧设置。
- `update(sol, params) -> dict`：由当前块解的 EOC 膨胀力算压力，更新 `params` 孔隙率参数并返回更新因子。
- `summary() -> dict`：返回膨胀力-孔隙率耦合的最新状态摘要。
- 经 `run_aging_with_dryout(..., swelling_coupler=SwellingCoupler(params, ...))` 接入。

## src/runtime.py

> Notebook 与示例入口的运行时辅助。

- `apply_pybamm_runtime_limits(...)`：应用项目 Notebook 默认的 PyBaMM 运行时限制（线程/求解器上限等）。
- `configure_notebook_environment(...)`：追加常用路径并应用默认 PyBaMM 运行时限制。

## src/plotting.py

### `BatteryPlotter`
- `add_exp_data(label, cycle, capacity, retention)`：注入实验曲线
- `add_sim_data(label, cycle, capacity, retention)`：注入仿真曲线
- `plot(target_exp=None, target_sim=None, figsize=..., ...)`：绘制**容量 + 保持率**双图。
- `plot_heat(target_exp=None, target_sim=None, figsize=..., ...)`：绘制**充电产热 + 放电产热**双图。
  - 按标签关键字（``_chg`` / ``_dchg`` / ``charge`` / ``discharge``）路由：放电关键字 → 右图，其它（含未命中）→ 左图。
- `plot(mode="heat")` 是历史入口；现仍接受但发出 ``DeprecationWarning`` 并转发到 ``plot_heat``。

### 其他函数
- `plot_and_calculate_rrmse(df, x_columns, y_columns, sol_list, labels, colors, charge_or_discharge)`
  - 作用：实验/仿真电压曲线对比并通过 ``logger.info`` 输出 RMSE/RRMSE；内部复用 ``calculate_rrmse_from_sol``。
  - 从 ``analysis`` 模块迁入。
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

> 老化参数辨识。提供搜索空间定义、loss 计算、目标函数构建、统一优化入口。

### `ParamSpec`
- `ParamSpec(scope: str, scale: str, low: float, high: float)` — dataclass
  - `scope`: `"user"` 或 `"model"`，决定参数注入位置（user 进入 `parameter_values`；model 进入模型选项）
  - `scale`: `"log"` 或 `"line"`，决定优化器搜索空间是否对数化
  - `low`, `high`: 物理量上下界（log 模式下内部自动转 log10）

### 参数空间映射
- `params_to_model_input(search_params: dict[str, float], change_params: dict[str, ParamSpec], fixed_input_params: dict[str, dict[str, float]] | None = None) -> dict[str, dict[str, float]]`
  - 把优化器空间的搜索点映射回 PyBaMM 输入：`{"user": {...}, "model": {...}}`。
  - 自动处理 log↔line 反变换；与 `fixed_input_params` 合并。

### Loss 计算
- `loss_line(exp_curve: list[np.ndarray], sim_curve: list[np.ndarray]) -> float`
  - 单条 V-t 曲线 RMSE。
- `loss_cycle_line(exp_curve, sim_output, t_factor) -> float`
  - 容量保持率曲线 loss（cycle vs capacity）。
- `loss_cycle_line_v2(exp_curve, sim_output, t_factor) -> float`
  - cycle_line 加长度惩罚：仿真曲线提前终止时引入额外罚项。
- `loss_record(exp_records: list[list[np.ndarray]], sim_output, t_factor) -> float`
  - 记录层 loss：对选定循环逐圈做归一化 V-t RMSE 并求平均。
- `compute_loss(loss_type: str | list[str], exp_data, sim_output, t_factor: int = 50) -> float`
  - 统一调度。`loss_type` 支持 `"line"` / `"cycle_line"` / `"cycle_line_v2"` / `"record"` 或它们的列表（hybrid 模式，需 `exp_data` 为 `dict[loss_type → data]`）。

### 仿真输出抽取
- `extract_aging_output(sol, cycle_index: list[int] | np.ndarray | None = None) -> dict`
  - 从 PyBaMM 解提取老化拟合输出。返回键：
    - `"discharge_capacity"`：每圈放电容量
    - `"Measured capacity [A.h]"`：兼容字段，同上
    - `"Simulation Record data"`：`[[t_charge, v_charge], [t_discharge, v_discharge], ...]`
    - `"Time [s]"`、`"Voltage [V]"`、`"Current [A]"`：完整时序

### 目标函数与优化入口
- `build_aging_objective(simulate_fn: Callable, change_params, exp_data, fixed_input_params: dict | None = None, loss_type: str | list[str] = "cycle_line", t_factor: int = 50, cycle_index_map: dict[str, list[int] | np.ndarray] | None = None, fail_penalty: Callable[[dict[str, float]], float] | None = None) -> Callable[[dict[str, float]], float]`
  - 包装可直接送进优化器的目标函数：`fitness = 1 / loss`。
  - `simulate_fn(model_input_params)` 返回 PyBaMM solution，或 hybrid 时返回 `dict[loss_type → solution]`。
  - `cycle_index_map` 给 record loss 指定每个 loss_type 抽取哪些循环。
  - `fail_penalty` 仿真失败时的兜底罚值（默认大常数）。

- `run_parameter_optimization(objective: Callable, change_params, method: str = "BO", method_params: dict[str, Any] | None = None, init: dict[str, float] | None = None) -> dict[str, float]`
  - 统一优化入口。返回最优参数字典。
  - **`method`** 支持：
    - `"BO"`：贝叶斯优化（依赖 `bayesian-optimization`）。`method_params` 常用键：`init_points`、`n_iter`、`utility_kind`、`random_state`。
    - `"GO"`：遗传算法（依赖 `pygad`）。常用键：`generation_num`、`num_parents_mating`、`sol_per_pop`、`parent_selection_type`、`keep_parents`、`crossover_type`（默认 `single_point`）、`mutation_type`（默认 `random`）、`mutation_probability`。
    - `"MO"`：scipy `minimize`（默认 SLSQP，可改 `nelder-mead`）。
    - `"DA"`：scipy `dual_annealing`。
    - `"BH"`：scipy `basinhopping`。`method_params={"stepsize": ..., "method": "nelder-mead"}`。
  - 选错时报错文案：`method must be one of: BO, GO, MO, DA, BH`。

## src/easy_imports.py

- 作用：聚合常用模块与函数，便于 Notebook 一行导入。
- 频率调节相关公共符号现已包含：
  - `build_frequency_day_steps`
  - `prepare_frequency_scenarios`
  - `run_frequency_scenario`
  - `run_frequency_scenarios`
  - `summarize_frequency_results`
  - `build_rpt_steps`
  - `run_branch_rpt`
  - `snapshot_degradation_variables`
  - `integrate_step_capacity_ah` / `integrate_step_energy_wh`
  - `extract_last_rpt_active_blocks`

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

> 一站式 Sim-vs-Exp 对标。支持工况自动匹配、bias 修正、子图嵌入。

### 单指标对标
- `compare_retention(sol_list, sim_labels, exp_data_list=None, acceleration_factor: int = 50, ax=None, figsize: tuple[float,float] = (8, 5), filter_conditions: dict[str, str] | None = None, sim_bias: float = 0.0, exp_bias: float = 0.0)`
  - 容量保持率对标图。
  - `filter_conditions` 形如 `{"temperature": "25°C", "rate": "0.5P"}`，自动按温度/倍率筛选。
  - `sim_bias`/`exp_bias` 在 retention 上做加性修正（用于校准初始容量差）。

- `compare_efficiency(sol_list, sim_labels, exp_data_list=None, acceleration_factor: int = 50, ax=None, figsize=(8, 5), filter_conditions=None, sim_bias=0.0, exp_bias=0.0)`
  - 能量效率对标图。参数同上。

- `compare_swelling(sol_list, sim_labels, exp_data_list=None, params=None, acceleration_factor: int = 50, ax_max=None, ax_min=None, figsize=(10, 5), omega_n=..., omega_p: float = 0, k_stiffness: float = 1e9, preload_force: float = 0, method="engineering", reference="parameter_initial", filter_conditions=None, sim_bias=0.0, exp_bias=0.0)`
  - 膨胀力（最大 / 最小）对标，需 `params` 含 thickness 信息。
  - `omega_n`/`omega_p`：负/正极偏摩尔体积；`k_stiffness`：模组等效刚度 [N/m]；`preload_force`：预紧力 [N]；`method`/`reference` 同 `calculate_cycle_swelling`。

### 一站式
- `compare_all(sol_list, sim_labels, exp_folder=None, exp_data_list=None, params=None, acceleration_factor: int = 50, channel: int = 0, metrics: tuple[str, ...] = ("retention", "efficiency", "swelling"), figsize_single=(8, 5), omega_n=..., omega_p=0, k_stiffness=1e9, preload_force=0, method="engineering", reference="parameter_initial", filter_conditions=None, sim_bias=0.0, exp_bias=0.0) -> dict`
  - 自动从 `exp_folder` 加载循环 CSV → 按 (温度, 倍率) 自动配对仿真与实验 → 输出三联图。
  - `metrics` 可裁剪只画其中部分。
  - 返回 dict，含每个 metric 的 figure、配对统计、未匹配工况列表。

## src/electrolyte_dryout.py

> 基于 Li2024（专利 14995785）的电解液干涸耦合循环老化。

### `DryoutTracker`
- `DryoutTracker(params, excess_ratio: float = 1.2)`
  - 初始化时把以下参数注入 `params`：
    - `Initial total electrolyte volume in whole cell [m3]`
    - `Initial total electrolyte volume in jelly roll [m3]`
    - `Current solvent concentration in the reservoir [mol.m-3]`
    - `Current electrolyte concentration in the reservoir [mol.m-3]`
    - `EC diffusivity [m2.s-1]`、`Electrolyte dry out rate [m3.s-1]`
  - **方法**：
    - `update(sol, params)` — 根据上一段 SEI 消耗量更新电解液体积、孔隙率、储液浓度
    - `plot()` — 绘制 6 子图历史
    - `summary() -> dict` — 当前最新状态字典
    - `get_lam_dryout_pct() -> float` — 当前因干涸引起的等效 LAM 百分比

### 模块级函数
- `apply_dryout_to_initial_conditions(model, sol, params) -> pybamm.BaseModel`
  - 把干涸更新后的电解液浓度应用到 `model.initial_conditions`，返回新 model（可继续仿真）。

- `plot_dryout(history, figsize: tuple[float, float] = (15, 10))`
  - 绘制 6 子图：电解液体积、储液浓度、孔隙率、EC 浓度、等效 LAM、SEI 厚度。

- `run_aging_with_dryout(model, params, experiment, solver, var_pts, starting_solution=None, tracker: DryoutTracker | None = None, n_blocks: int = 10, cycles_per_block: int = 10, t_factor: int = 50, temperature: float = 298.15, get_hithium_params: Callable | None = None, showprogress: bool = True) -> tuple[pybamm.Solution, DryoutTracker]`
  - 分块循环老化主入口。每个 block：跑 `cycles_per_block` 圈 → `tracker.update` → `apply_dryout_to_initial_conditions` → 进入下一块。
  - 返回 `(final_sol, tracker)`。`tracker.history` 留有完整时序，可直接传给 `plot_dryout`。

## src/experiment_utils.py

- `estimate_power_step_duration_hours(power_w, nominal_capacity_ah, reference_voltage_v=3.2, ...)`
  - 作用：估算恒功率步保守时长（含安全系数）。
- `build_power_step(direction, power_w, cutoff_voltage_v, nominal_capacity_ah, ...)`
  - 作用：生成带显式时长保护的 PyBaMM 恒功率实验字符串。

## src/psd_workflow.py

> 激光粒度仪体积百分比 → 面积加权对数正态拟合 → PSD 仿真对照研究的完整工作流。

### 输入归一化与面积分布
- `normalize_material_inputs(materials: dict[str, dict[str, Any]], default_diameters_um: Any | None = None) -> dict[str, dict[str, Any]]`
  - 校验 `materials` 字典：每个材料需含 `diameters_um` 与 `vol_pct`，长度一致、直径全为正、至少 1 个正体积 bin。
  - 自动填充 `Dv50_um`、`single_radius_um`、`metadata` 字段。
  - 报错文案如 `"Material X is missing diameters_um"`、`"... has mismatched diameters_um and vol_pct lengths"` 等。

- `compute_area_distribution(diameters_um, vol_pct) -> dict`
  - 把激光体积百分比转面积加权半径 PDF。
  - 返回键：`radii_m`、`area_pdf_m`、`cumulative_area`、`area_mean_radius_m`、`sd_rel`。

### 单/双对数正态拟合
- `fit_single_lognormal_psd(distribution: dict) -> dict`
  - 单 lognormal 拟合。返回 `{ok, mu_ln, sigma_ln, mean_radius_m, std_radius_m, sd_rel, ...}`。
  - 拟合失败时 `ok=False` 并附错误信息（"single-lognormal fit requires positive mean and standard deviation"）。

- `evaluate_single_fit(radii_m, fit_result) -> np.ndarray`
  - 在指定半径网格上还原拟合 PDF。

- `fit_bimodal_lognormal_psd(distribution, keep_percent: float = 99.0) -> dict`
  - 双 lognormal 混合拟合。`keep_percent` 控制累积面积截断比例。
  - 返回含 `weight_1/2`、`mu_1/2_ln`、`sigma_1/2_ln`、`mean_radius_1/2_m`、`std_radius_1/2_m`、`sd_rel_1/2`、`fit_ok`、`radius_min_m`、`radius_max_m` 等。

- `evaluate_bimodal_fit(radii_m, fit_result) -> np.ndarray`

### 多材料分析与汇总
- `analyze_materials(materials, default_diameters_um=None, selected_strategy: str = "bimodal", keep_percent: float = 99.0) -> dict[str, dict]`
  - 全流程：归一化 → 面积分布 → 单 + 双拟合 → 把 `selected_strategy`（`"single"` 或 `"bimodal"`）作为 `selected_fit`。
  - 返回 `{material_name: {distribution, single_fit, bimodal_fit, selected_fit, single_radius_m, ...}}`。

- `build_material_summary_frame(material_analysis) -> pd.DataFrame`
  - 一行/材料的对比表。列含：`material`、`area_mean_radius_um`、`single_sd_rel`、`bimodal_weight_1/2`、`bimodal_mean_radius_1/2_um`、`bimodal_sd_rel_1/2`、`radius_min_um/max_um`。

### 工况构造
- `build_operation_cases(design: dict[str, Any]) -> list[dict[str, Any]]`
  - 从 `design = {nominal_capacity_ah, nominal_voltage_v, rate_list | power_w_list, ...}` 生成工况列表。
  - `rate_list` 与 `power_w_list` 必须二选一，否则抛 `"Provide exactly one of rate_list or power_w_list"`。

- `build_power_experiment(power_w: float, design: dict) -> pybamm.Experiment`
  - 构造 charge → rest → discharge → rest 的恒功率实验。
  - `design` 支持 `period_minutes`、`rest_minutes`、`cycles`、`charge_cutoff_v`、`discharge_cutoff_v`、`temperature_k`。

### 单粒径 vs PSD 模式对照仿真
- `run_material_comparison_study(material_analysis, design, get_hithium_params, *, var_pts=None, solver=None, initial_soc=None, temperature_k: float = 298.15, negative_sd_rel: float | None = None) -> dict`
  - 对每种材料同时跑两组：
    - **single**：用 `single_radius_m` 设置 `Positive particle radius [m]`
    - **PSD**：用 `selected_fit` 的 lognormal 替换 `Positive particle radius [m]`（`particle phases` 选项启用）
  - `negative_sd_rel` 不为 None 时，负极也启用 PSD（用 `_pybamm_lognormal`）。
  - 返回 `{material: {case_label: {single: {solution, ...}, psd: {solution, ...}}}}`。

- `summarize_single_run(run_result, cycle_number: int = 2) -> dict`
  - 抽取单条 run 在指定 cycle 的容量、能量、平均电压、`Throughput capacity [A.h]` 等步级指标。

- `summarize_study(study_result, cycle_number: int = 2) -> pd.DataFrame`
  - 一行 / (material, case_label, mode) 的汇总表。

- `build_step_curve_frame(study_result, cycle_number: int = 2) -> pd.DataFrame`
  - 抽取每条 run 在指定循环的充/放电 V-t 曲线（步级别）。

- `build_full_curve_frame(study_result) -> pd.DataFrame`
  - 抽取每条 run 全程 V-t / I-t 时序。
