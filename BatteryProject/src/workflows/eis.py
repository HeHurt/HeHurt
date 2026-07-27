"""Canonical EIS workflow used by the Chinese notebook template."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import pybamm

from ..data_registry import HITHIUM_ROOT
from ..notebook import load_params
from ..simulation_eis import (
    DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS,
    extract_frequency_slices,
    impedance_to_frame,
    run_lifecycle_eis_study,
    summarize_impedance_components,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context, write_json
from ..workflow_specs import DatasetQuery

STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


@dataclass(frozen=True)
class EisExperimentSpec:
    """Optional registry-backed EIS experimental dataset selector."""

    query: DatasetQuery
    loader: str = "registry_only"


@dataclass(frozen=True)
class LifecycleEisSpec:
    """Lifecycle-aging condition used before SOH-checkpoint EIS."""

    temperature_c: float = 25.0
    aging_t_factor: int = 50
    aging_cycles: int = 1
    aging_power_rate: float = 0.5
    reference_voltage_v: float = 3.2
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    target_soh_levels: tuple[float, ...] = (100.0,)
    measurement_mode: str = "fixed_soc"
    target_soc: float = 0.5
    rest_minutes: float = 30.0
    period_minutes: float = 10.0
    conditioning_period_minutes: float = 1.0

    def __post_init__(self) -> None:
        if self.aging_cycles <= 0 or self.aging_t_factor <= 0:
            raise ValueError("aging_cycles and aging_t_factor must be positive")
        if self.aging_power_rate <= 0:
            raise ValueError("aging_power_rate must be positive")
        if self.measurement_mode not in {"fixed_soc", "cycle_end"}:
            raise ValueError("measurement_mode must be 'fixed_soc' or 'cycle_end'")
        if not 0 <= self.target_soc <= 1:
            raise ValueError("target_soc must be between 0 and 1")
        if not self.target_soh_levels:
            raise ValueError("target_soh_levels is required")


@dataclass(frozen=True)
class EisWorkflowSpec:
    """Validated input contract for the impedance-analysis workflow."""

    cell: str
    run_mode: str = "smoke"
    output_name: str = "阻抗分析"
    base_temperature_c: float = 25.0
    base_soc: float = 0.5
    soc_sweep: tuple[float, ...] = (0.2, 0.5, 0.8)
    temperature_sweep_c: tuple[float, ...] = (0.0, 25.0, 45.0)
    quick_frequencies_hz: tuple[float, ...] = field(
        default_factory=lambda: tuple(np.logspace(-3, 4, 70).tolist())
    )
    lifecycle_frequencies_hz: tuple[float, ...] = field(
        default_factory=lambda: tuple(np.logspace(-3, 4, 60).tolist())
    )
    frequency_targets_hz: tuple[float, ...] = (1e3, 1e2, 10.0, 1.0, 0.1, 0.01)
    double_layer_capacity_f_m2: float = 0.2
    run_quick_eis: bool = True
    run_soc_sweep: bool = True
    run_temperature_sweep: bool = True
    run_lifecycle: bool = True
    lifecycle: LifecycleEisSpec = field(default_factory=LifecycleEisSpec)
    experiment: EisExperimentSpec | None = None
    model_options: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS)
    )
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if not 0 <= self.base_soc <= 1:
            raise ValueError("base_soc must be between 0 and 1")
        if any(soc < 0 or soc > 1 for soc in self.soc_sweep):
            raise ValueError("all soc_sweep values must be between 0 and 1")
        if any(value <= 0 for value in self.quick_frequencies_hz + self.lifecycle_frequencies_hz):
            raise ValueError("frequencies must be positive")
        if self.double_layer_capacity_f_m2 <= 0:
            raise ValueError("double_layer_capacity_f_m2 must be positive")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "EisWorkflowSpec":
        """Build a spec from the single CONFIG cell mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        modes = config.get("modes", {})
        mode_config = dict(modes.get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        lifecycle_config = dict(config.get("lifecycle", {}))
        lifecycle_mode_config = dict(mode_config.get("lifecycle", {}))
        lifecycle_config.update(lifecycle_mode_config)
        lifecycle = LifecycleEisSpec(
            temperature_c=float(lifecycle_config.get("temperature_c", config.get("base_temperature_c", 25.0))),
            aging_t_factor=int(lifecycle_config.get("aging_t_factor", 50)),
            aging_cycles=int(lifecycle_config.get("aging_cycles", 1)),
            aging_power_rate=float(lifecycle_config.get("aging_power_rate", 0.5)),
            reference_voltage_v=float(lifecycle_config.get("reference_voltage_v", 3.2)),
            charge_cutoff_v=float(lifecycle_config.get("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(lifecycle_config.get("discharge_cutoff_v", 2.5)),
            target_soh_levels=tuple(float(v) for v in lifecycle_config.get("target_soh_levels", [100])),
            measurement_mode=str(lifecycle_config.get("measurement_mode", "fixed_soc")),
            target_soc=float(lifecycle_config.get("target_soc", config.get("base_soc", 0.5))),
            rest_minutes=float(lifecycle_config.get("rest_minutes", 30.0)),
            period_minutes=float(lifecycle_config.get("period_minutes", 10.0)),
            conditioning_period_minutes=float(lifecycle_config.get("conditioning_period_minutes", 1.0)),
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
            experiment = EisExperimentSpec(
                query=query,
                loader=str(experiment_config.get("loader", "registry_only")),
            )
        return cls(
            cell=str(config["cell"]),
            run_mode=run_mode,
            output_name=str(config.get("output_name", "阻抗分析")),
            base_temperature_c=float(config.get("base_temperature_c", 25.0)),
            base_soc=float(config.get("base_soc", 0.5)),
            soc_sweep=tuple(float(v) for v in config.get("soc_sweep", [0.2, 0.5, 0.8])),
            temperature_sweep_c=tuple(float(v) for v in config.get("temperature_sweep_c", [0, 25, 45])),
            quick_frequencies_hz=tuple(float(v) for v in option("quick_frequencies_hz", np.logspace(-3, 4, 70))),
            lifecycle_frequencies_hz=tuple(float(v) for v in option("lifecycle_frequencies_hz", np.logspace(-3, 4, 60))),
            frequency_targets_hz=tuple(float(v) for v in config.get("frequency_targets_hz", [1e3, 1e2, 10, 1, 0.1, 0.01])),
            double_layer_capacity_f_m2=float(config.get("double_layer_capacity_f_m2", 0.2)),
            run_quick_eis=bool(option("run_quick_eis", True)),
            run_soc_sweep=bool(option("run_soc_sweep", True)),
            run_temperature_sweep=bool(option("run_temperature_sweep", True)),
            run_lifecycle=bool(option("run_lifecycle", True)),
            lifecycle=lifecycle,
            experiment=experiment,
            model_options=dict(config.get("model_options", DEFAULT_LIFECYCLE_EIS_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)


def _build_eis_simulation(
    get_hithium_params,
    *,
    temperature_k: float,
    model_options: Mapping[str, Any],
    var_pts: Mapping[str, int],
    double_layer_capacity_f_m2: float,
) -> pybamm.EISSimulation:
    parameter_values = pybamm.ParameterValues("OKane2022")
    parameter_values.update(get_hithium_params(1, temperature=temperature_k), check_already_exists=False)
    parameter_values["Negative electrode double-layer capacity [F.m-2]"] = double_layer_capacity_f_m2
    parameter_values["Positive electrode double-layer capacity [F.m-2]"] = double_layer_capacity_f_m2
    model = pybamm.lithium_ion.DFN(options=dict(model_options))
    return pybamm.EISSimulation(model, parameter_values=parameter_values, var_pts=dict(var_pts))


def _solution_to_rows(solution: Any, *, label: str, temperature_c: float, soc: float, section: str) -> list[dict[str, Any]]:
    impedance = np.asarray(solution.impedance, dtype=complex)
    frequencies = np.asarray(solution.frequencies, dtype=float)
    rows = []
    for frequency, z_value in zip(frequencies, impedance):
        rows.append(
            {
                "section": section,
                "label": label,
                "temperature_c": temperature_c,
                "soc": soc,
                "frequency_hz": float(frequency),
                "z_real_ohm": float(z_value.real),
                "z_imag_ohm": float(z_value.imag),
                "minus_z_im_ohm": float(-z_value.imag),
                "z_magnitude_ohm": float(abs(z_value)),
                "phase_deg": float(np.degrees(np.angle(z_value))),
            }
        )
    return rows


def run_quick_eis_sections(spec: EisWorkflowSpec, get_hithium_params) -> dict[str, pd.DataFrame]:
    """Run baseline, SOC sweep, and temperature sweep EIS sections."""
    frequencies = np.asarray(spec.quick_frequencies_hz, dtype=float)
    frames: dict[str, pd.DataFrame] = {}
    base_temperature_k = spec.base_temperature_c + 273.15

    if spec.run_quick_eis or spec.run_soc_sweep:
        base_sim = _build_eis_simulation(
            get_hithium_params,
            temperature_k=base_temperature_k,
            model_options=spec.model_options,
            var_pts=spec.var_pts,
            double_layer_capacity_f_m2=spec.double_layer_capacity_f_m2,
        )
        if spec.run_quick_eis:
            solution = base_sim.solve(frequencies, initial_soc=spec.base_soc)
            frames["quick"] = pd.DataFrame(
                _solution_to_rows(
                    solution,
                    label=f"{spec.base_temperature_c:g}°C SOC={spec.base_soc:.0%}",
                    temperature_c=spec.base_temperature_c,
                    soc=spec.base_soc,
                    section="quick",
                )
            )
        if spec.run_soc_sweep:
            rows = []
            for soc in spec.soc_sweep:
                solution = base_sim.solve(frequencies, initial_soc=soc)
                rows.extend(
                    _solution_to_rows(
                        solution,
                        label=f"SOC={soc:.0%}",
                        temperature_c=spec.base_temperature_c,
                        soc=soc,
                        section="soc_sweep",
                    )
                )
            frames["soc_sweep"] = pd.DataFrame(rows)

    if spec.run_temperature_sweep:
        rows = []
        for temperature_c in spec.temperature_sweep_c:
            sim = _build_eis_simulation(
                get_hithium_params,
                temperature_k=temperature_c + 273.15,
                model_options=spec.model_options,
                var_pts=spec.var_pts,
                double_layer_capacity_f_m2=spec.double_layer_capacity_f_m2,
            )
            solution = sim.solve(frequencies, initial_soc=spec.base_soc)
            rows.extend(
                _solution_to_rows(
                    solution,
                    label=f"{temperature_c:g}°C",
                    temperature_c=temperature_c,
                    soc=spec.base_soc,
                    section="temperature_sweep",
                )
            )
        frames["temperature_sweep"] = pd.DataFrame(rows)
    return frames


def prepare_eis_experiment(
    spec: EisWorkflowSpec,
    *,
    workspace_root: Path = HITHIUM_ROOT,
) -> list[dict[str, Any]]:
    """Resolve optional registry-backed experimental EIS inputs."""
    if spec.experiment is None:
        return []
    if spec.experiment.loader != "registry_only":
        raise ValueError(f"unsupported EIS experiment loader: {spec.experiment.loader}")
    return spec.experiment.query.resolve(workspace_root)


def run_eis_workflow(
    spec: EisWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the configured EIS workflow and write standard artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "eis",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    get_hithium_params = load_params(spec.cell)
    experiment_entries = prepare_eis_experiment(spec, workspace_root=workspace_root)
    quick_frames = run_quick_eis_sections(spec, get_hithium_params)
    quick_impedance_df = pd.concat(quick_frames.values(), ignore_index=True) if quick_frames else pd.DataFrame()

    lifecycle_result: dict[str, Any] | None = None
    frequency_slice_df = pd.DataFrame()
    if spec.run_lifecycle:
        lifecycle = spec.lifecycle
        lifecycle_result = run_lifecycle_eis_study(
            get_hithium_params=get_hithium_params,
            frequencies=np.asarray(spec.lifecycle_frequencies_hz, dtype=float),
            target_soh_levels=lifecycle.target_soh_levels,
            aging_cycles=lifecycle.aging_cycles,
            aging_power_rate=lifecycle.aging_power_rate,
            var_pts=spec.var_pts,
            temperature_k=lifecycle.temperature_c + 273.15,
            aging_t_factor=lifecycle.aging_t_factor,
            reference_voltage_v=lifecycle.reference_voltage_v,
            charge_cutoff_v=lifecycle.charge_cutoff_v,
            discharge_cutoff_v=lifecycle.discharge_cutoff_v,
            measurement_mode=lifecycle.measurement_mode,
            target_soc=lifecycle.target_soc,
            rest_minutes=lifecycle.rest_minutes,
            period_minutes=lifecycle.period_minutes,
            conditioning_period_minutes=lifecycle.conditioning_period_minutes,
            double_layer_capacity=spec.double_layer_capacity_f_m2,
            model_options=dict(spec.model_options),
        )
        frequency_slice_df = extract_frequency_slices(
            lifecycle_result["impedance_df"],
            spec.frequency_targets_hz,
        )

    artifact_paths: dict[str, Path] = {}
    if not quick_impedance_df.empty:
        artifact_paths["quick_impedance_csv"] = context.artifacts_dir / "quick_impedance.csv"
        quick_impedance_df.to_csv(artifact_paths["quick_impedance_csv"], index=False)
    if lifecycle_result is not None:
        for key, filename in (
            ("soh_df", "lifecycle_soh.csv"),
            ("checkpoints_df", "lifecycle_checkpoints.csv"),
            ("impedance_df", "lifecycle_impedance.csv"),
            ("components_df", "lifecycle_components.csv"),
        ):
            artifact_paths[filename.removesuffix(".csv")] = context.artifacts_dir / filename
            lifecycle_result[key].to_csv(artifact_paths[filename.removesuffix(".csv")], index=False)
        artifact_paths["frequency_slices"] = context.artifacts_dir / "frequency_slices.csv"
        frequency_slice_df.to_csv(artifact_paths["frequency_slices"], index=False)

    workbook_path = context.artifacts_dir / "eis_summary.xlsx"
    with pd.ExcelWriter(workbook_path) as writer:
        if not quick_impedance_df.empty:
            quick_impedance_df.to_excel(writer, sheet_name="quick_impedance", index=False)
        if lifecycle_result is not None:
            lifecycle_result["checkpoints_df"].to_excel(writer, sheet_name="checkpoints", index=False)
            lifecycle_result["components_df"].to_excel(writer, sheet_name="components", index=False)
            frequency_slice_df.to_excel(writer, sheet_name="frequency_slices", index=False)
    artifact_paths["summary_workbook"] = workbook_path

    metrics_rows = [
        {"section": "quick_impedance", "rows": int(len(quick_impedance_df))},
        {"section": "experiment_entries", "rows": int(len(experiment_entries))},
        {"section": "frequency_slices", "rows": int(len(frequency_slice_df))},
    ]
    if lifecycle_result is not None:
        metrics_rows.extend(
            [
                {"section": "lifecycle_soh", "rows": int(len(lifecycle_result["soh_df"]))},
                {"section": "lifecycle_checkpoints", "rows": int(len(lifecycle_result["checkpoints_df"]))},
                {"section": "lifecycle_components", "rows": int(len(lifecycle_result["components_df"]))},
            ]
        )
    metrics = pd.DataFrame(metrics_rows)
    metrics_path = context.run_dir / "metrics.csv"
    metrics.to_csv(metrics_path, index=False)
    artifact_manifest = {name: str(path) for name, path in artifact_paths.items()}
    write_json(context.run_dir / "artifacts.json", artifact_manifest)
    write_json(context.run_dir / "status.json", {"status": "complete", "metrics_path": str(metrics_path)})

    return {
        "spec": spec,
        "context": context,
        "metrics": metrics,
        "metrics_path": metrics_path,
        "quick_frames": quick_frames,
        "quick_impedance_df": quick_impedance_df,
        "lifecycle": lifecycle_result,
        "frequency_slice_df": frequency_slice_df,
        "experiment_entries": experiment_entries,
        "artifact_paths": artifact_paths,
        "summary_workbook_path": workbook_path,
    }


def summarize_quick_components(quick_impedance_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize quick EIS rows with the same proxy metrics used for lifecycle EIS."""
    rows = []
    for label, frame in quick_impedance_df.groupby("label", sort=False):
        solution = type(
            "EisFrameSolution",
            (),
            {
                "frequencies": frame["frequency_hz"].to_numpy(dtype=float),
                "impedance": (
                    frame["z_real_ohm"].to_numpy(dtype=float)
                    + 1j * frame["z_imag_ohm"].to_numpy(dtype=float)
                ),
            },
        )()
        row = summarize_impedance_components(solution, label=label, soh_pct=np.nan, cycle_number=0)
        row["section"] = str(frame["section"].iloc[0])
        row["temperature_c"] = float(frame["temperature_c"].iloc[0])
        row["soc"] = float(frame["soc"].iloc[0])
        rows.append(row)
    return pd.DataFrame(rows)


__all__ = [
    "EisExperimentSpec",
    "EisWorkflowSpec",
    "LifecycleEisSpec",
    "STANDARD_VAR_PTS",
    "impedance_to_frame",
    "prepare_eis_experiment",
    "run_eis_workflow",
    "run_quick_eis_sections",
    "summarize_quick_components",
]
