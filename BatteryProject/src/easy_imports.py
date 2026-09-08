"""BatteryProject 高频接口聚合（收敛版 + 弃用兜底）。

设计原则
--------
- ``__all__`` 只列约 50 个 high-level facade，让 ``from easy_imports import *``
  和 IDE 自动完成都看到收敛后的表面。
- 子模块作为命名空间也在 ``__all__`` 中，长尾函数走 ``analysis.X`` / ``plotting.X``。
- 旧名字保留为模块级懒加载属性（通过 ``__getattr__``），首次按名字
  ``from easy_imports import compare_retention`` 仍能拿到，但会触发一次
  ``DeprecationWarning`` 提示新写法。计划在下个 major 版本删除。

行为对照
--------
- ``from src.easy_imports import *``：只拿到 ``__all__`` 里的名字（不含 legacy）
- ``from src.easy_imports import compare_retention``：能拿到，发一次警告
- ``easy_imports.compare_retention``：能拿到，发一次警告
- 不在新表也不在 legacy 表的名字：抛 ``AttributeError``

主要差异（相对旧版 ``__all__``）
------------------------------
- ``run_and_plot_all`` 已弃用（违反 AGENTS.md "src 不得 plt.show"）；
  老 notebook 临时仍可 ``from easy_imports import run_and_plot_all``，但建议改 ``simulation.run_and_plot_all(...)``。
- ``Different_cycle_voltage``（首字母大写别名）走 legacy 兜底，建议改 ``different_cycle_voltage``。
- ``compare_retention/efficiency/swelling``、``apply_dryout_to_initial_conditions``、
  ``fit_*_psd``、``params_to_model_input`` 等长尾低频函数全部走 legacy 兜底。

Notebook 推荐写法
----------------
::

    from src.easy_imports import *

    # 高层一行入口
    sol_dict = run_dcr_and_power_test(rate_range=[0.5, 1.0], ...)
    compare_all(sol_list, sim_labels, exp_folder=DATA_DIR / "exp_csv")

    # 子模块按需调用
    analysis.calc_rrmse(y_true, y_pred)
    plotting.plot_swelling(sol_list, sim_labels, params)
    parameter_identification.run_parameter_optimization(obj, change_params, method="BO")

精准导入（推荐工程代码）
----------------------
::

    from src.simulation import run_dcr_and_power_test
    from src.compare import compare_all
"""
from __future__ import annotations

import warnings as _warnings

from .runtime import apply_pybamm_runtime_limits, configure_notebook_environment

apply_pybamm_runtime_limits()

# 库层已统一用 logging（不再 print）。notebook 入口在此给 src 包挂一个
# INFO 级 StreamHandler（仅当用户尚未自行配置时），让 compare_all 等的
# 匹配结果输出仍然可见；工程代码直接 import 子模块则不受影响。
import logging as _logging  # noqa: E402

_pkg_logger = _logging.getLogger(__package__)
if not _pkg_logger.handlers:
    _pkg_handler = _logging.StreamHandler()
    _pkg_handler.setFormatter(_logging.Formatter("%(message)s"))
    _pkg_logger.addHandler(_pkg_handler)
    _pkg_logger.setLevel(_logging.INFO)

# --- 子模块命名空间 ---------------------------------------------------
from . import (  # noqa: E402
    analysis,
    compare,
    config,
    data_cleaning,
    electrolyte_dryout,
    exp_loader,
    experiment_utils,
    lifecycle_exp,
    parameter_identification,
    plotting,
    psd_workflow,
    simulation,
    utils,
    workflows,
)

# --- 配置常量与参数获取（高频引用） -----------------------------------
from .config import (  # noqa: E402
    ACCELERATION_FACTOR,
    DATA_DIR,
    NOMINAL_CAPACITY,
    OUTPUT_DIR,
    PARAMS_DIR,
    PROJECT_DIR,
    RATES,
    TEMPERATURES,
    get_hithium_params,
)

