"""Reusable calendar-aging workflow for periodic and endpoint-only storage tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import pybamm

from ..data_registry import HITHIUM_ROOT
from ..experiment_utils import build_power_step
from ..notebook import load_params
from ..workflow_runtime import WorkflowRunContext, create_run_context


STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
DEFAULT_MODEL_OPTIONS = {
    "SEI": "ec reaction limited",
    "SEI porosity change": "true",
    "lithium plating": "irreversible",
    "lithium plating porosity change": "true",
    "particle mechanics": ("swelling and cracking", "swelling only"),
    "SEI on cracks": "true",
    "loss of active material": "stress-driven",
    "calculate discharge energy": "true",
    "contact resistance": "true",
}
AGING_MODES = {"activated", "unactivated"}


@dataclass(frozen=True)
class CalendarAgingSpec:
    """Validated input contract for calendar-aging simulations."""

    cell: str = "MIC"
    aging_mode: str = "activated"
    run_mode: str = "smoke"
    temperature_c: float = 25.0
    diagnostic_rate_c: float = 0.25
    diagnostic_rate_p: float | None = None
    nominal_capacity_ah: float | None = None
    nominal_voltage_v: float = 3.2
    activated_months: int = 1
    unactivated_target_days: tuple[float, ...] = (365.0,)
    days_per_month: float = 30.0
    days_per_year: float = 365.0
    rest_period_hours: float = 24.0
    diagnostic_period_minutes: float = 0.5
    charge_cutoff_v: float = 3.65
    discharge_cutoff_v: float = 2.5
    showprogress: bool = False
    return_solutions: bool = True
    output_name: str = "日历老化"
    model_options: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_MODEL_OPTIONS)
    )
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.aging_mode not in AGING_MODES:
            raise ValueError("aging_mode must be 'activated' or 'unactivated'")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.diagnostic_rate_c <= 0:
            raise ValueError("diagnostic_rate_c must be positive")
        if self.diagnostic_rate_p is not None and self.diagnostic_rate_p <= 0:
            raise ValueError("diagnostic_rate_p must be positive")
        if self.diagnostic_rate_p is not None and self.nominal_capacity_ah is None:
            raise ValueError("nominal_capacity_ah is required for P-rate diagnostics")
        if self.activated_months <= 0:
            raise ValueError("activated_months must be positive")
        if not self.unactivated_target_days:
            raise ValueError("unactivated_target_days must not be empty")
        if any(day <= 0 for day in self.unactivated_target_days):
            raise ValueError("unactivated target days must be positive")
        if tuple(sorted(set(self.unactivated_target_days))) != self.unactivated_target_days:
            raise ValueError("unactivated_target_days must be unique and ascending")
        if min(
            self.days_per_month,
            self.days_per_year,
            self.rest_period_hours,
            self.diagnostic_period_minutes,
        ) <= 0:
            raise ValueError("time settings must be positive")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "CalendarAgingSpec":
        """Build a spec from a Notebook CONFIG mapping."""
        run_mode = str(config.get("run_mode", "smoke"))
        mode_config = dict(config.get("modes", {}).get(run_mode, {}))

        def option(name: str, default: Any) -> Any:
            return mode_config.get(name, config.get(name, default))

        days_per_year = float(option("days_per_year", 365.0))
        explicit_days = option("unactivated_target_days", None)
        if explicit_days is None:
            max_years = int(option("max_storage_years", 1))
            interval_years = int(option("storage_interval_years", 1))
            if max_years <= 0 or interval_years <= 0:
                raise ValueError("storage year settings must be positive")
            target_days = tuple(
                float(year * days_per_year)
                for year in range(interval_years, max_years + 1, interval_years)
            )
        else:
            target_days = tuple(sorted({float(day) for day in explicit_days}))

        return cls(
            cell=str(option("cell", "MIC")),
            aging_mode=str(option("aging_mode", "activated")),
            run_mode=run_mode,
            temperature_c=float(option("temperature_c", 25.0)),
            diagnostic_rate_c=float(option("diagnostic_rate_c", 0.25)),
            diagnostic_rate_p=(
                None
                if option("diagnostic_rate_p", None) is None
                else float(option("diagnostic_rate_p", None))
            ),
            nominal_capacity_ah=(
                None
                if option("nominal_capacity_ah", None) is None
                else float(option("nominal_capacity_ah", None))
            ),
            nominal_voltage_v=float(option("nominal_voltage_v", 3.2)),
            activated_months=int(option("activated_months", 1)),
            unactivated_target_days=target_days,
            days_per_month=float(option("days_per_month", 30.0)),
            days_per_year=days_per_year,
            rest_period_hours=float(option("rest_period_hours", 24.0)),
            diagnostic_period_minutes=float(option("diagnostic_period_minutes", 0.5)),
            charge_cutoff_v=float(option("charge_cutoff_v", 3.65)),
            discharge_cutoff_v=float(option("discharge_cutoff_v", 2.5)),
            showprogress=bool(option("showprogress", False)),
            return_solutions=bool(option("return_solutions", True)),
            output_name=str(option("output_name", "日历老化")),
            model_options=dict(option("model_options", DEFAULT_MODEL_OPTIONS)),
            var_pts=dict(option("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable config snapshot."""
        return asdict(self)


