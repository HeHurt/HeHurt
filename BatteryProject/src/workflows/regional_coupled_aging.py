"""Canonical workflow for regional parallel-coupled aging studies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pybamm

from ..data_registry import HITHIUM_ROOT
from ..notebook import load_params
from ..simulation_regional_lifecycle import (
    run_homogeneous_dfn_power_cycles,
    run_regional_dfn_power_cycles,
)
from ..simulation_regional_parallel import (
    DEFAULT_REGIONAL_DFN_VAR_PTS,
    RegionalDFNConfig,
    build_area_scaled_regions,
    run_regional_dfn_coupling,
    solve_parallel_current_split,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context
from ..workflow_specs import DatasetQuery


WORKFLOW_ID = "regional_coupled_aging"
STANDARD_VAR_PTS = dict(DEFAULT_REGIONAL_DFN_VAR_PTS)
DEFAULT_AREA_FRACTIONS = {"A_corner": 0.10, "B_middle": 0.70, "C_top": 0.20}
DEFAULT_POROSITY_PARAMETERS = (
    "Negative electrode porosity",
    "Separator porosity",
    "Positive electrode porosity",
)


@dataclass(frozen=True)
class ReducedNetworkCase:
    """One OCV plus resistance regional split case."""

    label: str
    resistance_multipliers: Any = 1.0
    capacity_retention: Any = 1.0
    current_bounds_a: Mapping[str, tuple[float | None, float | None]] | None = None

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("reduced network case label is required")


@dataclass(frozen=True)
class RegionalDFNCase:
    """One regional DFN case with per-region scalar parameter multipliers."""

    label: str
    parameter_multipliers_by_region: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("regional DFN case label is required")


@dataclass(frozen=True)
class ReducedNetworkSpec:
    """Configuration for quick OCV plus resistance coupling diagnostics."""

    enabled: bool = True
    base_ocv_v: float = 3.30
    base_resistance_ohm: float = 2.5e-4
    total_current_a: float | None = None
    current_c_rate: float = 1.0
    voltage_cutoff_v: float = 2.50
    local_blocked_region: str = "A_corner"
    sweep_multipliers: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0)
    cases: tuple[ReducedNetworkCase, ...] = (
        ReducedNetworkCase("healthy"),
        ReducedNetworkCase("A_blocked_x20", {"A_corner": 20.0, "B_middle": 1.0, "C_top": 1.0}),
        ReducedNetworkCase(
            "A_failed",
            {"A_corner": 1000.0, "B_middle": 1.0, "C_top": 1.0},
            {"A_corner": 0.0, "B_middle": 1.0, "C_top": 1.0},
            {"A_corner": (0.0, 0.0)},
        ),
    )

    def __post_init__(self) -> None:
        if self.base_resistance_ohm <= 0:
            raise ValueError("base_resistance_ohm must be positive")
        if self.current_c_rate <= 0:
            raise ValueError("current_c_rate must be positive")
        if not self.sweep_multipliers or any(value <= 0 for value in self.sweep_multipliers):
            raise ValueError("sweep_multipliers must contain positive values")


@dataclass(frozen=True)
class TransientDFNSpec:
    """Configuration for short regional DFN terminal-voltage coupling."""

    enabled: bool = False
    total_current_a: float | None = None
    current_c_rate: float = 0.25
    duration_s: float = 600.0
    macro_step_s: float = 60.0
    initial_soc: float = 0.5
    relaxation: float = 0.7
    max_iterations: int = 12

    def __post_init__(self) -> None:
        if self.current_c_rate <= 0:
            raise ValueError("current_c_rate must be positive")
        if self.duration_s <= 0 or self.macro_step_s <= 0:
            raise ValueError("duration_s and macro_step_s must be positive")
        if not 0 <= self.initial_soc <= 1:
            raise ValueError("initial_soc must be in [0, 1]")


@dataclass(frozen=True)
class LifecycleSpec:
    """Configuration for regional constant-power aging cycles."""

    enabled: bool = False
    run_homogeneous_baseline: bool = True
    discharge_power_w: float | None = None
    discharge_p_rate: float = 0.25
    charge_power_w: float | None = None
    cycles: int = 1
    equivalent_cycle_factor: float = 1.0
    rest_s: float = 600.0
    macro_step_s: float = 300.0
    maximum_macro_step_s: float | None = None
    initial_soc: float = 1.0
    lower_cutoff_v: float = 2.5
    upper_cutoff_v: float = 3.65
    max_segment_duration_s: float = 6 * 3600.0

    def __post_init__(self) -> None:
        if self.discharge_p_rate <= 0:
            raise ValueError("discharge_p_rate must be positive")
        if self.cycles <= 0:
            raise ValueError("cycles must be positive")
        if self.rest_s <= 0 or self.macro_step_s <= 0:
            raise ValueError("rest_s and macro_step_s must be positive")
        if not self.lower_cutoff_v < self.upper_cutoff_v:
            raise ValueError("lower_cutoff_v must be below upper_cutoff_v")


@dataclass(frozen=True)
class RegionalCoupledAgingWorkflowSpec:
    """Validated input contract for the regional coupled-aging canonical workflow."""

    cell: str
    area_fractions: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_AREA_FRACTIONS))
    regional_cases: tuple[RegionalDFNCase, ...] = (
        RegionalDFNCase("healthy"),
        RegionalDFNCase(
            "A_porosity_30pct",
            {"A_corner": {name: 0.30 for name in DEFAULT_POROSITY_PARAMETERS}},
        ),
    )
    run_mode: str = "smoke"
    temperature_c: float = 25.0
    aging_t_factor: int = 1
    nominal_capacity_ah: float | None = None
    nominal_voltage_v: float = 3.2
    reduced_network: ReducedNetworkSpec = field(default_factory=ReducedNetworkSpec)
    transient_dfn: TransientDFNSpec = field(default_factory=TransientDFNSpec)
    lifecycle: LifecycleSpec = field(default_factory=LifecycleSpec)
    datasets: tuple[DatasetQuery, ...] = ()
    model_options: dict[str, Any] = field(default_factory=lambda: {"contact resistance": "true"})
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))
    output_name: str = "区域并联耦合老化"

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.aging_t_factor <= 0:
            raise ValueError("aging_t_factor must be positive")
        if not self.area_fractions:
            raise ValueError("area_fractions is required")
        area_sum = sum(float(value) for value in self.area_fractions.values())
        if abs(area_sum - 1.0) > 1.0e-6:
            raise ValueError(f"area_fractions must sum to 1.0; got {area_sum:.12g}")
        if not self.regional_cases:
            raise ValueError("at least one regional case is required")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "RegionalCoupledAgingWorkflowSpec":
        """Build a workflow spec from the single notebook CONFIG mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        return cls(
            cell=str(config["cell"]),
            area_fractions=_area_fractions_from_config(config),
            regional_cases=_regional_cases_from_config(config),
            run_mode=run_mode,
            temperature_c=float(config.get("temperature_c", 25.0)),
            aging_t_factor=int(option("aging_t_factor", 1)),
            nominal_capacity_ah=config.get("nominal_capacity_ah"),
            nominal_voltage_v=float(config.get("nominal_voltage_v", 3.2)),
            reduced_network=_reduced_network_from_config(config, mode_config),
            transient_dfn=_transient_from_config(config, mode_config),
            lifecycle=_lifecycle_from_config(config, mode_config),
            datasets=_dataset_queries_from_config(config),
            model_options=dict(config.get("model_options", {"contact resistance": "true"})),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
            output_name=str(config.get("output_name", "区域并联耦合老化")),
        )

    @property
    def temperature_k(self) -> float:
        """Return configured temperature in kelvin."""
        return self.temperature_c + 273.15

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)