# --- 仿真入口 ---------------------------------------------------------
from .simulation import (  # noqa: E402
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    summarize_frequency_results,
    run_frequency_scenarios,
    run_frequency_scenario,
    prepare_frequency_scenarios,
    build_frequency_day_steps,
    EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE,
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    build_frequency_current_profile,
    build_pulse_lifecycle_capacity_check_steps,
    build_pulse_lifecycle_cycle_steps,
    extract_cycle_voltage_curve,
    p_rate_to_power_w,
    ParallelSplitResult,
    perform_dcr_test,
    prepare_pulse_lifecycle_scenarios,
    RegionalCellState,
    RegionalDFNConfig,
    RegionalDFNCouplingResult,
    RegionalPowerCycleResult,
    aggregate_regional_capacity_ah,
    build_area_scaled_regions,
    run_regional_dfn_coupling,
    run_homogeneous_dfn_power_cycles,
    run_regional_dfn_power_cycles,
    run_dcr_and_power_test,
    solve_parallel_current_split,
    solve_parallel_power_split,
    run_peak_current,
    run_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
    trim_current_profile,
)
from .experiment_utils import build_power_step  # noqa: E402

# --- 分析与指标 -------------------------------------------------------
from .analysis import (  # noqa: E402
    calc_rrmse,
    calculate_cycle_swelling,
    compute_cycle_energies,
    extract_all_metrics_from_sol,
    get_all_heat_components,
    get_discharge_capacity,
)
from .heat_calibration import (  # noqa: E402
    build_calibrated_parameter_loader,
    build_hysteresis_equilibrium_overrides,
    compute_cycle_calibrated_heat,
    compute_reference_reversible_heat,
    fit_hysteresis_allocation,
    load_branch_entropy_curves,
)

# --- 绘图核心 ---------------------------------------------------------
from .plotting import (  # noqa: E402
    BatteryPlotter,
    different_cycle_voltage,
    plot_efficiency_vs_cycle_all,
    plot_swelling,
    plot_swelling_coupling,
    process_sol_list_for_all_heat_components,
)

# --- 数据 IO ----------------------------------------------------------
from .utils import (  # noqa: E402
    BatteryDataLoader,
    export_cycle_data,
    load_dat_folder_to_plotter,
    load_excel_to_plotter,
    process_sol_list_with_custom_extractor,
)
from .exp_loader import (  # noqa: E402
    load_cycling_csv,
    load_cycling_folder,
    parse_condition_from_filename,
)
from .lifecycle_exp import (  # noqa: E402
    export_cycle_life_dat,
    load_lifecycle_dat,
    parse_cycle_life_excel,
)
from .data_cleaning import (  # noqa: E402
    clean_xy_curve,
    load_curve_file,
    load_experiment_data,
    load_record_layer_csv,
)

# --- Sim-Exp 一站式对标 ----------------------------------------------
from .compare import compare_all  # noqa: E402

# --- 老化 / 电解液干涸 -----------------------------------------------
from .electrolyte_dryout import (  # noqa: E402,F401
    DryoutTracker,
    plot_dryout,
    apply_dryout_to_initial_conditions,
    run_aging_with_dryout,
)
from .swelling_coupling import SwellingCoupler  # noqa: E402

# --- PSD 工作流 ------------------------------------------------------
from .psd_workflow import (  # noqa: E402
    analyze_materials,
    evaluate_single_fit,
    evaluate_bimodal_fit,
    build_step_curve_frame,
    build_material_summary_frame,
    build_full_curve_frame,
    DEFAULT_VAR_PTS,
    build_operation_cases,
    build_power_experiment,
    run_material_comparison_study,
    summarize_study,
)

# --- 参数辨识 --------------------------------------------------------
from .parameter_identification import (  # noqa: E402
    ParamSpec,
    build_aging_objective,
    compute_loss,
    extract_aging_output,
    run_parameter_optimization,
)