def _diagnostic_power_w(spec: CalendarAgingSpec) -> float:
    if spec.diagnostic_rate_p is None or spec.nominal_capacity_ah is None:
        raise ValueError("P-rate diagnostics require rate and nominal capacity")
    return spec.diagnostic_rate_p * spec.nominal_capacity_ah * spec.nominal_voltage_v


def _charge_step(spec: CalendarAgingSpec) -> str:
    if spec.diagnostic_rate_p is not None:
        return build_power_step(
            "Charge",
            _diagnostic_power_w(spec),
            spec.charge_cutoff_v,
            spec.nominal_capacity_ah,
            period_minutes=spec.diagnostic_period_minutes,
            reference_voltage_v=spec.nominal_voltage_v,
        )
    return (
        f"Charge at {spec.diagnostic_rate_c:g}C until {spec.charge_cutoff_v:g} V "
        f"({spec.diagnostic_period_minutes:g} minute period)"
    )


def _discharge_step(spec: CalendarAgingSpec) -> str:
    if spec.diagnostic_rate_p is not None:
        return build_power_step(
            "Discharge",
            _diagnostic_power_w(spec),
            spec.discharge_cutoff_v,
            spec.nominal_capacity_ah,
            period_minutes=spec.diagnostic_period_minutes,
            reference_voltage_v=spec.nominal_voltage_v,
        )
    return (
        f"Discharge at {spec.diagnostic_rate_c:g}C until "
        f"{spec.discharge_cutoff_v:g} V "
        f"({spec.diagnostic_period_minutes:g} minute period)"
    )


def _rest_step(days: float, period_hours: float) -> str:
    return (
        f"Rest for {days * 24:g} hour "
        f"({min(period_hours, days * 24):g} hour period)"
    )


def build_activated_cycles(spec: CalendarAgingSpec) -> list[tuple[str, ...]]:
    """Build one reference cycle followed by monthly rest/check/recharge cycles."""
    charge = _charge_step(spec)
    discharge = _discharge_step(spec)
    cycles = [(charge, discharge, charge)]
    monthly = (
        _rest_step(spec.days_per_month, spec.rest_period_hours),
        discharge,
        charge,
        discharge,
        charge,
    )
    cycles.extend([monthly] * spec.activated_months)
    return cycles


def build_unactivated_cycles(
    spec: CalendarAgingSpec,
    target_days: float,
) -> list[tuple[str, ...]]:
    """Build an independent endpoint-only storage experiment for one horizon."""
    charge = _charge_step(spec)
    discharge = _discharge_step(spec)
    return [
        (charge, discharge, charge),
        (
            _rest_step(target_days, spec.rest_period_hours),
            discharge,
            charge,
            discharge,
        ),
    ]


