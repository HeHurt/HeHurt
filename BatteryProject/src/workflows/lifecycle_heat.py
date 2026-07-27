"""Canonical lifecycle heat workflow used by the Chinese notebook template."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..analysis import get_discharge_capacity
from ..data_registry import HITHIUM_ROOT
from ..heat_calibration import (
    build_calibrated_parameter_loader,
    load_branch_entropy_curves,
)
from ..lifecycle_heat_reporting import (
    append_unconstrained_trend_extrapolation,
    build_cycle_heat_table,
    build_diagnostic_heat_table,
    build_mechanism_tables,
    export_lifecycle_heat_excel,
    make_wide_summary,
    save_lifecycle_heat_plots,
    write_artifact_manifest,
)
from ..notebook import load_params
from ..simulation_pulse_lifecycle import (
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    p_rate_to_power_w,
    run_pulse_lifecycle_scenarios,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context
from ..workflow_specs import DatasetQuery


STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


@dataclass(frozen=True)
class LifecycleHeatCondition:
    """One aging-mainline condition and its diagnostic P-rates."""

    temperature_c: float
    aging_p_rate: float
    diagnostic_p_rates: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.aging_p_rate <= 0:
            raise ValueError("aging_p_rate must be positive")
        if not self.diagnostic_p_rates or any(rate <= 0 for rate in self.diagnostic_p_rates):
            raise ValueError("diagnostic_p_rates must contain positive values")


@dataclass(frozen=True)
class ContactResistanceCase:
    """One independent contact-resistance branch."""

    label: str
    resistance_mohm: float

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("contact resistance label is required")
        if self.resistance_mohm < 0:
            raise ValueError("resistance_mohm must be non-negative")

    @property
    def resistance_ohm(self) -> float:
        """Return the resistance in ohm."""
        return self.resistance_mohm * 1.0e-3


@dataclass(frozen=True)
class EntropyCalibrationSpec:
    """Registry-backed entropy and hysteresis calibration settings."""

    query: DatasetQuery
    sample_label: str = "SOH95%"
    equilibrium_charge_weight: float = 0.0
    source_note: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.equilibrium_charge_weight <= 1:
            raise ValueError("equilibrium_charge_weight must be within [0, 1]")


@dataclass(frozen=True)
class LifecycleHeatWorkflowSpec:
    """Validated input contract for full lifecycle heat canonical notebooks."""

    cell: str
    conditions: tuple[LifecycleHeatCondition, ...]
    contact_resistances: tuple[ContactResistanceCase, ...]
    entropy: EntropyCalibrationSpec
    run_mode: str = "smoke"
    soh_targets_pct: tuple[float, ...] = (100.0,)
    total_cycles: int = 1
    aging_t_factor: int = 1
    cycles_per_block: int = 1
    nominal_voltage_v: float = 3.2
    nominal_capacity_ah: float | None = None
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    rest_minutes: float = 10.0
    period_minutes: float = 0.5
    solver_rtol: float = 1.0e-6
    solver_atol: float = 1.0e-6
    showprogress: bool = False
    return_solutions: bool = True
    stop_at_lowest_diagnostic_soh: bool = True
    return_partial_on_error: bool = True
    keep_only_last_cycle_solution: bool = True
    keep_only_last_capacity_check_solution: bool = True
    collect_cycle_heat: bool = False
    heat_correction: dict[str, Any] = field(default_factory=dict)
    output_name: str = "全生命周期产热"
    model_options: dict[str, Any] = field(default_factory=lambda: dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS))
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if not self.conditions:
            raise ValueError("at least one lifecycle heat condition is required")
        if not self.contact_resistances:
            raise ValueError("at least one contact resistance is required")
        if self.total_cycles <= 0 or self.aging_t_factor <= 0 or self.cycles_per_block <= 0:
            raise ValueError("total_cycles, aging_t_factor, and cycles_per_block must be positive")
        if not self.soh_targets_pct:
            raise ValueError("soh_targets_pct is required")
        if any(not 0 < target <= 100 for target in self.soh_targets_pct):
            raise ValueError("soh_targets_pct values must be within (0, 100]")
        if tuple(self.soh_targets_pct) != tuple(sorted(self.soh_targets_pct, reverse=True)):
            raise ValueError("soh_targets_pct must be unique and sorted descending")
        if len(set(self.soh_targets_pct)) != len(self.soh_targets_pct):
            raise ValueError("soh_targets_pct must be unique and sorted descending")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "LifecycleHeatWorkflowSpec":
        """Build a spec from the single CONFIG cell mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        entropy_config = dict(config["entropy"])
        entropy_query_config = dict(entropy_config["query"])
        entropy = EntropyCalibrationSpec(
            query=_dataset_query_from_mapping(entropy_query_config, default_cell=str(config["cell"])),
            sample_label=str(entropy_config.get("sample_label", "SOH95%")),
            equilibrium_charge_weight=float(entropy_config.get("equilibrium_charge_weight", 0.0)),
            source_note=str(entropy_config.get("source_note", "")),
        )
        conditions = tuple(
            LifecycleHeatCondition(
                temperature_c=float(item["temperature_c"]),
                aging_p_rate=float(item["aging_p_rate"]),
                diagnostic_p_rates=tuple(float(rate) for rate in item["diagnostic_p_rates"]),
            )
            for item in config.get("conditions", ())
        )
        contacts = tuple(
            ContactResistanceCase(
                label=str(item.get("label", f"R{float(item['resistance_mohm']):g}mOhm")),
                resistance_mohm=float(item["resistance_mohm"]),
            )
            for item in config.get("contact_resistances", ())
        )
        return cls(
            cell=str(config["cell"]),
            conditions=conditions,
            contact_resistances=contacts,
            entropy=entropy,
            run_mode=run_mode,
            soh_targets_pct=tuple(float(value) for value in option("soh_targets_pct", config.get("soh_targets_pct", (100,)))),
            total_cycles=int(option("total_cycles", 1)),
            aging_t_factor=int(option("aging_t_factor", 1)),
            cycles_per_block=int(option("cycles_per_block", 1)),
            nominal_voltage_v=float(config.get("nominal_voltage_v", 3.2)),
            nominal_capacity_ah=config.get("nominal_capacity_ah"),
            charge_cutoff_v=float(config.get("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(config.get("discharge_cutoff_v", 2.5)),
            rest_minutes=float(config.get("rest_minutes", 10.0)),
            period_minutes=float(config.get("period_minutes", 0.5)),
            solver_rtol=float(config.get("solver_rtol", 1.0e-6)),
            solver_atol=float(config.get("solver_atol", 1.0e-6)),
            showprogress=bool(option("showprogress", False)),
            return_solutions=bool(option("return_solutions", True)),
            stop_at_lowest_diagnostic_soh=bool(config.get("stop_at_lowest_diagnostic_soh", True)),
            return_partial_on_error=bool(config.get("return_partial_on_error", True)),
            keep_only_last_cycle_solution=bool(config.get("keep_only_last_cycle_solution", True)),
            keep_only_last_capacity_check_solution=bool(config.get("keep_only_last_capacity_check_solution", True)),
            collect_cycle_heat=bool(config.get("collect_cycle_heat", False)),
            heat_correction=dict(config.get("heat_correction", {})),
            output_name=str(config.get("output_name", "全生命周期产热")),
            model_options=dict(config.get("model_options", FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)

    @property
    def all_diagnostic_p_rates(self) -> tuple[float, ...]:
        """Return all configured diagnostic P-rates in stable order."""
        rates = {rate for condition in self.conditions for rate in condition.diagnostic_p_rates}
        return tuple(sorted(rates))


def _dataset_query_from_mapping(config: Mapping[str, Any], *, default_cell: str) -> DatasetQuery:
    return DatasetQuery(
        cell=str(config.get("cell", default_cell)),
        temperature_c=config.get("temperature_c"),
        rate=config.get("rate"),
        test_type=config.get("test_type"),
        kind=config.get("kind", "raw"),
        format=config.get("format"),
        path_contains=config.get("path_contains"),
        require_unique=config.get("require_unique", True),
    )


def resolve_entropy_file(spec: LifecycleHeatWorkflowSpec, *, workspace_root: Path = HITHIUM_ROOT) -> Path:
    """Resolve the entropy CSV through ``datasets.json``."""
    entries = spec.entropy.query.resolve(workspace_root)
    if len(entries) != 1:
        raise ValueError("entropy DatasetQuery must resolve to exactly one file")
    return Path(entries[0]["absolute_path"])


def build_feature_parity_table() -> pd.DataFrame:
    """Return the Batch 3 feature parity checklist for notebook display."""
    rows = [
        ("多电芯", "cell/params registry 参数化，默认 587Ah，可切 MIC_1175Ah", "保留"),
        ("多温度", "conditions[].temperature_c 支持 25/35/45°C 等矩阵", "保留"),
        ("多倍率", "aging_p_rate 与 diagnostic_p_rates 分离，支持统一老化路径诊断分支", "保留"),
        ("多接触电阻", "contact_resistances[] 独立主线、独立 Excel 与 artifact", "保留"),
        ("SOH 诊断", "diagnostic_soh_targets_pct 触发容量/产热分支，终态不回写老化主线", "保留"),
        ("entropy calibration", "DatasetQuery 定位 dU/dT CSV，支持 equilibrium_charge_weight", "保留"),
        ("checkpoint/partial recovery", "return_partial_on_error 与 run_status/pending targets 进入报告", "保留"),
        ("趋势外推", "缺失低 SOH 按末段线性/二次无约束外推并标记数据来源", "保留"),
        ("中文 Excel", "产热汇总、分项、老化机制、机制占比、配置表", "保留"),
        ("绘图/报告入口", "save_lifecycle_heat_plots 与 artifact manifest", "保留"),
        ("587Ah cycle/SOH 产热曲线", "collect_cycle_heat 可开启逐 block 产热点表", "保留"),
        ("DatasetQuery", "Notebook 不直接拼原始路径，数据解析统一走 datasets.json", "保留"),
        ("标准 output/runs", "create_run_context 写入 BatteryProject/output/runs/lifecycle_heat/<run_id>", "保留"),
    ]
    return pd.DataFrame(rows, columns=["功能", "canonical实现", "状态"])


def run_lifecycle_heat_workflow(
    spec: LifecycleHeatWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run lifecycle heat cases and write standard artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "lifecycle_heat",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    params_fn = load_params(spec.cell)
    nominal_capacity_ah = _resolve_nominal_capacity(spec, params_fn)
    entropy_file = resolve_entropy_file(spec, workspace_root=workspace_root)
    entropy_curves = load_branch_entropy_curves(entropy_file, sample_label=spec.entropy.sample_label)
    calibrated_params_fn = build_calibrated_parameter_loader(
        params_fn,
        spec.entropy.equilibrium_charge_weight,
    )

    cases: dict[str, dict[str, Any]] = {}
    detail_frames: list[pd.DataFrame] = []
    summary_frames: list[pd.DataFrame] = []
    mechanism_frames: list[pd.DataFrame] = []
    mechanism_share_frames: list[pd.DataFrame] = []
    cycle_heat_frames: list[pd.DataFrame] = []
    artifact_paths: list[Path] = []

    for condition in spec.conditions:
        temperature_k = condition.temperature_c + 273.15
        for contact in spec.contact_resistances:
            case_key = f"{condition.temperature_c:g}C_{condition.aging_p_rate:g}P_{contact.label}"
            case_dir = context.artifacts_dir / case_key
            case_dir.mkdir(parents=True, exist_ok=True)
            batch = _run_one_case(
                spec,
                condition,
                contact,
                nominal_capacity_ah=nominal_capacity_ah,
                temperature_k=temperature_k,
                get_hithium_params=_with_contact_resistance(calibrated_params_fn, contact.resistance_ohm),
            )
            bundle = batch["results"]["lifecycle_heat"]
            detail = build_diagnostic_heat_table(
                bundle,
                entropy_curves,
                contact_resistance_ohm=contact.resistance_ohm,
                temperature_c=condition.temperature_c,
                aging_p_rate=condition.aging_p_rate,
                contact_resistance_mohm=contact.resistance_mohm,
            )
            detail = append_unconstrained_trend_extrapolation(
                detail,
                spec.soh_targets_pct,
                condition.diagnostic_p_rates,
            )
            summary = make_wide_summary(detail, spec.soh_targets_pct, condition.diagnostic_p_rates)
            mechanism, mechanism_share = build_mechanism_tables(
                bundle,
                case_meta={
                    "temperature_c": condition.temperature_c,
                    "aging_p_rate": condition.aging_p_rate,
                    "contact_resistance_mohm": contact.resistance_mohm,
                },
            )
            cycle_heat = pd.DataFrame()
            if spec.collect_cycle_heat:
                cycle_heat = build_cycle_heat_table(
                    bundle,
                    entropy_curves,
                    contact_resistance_ohm=contact.resistance_ohm,
                    temperature_k=temperature_k,
                    temperature_c=condition.temperature_c,
                    p_rate=condition.aging_p_rate,
                    power_w=p_rate_to_power_w(condition.aging_p_rate, nominal_capacity_ah, spec.nominal_voltage_v),
                    aging_t_factor=spec.aging_t_factor,
                    cycles_per_block=spec.cycles_per_block,
                    label=f"{condition.temperature_c:g}°C {condition.aging_p_rate:g}P",
                    heat_correction=spec.heat_correction,
                )
            workbook = export_lifecycle_heat_excel(
                case_dir / f"{spec.cell}_{case_key}_全生命周期产热.xlsx",
                summary=summary,
                detail=detail,
                mechanism=mechanism,
                mechanism_share=mechanism_share,
                config_table=_config_table(spec, entropy_file, condition, contact, bundle),
                cycle_heat=cycle_heat,
            )
            plots = save_lifecycle_heat_plots(
                case_dir,
                summary=summary,
                detail=detail,
                mechanism_share=mechanism_share,
            )
            artifact_paths.extend([workbook, *plots])
            detail_frames.append(detail)
            summary_frames.append(summary)
            mechanism_frames.append(mechanism)
            mechanism_share_frames.append(mechanism_share)
            if not cycle_heat.empty:
                cycle_heat_frames.append(cycle_heat)
            cases[case_key] = {
                "batch": batch,
                "bundle": bundle,
                "detail": detail,
                "summary": summary,
                "mechanism": mechanism,
                "mechanism_share": mechanism_share,
                "cycle_heat": cycle_heat,
                "workbook": workbook,
                "plots": plots,
            }

    detail_all = _concat(detail_frames)
    summary_all = _concat(summary_frames)
    mechanism_all = _concat(mechanism_frames)
    mechanism_share_all = _concat(mechanism_share_frames)
    cycle_heat_all = _concat(cycle_heat_frames)
    metrics_path = context.run_dir / "metrics.csv"
    detail_all.to_csv(metrics_path, index=False)
    manifest = write_artifact_manifest(
        context.run_dir,
        {
            "workflow_id": context.workflow_id,
            "run_id": context.run_id,
            "entropy_file": str(entropy_file),
            "metrics": str(metrics_path),
            "artifacts": [str(path) for path in artifact_paths],
            "long_study_executed": spec.run_mode == "study",
        },
    )
    return {
        "spec": spec,
        "context": context,
        "feature_parity": build_feature_parity_table(),
        "entropy_file": entropy_file,
        "cases": cases,
        "summary": summary_all,
        "detail": detail_all,
        "mechanism": mechanism_all,
        "mechanism_share": mechanism_share_all,
        "cycle_heat": cycle_heat_all,
        "metrics_path": metrics_path,
        "artifact_manifest": manifest,
    }


def _run_one_case(
    spec: LifecycleHeatWorkflowSpec,
    condition: LifecycleHeatCondition,
    contact: ContactResistanceCase,
    *,
    nominal_capacity_ah: float,
    temperature_k: float,
    get_hithium_params,
) -> dict[str, Any]:
    runtime_config = {
        "total_cycles": spec.total_cycles,
        "use_block_acceleration": True,
        "cycles_per_block": spec.cycles_per_block,
        "aging_t_factor": spec.aging_t_factor,
        "conditioning_t_factor": 1,
        "capacity_check_interval_cycles": None,
        "capacity_check_at_start": False,
        "diagnostic_soh_targets_pct": spec.soh_targets_pct,
        "diagnostic_p_rates": condition.diagnostic_p_rates,
        "stop_at_lowest_diagnostic_soh": spec.stop_at_lowest_diagnostic_soh,
        "return_partial_on_error": spec.return_partial_on_error,
        "showprogress": spec.showprogress,
    }
    model_options = dict(spec.model_options)
    model_options["calculate heat source for isothermal models"] = "true"
    scenario = {
        "name": "lifecycle_heat",
        "display_name": f"{spec.cell} {condition.temperature_c:g}°C {condition.aging_p_rate:g}P {contact.label}",
        "pulse_p_rate": None,
        "enabled": True,
    }
    return run_pulse_lifecycle_scenarios(
        [scenario],
        runtime_config,
        model_options=model_options,
        var_pts=spec.var_pts,
        nominal_capacity_ah=nominal_capacity_ah,
        temperature_k=temperature_k,
        get_hithium_params=get_hithium_params,
        get_discharge_capacity_func=get_discharge_capacity,
        base_p_rate=condition.aging_p_rate,
        nominal_voltage_v=spec.nominal_voltage_v,
        charge_cutoff_v=spec.charge_cutoff_v,
        discharge_cutoff_v=spec.discharge_cutoff_v,
        rest_minutes=spec.rest_minutes,
        period_minutes=spec.period_minutes,
        solver_rtol=spec.solver_rtol,
        solver_atol=spec.solver_atol,
        keep_only_last_cycle_solution=spec.keep_only_last_cycle_solution,
        keep_only_last_capacity_check_solution=spec.keep_only_last_capacity_check_solution,
        return_solutions=spec.return_solutions,
    )


def _with_contact_resistance(parameter_loader, contact_resistance_ohm: float):
    def load_case_params(t_factor=1, temperature=298.15):
        values = dict(parameter_loader(t_factor, temperature=temperature))
        values["Contact resistance [Ohm]"] = float(contact_resistance_ohm)
        return values

    return load_case_params


def _resolve_nominal_capacity(spec: LifecycleHeatWorkflowSpec, params_fn) -> float:
    if spec.nominal_capacity_ah is not None:
        return float(spec.nominal_capacity_ah)
    base_params = params_fn(1, 298.15)
    return float(base_params["Nominal cell capacity [A.h]"])


def _config_table(
    spec: LifecycleHeatWorkflowSpec,
    entropy_file: Path,
    condition: LifecycleHeatCondition,
    contact: ContactResistanceCase,
    bundle: Mapping[str, Any],
) -> pd.DataFrame:
    rows = [
        ("电芯", spec.cell),
        ("运行模式", spec.run_mode),
        ("温度(°C)", condition.temperature_c),
        ("老化倍率(P)", condition.aging_p_rate),
        ("诊断倍率(P)", str(condition.diagnostic_p_rates)),
        ("接触电阻(mΩ)", contact.resistance_mohm),
        ("SOH目标", str(spec.soh_targets_pct)),
        ("老化加速因子", spec.aging_t_factor),
        ("每块仿真循环数", spec.cycles_per_block),
        ("总等效循环", spec.total_cycles),
        ("运行状态", bundle.get("run_status", "")),
        ("最后有效SOH(%)", bundle.get("last_valid_soh_pct", "")),
        ("未达到SOH目标", str(bundle.get("pending_diagnostic_soh_targets_pct", ""))),
        ("求解停止原因", bundle.get("failure_message", "")),
        ("熵热文件", str(entropy_file)),
        ("熵热样品", spec.entropy.sample_label),
        ("可逆热说明", spec.entropy.source_note),
        ("外推规则", "最后最多5个实际点二次趋势外推；无物理约束"),
        ("诊断老化处理", "t_factor=1独立分支，诊断终态不回写老化主线"),
    ]
    return pd.DataFrame(rows, columns=["配置项", "配置值"])


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame for frame in frames if frame is not None and not frame.empty]
    return pd.concat(usable, ignore_index=True) if usable else pd.DataFrame()
