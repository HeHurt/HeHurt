"""PyBaMM 仿真子模块的统一聚合 facade。

实际实现拆分在多个子模块；此文件只做向后兼容的统一再导出，
让 ``from src.simulation import perform_dcr_test`` 等旧调用继续可用。

- simulation_common：跨模块复用的工具（内部 API，不在此 facade 暴露）
- simulation_dcr   ：DCR + 恒功率分块循环（``perform_dcr_test`` 等）
- simulation_peak  ：峰值电流/功率搜索（``run_peak_current`` 等）
- simulation_rpt   ：Branch-RPT 诊断（容量、能量、力学）
- simulation_eis   ：生命周期 EIS 阻抗工作流
- simulation_frequency：频率调节工况老化
- simulation_regional_parallel：多区域并联电芯等压分流
- simulation_regional_lifecycle：多区域并联恒功率循环老化
"""
from .simulation_common import ensure_hysteresis_state_params
from .simulation_dcr import (
    perform_dcr_test,
    run_dcr_and_power_test,
    run_and_plot_all,
)
from .simulation_peak import (
    HYSTERESIS_OCP_OPTIONS,
    PEAK_POWER_REFERENCE_VOLTAGE,
    peak_current_condition,
    run_peak_current,
)
from .simulation_rpt import (
    safe_last_scalar,
    snapshot_degradation_variables,
    step_mean_current,
    integrate_step_capacity_ah,
    integrate_step_energy_wh,
    extract_last_rpt_active_blocks,
    build_rpt_steps,
    summarize_rpt_solution,
    run_branch_rpt,
    should_run_rpt,
)
from .simulation_eis import (
    DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS,
    build_lifecycle_power_experiment,
    format_eis_state_label,
    build_lifecycle_soh_table,
    pick_soh_checkpoints,
    prepare_eis_measurement_state,
    run_eis_from_checkpoint,
    impedance_to_frame,
    summarize_impedance_components,
    extract_frequency_slices,
    run_lifecycle_eis_study,
)
from .simulation_frequency import (
    EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE,
    build_frequency_day_steps,
    build_frequency_current_profile,
    prepare_frequency_scenarios,
    run_frequency_scenario,
    run_frequency_scenarios,
    summarize_frequency_results,
    trim_current_profile,
)
from .simulation_pulse_lifecycle import (
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    build_pulse_lifecycle_capacity_check_steps,
    build_pulse_lifecycle_cycle_steps,
    extract_cycle_voltage_curve,
    p_rate_to_power_w,
    prepare_pulse_lifecycle_scenarios,
    run_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
)
from .simulation_regional_parallel import (
    ParallelSplitResult,
    RegionalCellState,
    RegionalDFNConfig,
    RegionalDFNCouplingResult,
    aggregate_regional_capacity_ah,
    build_area_scaled_regions,
    run_regional_dfn_coupling,
    solve_parallel_current_split,
)
from .simulation_regional_lifecycle import (
    RegionalPowerCycleResult,
    run_regional_dfn_power_cycles,
    solve_parallel_power_split,
)

__all__ = [
    # common
    "ensure_hysteresis_state_params",
    # dcr
    "perform_dcr_test",
    "run_dcr_and_power_test",
    "run_and_plot_all",
    # peak
    "HYSTERESIS_OCP_OPTIONS",
    "PEAK_POWER_REFERENCE_VOLTAGE",
    "peak_current_condition",
    "run_peak_current",
    # rpt
    "safe_last_scalar",
    "snapshot_degradation_variables",
    "step_mean_current",
    "integrate_step_capacity_ah",
    "integrate_step_energy_wh",
    "extract_last_rpt_active_blocks",
    "build_rpt_steps",
    "summarize_rpt_solution",
    "run_branch_rpt",
    "should_run_rpt",
    # eis
    "DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS",
    "build_lifecycle_power_experiment",
    "format_eis_state_label",
    "build_lifecycle_soh_table",
    "pick_soh_checkpoints",
    "prepare_eis_measurement_state",
    "run_eis_from_checkpoint",
    "impedance_to_frame",
    "summarize_impedance_components",
    "extract_frequency_slices",
    "run_lifecycle_eis_study",
    # frequency
    "EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE",
    "build_frequency_day_steps",
    "trim_current_profile",
    "build_frequency_current_profile",
    "prepare_frequency_scenarios",
    "run_frequency_scenario",
    "run_frequency_scenarios",
    "summarize_frequency_results",
    # pulse lifecycle
    "DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "FULL_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "build_pulse_lifecycle_capacity_check_steps",
    "build_pulse_lifecycle_cycle_steps",
    "extract_cycle_voltage_curve",
    "p_rate_to_power_w",
    "prepare_pulse_lifecycle_scenarios",
    "run_pulse_lifecycle_scenarios",
    "summarize_pulse_lifecycle_results",
    # regional parallel
    "ParallelSplitResult",
    "RegionalCellState",
    "RegionalDFNConfig",
    "RegionalDFNCouplingResult",
    "aggregate_regional_capacity_ah",
    "build_area_scaled_regions",
    "run_regional_dfn_coupling",
    "solve_parallel_current_split",
    # regional lifecycle
    "RegionalPowerCycleResult",
    "run_regional_dfn_power_cycles",
    "solve_parallel_power_split",
]
