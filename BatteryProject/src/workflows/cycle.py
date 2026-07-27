"""Canonical cycle-aging workflow used by the Chinese notebook template."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pybamm

from ..analysis import get_discharge_capacity
from ..data_registry import HITHIUM_ROOT, scan
from ..exp_loader import load_cycling_folder
from ..lifecycle_exp import export_cycle_life_dat, load_lifecycle_dat
from ..notebook import load_params
from ..simulation_pulse_lifecycle import (
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    run_pulse_lifecycle_scenarios,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context
from ..workflow_specs import DatasetQuery

STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


@dataclass(frozen=True)
class CycleCondition:
    """One temperature/rate condition in a cycle-aging matrix."""

    temperature_c: float
    rate_p: float

    def __post_init__(self) -> None:
        if self.rate_p <= 0:
            raise ValueError("rate_p must be positive")


@dataclass(frozen=True)
class CycleExperimentSpec:
    """Optional registry-backed experimental dataset and preprocessing recipe."""

    query: DatasetQuery
    loader: str = "lifecycle_excel"
    sheet_name: str | None = None
    processed_name: str | None = None
    curve_type: str = "mean"
    retention_column: str = "capacity_retention_bol"


@dataclass(frozen=True)
class CycleWorkflowSpec:
    """Validated input contract for the cycle-aging workflow."""

    cell: str
    conditions: tuple[CycleCondition, ...]
    run_mode: str = "smoke"
    total_cycles: int = 1
    aging_t_factor: int = 1
    cycles_per_block: int | None = None
    nominal_voltage_v: float = 3.2
    nominal_capacity_ah: float | None = None
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    rest_minutes: float = 10.0
    period_minutes: float = 0.5
    showprogress: bool = False
    return_solutions: bool = True
    output_name: str = "循环老化"
    experiment: CycleExperimentSpec | None = None
    model_options: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS)
    )
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if not self.conditions:
            raise ValueError("at least one cycle condition is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.total_cycles <= 0 or self.aging_t_factor <= 0:
            raise ValueError("total_cycles and aging_t_factor must be positive")
        if self.cycles_per_block is not None and self.cycles_per_block <= 0:
            raise ValueError("cycles_per_block must be positive")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "CycleWorkflowSpec":
        """Build a spec from the single CONFIG cell mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        modes = config.get("modes", {})
        mode_config = dict(modes.get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        conditions = tuple(
            CycleCondition(float(item["temperature_c"]), float(item["rate_p"]))
            for item in config.get("conditions", ())
        )
        experiment = None
        experiment_config = config.get("experiment")
        if experiment_config:
            query_config = dict(experiment_config["query"])
            query = DatasetQuery(
                cell=str(query_config.get("cell", config["cell"])),
                temperature_c=query_config.get("temperature_c"),
                rate=query_config.get("rate"),
                test_type=query_config.get("test_type"),
                kind=query_config.get("kind", "raw"),
                format=query_config.get("format"),
                path_contains=query_config.get("path_contains"),
                require_unique=query_config.get("require_unique", True),
            )
            experiment = CycleExperimentSpec(
                query=query,
                loader=experiment_config.get("loader", "lifecycle_excel"),
                sheet_name=experiment_config.get("sheet_name"),
                processed_name=experiment_config.get("processed_name"),
                curve_type=experiment_config.get("curve_type", "mean"),
                retention_column=experiment_config.get(
                    "retention_column", "capacity_retention_bol"
                ),
            )
        return cls(
            cell=str(config["cell"]),
            conditions=conditions,
            run_mode=run_mode,
            total_cycles=int(option("total_cycles", 1)),
            aging_t_factor=int(option("aging_t_factor", 1)),
            cycles_per_block=option("cycles_per_block", None),
            nominal_voltage_v=float(config.get("nominal_voltage_v", 3.2)),
            nominal_capacity_ah=config.get("nominal_capacity_ah"),
            charge_cutoff_v=float(config.get("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(config.get("discharge_cutoff_v", 2.5)),
            rest_minutes=float(config.get("rest_minutes", 10.0)),
            period_minutes=float(config.get("period_minutes", 0.5)),
            showprogress=bool(option("showprogress", False)),
            return_solutions=bool(option("return_solutions", True)),
            output_name=str(config.get("output_name", "循环老化")),
            experiment=experiment,
            model_options=dict(config.get("model_options", DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)


def prepare_cycle_experiment(
    spec: CycleWorkflowSpec,
    *,
    workspace_root: Path = HITHIUM_ROOT,
) -> tuple[list[dict[str, Any]], Path | None]:
    """Resolve registry data and standardize only formats that need conversion."""
    if spec.experiment is None:
        return [], None
    experiment = spec.experiment
    entries = experiment.query.resolve(workspace_root)
    source_paths = [Path(entry["absolute_path"]) for entry in entries]
    if experiment.loader == "lifecycle_dat":
        if len(source_paths) != 1:
            raise ValueError("lifecycle_dat requires exactly one registry match")
        return load_lifecycle_dat(
            source_paths[0],
            curve_type=experiment.curve_type,
            retention_col=experiment.retention_column,
            drop_pre_bol=True,
        ), source_paths[0]
    if experiment.loader == "cycling_folder":
        experiment_data: list[dict[str, Any]] = []
        for folder in sorted({source.parent for source in source_paths}):
            experiment_data.extend(load_cycling_folder(str(folder)))
        return experiment_data, None
    if experiment.loader != "lifecycle_excel":
        raise ValueError(f"unsupported cycle experiment loader: {experiment.loader}")
    if len(source_paths) != 1:
        raise ValueError("lifecycle_excel requires exactly one registry match")
    if not experiment.sheet_name:
        raise ValueError("sheet_name is required for lifecycle_excel")
    source_path = source_paths[0]
    capacity_ah = spec.nominal_capacity_ah
    if capacity_ah is None:
        params_fn = load_params(spec.cell)
        capacity_ah = float(params_fn(1, 298.15)["Nominal cell capacity [A.h]"])
    processed_name = experiment.processed_name or f"{source_path.stem}_lifecycle.dat"
    processed_path = workspace_root / "data_processed" / spec.cell / "canonical_cycle" / processed_name
    export_cycle_life_dat(
        source_path,
        processed_path,
        sheet_name=experiment.sheet_name,
        nominal_capacity_ah=capacity_ah,
        nominal_energy_wh=capacity_ah * spec.nominal_voltage_v,
        rate_p=spec.conditions[0].rate_p,
    )
    scan(root=workspace_root)
    experiment_data = load_lifecycle_dat(
        processed_path,
        curve_type=experiment.curve_type,
        retention_col=experiment.retention_column,
        drop_pre_bol=True,
    )
    return experiment_data, processed_path


def run_cycle_workflow(
    spec: CycleWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run all configured cycle-aging conditions and write standard artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "cycle_aging",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    params_fn = load_params(spec.cell)
    base_params = params_fn(1, 298.15)
    nominal_capacity_ah = float(
        spec.nominal_capacity_ah or base_params["Nominal cell capacity [A.h]"]
    )
    runtime_config: dict[str, Any] = {
        "total_cycles": spec.total_cycles,
        "aging_t_factor": spec.aging_t_factor,
        "conditioning_t_factor": 1,
        "showprogress": spec.showprogress,
        "use_block_acceleration": spec.cycles_per_block is not None,
    }
    if spec.cycles_per_block is not None:
        runtime_config["cycles_per_block"] = spec.cycles_per_block
    scenarios = [{
        "name": "base_cycle",
        "display_name": "常规循环",
        "enabled": True,
        "pulse_p_rate": None,
    }]
    condition_frames: dict[str, pd.DataFrame] = {}
    batches: dict[str, dict[str, Any]] = {}
    analysis_solutions: list[Any] = []
    analysis_labels: list[str] = []
    analysis_params: list[pybamm.ParameterValues] = []
    for condition in spec.conditions:
        temperature_k = condition.temperature_c + 273.15
        label = f"{condition.temperature_c:g}°C {condition.rate_p:g}P"
        batch = run_pulse_lifecycle_scenarios(
            scenarios,
            runtime_config,
            model_options=spec.model_options,
            var_pts=spec.var_pts,
            nominal_capacity_ah=nominal_capacity_ah,
            temperature_k=temperature_k,
            get_hithium_params=params_fn,
            get_discharge_capacity_func=get_discharge_capacity,
            base_p_rate=condition.rate_p,
            nominal_voltage_v=spec.nominal_voltage_v,
            charge_cutoff_v=spec.charge_cutoff_v,
            discharge_cutoff_v=spec.discharge_cutoff_v,
            rest_minutes=spec.rest_minutes,
            period_minutes=spec.period_minutes,
            return_solutions=spec.return_solutions,
        )
        frame = batch["results"]["base_cycle"]["main_df"].copy()
        frame["label"] = label
        frame["temperature_c"] = condition.temperature_c
        frame["rate_p"] = condition.rate_p
        condition_frames[label] = frame
        batches[label] = batch
        final_solution = batch["results"]["base_cycle"].get("final_solution")
        if final_solution is not None:
            parameter_values = pybamm.ParameterValues("OKane2022")
            parameter_values.update(
                params_fn(spec.aging_t_factor, temperature=temperature_k),
                check_already_exists=False,
            )
            analysis_solutions.append(final_solution)
            analysis_labels.append(label)
            analysis_params.append(parameter_values)
    metrics = pd.concat(condition_frames.values(), ignore_index=True) if condition_frames else pd.DataFrame()
    metrics_path = context.run_dir / "metrics.csv"
    metrics.to_csv(metrics_path, index=False)
    experiment_data, processed_path = prepare_cycle_experiment(spec, workspace_root=workspace_root)
    return {
        "spec": spec,
        "context": context,
        "metrics": metrics,
        "metrics_path": metrics_path,
        "condition_frames": condition_frames,
        "batches": batches,
        "experiment_data": experiment_data,
        "processed_experiment_path": processed_path,
        "analysis_solutions": analysis_solutions,
        "analysis_labels": analysis_labels,
        "analysis_params": analysis_params,
        "reference_params": analysis_params[0] if analysis_params else None,
    }
