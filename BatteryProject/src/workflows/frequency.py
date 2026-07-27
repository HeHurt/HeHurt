"""Canonical frequency-regulation workflow runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..data_registry import HITHIUM_ROOT
from ..notebook import load_params
from ..simulation_frequency import (
    EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE,
    build_frequency_current_profile,
    prepare_frequency_scenarios,
    run_frequency_scenarios,
    trim_current_profile,
)
from ..swelling_coupling import calculate_cycle_swelling
from ..workflow_runtime import WorkflowRunContext, create_run_context
from ..workflow_specs import DatasetQuery

STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
FREQUENCY_MODEL_OPTIONS = {
    "SEI": "ec reaction limited",
    "SEI porosity change": "true",
    "lithium plating": "irreversible",
    "lithium plating porosity change": "true",
    "particle mechanics": ("swelling and cracking", "swelling only"),
    "SEI on cracks": "true",
    "loss of active material": "stress-driven",
    "calculate discharge energy": "true",
    "contact resistance": "true",
    "open-circuit potential": ("current sigmoid", "current sigmoid"),
}


@dataclass(frozen=True)
class FrequencyWorkflowSpec:
    """Validated input contract for the frequency-regulation workflow."""

    cell: str
    scenarios: tuple[dict[str, Any], ...]
    run_mode: str = "smoke"
    real_days_total: int = 2
    day_acceleration_factor: int = 1
    rpt_every_real_days: int = 1
    current_a: float = 293.5
    nominal_capacity_ah: float | None = None
    temperature_c: float = 25.0
    initial_soc: float = 0.6
    use_equivalent_frequency: bool = True
    equivalent_pair_group_size: int = EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE
    parallel: bool = False
    max_workers: int | None = 2
    return_solutions: bool = True
    showprogress: bool = False
    output_name: str = "调频"
    datasets: tuple[DatasetQuery, ...] = ()
    model_options: dict[str, Any] = field(default_factory=lambda: dict(FREQUENCY_MODEL_OPTIONS))
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if not self.scenarios:
            raise ValueError("at least one frequency scenario is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.real_days_total <= 0 or self.day_acceleration_factor <= 0 or self.current_a <= 0:
            raise ValueError("real_days_total, day_acceleration_factor, and current_a must be positive")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "FrequencyWorkflowSpec":
        """Build a frequency workflow spec from the single notebook CONFIG mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))
        parallel_default = run_mode == "study"

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        return cls(
            cell=str(config["cell"]),
            scenarios=tuple(dict(item) for item in config.get("scenarios", ())),
            run_mode=run_mode,
            real_days_total=int(option("real_days_total", 2)),
            day_acceleration_factor=int(option("day_acceleration_factor", 1)),
            rpt_every_real_days=int(option("rpt_every_real_days", 1)),
            current_a=float(config.get("current_a", 293.5)),
            nominal_capacity_ah=config.get("nominal_capacity_ah"),
            temperature_c=float(config.get("temperature_c", 25.0)),
            initial_soc=float(config.get("initial_soc", 0.6)),
            use_equivalent_frequency=bool(config.get("use_equivalent_frequency", True)),
            equivalent_pair_group_size=int(
                config.get("equivalent_pair_group_size", EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE)
            ),
            parallel=bool(option("parallel", parallel_default)),
            max_workers=option("max_workers", 2),
            return_solutions=bool(option("return_solutions", not parallel_default)),
            showprogress=bool(option("showprogress", False)),
            output_name=str(config.get("output_name", "调频")),
            datasets=_dataset_queries_from_config(config),
            model_options=dict(config.get("model_options", FREQUENCY_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot."""
        return asdict(self)


def prepare_frequency_workflow(spec: FrequencyWorkflowSpec) -> dict[str, Any]:
    """Prepare frequency-regulation scenarios without running PyBaMM."""
    nominal_capacity_ah = _resolve_nominal_capacity(spec)
    return prepare_frequency_scenarios(
        spec.scenarios,
        current_a=spec.current_a,
        nominal_capacity_ah=nominal_capacity_ah,
    )


def build_frequency_waveform_preview(spec: FrequencyWorkflowSpec) -> dict[str, Any]:
    """Build raw and equivalent current profiles for the shortest pulse scenario."""
    prepared = prepare_frequency_workflow(spec)
    focus = min(prepared["scenarios"], key=lambda scenario: float(scenario["pulse_seconds"]))
    raw_pair_count = int(focus["pair_count_per_day"])
    raw_time_s, raw_current_a = build_frequency_current_profile(
        float(focus["pulse_seconds"]),
        raw_pair_count,
        spec.current_a,
    )
    equivalent_pair_count = max(1, -(-raw_pair_count // spec.equivalent_pair_group_size))
    equivalent_segment_seconds = (
        float(focus["charge_ah_per_day"]) / spec.current_a * 3600.0 / equivalent_pair_count
    )
    equivalent_time_s, equivalent_current_a = build_frequency_current_profile(
        equivalent_segment_seconds,
        equivalent_pair_count,
        spec.current_a,
    )
    raw_zoom_seconds = min(120.0, float(focus["waveform_hours_per_day"]) * 3600.0)
    equivalent_zoom_seconds = min(
        max(120.0, equivalent_segment_seconds * 1.2),
        float(focus["waveform_hours_per_day"]) * 3600.0,
    )
    return {
        "focus_scenario": focus,
        "raw_time_s": raw_time_s,
        "raw_current_a": raw_current_a,
        "equivalent_time_s": equivalent_time_s,
        "equivalent_current_a": equivalent_current_a,
        "raw_zoom": trim_current_profile(raw_time_s, raw_current_a, raw_zoom_seconds),
        "equivalent_zoom": trim_current_profile(
            equivalent_time_s,
            equivalent_current_a,
            equivalent_zoom_seconds,
        ),
        "comparison_df": pd.DataFrame(
            [
                {
                    "waveform": "raw pulses",
                    "segments_per_day": focus["total_pulses_per_day"],
                    "pair_count": raw_pair_count,
                    "seconds_per_segment": focus["pulse_seconds"],
                    "total_waveform_hours": focus["waveform_hours_per_day"],
                    "compression_ratio": 1.0,
                },
                {
                    "waveform": "equivalent segments",
                    "segments_per_day": equivalent_pair_count * 2,
                    "pair_count": equivalent_pair_count,
                    "seconds_per_segment": equivalent_segment_seconds,
                    "total_waveform_hours": focus["waveform_hours_per_day"],
                    "compression_ratio": focus["total_pulses_per_day"] / (equivalent_pair_count * 2),
                },
            ]
        ),
    }


def run_frequency_workflow(
    spec: FrequencyWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run frequency-regulation scenarios and write standard workflow artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context = create_run_context("frequency_regulation", spec.to_dict(), project_root=project_root, run_id=run_id)
    params_fn = load_params(spec.cell)
    nominal_capacity_ah = _resolve_nominal_capacity(spec)
    runtime_config = {
        "real_days_total": spec.real_days_total,
        "day_acceleration_factor": spec.day_acceleration_factor,
        "rpt_every_real_days": spec.rpt_every_real_days,
        "showprogress": spec.showprogress,
    }
    prepared = prepare_frequency_workflow(spec)
    bundle = run_frequency_scenarios(
        scenarios=spec.scenarios,
        runtime_config=runtime_config,
        model_options=spec.model_options,
        var_pts=spec.var_pts,
        current_a=spec.current_a,
        nominal_capacity_ah=nominal_capacity_ah,
        initial_soc=spec.initial_soc,
        temperature_k=spec.temperature_c + 273.15,
        get_hithium_params=params_fn,
        calculate_cycle_swelling_func=calculate_cycle_swelling,
        parallel=spec.parallel,
        max_workers=spec.max_workers,
        keep_only_last_cycle_solution=True,
        keep_only_last_rpt_solution=True,
        return_solutions=spec.return_solutions,
        use_equivalent_frequency=spec.use_equivalent_frequency,
    )
    summary_df = bundle["summary_df"].sort_values("scenario").reset_index(drop=True)
    metrics_df = _combine_result_frames(bundle["results"], "main_df")
    if metrics_df.empty:
        metrics_df = summary_df.copy()
    datasets = _resolve_datasets(spec.datasets, workspace_root)
    artifact_paths = _write_common_tables(context, prepared["scenario_table"], summary_df, metrics_df, datasets)
    rpt_path = context.artifacts_dir / "rpt.csv"
    _combine_result_frames(bundle["results"], "rpt_df").to_csv(rpt_path, index=False)
    artifact_paths["rpt"] = rpt_path
    excel_path = context.artifacts_dir / "frequency_results.xlsx"
    _export_frequency_excel(excel_path, summary_df, bundle["results"])
    artifact_paths["excel"] = excel_path
    return {
        "spec": spec,
        "context": context,
        "prepared": prepared,
        "bundle": bundle,
        "results": bundle["results"],
        "summary_df": summary_df,
        "metrics": metrics_df,
        "datasets": datasets,
        "artifact_paths": artifact_paths,
    }


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


def _resolve_nominal_capacity(spec: FrequencyWorkflowSpec) -> float:
    if spec.nominal_capacity_ah is not None:
        return float(spec.nominal_capacity_ah)
    params_fn = load_params(spec.cell)
    return float(params_fn(1, 298.15)["Nominal cell capacity [A.h]"])


def _combine_result_frames(results: Mapping[str, dict[str, Any]], frame_key: str) -> pd.DataFrame:
    frames = []
    for name, result in results.items():
        frame = result.get(frame_key, pd.DataFrame()).copy()
        if not frame.empty:
            frame["scenario_name"] = name
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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


def _export_frequency_excel(
    path: Path,
    summary_df: pd.DataFrame,
    results: Mapping[str, dict[str, Any]],
) -> None:
    with pd.ExcelWriter(path) as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        for name, bundle in results.items():
            bundle.get("main_df", pd.DataFrame()).to_excel(writer, sheet_name=f"{name}_main"[:31], index=False)
            bundle.get("rpt_df", pd.DataFrame()).to_excel(writer, sheet_name=f"{name}_rpt"[:31], index=False)
