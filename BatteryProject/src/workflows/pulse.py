"""Canonical inserted-pulse workflow runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..analysis import get_discharge_capacity
from ..data_registry import HITHIUM_ROOT
from ..notebook import load_params
from ..simulation_pulse_lifecycle import (
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    prepare_pulse_lifecycle_scenarios,
    run_pulse_lifecycle_scenarios,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context
from ..workflow_specs import DatasetQuery

STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


@dataclass(frozen=True)
class PulseWorkflowSpec:
    """Validated input contract for the inserted-pulse lifecycle workflow."""

    cell: str
    scenarios: tuple[dict[str, Any], ...]
    run_mode: str = "smoke"
    total_cycles: int = 4
    cycles_per_block: int | None = 1
    aging_t_factor: int = 1
    conditioning_t_factor: int = 1
    nominal_capacity_ah: float | None = None
    nominal_voltage_v: float = 3.2
    base_p_rate: float = 0.25
    temperature_c: float = 25.0
    initial_soc: float | None = None
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    rest_minutes: float = 30.0
    period_minutes: float = 0.5
    capacity_check_interval_cycles: int | None = 500
    capacity_check_p_rate: float = 0.25
    capacity_check_at_start: bool = True
    adapt_pulse_windows_to_capacity: bool = True
    parallel: bool = False
    max_workers: int | None = 2
    return_solutions: bool = True
    showprogress: bool = False
    output_name: str = "插入脉冲"
    postprocess_adjustments: dict[str, dict[str, float]] = field(default_factory=dict)
    datasets: tuple[DatasetQuery, ...] = ()
    model_options: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS))
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if not self.scenarios:
            raise ValueError("at least one pulse scenario is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.total_cycles <= 0 or self.aging_t_factor <= 0 or self.base_p_rate <= 0:
            raise ValueError("total_cycles, aging_t_factor, and base_p_rate must be positive")
        if self.cycles_per_block is not None and self.cycles_per_block <= 0:
            raise ValueError("cycles_per_block must be positive")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "PulseWorkflowSpec":
        """Build a pulse workflow spec from the single notebook CONFIG mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        return cls(
            cell=str(config["cell"]),
            scenarios=tuple(dict(item) for item in config.get("scenarios", ())),
            run_mode=run_mode,
            total_cycles=int(option("total_cycles", 4)),
            cycles_per_block=option("cycles_per_block", 1),
            aging_t_factor=int(option("aging_t_factor", 1)),
            conditioning_t_factor=int(option("conditioning_t_factor", 1)),
            nominal_capacity_ah=config.get("nominal_capacity_ah"),
            nominal_voltage_v=float(config.get("nominal_voltage_v", 3.2)),
            base_p_rate=float(config.get("base_p_rate", 0.25)),
            temperature_c=float(config.get("temperature_c", 25.0)),
            initial_soc=config.get("initial_soc"),
            charge_cutoff_v=float(config.get("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(config.get("discharge_cutoff_v", 2.5)),
            rest_minutes=float(config.get("rest_minutes", 30.0)),
            period_minutes=float(config.get("period_minutes", 0.5)),
            capacity_check_interval_cycles=option("capacity_check_interval_cycles", 500),
            capacity_check_p_rate=float(config.get("capacity_check_p_rate", 0.25)),
            capacity_check_at_start=bool(config.get("capacity_check_at_start", True)),
            adapt_pulse_windows_to_capacity=bool(config.get("adapt_pulse_windows_to_capacity", True)),
            parallel=bool(option("parallel", False)),
            max_workers=option("max_workers", 2),
            return_solutions=bool(option("return_solutions", True)),
            showprogress=bool(option("showprogress", False)),
            output_name=str(config.get("output_name", "插入脉冲")),
            postprocess_adjustments=dict(config.get("postprocess_adjustments", {})),
            datasets=_dataset_queries_from_config(config),
            model_options=dict(config.get("model_options", DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)


def prepare_pulse_workflow(spec: PulseWorkflowSpec) -> dict[str, Any]:
    """Prepare inserted-pulse scenarios without running PyBaMM."""
    nominal_capacity_ah = _resolve_nominal_capacity(spec)
    return prepare_pulse_lifecycle_scenarios(
        spec.scenarios,
        nominal_capacity_ah=nominal_capacity_ah,
        base_p_rate=spec.base_p_rate,
        nominal_voltage_v=spec.nominal_voltage_v,
        charge_cutoff_v=spec.charge_cutoff_v,
        discharge_cutoff_v=spec.discharge_cutoff_v,
        rest_minutes=spec.rest_minutes,
        period_minutes=spec.period_minutes,
    )


def run_pulse_workflow(
    spec: PulseWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run inserted-pulse scenarios and write standard workflow artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context = create_run_context("inserted_pulse", spec.to_dict(), project_root=project_root, run_id=run_id)
    params_fn = load_params(spec.cell)
    nominal_capacity_ah = _resolve_nominal_capacity(spec)
    runtime_config = {
        "total_cycles": spec.total_cycles,
        "cycles_per_block": spec.cycles_per_block,
        "aging_t_factor": spec.aging_t_factor,
        "conditioning_t_factor": spec.conditioning_t_factor,
        "showprogress": spec.showprogress,
        "capacity_check_interval_cycles": spec.capacity_check_interval_cycles,
        "capacity_check_p_rate": spec.capacity_check_p_rate,
        "capacity_check_at_start": spec.capacity_check_at_start,
        "adapt_pulse_windows_to_capacity": spec.adapt_pulse_windows_to_capacity,
        "use_block_acceleration": spec.cycles_per_block is not None,
    }
    prepared = prepare_pulse_workflow(spec)
    bundle = run_pulse_lifecycle_scenarios(
        scenarios=spec.scenarios,
        runtime_config=runtime_config,
        model_options=spec.model_options,
        var_pts=spec.var_pts,
        nominal_capacity_ah=nominal_capacity_ah,
        temperature_k=spec.temperature_c + 273.15,
        get_hithium_params=params_fn,
        get_discharge_capacity_func=get_discharge_capacity,
        base_p_rate=spec.base_p_rate,
        nominal_voltage_v=spec.nominal_voltage_v,
        charge_cutoff_v=spec.charge_cutoff_v,
        discharge_cutoff_v=spec.discharge_cutoff_v,
        rest_minutes=spec.rest_minutes,
        period_minutes=spec.period_minutes,
        initial_soc=spec.initial_soc,
        parallel=spec.parallel,
        max_workers=spec.max_workers,
        keep_only_last_cycle_solution=True,
        keep_only_last_capacity_check_solution=True,
        return_solutions=spec.return_solutions,
    )
    summary_df = bundle["summary_df"].sort_values("scenario").reset_index(drop=True)
    capacity_check_df = bundle.get("capacity_check_df", pd.DataFrame())
    metrics_df = capacity_check_df.copy() if not capacity_check_df.empty else summary_df.copy()
    datasets = _resolve_datasets(spec.datasets, workspace_root)
    artifact_paths = _write_common_tables(context, prepared["scenario_table"], summary_df, metrics_df, datasets)
    capacity_path = context.artifacts_dir / "capacity_check.csv"
    capacity_check_df.to_csv(capacity_path, index=False)
    artifact_paths["capacity_check"] = capacity_path
    excel_path = context.artifacts_dir / "pulse_results.xlsx"
    _export_pulse_excel(excel_path, summary_df, capacity_check_df, bundle["results"])
    artifact_paths["excel"] = excel_path
    return {
        "spec": spec,
        "context": context,
        "prepared": prepared,
        "bundle": bundle,
        "results": bundle["results"],
        "summary_df": summary_df,
        "capacity_check_df": capacity_check_df,
        "metrics": metrics_df,
        "datasets": datasets,
        "artifact_paths": artifact_paths,
    }


def build_adjusted_capacity_table(
    results: Mapping[str, dict[str, Any]],
    adjustments: Mapping[str, Mapping[str, float]] | None = None,
) -> pd.DataFrame:
    """Build raw and adjusted capacity-check table for plotting/export."""
    adjustments = adjustments or {}
    frames = []
    for name, bundle in results.items():
        capacity_df = bundle.get("capacity_check_df", pd.DataFrame()).copy()
        if capacity_df.empty:
            continue
        scenario = bundle.get("scenario", {})
        adjustment = adjustments.get(name, {})
        raw_capacity = pd.to_numeric(
            capacity_df["capacity_check_discharge_capacity_ah"],
            errors="coerce",
        )
        raw_retention = pd.to_numeric(capacity_df["capacity_retention"], errors="coerce")
        capacity_df["scenario_name"] = name
        capacity_df["scenario"] = scenario.get("display_name", name)
        capacity_df["capacity_check_discharge_capacity_ah_raw"] = raw_capacity
        capacity_df["capacity_retention_raw"] = raw_retention
        capacity_df["capacity_scale"] = float(adjustment.get("capacity_scale", 1.0))
        capacity_df["capacity_offset_ah"] = float(adjustment.get("capacity_offset_ah", 0.0))
        capacity_df["retention_scale"] = float(adjustment.get("retention_scale", 1.0))
        capacity_df["retention_offset"] = float(adjustment.get("retention_offset", 0.0))
        capacity_df["capacity_check_discharge_capacity_ah_adjusted"] = (
            raw_capacity * capacity_df["capacity_scale"] + capacity_df["capacity_offset_ah"]
        )
        capacity_df["capacity_retention_adjusted"] = (
            raw_retention * capacity_df["retention_scale"] + capacity_df["retention_offset"]
        )
        frames.append(capacity_df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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


def _resolve_datasets(queries: tuple[DatasetQuery, ...], workspace_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for query in queries:
        entries.extend(query.resolve(workspace_root))
    return entries


def _resolve_nominal_capacity(spec: PulseWorkflowSpec) -> float:
    if spec.nominal_capacity_ah is not None:
        return float(spec.nominal_capacity_ah)
    params_fn = load_params(spec.cell)
    return float(params_fn(1, 298.15)["Nominal cell capacity [A.h]"])


def _write_common_tables(
    context: WorkflowRunContext,
    scenario_table: pd.DataFrame,
    summary_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    datasets: list[dict[str, Any]],
) -> dict[str, Path]:
    paths = {
        "scenario_table": context.artifacts_dir / "scenario_table.csv",
        "summary": context.run_dir / "summary.csv",
        "metrics": context.run_dir / "metrics.csv",
        "datasets": context.artifacts_dir / "datasets.csv",
    }
    scenario_table.to_csv(paths["scenario_table"], index=False)
    summary_df.to_csv(paths["summary"], index=False)
    metrics_df.to_csv(paths["metrics"], index=False)
    pd.DataFrame(datasets).to_csv(paths["datasets"], index=False)
    return paths


def _export_pulse_excel(
    path: Path,
    summary_df: pd.DataFrame,
    capacity_check_df: pd.DataFrame,
    results: Mapping[str, dict[str, Any]],
) -> None:
    with pd.ExcelWriter(path) as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        capacity_check_df.to_excel(writer, sheet_name="capacity_check", index=False)
        for name, bundle in results.items():
            bundle.get("main_df", pd.DataFrame()).to_excel(writer, sheet_name=f"{name}_main"[:31], index=False)
            bundle.get("capacity_check_df", pd.DataFrame()).to_excel(
                writer,
                sheet_name=f"{name}_capacity"[:31],
                index=False,
            )
