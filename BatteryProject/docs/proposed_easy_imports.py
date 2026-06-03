"""BatteryProject 高频接口聚合（收敛版 + 弃用兜底）。

设计原则
--------
- ``__all__`` 只列 ~50 个 high-level facade（旧版 80+），让 ``from easy_imports import *``
  和 IDE 自动完成都看到收敛后的表面。
- 子模块作为命名空间也在 ``__all__`` 中，长尾函数走 ``analysis.X`` / ``plotting.X``。
- 35 个旧名字保留为模块级懒加载属性（通过 ``__getattr__``），首次按名字
  ``from easy_imports import compare_retention`` 仍能拿到，但会触发一次
  ``DeprecationWarning`` 提示新写法。计划在下个 major 版本删除。

行为对照
--------
- ``from src.easy_imports import *``：只拿到 ``__all__`` 里的 ~50 名字（不含 legacy）
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

# --- 子模块命名空间 ---------------------------------------------------
from src import (
    analysis,
    compare,
    config,
    data_cleaning,
    electrolyte_dryout,
    exp_loader,
    experiment_utils,
    parameter_identification,
    plotting,
    psd_workflow,
    simulation,
    utils,
)

# --- 配置常量与参数获取（高频引用） -----------------------------------
from src.config import (
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
from src.simulation import (
    perform_dcr_test,
    run_dcr_and_power_test,
    run_peak_current,
)
from src.experiment_utils import build_power_step

# --- 分析与指标 -------------------------------------------------------
from src.analysis import (
    calc_rrmse,
    calculate_cycle_swelling,
    compute_cycle_energies,
    extract_all_metrics_from_sol,
    get_all_heat_components,
    get_discharge_capacity,
)

# --- 绘图核心 ---------------------------------------------------------
from src.plotting import (
    BatteryPlotter,
    different_cycle_voltage,
    plot_efficiency_vs_cycle_all,
    plot_swelling,
    process_sol_list_for_all_heat_components,
)

# --- 数据 IO ----------------------------------------------------------
from src.utils import (
    BatteryDataLoader,
    export_cycle_data,
    load_dat_folder_to_plotter,
    load_excel_to_plotter,
    process_sol_list_with_custom_extractor,
)
from src.exp_loader import (
    load_cycling_csv,
    load_cycling_folder,
    parse_condition_from_filename,
)
from src.data_cleaning import (
    clean_xy_curve,
    load_curve_file,
    load_experiment_data,
    load_record_layer_csv,
)

# --- Sim-Exp 一站式对标 ----------------------------------------------
from src.compare import compare_all

# --- 老化 / 电解液干涸 -----------------------------------------------
from src.electrolyte_dryout import (
    DryoutTracker,
    run_aging_with_dryout,
)

# --- PSD 工作流 ------------------------------------------------------
from src.psd_workflow import (
    analyze_materials,
    build_operation_cases,
    build_power_experiment,
    run_material_comparison_study,
    summarize_study,
)

# --- 参数辨识 --------------------------------------------------------
from src.parameter_identification import (
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
    "parameter_identification",
    "plotting",
    "psd_workflow",
    "simulation",
    "utils",
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
    # 仿真
    "build_power_step",
    "perform_dcr_test",
    "run_dcr_and_power_test",
    "run_peak_current",
    # 分析
    "calc_rrmse",
    "calculate_cycle_swelling",
    "compute_cycle_energies",
    "extract_all_metrics_from_sol",
    "get_all_heat_components",
    "get_discharge_capacity",
    # 绘图
    "BatteryPlotter",
    "different_cycle_voltage",
    "plot_efficiency_vs_cycle_all",
    "plot_swelling",
    "process_sol_list_for_all_heat_components",
    # IO
    "BatteryDataLoader",
    "clean_xy_curve",
    "export_cycle_data",
    "load_curve_file",
    "load_cycling_csv",
    "load_cycling_folder",
    "load_dat_folder_to_plotter",
    "load_excel_to_plotter",
    "load_experiment_data",
    "load_record_layer_csv",
    "parse_condition_from_filename",
    "process_sol_list_with_custom_extractor",
    # 对标
    "compare_all",
    # 老化
    "DryoutTracker",
    "run_aging_with_dryout",
    # PSD
    "analyze_materials",
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
import warnings as _warnings


_LEGACY_REDIRECTS: dict[str, tuple[str, str]] = {
    # 旧名字 → ("子模块名", "属性名")
    # --- analysis ---
    "calculate_rrmse_from_sol": ("analysis", "calculate_rrmse_from_sol"),
    "plot_and_calculate_rrmse": ("analysis", "plot_and_calculate_rrmse"),
    "export_cycle_metrics_report": ("analysis", "export_cycle_metrics_report"),
    "export_full_metrics_summary": ("analysis", "export_full_metrics_summary"),
    # --- plotting ---
    "Different_cycle_voltage": ("plotting", "Different_cycle_voltage"),
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


_MODULE_LOOKUP = {
    "analysis": analysis,
    "plotting": plotting,
    "config": config,
    "simulation": simulation,
    "parameter_identification": parameter_identification,
    "compare": compare,
    "electrolyte_dryout": electrolyte_dryout,
    "experiment_utils": experiment_utils,
    "psd_workflow": psd_workflow,
}


def __getattr__(name: str):  # PEP 562 — 模块级 __getattr__
    redirect = _LEGACY_REDIRECTS.get(name)
    if redirect is None:
        raise AttributeError(
            f"module 'src.easy_imports' has no attribute {name!r}"
        )
    module_name, attr_name = redirect
    target = getattr(_MODULE_LOOKUP[module_name], attr_name)
    _warnings.warn(
        f"src.easy_imports.{name} 已弃用，请改用 "
        f"`from src.{module_name} import {attr_name}` 或 "
        f"`{module_name}.{attr_name}`（计划在下个 major 版本移除）",
        DeprecationWarning,
        stacklevel=2,
    )
    # 缓存到模块全局，避免下次再 warn / 再做属性查找
    globals()[name] = target
    return target


def __dir__() -> list[str]:  # 让 ``dir(easy_imports)`` 也看到 legacy 名字（便于 IDE 跳转）
    return sorted(set(__all__) | set(_LEGACY_REDIRECTS))