def build_feature_parity_table() -> pd.DataFrame:
    """Return the regional coupled-aging feature parity checklist."""
    rows = [
        ("OCV+R区域并联", "build_area_scaled_regions + solve_parallel_current_split", "保留"),
        ("局部堵塞/失效", "ReducedNetworkCase 支持阻抗倍率、容量保持率和断开电流边界", "保留"),
        ("局部 vs 全局堵塞 sweep", "reduced_network.sweep_multipliers 生成 terminal voltage/current share 对比", "保留"),
        ("区域DFN等压耦合", "run_regional_dfn_coupling 保留 macro-step 回滚试算和收敛诊断", "保留"),
        ("区域电流分配", "steps/iterations 输出 current_a、c_rate、voltage_spread、KCL error", "保留"),
        ("生命周期演化", "run_regional_dfn_power_cycles 输出 step/cycle/degradation 表", "保留"),
        ("同质baseline", "可选 run_homogeneous_dfn_power_cycles 与区域结果对照", "保留"),
        ("孔隙率历史", "negative/separator/positive porosity 进入 steps 表", "保留"),
        ("负极电位/析锂诊断", "lifecycle steps 保留 negative potential / plating overpotential 列", "保留"),
        ("图表入口", "Notebook 保留端电压、电流重分配、迭代收敛、孔隙率、寿命诊断章节", "保留"),
        ("DatasetQuery", "datasets[] 可解析实验输入，runner 写 datasets.csv", "保留"),
        ("标准output/runs", "create_run_context 写 BatteryProject/output/runs/regional_coupled_aging/<run_id>", "保留"),
        ("PSD独立", "workflow_id、spec、runner、Notebook 与 PSD workflow 无共享状态", "保留"),
    ]
    return pd.DataFrame(rows, columns=["功能", "canonical实现", "状态"])