def _solve_case(
    spec: CalendarAgingSpec,
    cycles: list[tuple[str, ...]],
) -> pybamm.Solution:
    """Solve one independent calendar-aging case with fresh parameters."""
    temperature_k = spec.temperature_c + 273.15
    params_fn = load_params(spec.cell)
    params = pybamm.ParameterValues("OKane2022")
    params.update(params_fn(1, temperature_k), check_already_exists=False)
    model = pybamm.lithium_ion.DFN(spec.model_options)
    experiment = pybamm.Experiment(cycles, temperature=temperature_k)
    simulation = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=experiment,
        var_pts=spec.var_pts,
        solver=pybamm.IDAKLUSolver(),
    )
    return simulation.solve(showprogress=spec.showprogress)


def _step_current(step: pybamm.Solution) -> np.ndarray:
    return np.asarray(step["Current [A]"].entries, dtype=float).reshape(-1)


def _discharge_capacity_ah(step: pybamm.Solution) -> float:
    time_s = np.asarray(step["Time [s]"].entries, dtype=float).reshape(-1)
    current_a = np.clip(_step_current(step), 0.0, None)
    if len(time_s) < 2:
        return 0.0
    return float(np.trapz(current_a, time_s) / 3600.0)


def _discharge_capacities(cycle: pybamm.Solution) -> list[float]:
    capacities = []
    for step in cycle.steps:
        current = _step_current(step)
        if current.size and float(np.nanmax(current)) > 1e-6:
            capacities.append(_discharge_capacity_ah(step))
    return capacities


def _rest_profile(
    cycle: pybamm.Solution,
    *,
    case_label: str,
    storage_days: float,
) -> pd.DataFrame:
    for step in cycle.steps:
        current = _step_current(step)
        if current.size and float(np.nanmax(np.abs(current))) <= 1e-6:
            time_h = np.asarray(step["Time [h]"].entries, dtype=float).reshape(-1)
            voltage_v = np.asarray(step["Voltage [V]"].entries, dtype=float).reshape(-1)
            return pd.DataFrame({
                "case": case_label,
                "storage_days": storage_days,
                "rest_time_h": time_h - time_h[0],
                "voltage_v": voltage_v,
            })
    return pd.DataFrame(
        columns=["case", "storage_days", "rest_time_h", "voltage_v"]
    )


def _metric_row(
    *,
    case_label: str,
    storage_days: float,
    reference_capacity_ah: float,
    retained_capacity_ah: float,
    recovered_capacity_ah: float,
    days_per_year: float,
) -> dict[str, float | str]:
    if reference_capacity_ah <= 0 or recovered_capacity_ah <= 0:
        raise ValueError("reference and recovered capacities must be positive")
    retained_vs_recovered_delta_ah = recovered_capacity_ah - retained_capacity_ah
    return {
        "case": case_label,
        "storage_days": storage_days,
        "storage_years": storage_days / days_per_year,
        "reference_capacity_ah": reference_capacity_ah,
        "retained_capacity_ah": retained_capacity_ah,
        "recovered_capacity_ah": recovered_capacity_ah,
        "retention_rate": retained_capacity_ah / reference_capacity_ah,
        "recovery_rate": recovered_capacity_ah / reference_capacity_ah,
        "retained_vs_recovered_delta_ah": retained_vs_recovered_delta_ah,
        "reversible_self_discharge_rate": max(
            0.0,
            retained_vs_recovered_delta_ah / recovered_capacity_ah,
        ),
        "irreversible_capacity_loss_rate": 1.0 - (
            recovered_capacity_ah / reference_capacity_ah
        ),
    }


def _case_label(target_days: float, days_per_year: float) -> str:
    years = target_days / days_per_year
    if years >= 1 and np.isclose(years, round(years)):
        return f"{int(round(years))}_year"
    return f"{target_days:g}_day"