__all__ = [
    # 子模块命名空间
    "analysis",
    "compare",
    "config",
    "data_cleaning",
    "electrolyte_dryout",
    "exp_loader",
    "experiment_utils",
    "lifecycle_exp",
    "parameter_identification",
    "plotting",
    "psd_workflow",
    "simulation",
    "utils",
    "workflows",
    # 配置常量
    "ACCELERATION_FACTOR",
    "DATA_DIR",
    "NOMINAL_CAPACITY",
    "OUTPUT_DIR",
    "PARAMS_DIR",
    "PROJECT_DIR",
    "RATES",
    "TEMPERATURES",
    "get_hithium_params",
    "apply_pybamm_runtime_limits",
    "configure_notebook_environment",
    # 仿真
    "EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE",
    "summarize_frequency_results",
    "run_frequency_scenarios",
    "run_frequency_scenario",
    "prepare_frequency_scenarios",
    "build_frequency_day_steps",
    "build_power_step",
    "perform_dcr_test",
    "run_dcr_and_power_test",
    "run_peak_current",
    "trim_current_profile",
    "run_pulse_lifecycle_scenarios",
    "prepare_pulse_lifecycle_scenarios",
    "p_rate_to_power_w",
    "extract_cycle_voltage_curve",
    "build_pulse_lifecycle_capacity_check_steps",
    "build_pulse_lifecycle_cycle_steps",
    "build_frequency_current_profile",
    "DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "FULL_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "summarize_pulse_lifecycle_results",
    "ParallelSplitResult",
    "RegionalCellState",
    "RegionalDFNConfig",
    "RegionalDFNCouplingResult",
    "RegionalPowerCycleResult",
    "aggregate_regional_capacity_ah",
    "build_area_scaled_regions",
    "run_regional_dfn_coupling",
    "run_homogeneous_dfn_power_cycles",
    "run_regional_dfn_power_cycles",
    "solve_parallel_current_split",
    "solve_parallel_power_split",
    # 分析
    "calc_rrmse",
    "calculate_cycle_swelling",
    "compute_cycle_energies",
    "extract_all_metrics_from_sol",
    "get_all_heat_components",
    "get_discharge_capacity",
    "build_calibrated_parameter_loader",
    "build_hysteresis_equilibrium_overrides",
    "compute_cycle_calibrated_heat",
    "compute_reference_reversible_heat",
    "fit_hysteresis_allocation",
    "load_branch_entropy_curves",
    # 绘图
    "BatteryPlotter",
    "different_cycle_voltage",
    "plot_efficiency_vs_cycle_all",
    "plot_swelling",
    "plot_swelling_coupling",
    "process_sol_list_for_all_heat_components",
    # IO
    "BatteryDataLoader",
    "clean_xy_curve",
    "export_cycle_data",
    "load_curve_file",
    "load_cycling_csv",
    "load_cycling_folder",
    "load_lifecycle_dat",
    "load_dat_folder_to_plotter",
    "load_excel_to_plotter",
    "load_experiment_data",
    "load_record_layer_csv",
    "parse_condition_from_filename",
    "parse_cycle_life_excel",
    "process_sol_list_with_custom_extractor",
    "export_cycle_life_dat",
    # 对标
    "compare_all",
    # 老化
    "DryoutTracker",
    "plot_dryout",
    "run_aging_with_dryout",
    "SwellingCoupler",
    # PSD
    "analyze_materials",
    "evaluate_single_fit",
    "evaluate_bimodal_fit",
    "build_step_curve_frame",
    "build_material_summary_frame",
    "build_full_curve_frame",
    "DEFAULT_VAR_PTS",
    "build_operation_cases",
    "build_power_experiment",
    "run_material_comparison_study",
    "summarize_study",
    # 参数辨识
    "ParamSpec",
    "build_aging_objective",
    "compute_loss",
    "extract_aging_output",
    "run_parameter_optimization",
]