def build_region_configs(
    area_fractions: Mapping[str, float],
    case: RegionalDFNCase,
) -> tuple[RegionalDFNConfig, ...]:
    """Build regional DFN configs for one case."""
    configs = []
    for name, fraction in area_fractions.items():
        configs.append(
            RegionalDFNConfig(
                name=str(name),
                area_fraction=float(fraction),
                parameter_multipliers=dict(case.parameter_multipliers_by_region.get(name, {})),
            )
        )
    return tuple(configs)


def run_regional_coupled_aging_workflow(
    spec: RegionalCoupledAgingWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run regional coupled-aging sections and write standard artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        WORKFLOW_ID,
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    params_fn = load_params(spec.cell)
    nominal_capacity_ah = _resolve_nominal_capacity(spec, params_fn)
    datasets = _resolve_datasets(spec.datasets, workspace_root)

    feature_parity = build_feature_parity_table()
    feature_parity_path = context.artifacts_dir / "feature_parity.csv"
    feature_parity.to_csv(feature_parity_path, index=False)
    artifact_paths: dict[str, Path] = {"feature_parity": feature_parity_path}

    reduced_result = _run_reduced_network_section(spec, nominal_capacity_ah, context)
    artifact_paths.update(reduced_result["artifact_paths"])

    transient_result = _run_transient_dfn_section(spec, params_fn, context)
    artifact_paths.update(transient_result["artifact_paths"])

    lifecycle_result = _run_lifecycle_section(spec, params_fn, nominal_capacity_ah, context)
    artifact_paths.update(lifecycle_result["artifact_paths"])

    datasets_path = context.artifacts_dir / "datasets.csv"
    pd.DataFrame(datasets).to_csv(datasets_path, index=False)
    artifact_paths["datasets"] = datasets_path

    metrics = _build_metrics(reduced_result, transient_result, lifecycle_result)
    metrics_path = context.run_dir / "metrics.csv"
    metrics.to_csv(metrics_path, index=False)
    artifact_paths["metrics"] = metrics_path
    manifest_path = _write_artifact_manifest(context, artifact_paths)
    artifact_paths["artifact_manifest"] = manifest_path
    excel_path = _export_excel(context, reduced_result, transient_result, lifecycle_result, feature_parity)
    artifact_paths["excel"] = excel_path

    return {
        "spec": spec,
        "context": context,
        "feature_parity": feature_parity,
        "datasets": datasets,
        "reduced_network": reduced_result,
        "transient_dfn": transient_result,
        "lifecycle": lifecycle_result,
        "metrics": metrics,
        "metrics_path": metrics_path,
        "artifact_paths": artifact_paths,
    }


def _run_reduced_network_section(
    spec: RegionalCoupledAgingWorkflowSpec,
    nominal_capacity_ah: float,
    context: WorkflowRunContext,
) -> dict[str, Any]:
    if not spec.reduced_network.enabled:
        return {"case_df": pd.DataFrame(), "summary_df": pd.DataFrame(), "sweep_df": pd.DataFrame(), "artifact_paths": {}}

    section = spec.reduced_network
    total_current_a = _resolve_current(section.total_current_a, section.current_c_rate, nominal_capacity_ah)
    rows = []
    summary_rows = []
    for case in section.cases:
        regions = build_area_scaled_regions(
            spec.area_fractions,
            nominal_capacity_ah=nominal_capacity_ah,
            base_ocv_v=section.base_ocv_v,
            base_resistance_ohm=section.base_resistance_ohm,
            resistance_multipliers=case.resistance_multipliers,
            capacity_retention=case.capacity_retention,
            current_bounds_a=case.current_bounds_a,
        )
        split = solve_parallel_current_split(regions, total_current_a)
        case_rows = split.rows()
        for row in case_rows:
            row["case"] = case.label
            row["current_share_pct"] = row["current_a"] / total_current_a * 100.0
            rows.append(row)
        summary_rows.append(
            {
                "case": case.label,
                "terminal_voltage_v": split.terminal_voltage_v,
                "total_capacity_ah": sum(row["capacity_ah"] or 0.0 for row in case_rows),
                "kcl_error_a": sum(row["current_a"] for row in case_rows) - total_current_a,
                "clamped_regions": ",".join(split.clamped_regions),
            }
        )

    sweep_rows = _build_blockage_sweep(spec, nominal_capacity_ah, total_current_a)
    case_df = pd.DataFrame(rows)
    summary_df = pd.DataFrame(summary_rows)
    sweep_df = pd.DataFrame(sweep_rows)
    paths = {
        "reduced_network_cases": context.artifacts_dir / "reduced_network_cases.csv",
        "reduced_network_summary": context.artifacts_dir / "reduced_network_summary.csv",
        "reduced_network_sweep": context.artifacts_dir / "reduced_network_sweep.csv",
    }
    case_df.to_csv(paths["reduced_network_cases"], index=False)
    summary_df.to_csv(paths["reduced_network_summary"], index=False)
    sweep_df.to_csv(paths["reduced_network_sweep"], index=False)
    return {"case_df": case_df, "summary_df": summary_df, "sweep_df": sweep_df, "artifact_paths": paths}


def _build_blockage_sweep(
    spec: RegionalCoupledAgingWorkflowSpec,
    nominal_capacity_ah: float,
    total_current_a: float,
) -> list[dict[str, Any]]:
    section = spec.reduced_network
    rows = []
    other_regions = [name for name in spec.area_fractions if name != section.local_blocked_region]
    for multiplier in section.sweep_multipliers:
        local_multipliers = {name: 1.0 for name in spec.area_fractions}
        local_multipliers[section.local_blocked_region] = float(multiplier)
        local = solve_parallel_current_split(
            build_area_scaled_regions(
                spec.area_fractions,
                nominal_capacity_ah=nominal_capacity_ah,
                base_ocv_v=section.base_ocv_v,
                base_resistance_ohm=section.base_resistance_ohm,
                resistance_multipliers=local_multipliers,
            ),
            total_current_a,
        )
        global_split = solve_parallel_current_split(
            build_area_scaled_regions(
                spec.area_fractions,
                nominal_capacity_ah=nominal_capacity_ah,
                base_ocv_v=section.base_ocv_v,
                base_resistance_ohm=section.base_resistance_ohm,
                resistance_multipliers=float(multiplier),
            ),
            total_current_a,
        )
        row = {
            "blockage_multiplier": float(multiplier),
            "local_terminal_voltage_v": local.terminal_voltage_v,
            "global_terminal_voltage_v": global_split.terminal_voltage_v,
            "local_minus_global_voltage_mV": (local.terminal_voltage_v - global_split.terminal_voltage_v) * 1000.0,
            "voltage_cutoff_v": section.voltage_cutoff_v,
            "blocked_region": section.local_blocked_region,
            "blocked_current_share_pct": local.region_currents_a[section.local_blocked_region] / total_current_a * 100.0,
        }
        for name in other_regions:
            row[f"{name}_current_share_pct"] = local.region_currents_a[name] / total_current_a * 100.0
        rows.append(row)
    return rows


def _run_transient_dfn_section(
    spec: RegionalCoupledAgingWorkflowSpec,
    params_fn,
    context: WorkflowRunContext,
) -> dict[str, Any]:
    if not spec.transient_dfn.enabled:
        return {"cases": {}, "steps_df": pd.DataFrame(), "iterations_df": pd.DataFrame(), "artifact_paths": {}}

    section = spec.transient_dfn
    nominal_capacity_ah = _resolve_nominal_capacity(spec, params_fn)
    total_current_a = _resolve_current(section.total_current_a, section.current_c_rate, nominal_capacity_ah)
    case_results = {}
    step_frames = []
    iteration_frames = []
    paths: dict[str, Path] = {}
    for case in spec.regional_cases:
        configs = build_region_configs(spec.area_fractions, case)
        result = run_regional_dfn_coupling(
            _fresh_parameter_values(params_fn, spec),
            configs,
            total_current_a=total_current_a,
            duration_s=section.duration_s,
            macro_step_s=section.macro_step_s,
            initial_soc=section.initial_soc,
            model_options=spec.model_options,
            var_pts=spec.var_pts,
            max_iterations=section.max_iterations,
            relaxation=section.relaxation,
        )
        steps = pd.DataFrame(result.steps()).assign(case=case.label)
        iterations = pd.DataFrame(result.iterations()).assign(case=case.label)
        step_frames.append(steps)
        iteration_frames.append(iterations)
        case_results[case.label] = result
        paths[f"transient_{case.label}_steps"] = context.artifacts_dir / f"transient_{case.label}_steps.csv"
        paths[f"transient_{case.label}_iterations"] = context.artifacts_dir / f"transient_{case.label}_iterations.csv"
        steps.to_csv(paths[f"transient_{case.label}_steps"], index=False)
        iterations.to_csv(paths[f"transient_{case.label}_iterations"], index=False)

    steps_df = pd.concat(step_frames, ignore_index=True) if step_frames else pd.DataFrame()
    iterations_df = pd.concat(iteration_frames, ignore_index=True) if iteration_frames else pd.DataFrame()
    steps_path = context.artifacts_dir / "transient_dfn_steps.csv"
    iterations_path = context.artifacts_dir / "transient_dfn_iterations.csv"
    steps_df.to_csv(steps_path, index=False)
    iterations_df.to_csv(iterations_path, index=False)
    paths["transient_dfn_steps"] = steps_path
    paths["transient_dfn_iterations"] = iterations_path
    return {"cases": case_results, "steps_df": steps_df, "iterations_df": iterations_df, "artifact_paths": paths}


def _run_lifecycle_section(
    spec: RegionalCoupledAgingWorkflowSpec,
    params_fn,
    nominal_capacity_ah: float,
    context: WorkflowRunContext,
) -> dict[str, Any]:
    if not spec.lifecycle.enabled:
        return {
            "cases": {},
            "homogeneous": None,
            "steps_df": pd.DataFrame(),
            "cycles_df": pd.DataFrame(),
            "degradation_df": pd.DataFrame(),
            "iterations_df": pd.DataFrame(),
            "artifact_paths": {},
        }

    section = spec.lifecycle
    discharge_power_w = _resolve_power(section.discharge_power_w, section.discharge_p_rate, nominal_capacity_ah, spec.nominal_voltage_v)
    paths: dict[str, Path] = {}
    homogeneous = None
    if section.run_homogeneous_baseline:
        homogeneous = run_homogeneous_dfn_power_cycles(
            _fresh_parameter_values(params_fn, spec),
            discharge_power_w=discharge_power_w,
            charge_power_w=section.charge_power_w,
            cycles=section.cycles,
            rest_s=section.rest_s,
            output_period_s=section.macro_step_s,
            initial_soc=section.initial_soc,
            lower_cutoff_v=section.lower_cutoff_v,
            upper_cutoff_v=section.upper_cutoff_v,
            equivalent_cycle_factor=section.equivalent_cycle_factor,
            model_options=spec.model_options,
            var_pts=spec.var_pts,
        )

    case_results = {}
    step_frames = []
    cycle_frames = []
    degradation_frames = []
    iteration_frames = []
    for case in spec.regional_cases:
        configs = build_region_configs(spec.area_fractions, case)
        parameter_values_by_region = {
            config.name: _fresh_parameter_values(params_fn, spec) for config in configs
        }
        result = run_regional_dfn_power_cycles(
            parameter_values_by_region,
            configs,
            discharge_power_w=discharge_power_w,
            charge_power_w=section.charge_power_w,
            cycles=section.cycles,
            rest_s=section.rest_s,
            macro_step_s=section.macro_step_s,
            maximum_macro_step_s=section.maximum_macro_step_s,
            initial_soc=section.initial_soc,
            lower_cutoff_v=section.lower_cutoff_v,
            upper_cutoff_v=section.upper_cutoff_v,
            equivalent_cycle_factor=section.equivalent_cycle_factor,
            nominal_voltage_v=spec.nominal_voltage_v,
            model_options=spec.model_options,
            var_pts=spec.var_pts,
            max_segment_duration_s=section.max_segment_duration_s,
        )
        step_frames.append(pd.DataFrame(result.steps()).assign(case=case.label))
        cycle_frames.append(pd.DataFrame(result.cycles()).assign(case=case.label))
        degradation_frames.append(pd.DataFrame(result.degradation()).assign(case=case.label))
        iteration_frames.append(pd.DataFrame(result.iterations()).assign(case=case.label))
        case_results[case.label] = result

    steps_df = pd.concat(step_frames, ignore_index=True) if step_frames else pd.DataFrame()
    cycles_df = pd.concat(cycle_frames, ignore_index=True) if cycle_frames else pd.DataFrame()
    degradation_df = pd.concat(degradation_frames, ignore_index=True) if degradation_frames else pd.DataFrame()
    iterations_df = pd.concat(iteration_frames, ignore_index=True) if iteration_frames else pd.DataFrame()
    for name, frame in (
        ("lifecycle_steps", steps_df),
        ("lifecycle_cycles", cycles_df),
        ("lifecycle_degradation", degradation_df),
        ("lifecycle_iterations", iterations_df),
    ):
        paths[name] = context.artifacts_dir / f"{name}.csv"
        frame.to_csv(paths[name], index=False)
    if homogeneous is not None:
        homogeneous_cycles = pd.DataFrame(homogeneous.cycles()).assign(case="homogeneous")
        paths["homogeneous_cycles"] = context.artifacts_dir / "homogeneous_cycles.csv"
        homogeneous_cycles.to_csv(paths["homogeneous_cycles"], index=False)
    return {
        "cases": case_results,
        "homogeneous": homogeneous,
        "steps_df": steps_df,
        "cycles_df": cycles_df,
        "degradation_df": degradation_df,
        "iterations_df": iterations_df,
        "artifact_paths": paths,
    }


def _build_metrics(reduced_result, transient_result, lifecycle_result) -> pd.DataFrame:
    rows = []
    reduced_summary = reduced_result["summary_df"]
    if not reduced_summary.empty:
        rows.append({"section": "reduced_network", "rows": int(len(reduced_result["case_df"]))})
        for _, row in reduced_summary.iterrows():
            rows.append(
                {
                    "section": "reduced_network_case",
                    "case": row["case"],
                    "terminal_voltage_v": row["terminal_voltage_v"],
                    "kcl_error_a": row["kcl_error_a"],
                }
            )
    if not transient_result["steps_df"].empty:
        rows.append({"section": "transient_dfn", "rows": int(len(transient_result["steps_df"]))})
    if not lifecycle_result["cycles_df"].empty:
        rows.append({"section": "lifecycle", "rows": int(len(lifecycle_result["cycles_df"]))})
    return pd.DataFrame(rows)


def _export_excel(
    context: WorkflowRunContext,
    reduced_result,
    transient_result,
    lifecycle_result,
    feature_parity: pd.DataFrame,
) -> Path:
    path = context.artifacts_dir / "regional_coupled_aging.xlsx"
    with pd.ExcelWriter(path) as writer:
        feature_parity.to_excel(writer, sheet_name="feature_parity", index=False)
        for sheet, frame in (
            ("reduced_cases", reduced_result["case_df"]),
            ("reduced_summary", reduced_result["summary_df"]),
            ("reduced_sweep", reduced_result["sweep_df"]),
            ("transient_steps", transient_result["steps_df"]),
            ("transient_iterations", transient_result["iterations_df"]),
            ("lifecycle_steps", lifecycle_result["steps_df"]),
            ("lifecycle_cycles", lifecycle_result["cycles_df"]),
            ("lifecycle_degradation", lifecycle_result["degradation_df"]),
        ):
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)
    return path


