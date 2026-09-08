"""Staged 50% SOC calendar-aging workflow with a fixed 25°C capacity test."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pybamm

from ..data_registry import HITHIUM_ROOT
from ..experiment_utils import estimate_power_step_duration_hours
from ..notebook import load_params
from ..workflow_runtime import WorkflowRunContext, create_run_context
from .calendar_aging import CalendarAgingSpec


AGING_T_FACTOR = 1.0
DEFAULT_TEST_TEMPERATURE_C = 25.0
DEFAULT_RELAXATION_HOURS = 1.0


@dataclass(frozen=True)
class HalfSocBaseline:
    """Common 25°C reference state used to branch independent storage cases."""

    solution: pybamm.Solution
    c0_ah: float
    target_half_c0_ah: float
    charged_to_storage_ah: float
    test_temperature_c: float
    aging_t_factor: float = AGING_T_FACTOR
    storage_soc_pct: float = 50.0

    def metrics(self) -> dict[str, float]:
        """Return the serializable baseline metrics."""
        return {
            "c0_ah": self.c0_ah,
            "target_half_c0_ah": self.target_half_c0_ah,
            "charged_to_storage_ah": self.charged_to_storage_ah,
            "half_c0_error_ah": self.charged_to_storage_ah - self.target_half_c0_ah,
            "test_temperature_c": self.test_temperature_c,
            "aging_t_factor": self.aging_t_factor,
            "storage_soc_pct": self.storage_soc_pct,
        }


def _fresh_parameter_values(spec: CalendarAgingSpec, temperature_c: float) -> pybamm.ParameterValues:
    temperature_k = temperature_c + 273.15
    params_fn = load_params(spec.cell)
    params = pybamm.ParameterValues("OKane2022")
    params.update(params_fn(AGING_T_FACTOR, temperature_k), check_already_exists=False)
    return params


def _solve_experiment(
    spec: CalendarAgingSpec,
    experiment: pybamm.Experiment,
    *,
    parameter_temperature_c: float,
    starting_solution: pybamm.Solution | None = None,
) -> pybamm.Solution:
    model = pybamm.lithium_ion.DFN(spec.model_options)
    simulation = pybamm.Simulation(
        model,
        parameter_values=_fresh_parameter_values(spec, parameter_temperature_c),
        experiment=experiment,
        var_pts=spec.var_pts,
        solver=pybamm.IDAKLUSolver(),
    )
    return simulation.solve(
        starting_solution=starting_solution,
        showprogress=spec.showprogress,
    )


def _diagnostic_power_w(spec: CalendarAgingSpec) -> float:
    if spec.diagnostic_rate_p is None or spec.nominal_capacity_ah is None:
        raise ValueError("50% SOC workflow requires diagnostic_rate_p and nominal_capacity_ah")
    return spec.diagnostic_rate_p * spec.nominal_capacity_ah * spec.nominal_voltage_v


def _power_step(
    spec: CalendarAgingSpec,
    direction: str,
    *,
    temperature_c: float,
) -> pybamm.step.BaseStep:
    power_w = _diagnostic_power_w(spec)
    duration_hours = estimate_power_step_duration_hours(
        power_w=power_w,
        nominal_capacity_ah=spec.nominal_capacity_ah,
        reference_voltage_v=spec.nominal_voltage_v,
    )
    is_charge = direction.lower() == "charge"
    if not is_charge and direction.lower() != "discharge":
        raise ValueError("direction must be charge or discharge")
    cutoff_v = spec.charge_cutoff_v if is_charge else spec.discharge_cutoff_v
    return pybamm.step.power(
        -power_w if is_charge else power_w,
        duration=f"{duration_hours:g} hours",
        termination=pybamm.step.VoltageTermination(cutoff_v),
        period=f"{spec.diagnostic_period_minutes:g} minutes",
        temperature=temperature_c + 273.15,
        description=f"{direction} at {spec.diagnostic_rate_p:g}P",
    )


def build_final_test_steps(
    spec: CalendarAgingSpec,
    *,
    test_temperature_c: float = DEFAULT_TEST_TEMPERATURE_C,
    relaxation_hours: float = DEFAULT_RELAXATION_HOURS,
) -> tuple[pybamm.step.BaseStep, ...]:
    """Build 25°C relaxation, retained-capacity, and recovery test steps."""
    if relaxation_hours <= 0:
        raise ValueError("relaxation_hours must be positive")
    temperature_k = test_temperature_c + 273.15
    return (
        pybamm.step.current(
            0,
            duration=f"{relaxation_hours:g} hours",
            period="10 minutes",
            temperature=temperature_k,
            description="Relax before 25C capacity test",
        ),
        _power_step(spec, "discharge", temperature_c=test_temperature_c),
        _power_step(spec, "charge", temperature_c=test_temperature_c),
        _power_step(spec, "discharge", temperature_c=test_temperature_c),
    )


def _step_discharge_capacity_ah(step: pybamm.Solution) -> float:
    time_s = np.asarray(step["Time [s]"].entries, dtype=float).reshape(-1)
    current_a = np.asarray(step["Current [A]"].entries, dtype=float).reshape(-1)
    if time_s.size < 2:
        return 0.0
    return float(np.trapz(np.clip(current_a, 0.0, None), time_s) / 3600.0)


def _cycle_discharge_capacities(cycle: pybamm.Solution) -> list[float]:
    capacities = []
    for step in cycle.steps:
        current_a = np.asarray(step["Current [A]"].entries, dtype=float).reshape(-1)
        if current_a.size and float(np.nanmax(current_a)) > 1e-6:
            capacities.append(_step_discharge_capacity_ah(step))
    return capacities


def prepare_half_soc_baseline(
    spec: CalendarAgingSpec,
    *,
    test_temperature_c: float = DEFAULT_TEST_TEMPERATURE_C,
    storage_soc_pct: float = 50.0,
) -> HalfSocBaseline:
    """Measure C0 at 25°C, then charge exactly soc_pct*C0 by Ah throughput."""
    if not 0 < storage_soc_pct <= 100:
        raise ValueError("storage_soc_pct must be in (0, 100]")
    reference_steps = (
        _power_step(spec, "charge", temperature_c=test_temperature_c),
        _power_step(spec, "discharge", temperature_c=test_temperature_c),
    )
    reference_solution = _solve_experiment(
        spec,
        pybamm.Experiment([reference_steps], temperature=test_temperature_c + 273.15),
        parameter_temperature_c=test_temperature_c,
    )
    reference_caps = _cycle_discharge_capacities(reference_solution.cycles[-1])
    if len(reference_caps) != 1:
        raise ValueError("reference cycle must contain one discharge")
    c0_ah = reference_caps[0]
    target_half_c0_ah = (storage_soc_pct / 100.0) * c0_ah
    start_throughput_ah = float(reference_solution["Throughput capacity [A.h]"].entries[-1])
    target_throughput_ah = start_throughput_ah + target_half_c0_ah
    throughput_termination = pybamm.step.CustomTermination(
        f"{storage_soc_pct:g} percent C0 charge throughput",
        lambda variables, target=target_throughput_ah: (
            target - variables["Throughput capacity [A.h]"]
        ),
    )
    half_charge = pybamm.step.power(
        -_diagnostic_power_w(spec),
        duration="2 hours",
        termination=[
            pybamm.step.VoltageTermination(spec.charge_cutoff_v),
            throughput_termination,
        ],
        period=f"{spec.diagnostic_period_minutes:g} minutes",
        temperature=test_temperature_c + 273.15,
        description=f"Charge exactly {storage_soc_pct / 100.0:g}*C0 for storage",
    )
    half_soc_solution = _solve_experiment(
        spec,
        pybamm.Experiment([(half_charge,)], temperature=test_temperature_c + 273.15),
        parameter_temperature_c=test_temperature_c,
        starting_solution=reference_solution,
    )
    charged_to_storage_ah = float(
        half_soc_solution["Throughput capacity [A.h]"].entries[-1] - start_throughput_ah
    )
    if not np.isclose(charged_to_storage_ah, target_half_c0_ah, atol=1e-4, rtol=0):
        raise ValueError(
            f"{storage_soc_pct:g}% C0 charge target was not reached: "
            f"target={target_half_c0_ah:.6f} Ah, actual={charged_to_storage_ah:.6f} Ah"
        )
    return HalfSocBaseline(
        solution=half_soc_solution,
        c0_ah=c0_ah,
        target_half_c0_ah=target_half_c0_ah,
        charged_to_storage_ah=charged_to_storage_ah,
        test_temperature_c=test_temperature_c,
        storage_soc_pct=storage_soc_pct,
    )


def build_half_soc_metric_row(
    *,
    storage_temperature_c: float,
    storage_days: float,
    baseline: HalfSocBaseline,
    retained_capacity_ah: float,
    recovered_capacity_ah: float,
    days_per_year: float,
    relaxation_hours: float,
    storage_soc_pct: float | None = None,
) -> dict[str, float | str]:
    """Build metrics with retained capacity normalized by soc_pct*C0."""
    if baseline.c0_ah <= 0 or baseline.target_half_c0_ah <= 0:
        raise ValueError("C0 and storage SOC target must be positive")
    retention_rate = retained_capacity_ah / baseline.target_half_c0_ah
    recovery_rate = recovered_capacity_ah / baseline.c0_ah
    return {
        "case": f"{storage_days:g}_day",
        "storage_temperature_c": storage_temperature_c,
        "test_temperature_c": baseline.test_temperature_c,
        "storage_days": storage_days,
        "storage_years": storage_days / days_per_year,
        "storage_soc_pct": (
            float(storage_soc_pct)
            if storage_soc_pct is not None
            else baseline.storage_soc_pct
        ),
        "aging_t_factor": baseline.aging_t_factor,
        "relaxation_hours_at_test_temperature": relaxation_hours,
        "reference_capacity_ah": baseline.c0_ah,
        "storage_soc_target_ah": baseline.target_half_c0_ah,
        "retained_capacity_ah": retained_capacity_ah,
        "recovered_capacity_ah": recovered_capacity_ah,
        "retention_rate": retention_rate,
        "retained_capacity_vs_c0_rate": retained_capacity_ah / baseline.c0_ah,
        "recovery_rate": recovery_rate,
        "half_soc_capacity_loss_rate": max(0.0, 1.0 - retention_rate),
        "irreversible_capacity_loss_rate": max(0.0, 1.0 - recovery_rate),
    }


def run_half_soc_storage_case(
    spec: CalendarAgingSpec,
    *,
    storage_days: float,
    baseline: HalfSocBaseline,
    relaxation_hours: float = DEFAULT_RELAXATION_HOURS,
    storage_soc_pct: float | None = None,
) -> tuple[dict[str, float | str], pybamm.Solution]:
    """Store the common storage SOC state, then test at 25°C."""
    if storage_days <= 0:
        raise ValueError("storage_days must be positive")
    storage_temperature_k = spec.temperature_c + 273.15
    storage_step = pybamm.step.current(
        0,
        duration=f"{storage_days * 24:g} hours",
        period=f"{min(spec.rest_period_hours, storage_days * 24):g} hours",
        temperature=storage_temperature_k,
        description=f"Store at {spec.temperature_c:g}C",
    )
    stored_solution = _solve_experiment(
        spec,
        pybamm.Experiment([(storage_step,)], temperature=storage_temperature_k),
        parameter_temperature_c=spec.temperature_c,
        starting_solution=baseline.solution,
    )
    final_steps = build_final_test_steps(
        spec,
        test_temperature_c=baseline.test_temperature_c,
        relaxation_hours=relaxation_hours,
    )
    final_solution = _solve_experiment(
        spec,
        pybamm.Experiment(
            [final_steps],
            temperature=baseline.test_temperature_c + 273.15,
        ),
        parameter_temperature_c=baseline.test_temperature_c,
        starting_solution=stored_solution,
    )
    capacities = _cycle_discharge_capacities(final_solution.cycles[-1])
    if len(capacities) != 2:
        raise ValueError("final test must contain two discharges")
    row = build_half_soc_metric_row(
        storage_temperature_c=spec.temperature_c,
        storage_days=storage_days,
        baseline=baseline,
        retained_capacity_ah=capacities[0],
        recovered_capacity_ah=capacities[1],
        days_per_year=spec.days_per_year,
        relaxation_hours=relaxation_hours,
        storage_soc_pct=storage_soc_pct,
    )
    return row, final_solution


def run_half_soc_case_workflow(
    spec: CalendarAgingSpec,
    *,
    storage_days: float,
    baseline: HalfSocBaseline,
    project_root: Path | None = None,
    workspace_root: Path = HITHIUM_ROOT,
    run_id: str | None = None,
    relaxation_hours: float = DEFAULT_RELAXATION_HOURS,
    storage_soc_pct: float | None = None,
) -> dict[str, Any]:
    """Run and persist one independent storage endpoint at a given SOC."""
    del workspace_root
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "calendar_aging_half_soc",
        {
            "spec": asdict(spec),
            "storage_days": storage_days,
            "baseline": baseline.metrics(),
            "relaxation_hours": relaxation_hours,
        },
        project_root=project_root,
        run_id=run_id,
    )
    row, solution = run_half_soc_storage_case(
        spec,
        storage_days=storage_days,
        baseline=baseline,
        relaxation_hours=relaxation_hours,
        storage_soc_pct=storage_soc_pct,
    )
    metrics = pd.DataFrame([row])
    metrics_path = context.artifacts_dir / "calendar_aging_half_soc_metrics.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    return {
        "context": context,
        "metrics": metrics,
        "metrics_path": metrics_path,
        "solution": solution if spec.return_solutions else None,
    }


__all__ = [
    "AGING_T_FACTOR",
    "DEFAULT_RELAXATION_HOURS",
    "DEFAULT_TEST_TEMPERATURE_C",
    "HalfSocBaseline",
    "build_final_test_steps",
    "build_half_soc_metric_row",
    "prepare_half_soc_baseline",
    "run_half_soc_case_workflow",
    "run_half_soc_storage_case",
]
