"""Canonical particle-size-distribution workflow runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import pybamm
from scipy.optimize import least_squares
from scipy.stats import norm

from ..data_registry import HITHIUM_ROOT
from ..notebook import load_params
from ..psd_workflow import (
    DEFAULT_MODEL_OPTIONS,
    DEFAULT_VAR_PTS,
    analyze_materials,
    build_full_curve_frame,
    build_material_summary_frame,
    build_step_curve_frame,
    run_material_comparison_study,
    summarize_study,
)
from ..workflow_runtime import WorkflowRunContext, create_run_context, write_json
from ..workflow_specs import DatasetQuery

STANDARD_VAR_PTS = dict(DEFAULT_VAR_PTS)
COMSOL_WEIGHTINGS = {"number": 3, "surface": 1, "volume": 0}


@dataclass(frozen=True)
class PsdDatasetSpec:
    """Registry-backed PSD input dataset selector."""

    query: DatasetQuery
    loader: str = "psd_csv"
    material_column: str | None = "material"
    diameter_column: str = "diameter_um"
    volume_column: str = "vol_pct"


@dataclass(frozen=True)
class ComsolDvSpec:
    """COMSOL histogram request from Dv percentiles."""

    name: str
    dv_percentiles_um: dict[int, float]
    n_bins: int = 11
    rp_min_um: float | None = None
    rp_max_um: float | None = None
    total_count: int = 100
    weighting: str = "surface"
    function_tag: str = "int1"
    parameter_prefix: str = ""

    def __post_init__(self) -> None:
        if self.weighting not in COMSOL_WEIGHTINGS:
            raise ValueError("weighting must be one of number, surface, volume")
        if not self.dv_percentiles_um:
            raise ValueError("dv_percentiles_um is required")
        if self.n_bins <= 0 or self.total_count <= 0:
            raise ValueError("n_bins and total_count must be positive")


@dataclass(frozen=True)
class ComsolRawSpec:
    """COMSOL histogram request from a raw diameter-volume distribution."""

    name: str
    diameters_um: tuple[float, ...]
    vol_pct: tuple[float, ...]
    n_bins: int | None = None
    rp_min_um: float | None = None
    rp_max_um: float | None = None
    total_count: int = 100
    trim_zeros: bool = True
    log_spacing: bool = True
    function_tag: str = "int2"
    function_name: str | None = None
    parameter_prefix: str = ""

    def __post_init__(self) -> None:
        if len(self.diameters_um) != len(self.vol_pct):
            raise ValueError("diameters_um and vol_pct must have the same length")
        if not self.diameters_um:
            raise ValueError("raw COMSOL PSD input cannot be empty")
        if self.n_bins is not None and self.n_bins <= 0:
            raise ValueError("n_bins must be positive")
        if self.total_count <= 0:
            raise ValueError("total_count must be positive")


@dataclass(frozen=True)
class PsdWorkflowSpec:
    """Validated input contract for the independent PSD workflow."""

    cell: str
    materials: dict[str, dict[str, Any]] = field(default_factory=dict)
    run_mode: str = "smoke"
    output_name: str = "粒径分布"
    selected_strategy: str = "bimodal"
    keep_percent: float = 99.0
    default_diameters_um: tuple[float, ...] | None = None
    run_simulation: bool = False
    run_comsol_conversion: bool = True
    temperature_k: float = 298.15
    nominal_capacity_ah: float | None = None
    nominal_voltage_v: float = 3.2
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    period_minutes: float = 0.5
    rest_minutes: float = 30.0
    cycles: int = 1
    initial_soc: float | None = 0.5
    negative_sd_rel: float = 0.3
    rate_list: tuple[float, ...] | None = (0.5,)
    power_w_list: tuple[float, ...] | None = None
    summary_cycle: int = 1
    datasets: tuple[PsdDatasetSpec, ...] = ()
    comsol_dv: tuple[ComsolDvSpec, ...] = ()
    comsol_raw: tuple[ComsolRawSpec, ...] = ()
    parameter_overrides: dict[str, Any] = field(default_factory=dict)
    model_options: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_MODEL_OPTIONS))
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.selected_strategy not in {"single", "bimodal"}:
            raise ValueError("selected_strategy must be 'single' or 'bimodal'")
        if self.keep_percent <= 0 or self.keep_percent > 100:
            raise ValueError("keep_percent must be in (0, 100]")
        if self.cycles <= 0 or self.summary_cycle <= 0:
            raise ValueError("cycles and summary_cycle must be positive")
        if self.rate_list is not None and self.power_w_list is not None:
            raise ValueError("provide only one of rate_list or power_w_list")
        if self.rate_list is None and self.power_w_list is None:
            raise ValueError("provide rate_list or power_w_list")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "PsdWorkflowSpec":
        """Build a PSD spec from the single notebook CONFIG mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        datasets = tuple(_dataset_spec_from_mapping(item, default_cell=str(config["cell"])) for item in config.get("datasets", ()))
        comsol_dv = tuple(_comsol_dv_from_mapping(item) for item in config.get("comsol_dv", ()))
        comsol_raw = tuple(_comsol_raw_from_mapping(item) for item in config.get("comsol_raw", ()))
        rate_list = option("rate_list", config.get("rate_list", [0.5]))
        power_w_list = option("power_w_list", config.get("power_w_list"))
        return cls(
            cell=str(config["cell"]),
            materials=dict(config.get("materials", {})),
            run_mode=run_mode,
            output_name=str(config.get("output_name", "粒径分布")),
            selected_strategy=str(config.get("selected_strategy", "bimodal")),
            keep_percent=float(config.get("keep_percent", 99.0)),
            default_diameters_um=_optional_float_tuple(config.get("default_diameters_um")),
            run_simulation=bool(option("run_simulation", False)),
            run_comsol_conversion=bool(option("run_comsol_conversion", True)),
            temperature_k=float(config.get("temperature_k", 298.15)),
            nominal_capacity_ah=_optional_float(config.get("nominal_capacity_ah")),
            nominal_voltage_v=float(config.get("nominal_voltage_v", 3.2)),
            charge_cutoff_v=float(config.get("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(config.get("discharge_cutoff_v", 2.5)),
            period_minutes=float(option("period_minutes", config.get("period_minutes", 0.5))),
            rest_minutes=float(option("rest_minutes", config.get("rest_minutes", 30.0))),
            cycles=int(option("cycles", config.get("cycles", 1))),
            initial_soc=_optional_float(config.get("initial_soc", 0.5)),
            negative_sd_rel=float(config.get("negative_sd_rel", 0.3)),
            rate_list=_optional_float_tuple(rate_list),
            power_w_list=_optional_float_tuple(power_w_list),
            summary_cycle=int(option("summary_cycle", config.get("summary_cycle", 1))),
            datasets=datasets,
            comsol_dv=comsol_dv,
            comsol_raw=comsol_raw,
            parameter_overrides=dict(config.get("parameter_overrides", {})),
            model_options=dict(config.get("model_options", DEFAULT_MODEL_OPTIONS)),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration snapshot."""
        return asdict(self)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_float_tuple(values: Any) -> tuple[float, ...] | None:
    if values is None:
        return None
    return tuple(float(value) for value in values)


def _dataset_spec_from_mapping(config: Mapping[str, Any], *, default_cell: str) -> PsdDatasetSpec:
    query_config = dict(config["query"])
    query = DatasetQuery(
        cell=str(query_config.get("cell", default_cell)),
        temperature_c=query_config.get("temperature_c"),
        rate=query_config.get("rate"),
        test_type=query_config.get("test_type"),
        kind=query_config.get("kind", "raw"),
        format=query_config.get("format"),
        path_contains=query_config.get("path_contains"),
        require_unique=query_config.get("require_unique", True),
    )
    return PsdDatasetSpec(
        query=query,
        loader=str(config.get("loader", "psd_csv")),
        material_column=config.get("material_column", "material"),
        diameter_column=str(config.get("diameter_column", "diameter_um")),
        volume_column=str(config.get("volume_column", "vol_pct")),
    )


def _comsol_dv_from_mapping(config: Mapping[str, Any]) -> ComsolDvSpec:
    return ComsolDvSpec(
        name=str(config["name"]),
        dv_percentiles_um={int(key): float(value) for key, value in config["dv_percentiles_um"].items()},
        n_bins=int(config.get("n_bins", 11)),
        rp_min_um=_optional_float(config.get("rp_min_um")),
        rp_max_um=_optional_float(config.get("rp_max_um")),
        total_count=int(config.get("total_count", 100)),
        weighting=str(config.get("weighting", "surface")),
        function_tag=str(config.get("function_tag", "int1")),
        parameter_prefix=str(config.get("parameter_prefix", "")),
    )


def _comsol_raw_from_mapping(config: Mapping[str, Any]) -> ComsolRawSpec:
    return ComsolRawSpec(
        name=str(config["name"]),
        diameters_um=tuple(float(value) for value in config["diameters_um"]),
        vol_pct=tuple(float(value) for value in config["vol_pct"]),
        n_bins=None if config.get("n_bins") is None else int(config["n_bins"]),
        rp_min_um=_optional_float(config.get("rp_min_um")),
        rp_max_um=_optional_float(config.get("rp_max_um")),
        total_count=int(config.get("total_count", 100)),
        trim_zeros=bool(config.get("trim_zeros", True)),
        log_spacing=bool(config.get("log_spacing", True)),
        function_tag=str(config.get("function_tag", "int2")),
        function_name=config.get("function_name"),
        parameter_prefix=str(config.get("parameter_prefix", "")),
    )


def load_psd_materials_from_registry(
    datasets: tuple[PsdDatasetSpec, ...],
    *,
    workspace_root: Path = HITHIUM_ROOT,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Resolve DatasetQuery inputs and load registered PSD CSV tables."""
    materials: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    for dataset in datasets:
        if dataset.loader != "psd_csv":
            raise ValueError(f"unsupported PSD dataset loader: {dataset.loader}")
        resolved_entries = dataset.query.resolve(workspace_root)
        entries.extend(resolved_entries)
        for entry in resolved_entries:
            source_path = Path(entry["absolute_path"])
            frame = pd.read_csv(source_path)
            if dataset.material_column and dataset.material_column in frame.columns:
                groups = frame.groupby(dataset.material_column, sort=False)
                for material_name, group in groups:
                    materials[str(material_name)] = _frame_to_material(group, dataset)
            else:
                materials[source_path.stem] = _frame_to_material(frame, dataset)
    return materials, entries


def _frame_to_material(frame: pd.DataFrame, dataset: PsdDatasetSpec) -> dict[str, Any]:
    if dataset.diameter_column not in frame.columns or dataset.volume_column not in frame.columns:
        raise ValueError(
            f"PSD CSV must contain {dataset.diameter_column!r} and {dataset.volume_column!r} columns"
        )
    return {
        "diameters_um": frame[dataset.diameter_column].to_numpy(dtype=float),
        "vol_pct": frame[dataset.volume_column].to_numpy(dtype=float),
    }


def fit_dv_to_comsol_histogram(spec: ComsolDvSpec) -> dict[str, Any]:
    """Fit Dv percentiles and return a COMSOL radius-count histogram."""
    percentiles = np.array(sorted(spec.dv_percentiles_um), dtype=float) / 100.0
    diameters = np.array([spec.dv_percentiles_um[int(p * 100)] for p in percentiles], dtype=float)
    mu0 = np.log(spec.dv_percentiles_um.get(50, float(np.median(diameters))))
    sigma0 = np.log(spec.dv_percentiles_um[90] / spec.dv_percentiles_um[10]) / (2 * 1.2816) if {10, 90} <= set(spec.dv_percentiles_um) else 0.5

    def residuals(params: np.ndarray) -> np.ndarray:
        mu_value, sigma_value = params
        return norm.cdf((np.log(diameters) - mu_value) / sigma_value) - percentiles

    result = least_squares(residuals, [mu0, sigma0], bounds=([-10, 0.01], [10, 5]))
    mu_vol, sigma_vol = (float(value) for value in result.x)
    mu_weighted = mu_vol - COMSOL_WEIGHTINGS[spec.weighting] * sigma_vol**2
    rp_min = spec.rp_min_um if spec.rp_min_um is not None else max(np.exp(mu_weighted - 2.33 * sigma_vol) / 2, 0.05)
    rp_max = spec.rp_max_um if spec.rp_max_um is not None else np.exp(mu_vol + 2.58 * sigma_vol) / 2
    bin_edges_r = np.linspace(rp_min, rp_max, spec.n_bins + 1)
    bin_edges_d = bin_edges_r * 2
    bin_centers_r = (bin_edges_r[:-1] + bin_edges_r[1:]) / 2
    cdf_at_edges = norm.cdf((np.log(bin_edges_d) - mu_weighted) / sigma_vol)
    bin_probs = np.diff(cdf_at_edges)
    range_total = cdf_at_edges[-1] - cdf_at_edges[0]
    bin_probs_norm = bin_probs / range_total if range_total > 1e-12 else np.ones(spec.n_bins) / spec.n_bins
    counts = _normalize_counts(bin_probs_norm, spec.total_count)
    histogram = [[round(float(radius), 3), int(count)] for radius, count in zip(bin_centers_r, counts)]
    return {
        "name": spec.name,
        "source": "dv_percentiles",
        "histogram": histogram,
        "rp_min_um": round(float(rp_min), 4),
        "rp_max_um": round(float(rp_max), 4),
        "mu_vol": mu_vol,
        "sigma_vol": sigma_vol,
        "weighting": spec.weighting,
        "n_bins": spec.n_bins,
        "total_count": int(sum(count for _, count in histogram)),
        "function_tag": spec.function_tag,
        "parameter_prefix": spec.parameter_prefix,
    }


def raw_psd_to_comsol_histogram(spec: ComsolRawSpec) -> dict[str, Any]:
    """Convert raw laser PSD diameter-volume data to a COMSOL radius-count histogram."""
    diameters = np.asarray(spec.diameters_um, dtype=float)
    volumes = np.asarray(spec.vol_pct, dtype=float)
    if spec.trim_zeros:
        nonzero = np.where(volumes > 0)[0]
        if len(nonzero) > 0:
            lo = max(0, int(nonzero[0]) - 1)
            hi = min(len(volumes) - 1, int(nonzero[-1]) + 1)
            diameters = diameters[lo:hi + 1]
            volumes = volumes[lo:hi + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        counts_raw = np.where(diameters > 0, volumes / diameters**3, 0.0)
    radii = diameters / 2.0
    positive = counts_raw > 0
    rp_min = spec.rp_min_um if spec.rp_min_um is not None else float(radii[positive].min() if np.any(positive) else radii.min())
    rp_max = spec.rp_max_um if spec.rp_max_um is not None else float(radii[positive].max() if np.any(positive) else radii.max())

    if spec.n_bins is None:
        mask = (radii >= rp_min) & (radii <= rp_max)
        bin_centers = radii[mask]
        binned_raw = counts_raw[mask]
    else:
        if spec.log_spacing and rp_min > 0:
            bin_edges = np.logspace(np.log10(rp_min), np.log10(rp_max), spec.n_bins + 1)
        else:
            bin_edges = np.linspace(rp_min, rp_max, spec.n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        binned_raw = np.array([
            np.trapz(
                np.interp(np.linspace(bin_edges[i], bin_edges[i + 1], 20), radii, counts_raw, left=0, right=0),
                np.linspace(bin_edges[i], bin_edges[i + 1], 20),
            )
            for i in range(spec.n_bins)
        ])
    counts = _normalize_counts(binned_raw, spec.total_count)
    histogram = [[round(float(radius), 4), int(count)] for radius, count in zip(bin_centers, counts)]
    return {
        "name": spec.name,
        "source": "raw_psd",
        "histogram": histogram,
        "rp_min_um": round(float(rp_min), 4),
        "rp_max_um": round(float(rp_max), 4),
        "n_bins": len(histogram),
        "total_count": int(sum(count for _, count in histogram)),
        "function_tag": spec.function_tag,
        "function_name": spec.function_name or f"f_hist_{spec.name}",
        "parameter_prefix": spec.parameter_prefix,
    }


def _normalize_counts(weights: np.ndarray, total_count: int) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    if weights.sum() > 0:
        counts = np.round(weights / weights.sum() * total_count).astype(int)
    else:
        counts = np.ones(len(weights), dtype=int)
    counts = np.maximum(counts, 0)
    threshold = weights.max() * 0.01 if weights.size else 0
    for index, value in enumerate(weights):
        if value > threshold and counts[index] == 0:
            counts[index] = 1
    if counts.sum() == 0 and counts.size:
        counts[int(np.argmax(weights))] = 1
    return counts


def comsol_histogram_to_java(result: Mapping[str, Any]) -> str:
    """Generate a COMSOL Java API snippet for one histogram result."""
    hist = result["histogram"]
    tag = result["function_tag"]
    prefix = result.get("parameter_prefix", "")
    function_name = result.get("function_name")
    lines = [
        f'model.param().set("{prefix}Rp_min", "{result["rp_min_um"]}[um]");',
        f'model.param().set("{prefix}Rp_max", "{result["rp_max_um"]}[um]");',
    ]
    if function_name:
        lines.extend(
            [
                f'model.func().create("{tag}", "Interpolation");',
                f'model.func("{tag}").set("funcname", "{function_name}");',
                f'model.func("{tag}").set("interp", "neighbor");',
                f'model.func("{tag}").setIndex("fununit", 1, 0);',
                f'model.func("{tag}").setIndex("argunit", "um", 0);',
            ]
        )
    entries = ", ".join("{" + f'"{radius}", "{count}"' + "}" for radius, count in hist)
    lines.append(f'model.func("{tag}").set("table", new String[][]{{{entries}}});')
    return "\n".join(lines)


def build_comsol_histogram_frame(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten COMSOL histogram results into a dataframe."""
    rows = []
    for result in results:
        for index, (radius_um, count) in enumerate(result["histogram"]):
            rows.append(
                {
                    "name": result["name"],
                    "source": result["source"],
                    "bin": index + 1,
                    "radius_um": radius_um,
                    "count": count,
                    "rp_min_um": result["rp_min_um"],
                    "rp_max_um": result["rp_max_um"],
                    "function_tag": result["function_tag"],
                    "weighting": result.get("weighting"),
                }
            )
    return pd.DataFrame(rows)


def run_psd_workflow(
    spec: PsdWorkflowSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run PSD fitting, optional PyBaMM comparison, and COMSOL conversion artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "psd",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    registered_materials, dataset_entries = load_psd_materials_from_registry(spec.datasets, workspace_root=workspace_root)
    materials = {**registered_materials, **spec.materials}
    if not materials:
        raise ValueError("PSD workflow requires materials or registered PSD datasets")

    material_analysis = analyze_materials(
        materials,
        default_diameters_um=spec.default_diameters_um,
        selected_strategy=spec.selected_strategy,
        keep_percent=spec.keep_percent,
    )
    material_summary = build_material_summary_frame(material_analysis)
    material_summary_path = context.artifacts_dir / "material_summary.csv"
    material_summary.to_csv(material_summary_path, index=False)

    case_summary = pd.DataFrame()
    step_curves = pd.DataFrame()
    full_curves = pd.DataFrame()
    study = None
    if spec.run_simulation:
        params_fn = load_params(spec.cell)
        if spec.parameter_overrides:
            base_params_fn = params_fn

            def params_fn(t_factor: int = 1, temperature: float = 298.15) -> dict[str, Any]:
                params = base_params_fn(t_factor, temperature).copy()
                params.update(spec.parameter_overrides)
                return params

        base_params = params_fn(1, spec.temperature_k)
        nominal_capacity_ah = float(spec.nominal_capacity_ah or base_params["Nominal cell capacity [A.h]"])
        design = _build_simulation_design(spec, nominal_capacity_ah)
        study = run_material_comparison_study(material_analysis, design, params_fn)
        case_summary = summarize_study(study, cycle_number=spec.summary_cycle)
        step_curves = build_step_curve_frame(study, cycle_number=spec.summary_cycle)
        full_curves = build_full_curve_frame(study)

    comsol_results: list[dict[str, Any]] = []
    if spec.run_comsol_conversion:
        comsol_results.extend(fit_dv_to_comsol_histogram(item) for item in spec.comsol_dv)
        comsol_results.extend(raw_psd_to_comsol_histogram(item) for item in spec.comsol_raw)
    comsol_histograms = build_comsol_histogram_frame(comsol_results)
    java_snippets = {result["name"]: comsol_histogram_to_java(result) for result in comsol_results}

    artifact_paths: dict[str, Path] = {"material_summary": material_summary_path}
    for name, frame in (
        ("case_summary", case_summary),
        ("step_curves", step_curves),
        ("full_curves", full_curves),
        ("comsol_histograms", comsol_histograms),
    ):
        if not frame.empty:
            path = context.artifacts_dir / f"{name}.csv"
            frame.to_csv(path, index=False)
            artifact_paths[name] = path
    if java_snippets:
        path = context.artifacts_dir / "comsol_java_snippets.txt"
        path.write_text("\n\n".join(f"// {name}\n{snippet}" for name, snippet in java_snippets.items()), encoding="utf-8")
        artifact_paths["comsol_java_snippets"] = path

    workbook_path = context.artifacts_dir / "psd_summary.xlsx"
    with pd.ExcelWriter(workbook_path) as writer:
        material_summary.to_excel(writer, sheet_name="material_summary", index=False)
        if not case_summary.empty:
            case_summary.to_excel(writer, sheet_name="case_summary", index=False)
        if not step_curves.empty:
            step_curves.to_excel(writer, sheet_name="step_curves", index=False)
        if not comsol_histograms.empty:
            comsol_histograms.to_excel(writer, sheet_name="comsol_histograms", index=False)
    artifact_paths["summary_workbook"] = workbook_path

    metrics = pd.DataFrame(
        [
            {"section": "materials", "rows": int(len(material_summary))},
            {"section": "dataset_entries", "rows": int(len(dataset_entries))},
            {"section": "case_summary", "rows": int(len(case_summary))},
            {"section": "step_curves", "rows": int(len(step_curves))},
            {"section": "full_curves", "rows": int(len(full_curves))},
            {"section": "comsol_histograms", "rows": int(len(comsol_histograms))},
        ]
    )
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
        "material_analysis": material_analysis,
        "material_summary": material_summary,
        "case_summary": case_summary,
        "step_curves": step_curves,
        "full_curves": full_curves,
        "study": study,
        "dataset_entries": dataset_entries,
        "comsol_results": comsol_results,
        "comsol_histograms": comsol_histograms,
        "java_snippets": java_snippets,
        "artifact_paths": artifact_paths,
        "summary_workbook_path": workbook_path,
    }


def _build_simulation_design(spec: PsdWorkflowSpec, nominal_capacity_ah: float) -> dict[str, Any]:
    design: dict[str, Any] = {
        "temperature_k": spec.temperature_k,
        "nominal_capacity_ah": nominal_capacity_ah,
        "nominal_voltage_v": spec.nominal_voltage_v,
        "charge_cutoff_v": spec.charge_cutoff_v,
        "discharge_cutoff_v": spec.discharge_cutoff_v,
        "period_minutes": spec.period_minutes,
        "rest_minutes": spec.rest_minutes,
        "cycles": spec.cycles,
        "initial_soc": spec.initial_soc,
        "negative_sd_rel": spec.negative_sd_rel,
        "var_pts": spec.var_pts,
        "solver": pybamm.IDAKLUSolver(),
        "model_options": spec.model_options,
    }
    if spec.rate_list is not None:
        design["rate_list"] = list(spec.rate_list)
    if spec.power_w_list is not None:
        design["power_w_list"] = list(spec.power_w_list)
    return design


__all__ = [
    "COMSOL_WEIGHTINGS",
    "ComsolDvSpec",
    "ComsolRawSpec",
    "PsdDatasetSpec",
    "PsdWorkflowSpec",
    "STANDARD_VAR_PTS",
    "build_comsol_histogram_frame",
    "comsol_histogram_to_java",
    "fit_dv_to_comsol_histogram",
    "load_psd_materials_from_registry",
    "raw_psd_to_comsol_histogram",
    "run_psd_workflow",
]