def _write_artifact_manifest(context: WorkflowRunContext, artifact_paths: Mapping[str, Path]) -> Path:
    rows = [
        {
            "name": name,
            "path": str(path),
            "relative_path": str(path.relative_to(context.run_dir)),
        }
        for name, path in sorted(artifact_paths.items())
    ]
    path = context.run_dir / "artifact_manifest.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _resolve_nominal_capacity(spec: RegionalCoupledAgingWorkflowSpec, params_fn) -> float:
    if spec.nominal_capacity_ah is not None:
        return float(spec.nominal_capacity_ah)
    return float(params_fn(1, 298.15)["Nominal cell capacity [A.h]"])


def _resolve_current(current_a: float | None, c_rate: float, nominal_capacity_ah: float) -> float:
    return float(current_a) if current_a is not None else float(c_rate) * float(nominal_capacity_ah)


def _resolve_power(power_w: float | None, p_rate: float, nominal_capacity_ah: float, nominal_voltage_v: float) -> float:
    return float(power_w) if power_w is not None else float(p_rate) * float(nominal_capacity_ah) * float(nominal_voltage_v)


def _fresh_parameter_values(params_fn, spec: RegionalCoupledAgingWorkflowSpec):
    params = pybamm.ParameterValues("OKane2022")
    params.update(
        params_fn(spec.aging_t_factor, temperature=spec.temperature_k),
        check_already_exists=False,
    )
    return params


