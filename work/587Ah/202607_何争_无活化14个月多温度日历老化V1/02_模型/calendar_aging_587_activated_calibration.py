"""Prototype 587 Ah activated calendar-aging calibration runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pybamm

HITHIUM_ROOT = Path(__file__).resolve().parents[4]
PARAMS_ROOT = HITHIUM_ROOT / "params"
hithium_root_text = str(HITHIUM_ROOT)
params_root_text = str(PARAMS_ROOT)
if hithium_root_text not in sys.path:
    sys.path.insert(0, hithium_root_text)
if params_root_text not in sys.path:
    sys.path.append(params_root_text)

from BatteryProject.src.workflows.calendar_aging import (  # noqa: E402
    DEFAULT_MODEL_OPTIONS,
    STANDARD_VAR_PTS,
)
from params.common import BASE_CRACKING_RATE_AI2020, build_cracking_rate  # noqa: E402
from params.params587 import get_hithium_params as get_base_params  # noqa: E402


POWER_W = 587 * 3.2 * 0.5
TEST_TEMPERATURE_C = 25.0


@dataclass(frozen=True)
class CalibrationParameters:
    sei_kinetic_scale: float = 1.0
    ec_diffusivity_scale: float = 0.30
    sei_activation_energy_j_mol: float = 39000.0
    initial_sei_thickness_m: float = 5e-9
    cracking_rate_scale: float = 1.0


def _parameter_values(
    temperature_c: float,
    candidate: CalibrationParameters,
) -> pybamm.ParameterValues:
    values = dict(get_base_params(1, temperature_c + 273.15))
    values["SEI kinetic rate constant [m.s-1]"] *= candidate.sei_kinetic_scale
    values["EC diffusivity [m2.s-1]"] *= candidate.ec_diffusivity_scale
    values["SEI growth activation energy [J.mol-1]"] = (
        candidate.sei_activation_energy_j_mol
    )
    values["Initial SEI thickness [m]"] = candidate.initial_sei_thickness_m
    values["Negative electrode cracking rate"] = build_cracking_rate(
        1,
        base_rate=BASE_CRACKING_RATE_AI2020 * candidate.cracking_rate_scale,
        activation_energy=10000,
    )
    params = pybamm.ParameterValues("OKane2022")
    params.update(values, check_already_exists=False)
    return params


def _solve(
    experiment: pybamm.Experiment,
    *,
    temperature_c: float,
    candidate: CalibrationParameters,
    starting_solution: pybamm.Solution | None = None,
) -> pybamm.Solution:
    simulation = pybamm.Simulation(
        pybamm.lithium_ion.DFN(dict(DEFAULT_MODEL_OPTIONS)),
        parameter_values=_parameter_values(temperature_c, candidate),
        experiment=experiment,
        var_pts=dict(STANDARD_VAR_PTS),
        solver=pybamm.IDAKLUSolver(),
    )
    return simulation.solve(
        starting_solution=starting_solution,
        showprogress=False,
    )


def _power_step(direction: str, temperature_c: float) -> pybamm.step.BaseStep:
    is_charge = direction == "charge"
    return pybamm.step.power(
        -POWER_W if is_charge else POWER_W,
        duration="3 hours",
        termination=pybamm.step.VoltageTermination(3.65 if is_charge else 2.5),
        period="0.5 minutes",
        temperature=temperature_c + 273.15,
        description=f"{direction} at 0.5P",
    )


def _discharge_capacity_ah(step: pybamm.Solution) -> float:
    time_s = np.asarray(step["Time [s]"].entries, dtype=float).reshape(-1)
    current_a = np.asarray(step["Current [A]"].entries, dtype=float).reshape(-1)
    return float(np.trapz(np.clip(current_a, 0.0, None), time_s) / 3600)


def _half_discharge_step(
    starting_solution: pybamm.Solution,
    target_capacity_ah: float,
) -> pybamm.step.BaseStep:
    start_throughput = float(
        starting_solution["Throughput capacity [A.h]"].entries[-1]
    )
    target_throughput = start_throughput + 0.5 * target_capacity_ah
    termination = pybamm.step.CustomTermination(
        "Discharge 50 percent recovered capacity",
        lambda variables, target=target_throughput: (
            target - variables["Throughput capacity [A.h]"]
        ),
    )
    return pybamm.step.power(
        POWER_W,
        duration="3 hours",
        termination=[pybamm.step.VoltageTermination(2.5), termination],
        period="0.5 minutes",
        temperature=TEST_TEMPERATURE_C + 273.15,
        description="Discharge 50 percent capacity for storage",
    )


def _prepare_initial_state(
    candidate: CalibrationParameters,
) -> tuple[pybamm.Solution, float]:
    charge = _power_step("charge", TEST_TEMPERATURE_C)
    discharge = _power_step("discharge", TEST_TEMPERATURE_C)
    solution = _solve(
        pybamm.Experiment(
            [(charge, discharge), (charge, discharge)],
            temperature=TEST_TEMPERATURE_C + 273.15,
        ),
        temperature_c=TEST_TEMPERATURE_C,
        candidate=candidate,
    )
    c0_ah = _discharge_capacity_ah(solution.cycles[-1].steps[-1])
    charged = _solve(
        pybamm.Experiment(
            [(_power_step("charge", TEST_TEMPERATURE_C),)],
            temperature=TEST_TEMPERATURE_C + 273.15,
        ),
        temperature_c=TEST_TEMPERATURE_C,
        candidate=candidate,
        starting_solution=solution,
    )
    half_step = _half_discharge_step(charged, c0_ah)
    half_soc = _solve(
        pybamm.Experiment(
            [(half_step,)],
            temperature=TEST_TEMPERATURE_C + 273.15,
        ),
        temperature_c=TEST_TEMPERATURE_C,
        candidate=candidate,
        starting_solution=charged,
    )
    return half_soc, c0_ah


def run_activated_case(
    temperature_c: float,
    candidate: CalibrationParameters,
    *,
    checkpoint_days: tuple[int, ...] = (30,),
) -> pd.DataFrame:
    if not checkpoint_days or tuple(sorted(checkpoint_days)) != checkpoint_days:
        raise ValueError("checkpoint_days must be ascending")
    solution, c0_ah = _prepare_initial_state(candidate)
    rows = []
    elapsed_days = 0
    for checkpoint_day in checkpoint_days:
        interval_days = checkpoint_day - elapsed_days
        storage = pybamm.step.current(
            0,
            duration=f"{interval_days * 24:g} hours",
            period="24 hours",
            temperature=temperature_c + 273.15,
            description=f"Store at {temperature_c:g}C",
        )
        solution = _solve(
            pybamm.Experiment(
                [(storage,)],
                temperature=temperature_c + 273.15,
            ),
            temperature_c=temperature_c,
            candidate=candidate,
            starting_solution=solution,
        )
        test_steps = (
            pybamm.step.current(
                0,
                duration="1 hour",
                period="10 minutes",
                temperature=TEST_TEMPERATURE_C + 273.15,
            ),
            _power_step("charge", TEST_TEMPERATURE_C),
            _power_step("discharge", TEST_TEMPERATURE_C),
        )
        solution = _solve(
            pybamm.Experiment(
                [test_steps],
                temperature=TEST_TEMPERATURE_C + 273.15,
            ),
            temperature_c=TEST_TEMPERATURE_C,
            candidate=candidate,
            starting_solution=solution,
        )
        recovered_ah = _discharge_capacity_ah(solution.cycles[-1].steps[-1])
        rows.append(
            {
                "temperature_c": temperature_c,
                "storage_days": checkpoint_day,
                "c0_ah": c0_ah,
                "recovered_capacity_ah": recovered_ah,
                "recovery_rate": recovered_ah / c0_ah,
            }
        )
        solution = _solve(
            pybamm.Experiment(
                [(_power_step("charge", TEST_TEMPERATURE_C),)],
                temperature=TEST_TEMPERATURE_C + 273.15,
            ),
            temperature_c=TEST_TEMPERATURE_C,
            candidate=candidate,
            starting_solution=solution,
        )
        solution = _solve(
            pybamm.Experiment(
                [(_half_discharge_step(solution, recovered_ah),)],
                temperature=TEST_TEMPERATURE_C + 273.15,
            ),
            temperature_c=TEST_TEMPERATURE_C,
            candidate=candidate,
            starting_solution=solution,
        )
        elapsed_days = checkpoint_day
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(
        run_activated_case(
            25,
            CalibrationParameters(),
            checkpoint_days=(30,),
        ).to_string(index=False)
    )
