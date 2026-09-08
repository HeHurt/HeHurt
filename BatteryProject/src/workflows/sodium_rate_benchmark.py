"""Headless sodium-ion rate benchmark workflow for measured CC curves."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import time
from typing import Callable, Iterable

import numpy as np
import pandas as pd
import pybamm

from ..analysis import calc_rrmse


_FILE_RE = re.compile(r"Para-(?P<rate>\d+(?:\.\d+)?)C-(?P<kind>DisChrg|Chrg)", re.IGNORECASE)
_TEMP_RE = re.compile(r"(?P<temp>[+-]?\d+)\s*℃")


@dataclass(frozen=True, order=True)
class SodiumRateCase:
    """One measured constant-current charge or discharge condition."""

    mode: str
    temperature_c: float
    rate_c: float
    data_path: Path = field(compare=False)

    @property
    def key(self) -> tuple[str, float, float]:
        """Return a stable result key: ``(mode, temperature_C, rate_C)``."""

        return self.mode, self.temperature_c, self.rate_c

    @property
    def label(self) -> str:
        """Return a compact human-readable condition label."""

        return f"{self.mode}_{self.temperature_c:+g}C_{self.rate_c:g}C"


@dataclass(frozen=True)
class SodiumBenchmarkSpec:
    """Configuration shared by all sodium-ion rate cases."""

    charge_cutoff_v: float = 3.3
    discharge_cutoff_v: float = 1.5
    period_minutes: float = 0.5
    charge_initial_soc: float = 0.0
    discharge_initial_soc: float = 1.0
    model_lower_cutoff_margin_v: float = 0.01
    var_pts: dict[str, int] = field(
        default_factory=lambda: {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
    )


@dataclass
class SodiumCaseResult:
    """Measured and simulated curves plus metrics for one condition."""

    case: SodiumRateCase
    status: str
    experiment: pd.DataFrame
    simulation: pd.DataFrame
    metrics: dict[str, object]
    solution: object | None = None
    error: str | None = None


def _parse_temperature_c(folder_name: str) -> float:
    match = _TEMP_RE.search(folder_name)
    if match is None:
        raise ValueError(f"无法从目录名解析温度: {folder_name}")
    return float(match.group("temp"))


def _parse_rate_and_mode(file_name: str) -> tuple[float, str]:
    match = _FILE_RE.search(file_name)
    if match is None:
        raise ValueError(f"无法从文件名解析倍率/方向: {file_name}")
    mode = "discharge" if match.group("kind").lower() == "dischrg" else "charge"
    return float(match.group("rate")), mode


def discover_sodium_rate_cases(data_root: Path | str) -> list[SodiumRateCase]:
    """Discover measured rate cases from the two standard sodium data folders."""

    data_root = Path(data_root)
    folders = (
        data_root / "3_倍充数据-0324更新",
        data_root / "4_倍放数据-0324更新",
    )
    cases: list[SodiumRateCase] = []
    for root in folders:
        if not root.is_dir():
            raise FileNotFoundError(f"实验数据目录不存在: {root}")
        for data_path in sorted(root.glob("*/*_wc_data.csv")):
            rate_c, mode = _parse_rate_and_mode(data_path.name)
            temperature_c = _parse_temperature_c(data_path.parent.name)
            cases.append(SodiumRateCase(mode, temperature_c, rate_c, data_path))

    cases.sort()
    duplicates: dict[tuple[str, float, float], list[Path]] = {}
    for case in cases:
        duplicates.setdefault(case.key, []).append(case.data_path)
    repeated = {key: paths for key, paths in duplicates.items() if len(paths) > 1}
    if repeated:
        details = "; ".join(f"{key}: {paths}" for key, paths in repeated.items())
        raise ValueError(f"发现重复实验条件: {details}")
    return cases


def load_sodium_rate_curve(case: SodiumRateCase) -> pd.DataFrame:
    """Load one measured CC curve and normalize capacity to start at zero."""

    raw = pd.read_csv(case.data_path)
    required = {"TimeS", "CurrA", "VoltV", "AccuCapAh"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"{case.data_path.name} 缺少列: {sorted(missing)}")

    frame = pd.DataFrame(
        {
            "time_s": pd.to_numeric(raw["TimeS"], errors="coerce"),
            "current_a": pd.to_numeric(raw["CurrA"], errors="coerce"),
            "voltage_v": pd.to_numeric(raw["VoltV"], errors="coerce"),
            "raw_capacity_ah": pd.to_numeric(raw["AccuCapAh"], errors="coerce"),
        }
    ).dropna()
    if frame.empty:
        raise ValueError(f"{case.data_path.name} 没有可用数值数据")
    frame["capacity_ah"] = (frame["raw_capacity_ah"] - frame["raw_capacity_ah"].iloc[0]).abs()
    frame = frame.sort_values("capacity_ah").drop_duplicates("capacity_ah").reset_index(drop=True)
    return frame[["time_s", "current_a", "voltage_v", "capacity_ah"]]


def build_sodium_rate_model() -> pybamm.BaseModel:
    """Build the DFN model used by the sodium-ion benchmark."""

    return pybamm.lithium_ion.DFN(
        {
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def _build_step(case: SodiumRateCase, current_a: float, spec: SodiumBenchmarkSpec) -> tuple[str, float]:
    if case.mode == "charge":
        step = (
            f"Charge at {current_a:.8g} A until {spec.charge_cutoff_v:g} V "
            f"({spec.period_minutes:g} minute period)"
        )
        return step, spec.charge_initial_soc
    if case.mode == "discharge":
        step = (
            f"Discharge at {current_a:.8g} A until {spec.discharge_cutoff_v:g} V "
            f"({spec.period_minutes:g} minute period)"
        )
        return step, spec.discharge_initial_soc
    raise ValueError(f"不支持的模式: {case.mode}")


def _curve_metrics(experiment: pd.DataFrame, simulation: pd.DataFrame) -> dict[str, object]:
    exp_capacity = experiment["capacity_ah"].to_numpy(dtype=float)
    exp_voltage = experiment["voltage_v"].to_numpy(dtype=float)
    sim_capacity = simulation["capacity_ah"].to_numpy(dtype=float)
    sim_voltage = simulation["voltage_v"].to_numpy(dtype=float)
    overlap_capacity = min(float(exp_capacity[-1]), float(sim_capacity[-1]))
    mask = exp_capacity <= overlap_capacity
    matched_exp_capacity = exp_capacity[mask]
    matched_exp_voltage = exp_voltage[mask]
    matched_sim_voltage = np.interp(matched_exp_capacity, sim_capacity, sim_voltage)
    rmse_v, rrmse = calc_rrmse(matched_exp_voltage, matched_sim_voltage)
    exp_capacity_ah = float(exp_capacity[-1])
    sim_capacity_ah = float(sim_capacity[-1])
    capacity_error_ah = sim_capacity_ah - exp_capacity_ah
    return {
        "exp_capacity_ah": exp_capacity_ah,
        "sim_capacity_ah": sim_capacity_ah,
        "capacity_error_ah": capacity_error_ah,
        "capacity_error_pct": 100 * capacity_error_ah / exp_capacity_ah,
        "overlap_capacity_ah": overlap_capacity,
        "matched_points": int(mask.sum()),
        "voltage_rmse_v": rmse_v,
        "voltage_rrmse_pct": 100 * rrmse,
        "exp_start_v": float(exp_voltage[0]),
        "sim_start_v": float(sim_voltage[0]),
        "exp_end_v": float(exp_voltage[-1]),
        "sim_end_v": float(sim_voltage[-1]),
    }


def run_sodium_rate_case(
    case: SodiumRateCase,
    get_hithium_params: Callable[..., dict],
    *,
    spec: SodiumBenchmarkSpec | None = None,
    solver: pybamm.BaseSolver | None = None,
    showprogress: bool = False,
) -> SodiumCaseResult:
    """Run one measured-matched sodium-ion CC case and calculate curve metrics."""

    spec = spec or SodiumBenchmarkSpec()
    experiment_curve = load_sodium_rate_curve(case)
    measured_current_a = float(experiment_curve["current_a"].abs().median())
    step, initial_soc = _build_step(case, measured_current_a, spec)
    temperature_k = case.temperature_c + 273.15

    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(get_hithium_params(1, temperature_k), check_already_exists=False)
    if case.mode == "discharge":
        parameters.update(
            {"Lower voltage cut-off [V]": spec.discharge_cutoff_v - spec.model_lower_cutoff_margin_v},
            check_already_exists=True,
        )

    experiment = pybamm.Experiment([step], temperature=temperature_k)
    simulation = pybamm.Simulation(
        build_sodium_rate_model(),
        parameter_values=parameters,
        experiment=experiment,
        var_pts=spec.var_pts,
        solver=solver or pybamm.IDAKLUSolver(),
    )
    started = time.perf_counter()
    solution = simulation.solve(initial_soc=initial_soc, showprogress=showprogress)
    elapsed_s = time.perf_counter() - started
    simulation_curve = pd.DataFrame(
        {
            "capacity_ah": solution["Throughput capacity [A.h]"].entries,
            "voltage_v": solution["Voltage [V]"].entries,
            "current_a": solution["Current [A]"].entries,
            "time_s": solution["Time [s]"].entries,
        }
    ).sort_values("capacity_ah").drop_duplicates("capacity_ah").reset_index(drop=True)
    metrics = _curve_metrics(experiment_curve, simulation_curve)
    metrics.update(
        {
            "mode": case.mode,
            "temperature_c": case.temperature_c,
            "rate_c": case.rate_c,
            "measured_current_a": measured_current_a,
            "solve_seconds": elapsed_s,
            "termination": str(solution.termination),
            "status": "ok",
            "error": "",
        }
    )
    return SodiumCaseResult(case, "ok", experiment_curve, simulation_curve, metrics, solution=solution)


def run_sodium_rate_benchmark(
    cases: Iterable[SodiumRateCase],
    get_hithium_params: Callable[..., dict],
    *,
    spec: SodiumBenchmarkSpec | None = None,
    showprogress: bool = False,
    stop_on_error: bool = False,
) -> dict[tuple[str, float, float], SodiumCaseResult]:
    """Run independent sodium cases and retain failures as machine-readable rows."""

    spec = spec or SodiumBenchmarkSpec()
    results: dict[tuple[str, float, float], SodiumCaseResult] = {}
    for case in cases:
        try:
            result = run_sodium_rate_case(
                case,
                get_hithium_params,
                spec=spec,
                showprogress=showprogress,
            )
        except Exception as exc:
            if stop_on_error:
                raise
            result = SodiumCaseResult(
                case=case,
                status="failed",
                experiment=pd.DataFrame(),
                simulation=pd.DataFrame(),
                metrics={
                    "mode": case.mode,
                    "temperature_c": case.temperature_c,
                    "rate_c": case.rate_c,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                error=f"{type(exc).__name__}: {exc}",
            )
        results[case.key] = result
    return results


def sodium_metrics_frame(results: dict[tuple[str, float, float], SodiumCaseResult]) -> pd.DataFrame:
    """Return one sorted metrics row per requested condition."""

    rows = [result.metrics for result in results.values()]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["mode", "temperature_c", "rate_c"]).reset_index(drop=True)


def sodium_curve_frame(
    results: dict[tuple[str, float, float], SodiumCaseResult],
    *,
    max_points_per_curve: int = 400,
) -> pd.DataFrame:
    """Build a compact long-form curve table for export and plotting."""

    tables: list[pd.DataFrame] = []
    for result in results.values():
        if result.status != "ok":
            continue
        for source, frame in (("experiment", result.experiment), ("simulation", result.simulation)):
            if len(frame) > max_points_per_curve:
                indices = np.linspace(0, len(frame) - 1, max_points_per_curve, dtype=int)
                compact = frame.iloc[np.unique(indices)].copy()
            else:
                compact = frame.copy()
            compact.insert(0, "source", source)
            compact.insert(0, "rate_c", result.case.rate_c)
            compact.insert(0, "temperature_c", result.case.temperature_c)
            compact.insert(0, "mode", result.case.mode)
            tables.append(compact)
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, ignore_index=True)


__all__ = [
    "SodiumBenchmarkSpec",
    "SodiumCaseResult",
    "SodiumRateCase",
    "build_sodium_rate_model",
    "discover_sodium_rate_cases",
    "load_sodium_rate_curve",
    "run_sodium_rate_benchmark",
    "run_sodium_rate_case",
    "sodium_curve_frame",
    "sodium_metrics_frame",
]