def _resolve_datasets(queries: tuple[DatasetQuery, ...], workspace_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for query in queries:
        entries.extend(query.resolve(workspace_root))
    return entries


def _area_fractions_from_config(config: Mapping[str, Any]) -> Mapping[str, float]:
    if "area_fractions" in config:
        return {str(name): float(value) for name, value in dict(config["area_fractions"]).items()}
    regions = config.get("regions")
    if regions:
        return {str(item["name"]): float(item["area_fraction"]) for item in regions}
    return dict(DEFAULT_AREA_FRACTIONS)


def _regional_cases_from_config(config: Mapping[str, Any]) -> tuple[RegionalDFNCase, ...]:
    cases = config.get("regional_cases")
    if not cases:
        return RegionalCoupledAgingWorkflowSpec.__dataclass_fields__["regional_cases"].default
    return tuple(
        RegionalDFNCase(
            label=str(item["label"]),
            parameter_multipliers_by_region={
                str(region): dict(values)
                for region, values in dict(item.get("parameter_multipliers_by_region", {})).items()
            },
        )
        for item in cases
    )


def _reduced_network_from_config(config: Mapping[str, Any], mode_config: Mapping[str, Any]) -> ReducedNetworkSpec:
    section = dict(config.get("reduced_network", {}))
    section.update(mode_config.get("reduced_network", {}))
    cases = tuple(_reduced_case_from_config(item) for item in section.get("cases", ReducedNetworkSpec().cases))
    return ReducedNetworkSpec(
        enabled=bool(section.get("enabled", True)),
        base_ocv_v=float(section.get("base_ocv_v", 3.30)),
        base_resistance_ohm=float(section.get("base_resistance_ohm", 2.5e-4)),
        total_current_a=section.get("total_current_a"),
        current_c_rate=float(section.get("current_c_rate", 1.0)),
        voltage_cutoff_v=float(section.get("voltage_cutoff_v", 2.50)),
        local_blocked_region=str(section.get("local_blocked_region", "A_corner")),
        sweep_multipliers=tuple(float(value) for value in section.get("sweep_multipliers", ReducedNetworkSpec().sweep_multipliers)),
        cases=cases,
    )


def _transient_from_config(config: Mapping[str, Any], mode_config: Mapping[str, Any]) -> TransientDFNSpec:
    section = dict(config.get("transient_dfn", {}))
    section.update(mode_config.get("transient_dfn", {}))
    return TransientDFNSpec(
        enabled=bool(section.get("enabled", False)),
        total_current_a=section.get("total_current_a"),
        current_c_rate=float(section.get("current_c_rate", 0.25)),
        duration_s=float(section.get("duration_s", 600.0)),
        macro_step_s=float(section.get("macro_step_s", 60.0)),
        initial_soc=float(section.get("initial_soc", 0.5)),
        relaxation=float(section.get("relaxation", 0.7)),
        max_iterations=int(section.get("max_iterations", 12)),
    )


def _lifecycle_from_config(config: Mapping[str, Any], mode_config: Mapping[str, Any]) -> LifecycleSpec:
    section = dict(config.get("lifecycle", {}))
    section.update(mode_config.get("lifecycle", {}))
    return LifecycleSpec(
        enabled=bool(section.get("enabled", False)),
        run_homogeneous_baseline=bool(section.get("run_homogeneous_baseline", True)),
        discharge_power_w=section.get("discharge_power_w"),
        discharge_p_rate=float(section.get("discharge_p_rate", 0.25)),
        charge_power_w=section.get("charge_power_w"),
        cycles=int(section.get("cycles", 1)),
        equivalent_cycle_factor=float(section.get("equivalent_cycle_factor", 1.0)),
        rest_s=float(section.get("rest_s", 600.0)),
        macro_step_s=float(section.get("macro_step_s", 300.0)),
        maximum_macro_step_s=section.get("maximum_macro_step_s"),
        initial_soc=float(section.get("initial_soc", 1.0)),
        lower_cutoff_v=float(section.get("lower_cutoff_v", 2.5)),
        upper_cutoff_v=float(section.get("upper_cutoff_v", 3.65)),
        max_segment_duration_s=float(section.get("max_segment_duration_s", 6 * 3600.0)),
    )


def _dataset_queries_from_config(config: Mapping[str, Any]) -> tuple[DatasetQuery, ...]:
    queries = []
    for item in config.get("datasets", ()):
        query_config = dict(item)
        queries.append(
            DatasetQuery(
                cell=str(query_config.get("cell", config["cell"])),
                temperature_c=query_config.get("temperature_c"),
                rate=query_config.get("rate"),
                test_type=query_config.get("test_type"),
                kind=query_config.get("kind", "raw"),
                format=query_config.get("format"),
                path_contains=query_config.get("path_contains"),
                require_unique=query_config.get("require_unique", True),
            )
        )
    return tuple(queries)


def _reduced_case_from_config(item) -> ReducedNetworkCase:
    if isinstance(item, ReducedNetworkCase):
        return item
    item_config = dict(item)
    return ReducedNetworkCase(
        label=str(item_config["label"]),
        resistance_multipliers=item_config.get("resistance_multipliers", 1.0),
        capacity_retention=item_config.get("capacity_retention", 1.0),
        current_bounds_a=_bounds_from_mapping(item_config.get("current_bounds_a")),
    )


def _bounds_from_mapping(bounds):
    if bounds is None:
        return None
    return {
        str(name): (
            None if values[0] is None else float(values[0]),
            None if values[1] is None else float(values[1]),
        )
        for name, values in dict(bounds).items()
    }


__all__ = [
    "WORKFLOW_ID",
    "LifecycleSpec",
    "ReducedNetworkCase",
    "ReducedNetworkSpec",
    "RegionalCoupledAgingWorkflowSpec",
    "RegionalDFNCase",
    "TransientDFNSpec",
    "build_feature_parity_table",
    "build_region_configs",
    "run_regional_coupled_aging_workflow",
]