def extract_activated_results(
    solution: pybamm.Solution,
    spec: CalendarAgingSpec,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract monthly retained/recovered capacity and rest-voltage profiles."""
    reference = _discharge_capacities(solution.cycles[0])
    if len(reference) != 1:
        raise ValueError("reference cycle must contain exactly one discharge")
    rows = []
    profiles = []
    for month, cycle in enumerate(solution.cycles[1:], start=1):
        capacities = _discharge_capacities(cycle)
        if len(capacities) != 2:
            raise ValueError("activated monthly cycle must contain two discharges")
        storage_days = month * spec.days_per_month
        label = f"month_{month}"
        rows.append(_metric_row(
            case_label=label,
            storage_days=storage_days,
            reference_capacity_ah=reference[0],
            retained_capacity_ah=capacities[0],
            recovered_capacity_ah=capacities[1],
            days_per_year=spec.days_per_year,
        ))
        profiles.append(
            _rest_profile(cycle, case_label=label, storage_days=storage_days)
        )
    return pd.DataFrame(rows), pd.concat(profiles, ignore_index=True)


def extract_unactivated_result(
    solution: pybamm.Solution,
    spec: CalendarAgingSpec,
    target_days: float,
) -> tuple[dict[str, float | str], pd.DataFrame]:
    """Extract the endpoint metrics for one independent storage horizon."""
    reference = _discharge_capacities(solution.cycles[0])
    endpoint = _discharge_capacities(solution.cycles[1])
    if len(reference) != 1 or len(endpoint) != 2:
        raise ValueError("unactivated case requires one reference and two endpoint discharges")
    label = _case_label(target_days, spec.days_per_year)
    row = _metric_row(
        case_label=label,
        storage_days=target_days,
        reference_capacity_ah=reference[0],
        retained_capacity_ah=endpoint[0],
        recovered_capacity_ah=endpoint[1],
        days_per_year=spec.days_per_year,
    )
    profile = _rest_profile(
        solution.cycles[1],
        case_label=label,
        storage_days=target_days,
    )
    return row, profile


def run_calendar_aging_workflow(
    spec: CalendarAgingSpec,
    *,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run activated or independent endpoint-only calendar-aging cases."""
    del workspace_root  # reserved for future registry-backed comparisons
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "calendar_aging",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    solutions: dict[str, pybamm.Solution] = {}
    profiles: list[pd.DataFrame] = []

    if spec.aging_mode == "activated":
        solution = _solve_case(spec, build_activated_cycles(spec))
        metrics, profile = extract_activated_results(solution, spec)
        if spec.return_solutions:
            solutions["activated"] = solution
        profiles.append(profile)
    else:
        rows = []
        for target_days in spec.unactivated_target_days:
            label = _case_label(target_days, spec.days_per_year)
            solution = _solve_case(
                spec,
                build_unactivated_cycles(spec, target_days),
            )
            row, profile = extract_unactivated_result(
                solution,
                spec,
                target_days,
            )
            rows.append(row)
            profiles.append(profile)
            if spec.return_solutions:
                solutions[label] = solution
        metrics = pd.DataFrame(rows)

    rest_profiles = pd.concat(profiles, ignore_index=True)
    metrics_path = context.artifacts_dir / "calendar_aging_metrics.csv"
    profile_path = context.artifacts_dir / "rest_voltage_profiles.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    rest_profiles.to_csv(profile_path, index=False, encoding="utf-8-sig")
    return {
        "context": context,
        "spec": spec,
        "metrics": metrics,
        "rest_profiles": rest_profiles,
        "solutions": solutions,
        "metrics_path": metrics_path,
        "rest_profiles_path": profile_path,
    }


__all__ = [
    "CalendarAgingSpec",
    "build_activated_cycles",
    "build_unactivated_cycles",
    "extract_activated_results",
    "extract_unactivated_result",
    "run_calendar_aging_workflow",
]