# ---------------------------------------------------------------------
# Legacy 兼容层 —— 计划在下个 major 版本删除
# ---------------------------------------------------------------------
# 这些名字**不**在 __all__ 中，所以 ``from easy_imports import *`` 不会拿到。
# 但 ``from easy_imports import <name>`` 与 ``easy_imports.<name>`` 仍可工作，
# 首次访问时通过 ``__getattr__`` 懒加载并触发一次 DeprecationWarning。
_LEGACY_REDIRECTS: dict[str, tuple[str, str]] = {
    # 旧名字 -> ("子模块名", "属性名")
    # --- analysis ---
    "calculate_rrmse_from_sol": ("analysis", "calculate_rrmse_from_sol"),
    # --- reporting (旧版从 analysis re-export) ---
    "export_cycle_metrics_report": ("reporting", "export_cycle_metrics_report"),
    "export_full_metrics_summary": ("reporting", "export_full_metrics_summary"),
    # --- plotting ---
    "Different_cycle_voltage": ("plotting", "Different_cycle_voltage"),
    "plot_and_calculate_rrmse": ("plotting", "plot_and_calculate_rrmse"),
    "plot_analysis": ("plotting", "plot_analysis"),
    "plot_cycle_layer": ("plotting", "plot_cycle_layer"),
    "plot_charge_discharge": ("plotting", "plot_charge_discharge"),
    "plot_porosity": ("plotting", "plot_porosity"),
    "plot_lithium_loss": ("plotting", "plot_lithium_loss"),
    "plot_plating_overpotential": ("plotting", "plot_plating_overpotential"),
    "plot_electrolyte": ("plotting", "plot_electrolyte"),
    "plot_efficiency_vs_cycle": ("plotting", "plot_efficiency_vs_cycle"),
    "plot_swelling_for_condition": ("plotting", "plot_swelling_for_condition"),
    # --- config ---
    "ensure_entropy_loaded": ("config", "ensure_entropy_loaded"),
    "load_entropy": ("config", "load_entropy"),
    # --- simulation ---
    "run_and_plot_all": ("simulation", "run_and_plot_all"),
    "peak_current_condition": ("simulation", "peak_current_condition"),
    "build_frequency_day_steps": ("simulation", "build_frequency_day_steps"),
    "EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE": ("simulation", "EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE"),
    "prepare_frequency_scenarios": ("simulation", "prepare_frequency_scenarios"),
    "run_frequency_scenario": ("simulation", "run_frequency_scenario"),
    "run_frequency_scenarios": ("simulation", "run_frequency_scenarios"),
    "summarize_frequency_results": ("simulation", "summarize_frequency_results"),
    "build_frequency_current_profile": ("simulation", "build_frequency_current_profile"),
    "trim_current_profile": ("simulation", "trim_current_profile"),
    "DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS": ("simulation", "DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS"),
    "FULL_PULSE_LIFECYCLE_MODEL_OPTIONS": ("simulation", "FULL_PULSE_LIFECYCLE_MODEL_OPTIONS"),
    "LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS": ("simulation", "LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS"),
    "build_pulse_lifecycle_capacity_check_steps": ("simulation", "build_pulse_lifecycle_capacity_check_steps"),
    "build_pulse_lifecycle_cycle_steps": ("simulation", "build_pulse_lifecycle_cycle_steps"),
    "extract_cycle_voltage_curve": ("simulation", "extract_cycle_voltage_curve"),
    "p_rate_to_power_w": ("simulation", "p_rate_to_power_w"),
    "prepare_pulse_lifecycle_scenarios": ("simulation", "prepare_pulse_lifecycle_scenarios"),
    "run_pulse_lifecycle_scenarios": ("simulation", "run_pulse_lifecycle_scenarios"),
    "summarize_pulse_lifecycle_results": ("simulation", "summarize_pulse_lifecycle_results"),
    "build_rpt_steps": ("simulation", "build_rpt_steps"),
    "run_branch_rpt": ("simulation", "run_branch_rpt"),
    "snapshot_degradation_variables": ("simulation", "snapshot_degradation_variables"),
    "integrate_step_capacity_ah": ("simulation", "integrate_step_capacity_ah"),
    "integrate_step_energy_wh": ("simulation", "integrate_step_energy_wh"),
    "extract_last_rpt_active_blocks": ("simulation", "extract_last_rpt_active_blocks"),
    "DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS": ("simulation", "DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS"),
    "build_lifecycle_power_experiment": ("simulation", "build_lifecycle_power_experiment"),
    "format_eis_state_label": ("simulation", "format_eis_state_label"),
    "build_lifecycle_soh_table": ("simulation", "build_lifecycle_soh_table"),
    "pick_soh_checkpoints": ("simulation", "pick_soh_checkpoints"),
    "prepare_eis_measurement_state": ("simulation", "prepare_eis_measurement_state"),
    "run_eis_from_checkpoint": ("simulation", "run_eis_from_checkpoint"),
    "impedance_to_frame": ("simulation", "impedance_to_frame"),
    "summarize_impedance_components": ("simulation", "summarize_impedance_components"),
    "extract_frequency_slices": ("simulation", "extract_frequency_slices"),
    "run_lifecycle_eis_study": ("simulation", "run_lifecycle_eis_study"),
    # --- parameter_identification ---
    "params_to_model_input": ("parameter_identification", "params_to_model_input"),
    # --- compare ---
    "compare_retention": ("compare", "compare_retention"),
    "compare_efficiency": ("compare", "compare_efficiency"),
    "compare_swelling": ("compare", "compare_swelling"),
    # --- electrolyte_dryout ---
    "apply_dryout_to_initial_conditions": (
        "electrolyte_dryout",
        "apply_dryout_to_initial_conditions",
    ),
    "plot_dryout": ("electrolyte_dryout", "plot_dryout"),
    # --- experiment_utils ---
    "estimate_power_step_duration_hours": (
        "experiment_utils",
        "estimate_power_step_duration_hours",
    ),
    # --- psd_workflow ---
    "normalize_material_inputs": ("psd_workflow", "normalize_material_inputs"),
    "compute_area_distribution": ("psd_workflow", "compute_area_distribution"),
    "fit_single_lognormal_psd": ("psd_workflow", "fit_single_lognormal_psd"),
    "evaluate_single_fit": ("psd_workflow", "evaluate_single_fit"),
    "fit_bimodal_lognormal_psd": ("psd_workflow", "fit_bimodal_lognormal_psd"),
    "evaluate_bimodal_fit": ("psd_workflow", "evaluate_bimodal_fit"),
    "build_material_summary_frame": ("psd_workflow", "build_material_summary_frame"),
    "summarize_single_run": ("psd_workflow", "summarize_single_run"),
    "build_step_curve_frame": ("psd_workflow", "build_step_curve_frame"),
    "build_full_curve_frame": ("psd_workflow", "build_full_curve_frame"),
}


def __getattr__(name: str):  # PEP 562 — 模块级 __getattr__
    redirect = _LEGACY_REDIRECTS.get(name)
    if redirect is None:
        raise AttributeError(f"module 'src.easy_imports' has no attribute {name!r}")
    module_name, attr_name = redirect
    # 子模块按需 import，避免顶层硬依赖
    import importlib
    module = importlib.import_module(f".{module_name}", package=__package__)
    target = getattr(module, attr_name)
    _warnings.warn(
        f"src.easy_imports.{name} 已弃用，请改用 "
        f"`from src.{module_name} import {attr_name}` 或 `{module_name}.{attr_name}`"
        f"（计划在下个 major 版本移除）",
        DeprecationWarning,
        stacklevel=2,
    )
    globals()[name] = target
    return target


def __dir__() -> list[str]:  # 让 dir(easy_imports) 也看到 legacy 名字（便于 IDE 跳转）
    return sorted(set(__all__) | set(_LEGACY_REDIRECTS))
