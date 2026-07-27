"""Constant-power lifecycle coupling for regional parallel DFN models.

The runner in this module advances several independently aging DFN branches
while enforcing a shared terminal voltage. Positive current and power denote
discharge; negative current and power denote charge.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping, Sequence

import numpy as np
import pybamm
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import least_squares

from .simulation_regional_parallel import (
    AREA_SUM_TOLERANCE,
    CURRENT_INPUT_NAME,
    CURRENT_TOLERANCE_A,
    DEFAULT_REGIONAL_DFN_VAR_PTS,
    REGIONAL_POROSITY_VARIABLES,
    RegionalCellState,
    RegionalDFNConfig,
    _build_regional_dfn_parameter_values,
    _last_solution_scalar,
    solve_parallel_current_split,
)
from .simulation_rpt import safe_last_scalar, snapshot_degradation_variables


NEGATIVE_SURFACE_POTENTIAL_DIFFERENCE = (
    "Negative electrode surface potential difference [V]"
)
NEGATIVE_PLATING_OVERPOTENTIAL = (
    "Negative electrode lithium plating reaction overpotential [V]"
)


@dataclass(frozen=True)
class RegionalPowerCycleResult:
    """Outputs from regional constant-power lifecycle coupling."""

    region_configs: tuple[RegionalDFNConfig, ...]
    step_rows: tuple[Mapping[str, object], ...]
    iteration_rows: tuple[Mapping[str, object], ...]
    cycle_rows: tuple[Mapping[str, object], ...]
    degradation_rows: tuple[Mapping[str, object], ...]
    final_solutions: Mapping[str, object]

    def steps(self):
        """Return accepted macro-step rows for DataFrame construction."""
        return [dict(row) for row in self.step_rows]

    def iterations(self):
        """Return nonlinear iteration rows for DataFrame construction."""
        return [dict(row) for row in self.iteration_rows]

    def cycles(self):
        """Return cycle summary rows for DataFrame construction."""
        return [dict(row) for row in self.cycle_rows]

    def degradation(self):
        """Return region-level degradation snapshots for DataFrame construction."""
        return [dict(row) for row in self.degradation_rows]


@dataclass
class _RegionalRuntime:
    config: RegionalDFNConfig
    simulation: object
    accepted_solution: object
    current_a: float
    resistance_ohm: float
    capacity_ah: float


@dataclass(frozen=True)
class _CoupledStepResult:
    solutions: Mapping[str, object]
    currents_a: Mapping[str, float]
    resistances_ohm: Mapping[str, float]
    terminal_voltage_v: float
    voltage_spread_v: float
    actual_power_w: float
    power_error_w: float
    iterations: int


class _ModelSafetyEvent(RuntimeError):
    """Signal that a trial macro step crossed an internal PyBaMM event."""


class _CouplingConvergenceError(RuntimeError):
    """Signal that a regional macro step needs a shorter continuation step."""


def run_homogeneous_dfn_power_cycles(
    parameter_values,
    *,
    discharge_power_w: float,
    charge_power_w: float | None = None,
    cycles: int,
    rest_s: float = 600.0,
    output_period_s: float = 120.0,
    initial_soc: float = 1.0,
    lower_cutoff_v: float = 2.5,
    upper_cutoff_v: float = 3.65,
    equivalent_cycle_factor: float = 1.0,
    model_options: Mapping[str, object] | None = None,
    var_pts: Mapping[str, int] | None = None,
    rtol: float = 1e-6,
    atol: float = 1e-6,
    model_voltage_limits_v: tuple[float, float] = (2.0, 4.0),
    progress_callback=None,
) -> RegionalPowerCycleResult:
    """Run a homogeneous DFN lifecycle with native PyBaMM power control.

    The protocol is solved continuously by IDAKLU. ``output_period_s`` only
    controls stored result resolution and does not split the electrochemical
    solve into external coupling steps.
    """
    charge_power_w = float(discharge_power_w if charge_power_w is None else charge_power_w)
    _validate_homogeneous_inputs(
        discharge_power_w=discharge_power_w,
        charge_power_w=charge_power_w,
        cycles=cycles,
        rest_s=rest_s,
        output_period_s=output_period_s,
        initial_soc=initial_soc,
        lower_cutoff_v=lower_cutoff_v,
        upper_cutoff_v=upper_cutoff_v,
        equivalent_cycle_factor=equivalent_cycle_factor,
        rtol=rtol,
        atol=atol,
        model_voltage_limits_v=model_voltage_limits_v,
    )

    options = {"contact resistance": "true"}
    if model_options is not None:
        options.update(dict(model_options))
    mesh_points = dict(DEFAULT_REGIONAL_DFN_VAR_PTS if var_pts is None else var_pts)
    params = parameter_values.copy()
    params.update(
        {
            "Lower voltage cut-off [V]": float(model_voltage_limits_v[0]),
            "Upper voltage cut-off [V]": float(model_voltage_limits_v[1]),
        },
        check_already_exists=False,
    )
    cycle_steps = (
        f"Discharge at {float(discharge_power_w):.12g} W until {float(lower_cutoff_v):.12g} V",
        f"Rest for {float(rest_s):.12g} seconds",
        f"Charge at {charge_power_w:.12g} W until {float(upper_cutoff_v):.12g} V",
        f"Rest for {float(rest_s):.12g} seconds",
    )
    experiment = pybamm.Experiment(
        [cycle_steps] * int(cycles),
        period=f"{float(output_period_s):.12g} seconds",
    )
    simulation = pybamm.Simulation(
        pybamm.lithium_ion.DFN(options),
        parameter_values=params,
        experiment=experiment,
        solver=pybamm.IDAKLUSolver(rtol=float(rtol), atol=float(atol)),
        var_pts=mesh_points,
    )
    solution = simulation.solve(initial_soc=float(initial_soc), showprogress=False)
    return _convert_homogeneous_solution(
        solution,
        cycles=int(cycles),
        equivalent_cycle_factor=float(equivalent_cycle_factor),
        nominal_capacity_ah=float(params["Nominal cell capacity [A.h]"]),
        discharge_power_w=float(discharge_power_w),
        charge_power_w=charge_power_w,
        progress_callback=progress_callback,
    )


def _validate_homogeneous_inputs(
    *,
    discharge_power_w,
    charge_power_w,
    cycles,
    rest_s,
    output_period_s,
    initial_soc,
    lower_cutoff_v,
    upper_cutoff_v,
    equivalent_cycle_factor,
    rtol,
    atol,
    model_voltage_limits_v,
):
    positive = {
        "discharge_power_w": discharge_power_w,
        "charge_power_w": charge_power_w,
        "rest_s": rest_s,
        "output_period_s": output_period_s,
        "equivalent_cycle_factor": equivalent_cycle_factor,
        "rtol": rtol,
        "atol": atol,
    }
    for name, value in positive.items():
        if not isfinite(float(value)) or float(value) <= 0:
            raise ValueError(f"{name} must be positive and finite")
    if int(cycles) != cycles or cycles <= 0:
        raise ValueError("cycles must be a positive integer")
    if not 0 <= float(initial_soc) <= 1:
        raise ValueError("initial_soc must be in [0, 1]")
    if not float(lower_cutoff_v) < float(upper_cutoff_v):
        raise ValueError("lower_cutoff_v must be below upper_cutoff_v")
    if len(model_voltage_limits_v) != 2 or not (
        float(model_voltage_limits_v[0]) < float(lower_cutoff_v)
        and float(model_voltage_limits_v[1]) > float(upper_cutoff_v)
    ):
        raise ValueError("model voltage limits must sit outside protocol voltage cutoffs")


def _solution_time_series(solution, variable_name, *, default=float("nan")):
    time_s = np.asarray(solution["Time [s]"].entries, dtype=float).reshape(-1)
    try:
        values = np.asarray(solution[variable_name].entries, dtype=float)
    except (KeyError, TypeError, ValueError):
        return np.full(time_s.size, default, dtype=float)
    if values.ndim == 0:
        return np.full(time_s.size, float(values), dtype=float)
    if values.ndim == 1:
        return values.reshape(-1)
    return values.reshape(-1, values.shape[-1])[0]


def _solution_spatial_min_series(solution, variable_name):
    time_s = np.asarray(solution["Time [s]"].entries, dtype=float).reshape(-1)
    try:
        values = np.asarray(solution[variable_name].entries, dtype=float)
    except (KeyError, TypeError, ValueError):
        return np.full(time_s.size, float("nan"), dtype=float)
    if values.ndim <= 1:
        return values.reshape(-1)
    return np.nanmin(values.reshape(-1, values.shape[-1]), axis=0)


def _cumulative_absolute_integral(values, time_s):
    values = np.asarray(values, dtype=float).reshape(-1)
    time_s = np.asarray(time_s, dtype=float).reshape(-1)
    if time_s.size <= 1:
        return np.zeros(time_s.size, dtype=float)
    return np.concatenate([[0.0], cumulative_trapezoid(np.abs(values), time_s)])


def _homogeneous_step_rows(
    step_solution,
    *,
    cycle,
    equivalent_cycle,
    segment,
    target_power_w,
    nominal_capacity_ah,
):
    time_s = np.asarray(step_solution["Time [s]"].entries, dtype=float).reshape(-1)
    segment_time_s = time_s - time_s[0]
    voltage_v = _solution_time_series(step_solution, "Terminal voltage [V]")
    current_a = _solution_time_series(step_solution, "Current [A]")
    ocv_v = _solution_time_series(step_solution, "Surface open-circuit voltage [V]")
    actual_power_w = voltage_v * current_a
    capacity_ah = _cumulative_absolute_integral(current_a, time_s) / 3600.0
    negative_potential_v = _solution_spatial_min_series(
        step_solution, NEGATIVE_SURFACE_POTENTIAL_DIFFERENCE
    )
    plating_overpotential_v = _solution_spatial_min_series(
        step_solution, NEGATIVE_PLATING_OVERPOTENTIAL
    )
    porosity = {
        column_name: _solution_time_series(step_solution, variable_name)
        for column_name, variable_name in REGIONAL_POROSITY_VARIABLES.items()
    }
    rows = []
    for index in range(time_s.size):
        if abs(current_a[index]) > CURRENT_TOLERANCE_A:
            resistance_ohm = abs((ocv_v[index] - voltage_v[index]) / current_a[index])
        else:
            resistance_ohm = float("nan")
        row = {
            "sim_cycle": cycle,
            "equivalent_cycle": equivalent_cycle,
            "segment": segment,
            "segment_step": index,
            "segment_time_s": segment_time_s[index],
            "global_time_s": time_s[index],
            "segment_capacity_ah": capacity_ah[index],
            "region": "whole",
            "area_fraction": 1.0,
            "current_a": current_a[index],
            "total_current_a": current_a[index],
            "c_rate": current_a[index] / nominal_capacity_ah,
            "target_power_w": target_power_w,
            "actual_power_w": actual_power_w[index],
            "power_error_w": actual_power_w[index] - target_power_w,
            "voltage_v": voltage_v[index],
            "terminal_voltage_v": voltage_v[index],
            "ocv_v": ocv_v[index],
            "apparent_resistance_ohm": resistance_ohm,
            "iterations": 0,
            "voltage_spread_v": 0.0,
            "negative_surface_potential_difference_min_v": negative_potential_v[index],
            "negative_plating_overpotential_min_v": plating_overpotential_v[index],
        }
        row.update({name: values[index] for name, values in porosity.items()})
        rows.append(row)
    return rows


def _segment_metrics(step_solution):
    time_s = np.asarray(step_solution["Time [s]"].entries, dtype=float).reshape(-1)
    voltage_v = _solution_time_series(step_solution, "Terminal voltage [V]")
    current_a = _solution_time_series(step_solution, "Current [A]")
    power_w = voltage_v * current_a
    capacity_ah = _cumulative_absolute_integral(current_a, time_s)[-1] / 3600.0
    energy_wh = _cumulative_absolute_integral(power_w, time_s)[-1] / 3600.0
    return {
        "capacity_ah": float(capacity_ah),
        "energy_wh": float(energy_wh),
        "duration_s": float(time_s[-1] - time_s[0]),
        "end_voltage_v": float(voltage_v[-1]),
    }


def _snapshot_solution_degradation(solution, cycle, equivalent_cycle, stage, config):
    faraday_to_ah = 96485.33212 / 3600.0
    snapshot = snapshot_degradation_variables(solution)
    lam_pos_mol = safe_last_scalar(
        solution,
        "Loss of lithium due to loss of active material in positive electrode [mol]",
    )
    snapshot.update(
        {
            "sim_cycle": cycle,
            "equivalent_cycle": equivalent_cycle,
            "stage": stage,
            "region": config.name,
            "area_fraction": config.area_fraction,
            "lam_pos_ah": (
                float("nan") if not isfinite(lam_pos_mol) else lam_pos_mol * faraday_to_ah
            ),
            "lam_negative_pct": safe_last_scalar(
                solution, "Loss of active material in negative electrode [%]"
            ),
            "lam_positive_pct": safe_last_scalar(
                solution, "Loss of active material in positive electrode [%]"
            ),
            "separator_porosity_avg": safe_last_scalar(
                solution, "X-averaged separator porosity"
            ),
            "positive_porosity_avg": safe_last_scalar(
                solution, "X-averaged positive electrode porosity"
            ),
        }
    )
    return snapshot


def _convert_homogeneous_solution(
    solution,
    *,
    cycles,
    equivalent_cycle_factor,
    nominal_capacity_ah,
    discharge_power_w,
    charge_power_w,
    progress_callback,
):
    if len(solution.cycles) != cycles:
        raise RuntimeError(f"expected {cycles} cycles, PyBaMM returned {len(solution.cycles)}")
    segment_names = ("discharge", "rest_after_discharge", "charge", "rest_after_charge")
    target_powers = (discharge_power_w, 0.0, -charge_power_w, 0.0)
    whole = RegionalDFNConfig("whole", 1.0)
    step_rows = []
    cycle_rows = []
    degradation_rows = []
    first_discharge_capacity_ah = None
    for cycle_index, cycle_solution in enumerate(solution.cycles, start=1):
        if len(cycle_solution.steps) != 4:
            raise RuntimeError(
                f"cycle {cycle_index} expected 4 protocol steps, got {len(cycle_solution.steps)}"
            )
        equivalent_cycle = cycle_index * equivalent_cycle_factor
        for segment, target_power_w, step_solution in zip(
            segment_names, target_powers, cycle_solution.steps
        ):
            step_rows.extend(
                _homogeneous_step_rows(
                    step_solution,
                    cycle=cycle_index,
                    equivalent_cycle=equivalent_cycle,
                    segment=segment,
                    target_power_w=target_power_w,
                    nominal_capacity_ah=nominal_capacity_ah,
                )
            )
        discharge = _segment_metrics(cycle_solution.steps[0])
        charge = _segment_metrics(cycle_solution.steps[2])
        if first_discharge_capacity_ah is None:
            first_discharge_capacity_ah = discharge["capacity_ah"]
        cycle_step_rows = [row for row in step_rows if row["sim_cycle"] == cycle_index]
        cycle_row = {
            "sim_cycle": cycle_index,
            "equivalent_cycle": equivalent_cycle,
            "discharge_capacity_ah": discharge["capacity_ah"],
            "charge_capacity_ah": charge["capacity_ah"],
            "capacity_retention_pct": (
                discharge["capacity_ah"] / first_discharge_capacity_ah * 100.0
            ),
            "discharge_energy_wh": discharge["energy_wh"],
            "charge_energy_wh": charge["energy_wh"],
            "discharge_duration_s": discharge["duration_s"],
            "charge_duration_s": charge["duration_s"],
            "discharge_end_voltage_v": discharge["end_voltage_v"],
            "charge_end_voltage_v": charge["end_voltage_v"],
            "max_voltage_spread_v": 0.0,
            "max_abs_power_error_w": max(
                abs(row["power_error_w"]) for row in cycle_step_rows
            ),
        }
        cycle_rows.append(cycle_row)
        degradation_rows.append(
            _snapshot_solution_degradation(
                cycle_solution.steps[0], cycle_index, equivalent_cycle, "discharge_end", whole
            )
        )
        if progress_callback is not None:
            progress_callback(dict(cycle_row))
    return RegionalPowerCycleResult(
        region_configs=(whole,),
        step_rows=tuple(step_rows),
        iteration_rows=(),
        cycle_rows=tuple(cycle_rows),
        degradation_rows=tuple(degradation_rows),
        final_solutions={"whole": solution},
    )


def solve_parallel_power_split(
    regions: Sequence[RegionalCellState],
    target_power_w: float,
):
    """Solve a reduced parallel ``OCV + R`` network at constant terminal power.

    Positive power denotes discharge and negative power denotes charge. At zero
    power the total terminal current is zero, while OCV mismatch may still
    produce balancing branch currents.
    """
    region_tuple = tuple(regions)
    if not region_tuple:
        raise ValueError("regions must not be empty")
    if not isfinite(float(target_power_w)):
        raise ValueError("target_power_w must be finite")

    conductance_sum = sum(1.0 / region.resistance_ohm for region in region_tuple)
    ocv_over_r_sum = sum(region.ocv_v / region.resistance_ohm for region in region_tuple)
    equivalent_ocv_v = ocv_over_r_sum / conductance_sum
    equivalent_resistance_ohm = 1.0 / conductance_sum

    if abs(float(target_power_w)) <= CURRENT_TOLERANCE_A:
        total_current_a = 0.0
    else:
        discriminant = equivalent_ocv_v**2 - 4.0 * equivalent_resistance_ohm * float(target_power_w)
        if discriminant <= 0:
            maximum_power_w = equivalent_ocv_v**2 / (4.0 * equivalent_resistance_ohm)
            raise ValueError(
                f"target power {target_power_w:.6g} W exceeds reduced-network limit "
                f"{maximum_power_w:.6g} W"
            )
        total_current_a = 2.0 * float(target_power_w) / (equivalent_ocv_v + sqrt(discriminant))

    return solve_parallel_current_split(region_tuple, total_current_a)


def run_regional_dfn_power_cycles(
    parameter_values_by_region: Mapping[str, object],
    region_configs: Sequence[RegionalDFNConfig],
    *,
    discharge_power_w: float,
    charge_power_w: float | None = None,
    cycles: int,
    rest_s: float = 600.0,
    macro_step_s: float = 300.0,
    maximum_macro_step_s: float | None = None,
    adaptive_voltage_window_v: float = 0.15,
    initial_soc: float = 1.0,
    lower_cutoff_v: float = 2.5,
    upper_cutoff_v: float = 3.65,
    equivalent_cycle_factor: float = 1.0,
    nominal_voltage_v: float = 3.2,
    model_options: Mapping[str, object] | None = None,
    var_pts: Mapping[str, int] | None = None,
    rtol: float = 1e-6,
    atol: float = 1e-6,
    max_iterations: int = 15,
    voltage_tolerance_v: float = 1e-3,
    power_tolerance_w: float = 0.5,
    relaxation: float = 0.7,
    minimum_resistance_ohm: float = 1e-8,
    max_segment_duration_s: float = 6 * 3600.0,
    model_voltage_limits_v: tuple[float, float] = (2.0, 4.0),
    progress_callback=None,
) -> RegionalPowerCycleResult:
    """Run discharge-rest-charge-rest cycles for parallel regional DFNs.

    A private parameter set and DFN state are retained for each region. Every
    macro step is repeatedly solved from the same accepted state until actual
    DFN voltage spread and terminal-power error meet their tolerances. Voltage
    cutoffs are applied to the coupled terminal voltage, not to an individual
    branch.

    Parameters
    ----------
    parameter_values_by_region : mapping
        ``{region_name: pybamm.ParameterValues}``. Build these independently
        when regions use different temperatures or accelerated-aging factors.
    region_configs : sequence of RegionalDFNConfig
        Area fractions and local scalar parameter multipliers.
    discharge_power_w, charge_power_w : float
        Positive power magnitudes [W]. Charge defaults to the discharge value.
    cycles : int
        Number of simulated cycles.
    equivalent_cycle_factor : float
        Reporting multiplier, for example 50 accelerated real cycles per
        simulated cycle.
    maximum_macro_step_s : float or None
        When provided above ``macro_step_s``, use larger steps away from voltage
        cutoffs and during rests. ``macro_step_s`` remains the near-cutoff step.
    progress_callback : callable or None
        Optional callback receiving the completed cycle-summary dictionary.

    Returns
    -------
    RegionalPowerCycleResult
        Macro-step histories, cycle capacities, degradation snapshots, and
        final independent DFN states.
    """
    configs = _validate_inputs(
        parameter_values_by_region,
        region_configs,
        discharge_power_w=discharge_power_w,
        charge_power_w=charge_power_w,
        cycles=cycles,
        rest_s=rest_s,
        macro_step_s=macro_step_s,
        maximum_macro_step_s=maximum_macro_step_s,
        adaptive_voltage_window_v=adaptive_voltage_window_v,
        initial_soc=initial_soc,
        lower_cutoff_v=lower_cutoff_v,
        upper_cutoff_v=upper_cutoff_v,
        equivalent_cycle_factor=equivalent_cycle_factor,
        nominal_voltage_v=nominal_voltage_v,
        rtol=rtol,
        atol=atol,
        max_iterations=max_iterations,
        voltage_tolerance_v=voltage_tolerance_v,
        power_tolerance_w=power_tolerance_w,
        relaxation=relaxation,
        minimum_resistance_ohm=minimum_resistance_ohm,
        max_segment_duration_s=max_segment_duration_s,
        model_voltage_limits_v=model_voltage_limits_v,
    )
    charge_power_w = float(discharge_power_w if charge_power_w is None else charge_power_w)
    options = {"contact resistance": "true"}
    if model_options is not None:
        options.update(dict(model_options))
    mesh_points = dict(DEFAULT_REGIONAL_DFN_VAR_PTS if var_pts is None else var_pts)

    runtimes = _build_runtimes(
        parameter_values_by_region,
        configs,
        options=options,
        mesh_points=mesh_points,
        initial_soc=float(initial_soc),
        initial_total_current_a=float(discharge_power_w) / float(nominal_voltage_v),
        rtol=float(rtol),
        atol=float(atol),
        minimum_resistance_ohm=float(minimum_resistance_ohm),
        model_voltage_limits_v=model_voltage_limits_v,
    )

    step_rows = []
    iteration_rows = []
    cycle_rows = []
    degradation_rows = []
    global_time_s = 0.0
    last_terminal_voltage_v = float(upper_cutoff_v)
    first_discharge_capacity_ah = None

    for cycle in range(1, int(cycles) + 1):
        equivalent_cycle = float(cycle) * float(equivalent_cycle_factor)
        discharge = _advance_segment(
            runtimes,
            cycle=cycle,
            equivalent_cycle=equivalent_cycle,
            segment="discharge",
            target_power_w=float(discharge_power_w),
            duration_s=None,
            cutoff_v=float(lower_cutoff_v),
            cutoff_direction="lower",
            global_time_s=global_time_s,
            previous_terminal_voltage_v=last_terminal_voltage_v,
            macro_step_s=float(macro_step_s),
            maximum_macro_step_s=(
                None if maximum_macro_step_s is None else float(maximum_macro_step_s)
            ),
            adaptive_voltage_window_v=float(adaptive_voltage_window_v),
            max_segment_duration_s=float(max_segment_duration_s),
            max_iterations=int(max_iterations),
            voltage_tolerance_v=float(voltage_tolerance_v),
            power_tolerance_w=float(power_tolerance_w),
            relaxation=float(relaxation),
            minimum_resistance_ohm=float(minimum_resistance_ohm),
            step_rows=step_rows,
            iteration_rows=iteration_rows,
        )
        global_time_s = discharge["global_time_s"]
        last_terminal_voltage_v = discharge["terminal_voltage_v"]
        degradation_rows.extend(
            _snapshot_region_degradation(runtimes, cycle, equivalent_cycle, "discharge_end")
        )

        rest_after_discharge = _advance_segment(
            runtimes,
            cycle=cycle,
            equivalent_cycle=equivalent_cycle,
            segment="rest_after_discharge",
            target_power_w=0.0,
            duration_s=float(rest_s),
            cutoff_v=None,
            cutoff_direction=None,
            global_time_s=global_time_s,
            previous_terminal_voltage_v=last_terminal_voltage_v,
            macro_step_s=float(macro_step_s),
            maximum_macro_step_s=(
                None if maximum_macro_step_s is None else float(maximum_macro_step_s)
            ),
            adaptive_voltage_window_v=float(adaptive_voltage_window_v),
            max_segment_duration_s=float(max_segment_duration_s),
            max_iterations=int(max_iterations),
            voltage_tolerance_v=float(voltage_tolerance_v),
            power_tolerance_w=float(power_tolerance_w),
            relaxation=float(relaxation),
            minimum_resistance_ohm=float(minimum_resistance_ohm),
            step_rows=step_rows,
            iteration_rows=iteration_rows,
        )
        global_time_s = rest_after_discharge["global_time_s"]
        last_terminal_voltage_v = rest_after_discharge["terminal_voltage_v"]

        charge = _advance_segment(
            runtimes,
            cycle=cycle,
            equivalent_cycle=equivalent_cycle,
            segment="charge",
            target_power_w=-charge_power_w,
            duration_s=None,
            cutoff_v=float(upper_cutoff_v),
            cutoff_direction="upper",
            global_time_s=global_time_s,
            previous_terminal_voltage_v=last_terminal_voltage_v,
            macro_step_s=float(macro_step_s),
            maximum_macro_step_s=(
                None if maximum_macro_step_s is None else float(maximum_macro_step_s)
            ),
            adaptive_voltage_window_v=float(adaptive_voltage_window_v),
            max_segment_duration_s=float(max_segment_duration_s),
            max_iterations=int(max_iterations),
            voltage_tolerance_v=float(voltage_tolerance_v),
            power_tolerance_w=float(power_tolerance_w),
            relaxation=float(relaxation),
            minimum_resistance_ohm=float(minimum_resistance_ohm),
            step_rows=step_rows,
            iteration_rows=iteration_rows,
        )
        global_time_s = charge["global_time_s"]
        last_terminal_voltage_v = charge["terminal_voltage_v"]

        rest_after_charge = _advance_segment(
            runtimes,
            cycle=cycle,
            equivalent_cycle=equivalent_cycle,
            segment="rest_after_charge",
            target_power_w=0.0,
            duration_s=float(rest_s),
            cutoff_v=None,
            cutoff_direction=None,
            global_time_s=global_time_s,
            previous_terminal_voltage_v=last_terminal_voltage_v,
            macro_step_s=float(macro_step_s),
            maximum_macro_step_s=(
                None if maximum_macro_step_s is None else float(maximum_macro_step_s)
            ),
            adaptive_voltage_window_v=float(adaptive_voltage_window_v),
            max_segment_duration_s=float(max_segment_duration_s),
            max_iterations=int(max_iterations),
            voltage_tolerance_v=float(voltage_tolerance_v),
            power_tolerance_w=float(power_tolerance_w),
            relaxation=float(relaxation),
            minimum_resistance_ohm=float(minimum_resistance_ohm),
            step_rows=step_rows,
            iteration_rows=iteration_rows,
        )
        global_time_s = rest_after_charge["global_time_s"]
        last_terminal_voltage_v = rest_after_charge["terminal_voltage_v"]

        discharge_capacity_ah = discharge["capacity_ah"]
        if first_discharge_capacity_ah is None:
            first_discharge_capacity_ah = discharge_capacity_ah
        cycle_row = {
            "sim_cycle": cycle,
            "equivalent_cycle": equivalent_cycle,
            "discharge_capacity_ah": discharge_capacity_ah,
            "charge_capacity_ah": charge["capacity_ah"],
            "capacity_retention_pct": discharge_capacity_ah / first_discharge_capacity_ah * 100.0,
            "discharge_energy_wh": discharge["energy_wh"],
            "charge_energy_wh": charge["energy_wh"],
            "discharge_duration_s": discharge["elapsed_s"],
            "charge_duration_s": charge["elapsed_s"],
            "discharge_end_voltage_v": discharge["terminal_voltage_v"],
            "charge_end_voltage_v": charge["terminal_voltage_v"],
            "max_voltage_spread_v": max(
                discharge["max_voltage_spread_v"],
                rest_after_discharge["max_voltage_spread_v"],
                charge["max_voltage_spread_v"],
                rest_after_charge["max_voltage_spread_v"],
            ),
            "max_abs_power_error_w": max(
                discharge["max_abs_power_error_w"],
                rest_after_discharge["max_abs_power_error_w"],
                charge["max_abs_power_error_w"],
                rest_after_charge["max_abs_power_error_w"],
            ),
        }
        cycle_rows.append(cycle_row)
        if progress_callback is not None:
            progress_callback(dict(cycle_row))

    return RegionalPowerCycleResult(
        region_configs=configs,
        step_rows=tuple(step_rows),
        iteration_rows=tuple(iteration_rows),
        cycle_rows=tuple(cycle_rows),
        degradation_rows=tuple(degradation_rows),
        final_solutions={runtime.config.name: runtime.accepted_solution for runtime in runtimes.values()},
    )


def _build_runtimes(
    parameter_values_by_region,
    configs,
    *,
    options,
    mesh_points,
    initial_soc,
    initial_total_current_a,
    rtol,
    atol,
    minimum_resistance_ohm,
    model_voltage_limits_v,
):
    runtimes = {}
    for config in configs:
        params = _build_regional_dfn_parameter_values(parameter_values_by_region[config.name], config)
        initial_current_a = initial_total_current_a * config.area_fraction
        params.set_initial_stoichiometries(
            initial_soc,
            inplace=True,
            options=options,
            inputs={CURRENT_INPUT_NAME: initial_current_a},
        )
        params.update(
            {
                "Lower voltage cut-off [V]": float(model_voltage_limits_v[0]),
                "Upper voltage cut-off [V]": float(model_voltage_limits_v[1]),
            },
            check_already_exists=False,
        )
        model = pybamm.lithium_ion.DFN(options)
        solver = pybamm.IDAKLUSolver(rtol=rtol, atol=atol)
        simulation = pybamm.Simulation(
            model,
            parameter_values=params,
            solver=solver,
            var_pts=mesh_points,
        )
        simulation.build(inputs={CURRENT_INPUT_NAME: initial_current_a})
        contact_resistance_ohm = max(
            float(params["Contact resistance [Ohm]"]),
            minimum_resistance_ohm,
        )
        runtimes[config.name] = _RegionalRuntime(
            config=config,
            simulation=simulation,
            accepted_solution=pybamm.EmptySolution(),
            current_a=initial_current_a,
            resistance_ohm=contact_resistance_ohm,
            capacity_ah=float(params["Nominal cell capacity [A.h]"]),
        )
    return runtimes


def _select_macro_step_s(
    *,
    segment,
    terminal_voltage_v,
    cutoff_v,
    minimum_step_s,
    maximum_step_s,
    adaptive_voltage_window_v,
):
    """Choose a larger flat-region step while retaining cutoff resolution."""
    if maximum_step_s is None or maximum_step_s <= minimum_step_s:
        return float(minimum_step_s)
    if cutoff_v is None or segment.startswith("rest"):
        return float(maximum_step_s)
    distance_v = abs(float(terminal_voltage_v) - float(cutoff_v))
    if distance_v <= adaptive_voltage_window_v / 3.0:
        return float(minimum_step_s)
    if distance_v <= adaptive_voltage_window_v:
        return float(min(2.0 * minimum_step_s, maximum_step_s))
    return float(maximum_step_s)


def _advance_segment(
    runtimes,
    *,
    cycle,
    equivalent_cycle,
    segment,
    target_power_w,
    duration_s,
    cutoff_v,
    cutoff_direction,
    global_time_s,
    previous_terminal_voltage_v,
    macro_step_s,
    maximum_macro_step_s,
    adaptive_voltage_window_v,
    max_segment_duration_s,
    max_iterations,
    voltage_tolerance_v,
    power_tolerance_w,
    relaxation,
    minimum_resistance_ohm,
    step_rows,
    iteration_rows,
):
    elapsed_s = 0.0
    capacity_ah = 0.0
    energy_wh = 0.0
    step_index = 0
    max_voltage_spread_v = 0.0
    max_abs_power_error_w = 0.0
    terminal_voltage_v = float(previous_terminal_voltage_v)
    initial_currents = _segment_initial_currents(runtimes, target_power_w, terminal_voltage_v)

    while True:
        if duration_s is not None and elapsed_s >= duration_s - 1e-9:
            break
        if duration_s is None and elapsed_s >= max_segment_duration_s:
            raise RuntimeError(
                f"cycle {cycle} {segment} exceeded {max_segment_duration_s:.6g} s before cutoff"
            )
        dt_s = _select_macro_step_s(
            segment=segment,
            terminal_voltage_v=terminal_voltage_v,
            cutoff_v=cutoff_v,
            minimum_step_s=macro_step_s,
            maximum_step_s=maximum_macro_step_s,
            adaptive_voltage_window_v=adaptive_voltage_window_v,
        )
        if duration_s is not None:
            dt_s = min(dt_s, duration_s - elapsed_s)
        step_index += 1
        starting_currents = dict(initial_currents)
        while True:
            try:
                result = _solve_coupled_step(
                    runtimes,
                    dt_s=dt_s,
                    target_power_w=target_power_w,
                    initial_currents_a=starting_currents,
                    max_iterations=max_iterations,
                    voltage_tolerance_v=voltage_tolerance_v,
                    power_tolerance_w=power_tolerance_w,
                    relaxation=relaxation,
                    minimum_resistance_ohm=minimum_resistance_ohm,
                    iteration_context=(cycle, equivalent_cycle, segment, step_index),
                    iteration_rows=iteration_rows,
                )
                break
            except (_ModelSafetyEvent, _CouplingConvergenceError):
                if dt_s <= 1.0:
                    raise
                dt_s = max(1.0, dt_s / 2.0)

        crossed = _cutoff_crossed(result.terminal_voltage_v, cutoff_v, cutoff_direction)
        if crossed and cutoff_v is not None:
            low_dt_s = 0.0
            high_dt_s = dt_s
            high_result = result
            for _ in range(12):
                if (
                    abs(high_result.terminal_voltage_v - float(cutoff_v)) <= voltage_tolerance_v
                    or high_dt_s - low_dt_s <= 0.1
                ):
                    break
                trial_dt_s = (low_dt_s + high_dt_s) / 2.0
                trial_result = _solve_coupled_step(
                    runtimes,
                    dt_s=trial_dt_s,
                    target_power_w=target_power_w,
                    initial_currents_a=starting_currents,
                    max_iterations=max_iterations,
                    voltage_tolerance_v=voltage_tolerance_v,
                    power_tolerance_w=power_tolerance_w,
                    relaxation=relaxation,
                    minimum_resistance_ohm=minimum_resistance_ohm,
                    iteration_context=(cycle, equivalent_cycle, segment, step_index),
                    iteration_rows=iteration_rows,
                )
                if _cutoff_crossed(
                    trial_result.terminal_voltage_v,
                    cutoff_v,
                    cutoff_direction,
                ):
                    high_dt_s = trial_dt_s
                    high_result = trial_result
                else:
                    low_dt_s = trial_dt_s
            dt_s = high_dt_s
            result = high_result

        _accept_step(runtimes, result)
        total_current_a = sum(result.currents_a.values())
        elapsed_s += dt_s
        global_time_s += dt_s
        terminal_voltage_v = result.terminal_voltage_v
        capacity_ah += abs(total_current_a) * dt_s / 3600.0
        energy_wh += abs(result.actual_power_w) * dt_s / 3600.0
        max_voltage_spread_v = max(max_voltage_spread_v, result.voltage_spread_v)
        max_abs_power_error_w = max(max_abs_power_error_w, abs(result.power_error_w))

        for runtime in runtimes.values():
            data = result.solutions[runtime.config.name]
            row = {
                "sim_cycle": cycle,
                "equivalent_cycle": equivalent_cycle,
                "segment": segment,
                "segment_step": step_index,
                "segment_time_s": elapsed_s,
                "global_time_s": global_time_s,
                "segment_capacity_ah": capacity_ah,
                "region": runtime.config.name,
                "area_fraction": runtime.config.area_fraction,
                "current_a": result.currents_a[runtime.config.name],
                "total_current_a": total_current_a,
                "c_rate": result.currents_a[runtime.config.name] / runtime.capacity_ah,
                "target_power_w": target_power_w,
                "actual_power_w": result.actual_power_w,
                "power_error_w": result.power_error_w,
                "voltage_v": _last_solution_scalar(data, "Terminal voltage [V]"),
                "terminal_voltage_v": terminal_voltage_v,
                "ocv_v": _last_solution_scalar(data, "Surface open-circuit voltage [V]"),
                "apparent_resistance_ohm": result.resistances_ohm[runtime.config.name],
                "iterations": result.iterations,
                "voltage_spread_v": result.voltage_spread_v,
            }
            row.update(
                {
                    column_name: _last_solution_scalar(data, variable_name)
                    for column_name, variable_name in REGIONAL_POROSITY_VARIABLES.items()
                }
            )
            row.update(
                {
                    "negative_surface_potential_difference_min_v": _solution_min_scalar(
                        data, NEGATIVE_SURFACE_POTENTIAL_DIFFERENCE
                    ),
                    "negative_plating_overpotential_min_v": _solution_min_scalar(
                        data, NEGATIVE_PLATING_OVERPOTENTIAL
                    ),
                }
            )
            step_rows.append(row)

        initial_currents = dict(result.currents_a)
        if crossed:
            break

    return {
        "elapsed_s": elapsed_s,
        "global_time_s": global_time_s,
        "capacity_ah": capacity_ah,
        "energy_wh": energy_wh,
        "terminal_voltage_v": terminal_voltage_v,
        "max_voltage_spread_v": max_voltage_spread_v,
        "max_abs_power_error_w": max_abs_power_error_w,
    }


def _solution_min_scalar(solution, variable_name):
    """Return the finite spatial-time minimum of one solution variable."""
    try:
        values = np.asarray(solution[variable_name].entries, dtype=float)
    except (KeyError, TypeError, ValueError):
        return float("nan")
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    return float(np.min(finite))


def _solve_coupled_step(
    runtimes,
    *,
    dt_s,
    target_power_w,
    initial_currents_a,
    max_iterations,
    voltage_tolerance_v,
    power_tolerance_w,
    relaxation,
    minimum_resistance_ohm,
    iteration_context,
    iteration_rows,
):
    trial_currents = dict(initial_currents_a)
    cycle, equivalent_cycle, segment, segment_step = iteration_context
    linear_resistances = {
        runtime.config.name: runtime.resistance_ohm for runtime in runtimes.values()
    }
    previous_currents = None
    previous_voltages = None
    fixed_point_limit = min(max_iterations, 3) if segment == "rest_after_charge" else max_iterations

    for iteration in range(1, fixed_point_limit + 1):
        candidates, _, voltages, _ = _evaluate_trial_currents(
            runtimes,
            dt_s=dt_s,
            trial_currents=trial_currents,
            minimum_resistance_ohm=minimum_resistance_ohm,
            cycle=cycle,
            segment=segment,
        )
        voltage_by_name = dict(zip(runtimes, voltages))
        if previous_currents is not None:
            for runtime in runtimes.values():
                name = runtime.config.name
                delta_current_a = trial_currents[name] - previous_currents[name]
                minimum_delta_a = max(1e-3, runtime.capacity_ah * 1e-5)
                if abs(delta_current_a) <= minimum_delta_a:
                    continue
                candidate_resistance_ohm = -(
                    voltage_by_name[name] - previous_voltages[name]
                ) / delta_current_a
                if (
                    isfinite(candidate_resistance_ohm)
                    and minimum_resistance_ohm <= candidate_resistance_ohm <= 1.0
                ):
                    linear_resistances[name] = candidate_resistance_ohm

        states = [
            RegionalCellState(
                name=runtime.config.name,
                ocv_v=(
                    voltage_by_name[runtime.config.name]
                    + linear_resistances[runtime.config.name]
                    * trial_currents[runtime.config.name]
                ),
                resistance_ohm=linear_resistances[runtime.config.name],
                area_fraction=runtime.config.area_fraction,
            )
            for runtime in runtimes.values()
        ]

        if len(states) == 1:
            name = states[0].name
            proposal_currents = {
                name: 0.0 if abs(target_power_w) <= CURRENT_TOLERANCE_A else target_power_w / voltages[0]
            }
        else:
            try:
                proposal = solve_parallel_power_split(states, target_power_w)
            except ValueError as exc:
                raise _CouplingConvergenceError(
                    f"cycle {cycle} {segment} step {segment_step} local power split failed: {exc}"
                ) from exc
            proposal_currents = proposal.region_currents_a
        relaxed_currents = {
            runtime.config.name: (
                trial_currents[runtime.config.name]
                + relaxation
                * (proposal_currents[runtime.config.name] - trial_currents[runtime.config.name])
            )
            for runtime in runtimes.values()
        }
        terminal_voltage_v = sum(voltages) / len(voltages)
        total_current_a = sum(trial_currents.values())
        actual_power_w = terminal_voltage_v * total_current_a
        power_error_w = actual_power_w - target_power_w
        voltage_spread_v = max(voltages) - min(voltages)
        current_update_a = max(
            abs(relaxed_currents[name] - trial_currents[name]) for name in trial_currents
        )
        converged = (
            voltage_spread_v <= voltage_tolerance_v
            and abs(power_error_w) <= power_tolerance_w
        )
        iteration_rows.append(
            {
                "sim_cycle": cycle,
                "equivalent_cycle": equivalent_cycle,
                "segment": segment,
                "segment_step": segment_step,
                "iteration": iteration,
                "voltage_spread_v": voltage_spread_v,
                "actual_power_w": actual_power_w,
                "power_error_w": power_error_w,
                "current_update_a": current_update_a,
                "converged": converged,
                "solver": "fixed_point",
            }
        )
        if converged:
            return _CoupledStepResult(
                solutions=candidates,
                currents_a=dict(trial_currents),
                resistances_ohm=dict(linear_resistances),
                terminal_voltage_v=terminal_voltage_v,
                voltage_spread_v=voltage_spread_v,
                actual_power_w=actual_power_w,
                power_error_w=power_error_w,
                iterations=iteration,
            )
        previous_currents = dict(trial_currents)
        previous_voltages = dict(voltage_by_name)
        trial_currents = relaxed_currents

    return _solve_coupled_step_least_squares(
        runtimes,
        dt_s=dt_s,
        target_power_w=target_power_w,
        initial_currents_a=trial_currents,
        voltage_tolerance_v=voltage_tolerance_v,
        power_tolerance_w=power_tolerance_w,
        minimum_resistance_ohm=minimum_resistance_ohm,
        iteration_context=iteration_context,
        iteration_rows=iteration_rows,
        fixed_point_iterations=fixed_point_limit,
    )


def _evaluate_trial_currents(
    runtimes,
    *,
    dt_s,
    trial_currents,
    minimum_resistance_ohm,
    cycle,
    segment,
):
    candidates = {}
    states = []
    voltages = []
    resistances = {}
    for runtime in runtimes.values():
        name = runtime.config.name
        current_a = float(trial_currents[name])
        solution = runtime.simulation.step(
            dt_s,
            starting_solution=runtime.accepted_solution,
            save=False,
            inputs={CURRENT_INPUT_NAME: current_a},
        )
        if solution.termination != "final time":
            raise _ModelSafetyEvent(
                f"region {name!r} hit model safety event during cycle {cycle} "
                f"{segment}: {solution.termination}"
            )
        voltage_v = _last_solution_scalar(solution, "Terminal voltage [V]")
        ocv_v = _last_solution_scalar(solution, "Surface open-circuit voltage [V]")
        if abs(current_a) > CURRENT_TOLERANCE_A:
            resistance_ohm = max(
                abs((ocv_v - voltage_v) / current_a),
                minimum_resistance_ohm,
            )
        else:
            resistance_ohm = runtime.resistance_ohm
        candidates[name] = solution
        resistances[name] = resistance_ohm
        voltages.append(voltage_v)
        states.append(
            RegionalCellState(
                name=name,
                ocv_v=ocv_v,
                resistance_ohm=resistance_ohm,
                area_fraction=runtime.config.area_fraction,
            )
        )
    return candidates, states, voltages, resistances


def _solve_coupled_step_least_squares(
    runtimes,
    *,
    dt_s,
    target_power_w,
    initial_currents_a,
    voltage_tolerance_v,
    power_tolerance_w,
    minimum_resistance_ohm,
    iteration_context,
    iteration_rows,
    fixed_point_iterations,
):
    cycle, equivalent_cycle, segment, segment_step = iteration_context
    names = tuple(runtimes)
    full_x0 = np.asarray([initial_currents_a[name] for name in names], dtype=float)
    full_current_scales = np.asarray(
        [max(1.0, runtimes[name].capacity_ah) for name in names],
        dtype=float,
    )
    reduced_rest_system = abs(target_power_w) <= CURRENT_TOLERANCE_A and len(names) > 1
    if reduced_rest_system:
        x0 = full_x0[:-1]
        current_scales = full_current_scales[:-1]
        current_limits = np.maximum(20.0 * current_scales, 2.0 * np.abs(x0) + 1.0)
    else:
        x0 = full_x0
        current_scales = full_current_scales
        current_limits = np.maximum(5.0 * current_scales, 2.0 * np.abs(x0) + 1.0)
    evaluation_count = 0
    latest = {}

    def residual(currents):
        nonlocal evaluation_count, latest
        evaluation_count += 1
        if reduced_rest_system:
            full_currents = np.concatenate([currents, [-float(np.sum(currents))]])
        else:
            full_currents = currents
        trial_currents = {
            name: float(full_currents[index]) for index, name in enumerate(names)
        }
        candidates, _, voltages, resistances = _evaluate_trial_currents(
            runtimes,
            dt_s=dt_s,
            trial_currents=trial_currents,
            minimum_resistance_ohm=minimum_resistance_ohm,
            cycle=cycle,
            segment=segment,
        )
        terminal_voltage_v = float(np.mean(voltages))
        total_current_a = float(np.sum(full_currents))
        actual_power_w = terminal_voltage_v * total_current_a
        power_error_w = actual_power_w - target_power_w
        voltage_spread_v = max(voltages) - min(voltages)
        scaled_residuals = [
            (voltage_v - voltages[-1]) / voltage_tolerance_v
            for voltage_v in voltages[:-1]
        ]
        if not reduced_rest_system:
            scaled_residuals.append(power_error_w / power_tolerance_w)
        latest = {
            "solutions": candidates,
            "currents_a": trial_currents,
            "resistances_ohm": resistances,
            "terminal_voltage_v": terminal_voltage_v,
            "voltage_spread_v": voltage_spread_v,
            "actual_power_w": actual_power_w,
            "power_error_w": power_error_w,
        }
        iteration_rows.append(
            {
                "sim_cycle": cycle,
                "equivalent_cycle": equivalent_cycle,
                "segment": segment,
                "segment_step": segment_step,
                "iteration": fixed_point_iterations + evaluation_count,
                "voltage_spread_v": voltage_spread_v,
                "actual_power_w": actual_power_w,
                "power_error_w": power_error_w,
                "current_update_a": float("nan"),
                "converged": (
                    voltage_spread_v <= voltage_tolerance_v
                    and abs(power_error_w) <= power_tolerance_w
                ),
                "solver": "least_squares",
            }
        )
        return np.asarray(scaled_residuals, dtype=float)

    optimum = least_squares(
        residual,
        x0,
        bounds=(-current_limits, current_limits),
        x_scale=current_scales,
        max_nfev=60 if reduced_rest_system else max(12, 5 * len(names)),
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
    )
    residual(optimum.x)
    if (
        latest["voltage_spread_v"] > voltage_tolerance_v
        or abs(latest["power_error_w"]) > power_tolerance_w
    ):
        raise _CouplingConvergenceError(
            f"cycle {cycle} {segment} step {segment_step} nonlinear coupling failed; "
            f"voltage spread={latest['voltage_spread_v']:.6g} V, "
            f"power error={latest['power_error_w']:.6g} W, status={optimum.status}, "
            f"nfev={optimum.nfev}, currents={latest['currents_a']}"
        )
    return _CoupledStepResult(
        solutions=latest["solutions"],
        currents_a=latest["currents_a"],
        resistances_ohm=latest["resistances_ohm"],
        terminal_voltage_v=latest["terminal_voltage_v"],
        voltage_spread_v=latest["voltage_spread_v"],
        actual_power_w=latest["actual_power_w"],
        power_error_w=latest["power_error_w"],
        iterations=fixed_point_iterations + evaluation_count,
    )


def _accept_step(runtimes, result):
    for runtime in runtimes.values():
        name = runtime.config.name
        runtime.accepted_solution = result.solutions[name]
        runtime.current_a = result.currents_a[name]
        runtime.resistance_ohm = result.resistances_ohm[name]


def _segment_initial_currents(runtimes, target_power_w, terminal_voltage_v):
    if abs(target_power_w) <= CURRENT_TOLERANCE_A:
        return {runtime.config.name: 0.0 for runtime in runtimes.values()}
    total_current_a = target_power_w / terminal_voltage_v
    return {
        runtime.config.name: total_current_a * runtime.config.area_fraction
        for runtime in runtimes.values()
    }


def _cutoff_crossed(voltage_v, cutoff_v, direction):
    if cutoff_v is None:
        return False
    if direction == "lower":
        return voltage_v <= cutoff_v
    if direction == "upper":
        return voltage_v >= cutoff_v
    raise ValueError(f"unknown cutoff direction {direction!r}")


def _snapshot_region_degradation(runtimes, cycle, equivalent_cycle, stage):
    rows = []
    faraday_to_ah = 96485.33212 / 3600.0
    for runtime in runtimes.values():
        solution = runtime.accepted_solution
        snapshot = snapshot_degradation_variables(solution)
        lam_pos_mol = safe_last_scalar(
            solution,
            "Loss of lithium due to loss of active material in positive electrode [mol]",
        )
        snapshot.update(
            {
                "sim_cycle": cycle,
                "equivalent_cycle": equivalent_cycle,
                "stage": stage,
                "region": runtime.config.name,
                "area_fraction": runtime.config.area_fraction,
                "lam_pos_ah": (
                    float("nan") if not isfinite(lam_pos_mol) else lam_pos_mol * faraday_to_ah
                ),
                "lam_negative_pct": safe_last_scalar(
                    solution,
                    "Loss of active material in negative electrode [%]",
                ),
                "lam_positive_pct": safe_last_scalar(
                    solution,
                    "Loss of active material in positive electrode [%]",
                ),
                "separator_porosity_avg": safe_last_scalar(
                    solution,
                    "X-averaged separator porosity",
                ),
                "positive_porosity_avg": safe_last_scalar(
                    solution,
                    "X-averaged positive electrode porosity",
                ),
            }
        )
        rows.append(snapshot)
    return rows


def _validate_inputs(
    parameter_values_by_region,
    region_configs,
    *,
    discharge_power_w,
    charge_power_w,
    cycles,
    rest_s,
    macro_step_s,
    maximum_macro_step_s,
    adaptive_voltage_window_v,
    initial_soc,
    lower_cutoff_v,
    upper_cutoff_v,
    equivalent_cycle_factor,
    nominal_voltage_v,
    rtol,
    atol,
    max_iterations,
    voltage_tolerance_v,
    power_tolerance_w,
    relaxation,
    minimum_resistance_ohm,
    max_segment_duration_s,
    model_voltage_limits_v,
):
    configs = tuple(region_configs)
    if not configs or not all(isinstance(config, RegionalDFNConfig) for config in configs):
        raise TypeError("region_configs must contain RegionalDFNConfig instances")
    names = [config.name for config in configs]
    if len(names) != len(set(names)):
        raise ValueError(f"region names must be unique; got {names}")
    area_sum = sum(config.area_fraction for config in configs)
    if abs(area_sum - 1.0) > AREA_SUM_TOLERANCE:
        raise ValueError(f"regional area fractions must sum to 1.0; got {area_sum:.12g}")
    missing = [name for name in names if name not in parameter_values_by_region]
    if missing:
        raise KeyError(f"parameter_values_by_region missing regions: {missing}")

    positive_values = {
        "discharge_power_w": discharge_power_w,
        "rest_s": rest_s,
        "macro_step_s": macro_step_s,
        "adaptive_voltage_window_v": adaptive_voltage_window_v,
        "equivalent_cycle_factor": equivalent_cycle_factor,
        "nominal_voltage_v": nominal_voltage_v,
        "rtol": rtol,
        "atol": atol,
        "voltage_tolerance_v": voltage_tolerance_v,
        "power_tolerance_w": power_tolerance_w,
        "minimum_resistance_ohm": minimum_resistance_ohm,
        "max_segment_duration_s": max_segment_duration_s,
    }
    if maximum_macro_step_s is not None:
        positive_values["maximum_macro_step_s"] = maximum_macro_step_s
        if float(maximum_macro_step_s) < float(macro_step_s):
            raise ValueError("maximum_macro_step_s must be at least macro_step_s")
    if charge_power_w is not None:
        positive_values["charge_power_w"] = charge_power_w
    for name, value in positive_values.items():
        if not isfinite(float(value)) or float(value) <= 0:
            raise ValueError(f"{name} must be positive and finite")
    if int(cycles) != cycles or cycles <= 0:
        raise ValueError("cycles must be a positive integer")
    if int(max_iterations) != max_iterations or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    if not 0 <= float(initial_soc) <= 1:
        raise ValueError("initial_soc must be in [0, 1]")
    if not float(lower_cutoff_v) < float(upper_cutoff_v):
        raise ValueError("lower_cutoff_v must be below upper_cutoff_v")
    if not 0 < float(relaxation) <= 1:
        raise ValueError("relaxation must be in (0, 1]")
    if len(model_voltage_limits_v) != 2:
        raise ValueError("model_voltage_limits_v must contain lower and upper limits")
    if not (
        float(model_voltage_limits_v[0]) < float(lower_cutoff_v)
        and float(model_voltage_limits_v[1]) > float(upper_cutoff_v)
    ):
        raise ValueError("model voltage limits must sit outside coupled voltage cutoffs")
    return configs


__all__ = [
    "RegionalPowerCycleResult",
    "run_homogeneous_dfn_power_cycles",
    "run_regional_dfn_power_cycles",
    "solve_parallel_power_split",
]
