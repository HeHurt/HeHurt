"""Regional parallel-cell coupling utilities.

This module provides the electrical core for approximating one large cell as
several independent PyBaMM 1D regions connected in parallel.  It follows the
same reduced circuit idea used by liionpack: each region is represented by an
OCV voltage source plus a series resistance, and all regions share the same
terminal voltage.

Current sign convention: positive current means discharge from the region to
the external circuit.  For each region k,

    V_cell = E_k - I_k * R_k

and the solver enforces ``sum(I_k) == total_current_a``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, isfinite
from typing import Mapping, Sequence

import pybamm


AREA_SUM_TOLERANCE = 1e-6
CURRENT_TOLERANCE_A = 1e-9
DEFAULT_REGIONAL_DFN_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
CURRENT_INPUT_NAME = "Current function [A]"
REGIONAL_POROSITY_VARIABLES = {
    "negative_porosity": "X-averaged negative electrode porosity",
    "separator_porosity": "X-averaged separator porosity",
    "positive_porosity": "X-averaged positive electrode porosity",
}


@dataclass(frozen=True)
class RegionalCellState:
    """Electrical state of one pseudo-2D/3D region in a parallel cell.

    Parameters
    ----------
    name : str
        Region label, for example ``"corner"``, ``"middle"`` or ``"top"``.
    ocv_v : float
        Region open-circuit voltage [V] at the current state.
    resistance_ohm : float
        Region-level apparent resistance [Ohm]. If a full-cell resistance is
        scaled by area fraction f, use ``R_region = R_full / f``.
    area_fraction : float
        Geometric area fraction represented by this region.
    capacity_ah : float or None
        Region-level remaining capacity [A.h]. Use ``Q_full * f * SOH`` when
        creating area-scaled regions.
    lower_current_a, upper_current_a : float or None
        Optional branch current bounds [A]. Set both to 0 to electrically
        disconnect a failed region while keeping its capacity accounting.
    """

    name: str
    ocv_v: float
    resistance_ohm: float
    area_fraction: float = 1.0
    capacity_ah: float | None = None
    lower_current_a: float | None = None
    upper_current_a: float | None = None

    def __post_init__(self):
        if not str(self.name):
            raise ValueError("region name must be non-empty")
        _validate_finite("ocv_v", self.ocv_v)
        _validate_positive("resistance_ohm", self.resistance_ohm)
        _validate_positive("area_fraction", self.area_fraction)
        if self.capacity_ah is not None:
            _validate_non_negative("capacity_ah", self.capacity_ah)
        if self.lower_current_a is not None:
            _validate_finite("lower_current_a", self.lower_current_a)
        if self.upper_current_a is not None:
            _validate_finite("upper_current_a", self.upper_current_a)
        if (
            self.lower_current_a is not None
            and self.upper_current_a is not None
            and self.lower_current_a > self.upper_current_a
        ):
            raise ValueError(f"{self.name}: lower_current_a must be <= upper_current_a")


@dataclass(frozen=True)
class ParallelSplitResult:
    """Result of equal-voltage current splitting across parallel regions."""

    terminal_voltage_v: float
    total_current_a: float
    region_currents_a: Mapping[str, float]
    region_overpotentials_v: Mapping[str, float]
    region_powers_w: Mapping[str, float]
    clamped_regions: tuple[str, ...]
    regions: tuple[RegionalCellState, ...]

    def rows(self):
        """Return row dictionaries suitable for DataFrame/report construction."""
        rows = []
        for region in self.regions:
            current_a = self.region_currents_a[region.name]
            c_rate = None
            if region.capacity_ah is not None and region.capacity_ah > 0:
                c_rate = current_a / region.capacity_ah
            rows.append(
                {
                    "region": region.name,
                    "area_fraction": region.area_fraction,
                    "capacity_ah": region.capacity_ah,
                    "ocv_v": region.ocv_v,
                    "resistance_ohm": region.resistance_ohm,
                    "current_a": current_a,
                    "c_rate": c_rate,
                    "overpotential_v": self.region_overpotentials_v[region.name],
                    "power_w": self.region_powers_w[region.name],
                    "clamped": region.name in self.clamped_regions,
                }
            )
        return rows


@dataclass(frozen=True)
class RegionalDFNConfig:
    """Geometry and parameter perturbations for one regional DFN branch.

    ``area_fraction`` scales electrode width and nominal capacity. Absolute
    contact resistance is divided by the same fraction so identical branches
    recover the original full-cell behavior when connected in parallel.
    ``parameter_multipliers`` is applied only to this region's parameter copy;
    it is intended for scalar heterogeneity such as local porosity loss.
    """

    name: str
    area_fraction: float
    parameter_multipliers: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not str(self.name):
            raise ValueError("region name must be non-empty")
        _validate_positive("area_fraction", self.area_fraction)
        for parameter_name, multiplier in self.parameter_multipliers.items():
            if not str(parameter_name):
                raise ValueError("parameter multiplier name must be non-empty")
            _validate_positive(f"{self.name}.{parameter_name} multiplier", multiplier)


@dataclass(frozen=True)
class RegionalDFNCouplingResult:
    """Time history from independently solved DFNs coupled at their terminals."""

    region_configs: tuple[RegionalDFNConfig, ...]
    step_rows: tuple[Mapping[str, object], ...]
    iteration_rows: tuple[Mapping[str, object], ...]
    final_solutions: Mapping[str, object]

    def steps(self):
        """Return accepted macro-step rows for DataFrame construction."""
        return [dict(row) for row in self.step_rows]

    def iterations(self):
        """Return nonlinear iteration rows for DataFrame construction."""
        return [dict(row) for row in self.iteration_rows]


def build_area_scaled_regions(
    area_fractions: Mapping[str, float],
    *,
    nominal_capacity_ah: float,
    base_ocv_v: float | Mapping[str, float],
    base_resistance_ohm: float,
    resistance_multipliers: float | Mapping[str, float] = 1.0,
    capacity_retention: float | Mapping[str, float] = 1.0,
    current_bounds_a: Mapping[str, tuple[float | None, float | None]] | None = None,
    require_area_sum_one: bool = True,
) -> tuple[RegionalCellState, ...]:
    """Build region states from area fractions and full-cell reference values.

    The returned resistance is scaled as ``R_region = R_full / area_fraction``.
    Therefore regions with identical OCV and multiplier recover the original
    full-cell resistance when connected in parallel.

    Parameters
    ----------
    area_fractions : mapping
        ``{region_name: geometric_area_fraction}``.
    nominal_capacity_ah : float
        Full-cell nominal capacity [A.h].
    base_ocv_v : float or mapping
        Common OCV or per-region OCV values [V].
    base_resistance_ohm : float
        Full-cell reference resistance [Ohm].
    resistance_multipliers : float or mapping
        Per-region aging/transport multiplier. A clogged region should have a
        multiplier greater than 1.
    capacity_retention : float or mapping
        Per-region remaining capacity ratio. A fully failed region can use 0.
    current_bounds_a : mapping or None
        Optional ``{region_name: (lower_current_a, upper_current_a)}``.
    require_area_sum_one : bool
        When true, reject area fractions that do not sum to one.

    Returns
    -------
    tuple[RegionalCellState, ...]
        Region-level states ready for :func:`solve_parallel_current_split`.
    """
    if not area_fractions:
        raise ValueError("area_fractions must not be empty")
    _validate_positive("nominal_capacity_ah", nominal_capacity_ah)
    _validate_positive("base_resistance_ohm", base_resistance_ohm)

    total_area_fraction = sum(float(value) for value in area_fractions.values())
    if require_area_sum_one and abs(total_area_fraction - 1.0) > AREA_SUM_TOLERANCE:
        raise ValueError(
            "area fractions must sum to 1.0; "
            f"got {total_area_fraction:.12g}. Set require_area_sum_one=False to allow this."
        )

    regions = []
    for name, raw_fraction in area_fractions.items():
        fraction = float(raw_fraction)
        _validate_positive(f"{name}.area_fraction", fraction)
        ocv_v = float(_lookup_region_value(base_ocv_v, name, "base_ocv_v"))
        multiplier = float(_lookup_region_value(resistance_multipliers, name, "resistance_multipliers"))
        retention = float(_lookup_region_value(capacity_retention, name, "capacity_retention"))
        _validate_positive(f"{name}.resistance_multiplier", multiplier)
        _validate_non_negative(f"{name}.capacity_retention", retention)

        lower_current_a = None
        upper_current_a = None
        if current_bounds_a is not None and name in current_bounds_a:
            lower_current_a, upper_current_a = current_bounds_a[name]

        regions.append(
            RegionalCellState(
                name=str(name),
                ocv_v=ocv_v,
                resistance_ohm=base_resistance_ohm / fraction * multiplier,
                area_fraction=fraction,
                capacity_ah=nominal_capacity_ah * fraction * retention,
                lower_current_a=lower_current_a,
                upper_current_a=upper_current_a,
            )
        )
    return tuple(regions)


def solve_parallel_current_split(
    regions: Sequence[RegionalCellState],
    total_current_a: float,
    *,
    tolerance_a: float = CURRENT_TOLERANCE_A,
) -> ParallelSplitResult:
    """Solve equal-voltage current splitting for parallel regional branches.

    Positive ``total_current_a`` means discharge. Negative current means charge.
    Optional branch current bounds are handled with a small active-set loop.

    Parameters
    ----------
    regions : sequence of RegionalCellState
        Parallel branches to couple.
    total_current_a : float
        Total terminal current [A].
    tolerance_a : float
        Absolute current tolerance for active-set bound checks.

    Returns
    -------
    ParallelSplitResult
        Terminal voltage and region current split.
    """
    _validate_finite("total_current_a", total_current_a)
    _validate_positive("tolerance_a", tolerance_a)
    region_tuple = _validate_regions(regions)
    active = set(range(len(region_tuple)))
    clamped_currents: dict[int, float] = {}

    for _ in range(len(region_tuple) + 1):
        if not active:
            clamped_total = sum(clamped_currents.values())
            raise ValueError(
                "current bounds leave no active branch to determine terminal voltage; "
                f"clamped current is {clamped_total:.12g} A, target is {total_current_a:.12g} A"
            )

        conductance_sum = sum(1.0 / region_tuple[i].resistance_ohm for i in active)
        ocv_over_r_sum = sum(region_tuple[i].ocv_v / region_tuple[i].resistance_ohm for i in active)
        clamped_total = sum(clamped_currents.values())
        terminal_voltage_v = (ocv_over_r_sum + clamped_total - total_current_a) / conductance_sum

        currents = dict(clamped_currents)
        violation = None
        violation_size = 0.0
        for i in sorted(active):
            region = region_tuple[i]
            current_a = (region.ocv_v - terminal_voltage_v) / region.resistance_ohm
            currents[i] = current_a
            lower, upper = _current_bounds(region)
            if current_a < lower - tolerance_a and lower - current_a > violation_size:
                violation = (i, lower)
                violation_size = lower - current_a
            if current_a > upper + tolerance_a and current_a - upper > violation_size:
                violation = (i, upper)
                violation_size = current_a - upper

        if violation is None:
            return _build_split_result(region_tuple, currents, terminal_voltage_v, total_current_a, clamped_currents)

        index, bound = violation
        clamped_currents[index] = bound
        active.remove(index)

    raise RuntimeError("parallel current split active-set solver did not converge")


def run_regional_dfn_coupling(
    base_parameter_values,
    region_configs: Sequence[RegionalDFNConfig],
    *,
    total_current_a: float,
    duration_s: float,
    macro_step_s: float = 60.0,
    initial_soc: float = 0.5,
    model_options: Mapping[str, object] | None = None,
    var_pts: Mapping[str, int] | None = None,
    rtol: float = 1e-6,
    atol: float = 1e-6,
    max_iterations: int = 12,
    kcl_tolerance_a: float = 1e-6,
    voltage_tolerance_v: float = 1e-3,
    relaxation: float = 0.7,
    minimum_resistance_ohm: float = 1e-8,
) -> RegionalDFNCouplingResult:
    """Run independent regional DFNs with equal-voltage current coupling.

    Each macro step is solved by waveform relaxation. Every branch is repeatedly
    advanced from the same previously accepted solution, so failed trial currents
    do not advance electrochemical state. The branch currents are updated from the
    liionpack-style apparent ``OCV + R`` network and accepted only when Kirchhoff's
    current law and the directly evaluated DFN terminal voltages both converge.

    Positive current denotes discharge. This first implementation supports a
    non-zero constant total current and an isothermal DFN in each region.

    Parameters
    ----------
    base_parameter_values : pybamm.ParameterValues
        Full-cell parameter set. A private copy is made for every region.
    region_configs : sequence of RegionalDFNConfig
        Region area fractions and optional scalar parameter multipliers.
    total_current_a : float
        Full-cell terminal current [A], positive for discharge.
    duration_s, macro_step_s : float
        Total simulated duration and coupling interval [s].
    initial_soc : float
        Common initial SOC in ``[0, 1]``.
    model_options, var_pts : mapping or None
        PyBaMM DFN options and mesh resolution. Contact resistance is enabled by
        default and ``DEFAULT_REGIONAL_DFN_VAR_PTS`` is used by default.
    rtol, atol : float
        IDAKLU solver tolerances.
    max_iterations : int
        Maximum current-redistribution iterations per macro step.
    kcl_tolerance_a, voltage_tolerance_v : float
        Acceptance tolerances for current balance and regional voltage spread.
    relaxation : float
        Current-update relaxation in ``(0, 1]``.
    minimum_resistance_ohm : float
        Floor for apparent regional resistance.

    Returns
    -------
    RegionalDFNCouplingResult
        Accepted step history, full iteration history, and final branch states.
    """
    _validate_finite("total_current_a", total_current_a)
    if abs(float(total_current_a)) <= CURRENT_TOLERANCE_A:
        raise ValueError("total_current_a must be non-zero for DFN coupling")
    _validate_positive("duration_s", duration_s)
    _validate_positive("macro_step_s", macro_step_s)
    _validate_positive("rtol", rtol)
    _validate_positive("atol", atol)
    _validate_positive("kcl_tolerance_a", kcl_tolerance_a)
    _validate_positive("voltage_tolerance_v", voltage_tolerance_v)
    _validate_positive("minimum_resistance_ohm", minimum_resistance_ohm)
    if not 0 <= float(initial_soc) <= 1:
        raise ValueError("initial_soc must be in [0, 1]")
    if int(max_iterations) != max_iterations or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    if not 0 < float(relaxation) <= 1:
        raise ValueError("relaxation must be in (0, 1]")

    configs = _validate_regional_dfn_configs(region_configs)
    options = {"contact resistance": "true"}
    if model_options is not None:
        options.update(dict(model_options))
    mesh_points = dict(DEFAULT_REGIONAL_DFN_VAR_PTS if var_pts is None else var_pts)

    simulations = {}
    accepted_solutions = {}
    accepted_currents = {}
    accepted_resistances = {}
    for config in configs:
        current_a = float(total_current_a) * config.area_fraction
        params = _build_regional_dfn_parameter_values(base_parameter_values, config)
        model = pybamm.lithium_ion.DFN(options)
        solver = pybamm.IDAKLUSolver(rtol=rtol, atol=atol)
        simulation = pybamm.Simulation(
            model,
            parameter_values=params,
            solver=solver,
            var_pts=mesh_points,
        )
        simulation.build(initial_soc=initial_soc, inputs={CURRENT_INPUT_NAME: current_a})
        simulations[config.name] = simulation
        accepted_solutions[config.name] = pybamm.EmptySolution()
        accepted_currents[config.name] = current_a

    step_rows = []
    iteration_rows = []
    step_count = int(ceil(float(duration_s) / float(macro_step_s)))
    elapsed_s = 0.0

    for step_index in range(1, step_count + 1):
        dt_s = min(float(macro_step_s), float(duration_s) - elapsed_s)
        trial_currents = dict(accepted_currents)
        converged_data = None

        for iteration in range(1, int(max_iterations) + 1):
            candidate_data = {}
            electrical_states = []
            voltages = []
            for config in configs:
                name = config.name
                current_a = trial_currents[name]
                solution = simulations[name].step(
                    dt_s,
                    starting_solution=accepted_solutions[name],
                    save=False,
                    inputs={CURRENT_INPUT_NAME: current_a},
                )
                if solution.termination != "final time":
                    raise RuntimeError(
                        f"region {name!r} terminated at step {step_index}: "
                        f"{solution.termination}"
                    )
                voltage_v = _last_solution_scalar(solution, "Terminal voltage [V]")
                ocv_v = _last_solution_scalar(solution, "Surface open-circuit voltage [V]")
                porosity_values = {
                    column_name: _last_solution_scalar(solution, variable_name)
                    for column_name, variable_name in REGIONAL_POROSITY_VARIABLES.items()
                }
                if abs(current_a) > CURRENT_TOLERANCE_A:
                    resistance_ohm = max(
                        abs((ocv_v - voltage_v) / current_a),
                        float(minimum_resistance_ohm),
                    )
                else:
                    resistance_ohm = accepted_resistances.get(name, float(minimum_resistance_ohm))

                candidate_data[name] = {
                    "solution": solution,
                    "voltage_v": voltage_v,
                    "ocv_v": ocv_v,
                    "resistance_ohm": resistance_ohm,
                    **porosity_values,
                }
                electrical_states.append(
                    RegionalCellState(
                        name=name,
                        ocv_v=ocv_v,
                        resistance_ohm=resistance_ohm,
                        area_fraction=config.area_fraction,
                    )
                )
                voltages.append(voltage_v)

            split = solve_parallel_current_split(electrical_states, float(total_current_a))
            proposal_currents = dict(split.region_currents_a)
            relaxed_currents = {
                config.name: (
                    trial_currents[config.name]
                    + float(relaxation)
                    * (proposal_currents[config.name] - trial_currents[config.name])
                )
                for config in configs
            }
            kcl_error_a = abs(sum(trial_currents.values()) - float(total_current_a))
            voltage_spread_v = max(voltages) - min(voltages)
            current_update_a = max(
                abs(relaxed_currents[name] - trial_currents[name]) for name in trial_currents
            )
            converged = (
                kcl_error_a <= float(kcl_tolerance_a)
                and voltage_spread_v <= float(voltage_tolerance_v)
            )
            step_end_s = float(next(iter(candidate_data.values()))["solution"].t[-1])

            for config in configs:
                name = config.name
                data = candidate_data[name]
                iteration_rows.append(
                    {
                        "step": step_index,
                        "step_end_s": step_end_s,
                        "iteration": iteration,
                        "region": name,
                        "current_a": trial_currents[name],
                        "proposal_current_a": proposal_currents[name],
                        "relaxed_current_a": relaxed_currents[name],
                        "current_update_a": current_update_a,
                        "voltage_v": data["voltage_v"],
                        "ocv_v": data["ocv_v"],
                        "apparent_resistance_ohm": data["resistance_ohm"],
                        **{column_name: data[column_name] for column_name in REGIONAL_POROSITY_VARIABLES},
                        "kcl_error_a": kcl_error_a,
                        "voltage_spread_v": voltage_spread_v,
                        "converged": converged,
                    }
                )

            if converged:
                converged_data = candidate_data
                accepted_currents = dict(trial_currents)
                break
            trial_currents = relaxed_currents

        if converged_data is None:
            raise RuntimeError(
                f"regional DFN coupling did not converge at step {step_index} "
                f"within {max_iterations} iterations; last voltage spread was "
                f"{voltage_spread_v:.6g} V"
            )

        accepted_solutions = {
            name: data["solution"] for name, data in converged_data.items()
        }
        accepted_resistances = {
            name: data["resistance_ohm"] for name, data in converged_data.items()
        }
        terminal_voltage_v = sum(
            data["voltage_v"] for data in converged_data.values()
        ) / len(converged_data)
        elapsed_s += dt_s

        for config in configs:
            name = config.name
            data = converged_data[name]
            step_rows.append(
                {
                    "step": step_index,
                    "time_s": float(data["solution"].t[-1]),
                    "region": name,
                    "area_fraction": config.area_fraction,
                    "current_a": accepted_currents[name],
                    "c_rate": accepted_currents[name]
                    / (float(base_parameter_values["Nominal cell capacity [A.h]"]) * config.area_fraction),
                    "voltage_v": data["voltage_v"],
                    "terminal_voltage_v": terminal_voltage_v,
                    "ocv_v": data["ocv_v"],
                    "apparent_resistance_ohm": data["resistance_ohm"],
                    **{column_name: data[column_name] for column_name in REGIONAL_POROSITY_VARIABLES},
                    "iterations": iteration,
                    "kcl_error_a": kcl_error_a,
                    "voltage_spread_v": voltage_spread_v,
                }
            )

    return RegionalDFNCouplingResult(
        region_configs=configs,
        step_rows=tuple(step_rows),
        iteration_rows=tuple(iteration_rows),
        final_solutions=dict(accepted_solutions),
    )


def aggregate_regional_capacity_ah(regions: Sequence[RegionalCellState]) -> float:
    """Return total remaining capacity from region-level capacities [A.h]."""
    region_tuple = _validate_regions(regions)
    total_capacity_ah = 0.0
    missing = []
    for region in region_tuple:
        if region.capacity_ah is None:
            missing.append(region.name)
        else:
            total_capacity_ah += float(region.capacity_ah)
    if missing:
        raise ValueError(f"capacity_ah is missing for regions: {missing}")
    return total_capacity_ah


def _validate_regional_dfn_configs(region_configs):
    if not region_configs:
        raise ValueError("region_configs must not be empty")
    configs = tuple(region_configs)
    if not all(isinstance(config, RegionalDFNConfig) for config in configs):
        raise TypeError("region_configs must contain RegionalDFNConfig instances")
    names = [config.name for config in configs]
    if len(names) != len(set(names)):
        raise ValueError(f"region names must be unique; got {names}")
    area_sum = sum(config.area_fraction for config in configs)
    if abs(area_sum - 1.0) > AREA_SUM_TOLERANCE:
        raise ValueError(f"regional DFN area fractions must sum to 1.0; got {area_sum:.12g}")
    return configs


def _build_regional_dfn_parameter_values(base_parameter_values, config):
    params = base_parameter_values.copy()
    try:
        full_width_m = float(params["Electrode width [m]"])
        full_capacity_ah = float(params["Nominal cell capacity [A.h]"])
        full_contact_resistance_ohm = float(params["Contact resistance [Ohm]"])
    except KeyError as exc:
        raise KeyError(f"regional DFN area scaling requires parameter {exc.args[0]!r}") from exc

    params.update(
        {
            "Electrode width [m]": full_width_m * config.area_fraction,
            "Nominal cell capacity [A.h]": full_capacity_ah * config.area_fraction,
            "Contact resistance [Ohm]": full_contact_resistance_ohm / config.area_fraction,
            CURRENT_INPUT_NAME: pybamm.InputParameter(CURRENT_INPUT_NAME),
        },
        check_already_exists=False,
    )
    for parameter_name, multiplier in config.parameter_multipliers.items():
        try:
            value = float(params[parameter_name])
        except KeyError as exc:
            raise KeyError(
                f"region {config.name!r} multiplier references missing parameter "
                f"{parameter_name!r}"
            ) from exc
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"region {config.name!r} can only multiply scalar parameter "
                f"{parameter_name!r}"
            ) from exc
        params.update(
            {parameter_name: value * float(multiplier)},
            check_already_exists=False,
        )
    return params


def _last_solution_scalar(solution, variable_name):
    entries = solution[variable_name].entries
    return float(entries[-1])


def _build_split_result(regions, currents_by_index, terminal_voltage_v, total_current_a, clamped_currents):
    region_currents_a = {}
    region_overpotentials_v = {}
    region_powers_w = {}
    for i, region in enumerate(regions):
        current_a = float(currents_by_index[i])
        region_currents_a[region.name] = current_a
        region_overpotentials_v[region.name] = region.ocv_v - terminal_voltage_v
        region_powers_w[region.name] = terminal_voltage_v * current_a

    return ParallelSplitResult(
        terminal_voltage_v=float(terminal_voltage_v),
        total_current_a=float(total_current_a),
        region_currents_a=region_currents_a,
        region_overpotentials_v=region_overpotentials_v,
        region_powers_w=region_powers_w,
        clamped_regions=tuple(regions[i].name for i in sorted(clamped_currents)),
        regions=tuple(regions),
    )


def _validate_regions(regions):
    if not regions:
        raise ValueError("regions must not be empty")
    region_tuple = tuple(regions)
    names = [region.name for region in region_tuple]
    if len(names) != len(set(names)):
        raise ValueError(f"region names must be unique; got {names}")
    for region in region_tuple:
        if not isinstance(region, RegionalCellState):
            raise TypeError("regions must contain RegionalCellState instances")
    return region_tuple


def _lookup_region_value(value_or_mapping, region_name, label):
    if isinstance(value_or_mapping, Mapping):
        if region_name not in value_or_mapping:
            raise KeyError(f"{label} missing value for region {region_name!r}")
        return value_or_mapping[region_name]
    return value_or_mapping


def _current_bounds(region):
    lower = float("-inf") if region.lower_current_a is None else float(region.lower_current_a)
    upper = float("inf") if region.upper_current_a is None else float(region.upper_current_a)
    return lower, upper


def _validate_finite(name, value):
    if not isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


def _validate_positive(name, value):
    _validate_finite(name, value)
    if float(value) <= 0:
        raise ValueError(f"{name} must be positive")


def _validate_non_negative(name, value):
    _validate_finite(name, value)
    if float(value) < 0:
        raise ValueError(f"{name} must be non-negative")


__all__ = [
    "AREA_SUM_TOLERANCE",
    "CURRENT_INPUT_NAME",
    "CURRENT_TOLERANCE_A",
    "DEFAULT_REGIONAL_DFN_VAR_PTS",
    "REGIONAL_POROSITY_VARIABLES",
    "ParallelSplitResult",
    "RegionalCellState",
    "RegionalDFNConfig",
    "RegionalDFNCouplingResult",
    "aggregate_regional_capacity_ah",
    "build_area_scaled_regions",
    "run_regional_dfn_coupling",
    "solve_parallel_current_split",
]
