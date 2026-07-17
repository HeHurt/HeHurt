"""Heat calibration helpers for branch entropy and OCP hysteresis."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd


DIRECTIONS = ("charge", "discharge")
BRANCH_LABELS = {"charge": "充电支路", "discharge": "放电支路"}


def load_branch_entropy_curves(
    csv_path: str | Path,
    *,
    sample_label: str = "SOH95%",
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Load full-cell branch dU/dT curves as ``SOC[%], dU/dT[V/K]`` arrays."""
    table = pd.read_csv(csv_path)
    required = {"sample_label", "branch", "soc_target", "dudt_v_per_k"}
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Entropy table is missing columns: {sorted(missing)}")

    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for direction, branch_label in BRANCH_LABELS.items():
        branch = table.loc[
            table["sample_label"].eq(sample_label) & table["branch"].eq(branch_label),
            ["soc_target", "dudt_v_per_k"],
        ].dropna()
        branch = branch.groupby("soc_target", as_index=False)["dudt_v_per_k"].mean()
        branch = branch.sort_values("soc_target")
        if len(branch) < 2:
            raise ValueError(f"No usable {branch_label} entropy curve for {sample_label}")
        curves[direction] = (
            branch["soc_target"].to_numpy(dtype=float),
            branch["dudt_v_per_k"].to_numpy(dtype=float),
        )
    return curves


def blend_ocp_functions(
    discharge_ocp: Callable,
    charge_ocp: Callable,
    charge_weight: float,
) -> Callable:
    """Return an equilibrium OCP between discharge and charge branch OCPs."""
    weight = float(charge_weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError("charge_weight must be within [0, 1]")

    def equilibrium_ocp(sto):
        return (1.0 - weight) * discharge_ocp(sto) + weight * charge_ocp(sto)

    equilibrium_ocp.__name__ = f"equilibrium_ocp_charge_weight_{weight:.6f}"
    return equilibrium_ocp


def build_hysteresis_equilibrium_overrides(
    cell_params: Mapping[str, object],
    charge_weight: float,
) -> dict[str, Callable]:
    """Build equilibrium OCP overrides for a shared charge-branch weight.

    ``charge_weight=0`` reproduces the historical discharge-branch equilibrium.
    The calibrated hysteresis allocation is then ``1-weight`` on charge and
    ``weight`` on discharge.
    """
    required = {
        "Negative electrode lithiation OCP [V]",
        "Negative electrode delithiation OCP [V]",
        "Positive electrode lithiation OCP [V]",
        "Positive electrode delithiation OCP [V]",
    }
    missing = required.difference(cell_params)
    if missing:
        raise KeyError(f"Cell parameters are missing hysteresis OCP keys: {sorted(missing)}")

    return {
        "Negative electrode OCP [V]": blend_ocp_functions(
            cell_params["Negative electrode delithiation OCP [V]"],
            cell_params["Negative electrode lithiation OCP [V]"],
            charge_weight,
        ),
        "Positive electrode OCP [V]": blend_ocp_functions(
            cell_params["Positive electrode lithiation OCP [V]"],
            cell_params["Positive electrode delithiation OCP [V]"],
            charge_weight,
        ),
    }


def build_calibrated_parameter_loader(
    parameter_loader: Callable,
    charge_weight: float,
) -> Callable:
    """Wrap a Hithium parameter loader with calibrated equilibrium OCPs."""
    weight = float(charge_weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError("charge_weight must be within [0, 1]")

    def calibrated_parameter_loader(*args, **kwargs):
        cell_params = dict(parameter_loader(*args, **kwargs))
        cell_params.update(build_hysteresis_equilibrium_overrides(cell_params, weight))
        return cell_params

    calibrated_parameter_loader.__name__ = f"calibrated_parameter_loader_{weight:.6f}"
    return calibrated_parameter_loader


def _entries(step, variable_name: str) -> np.ndarray:
    return np.asarray(step[variable_name].entries, dtype=float).reshape(-1)


def _time_weighted_mean(time_s: np.ndarray, values: np.ndarray) -> float:
    if time_s.size != values.size or time_s.size < 2:
        raise ValueError("Time and value arrays must have the same length >= 2")
    duration = float(time_s[-1] - time_s[0])
    if duration <= 0:
        raise ValueError("Step duration must be positive")
    return float(np.trapz(values, time_s) / duration)


def compute_reference_reversible_heat(
    step,
    direction: str,
    entropy_curves: Mapping[str, tuple[np.ndarray, np.ndarray]],
) -> float:
    """Compute branch-specific full-cell reversible heat on a solved step."""
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    if direction not in entropy_curves:
        raise KeyError(f"Missing entropy curve for {direction}")

    time_s = _entries(step, "Time [s]")
    current_a = _entries(step, "Current [A]")
    temperature_k = _entries(step, "Volume-averaged cell temperature [K]")
    throughput_ah = _entries(step, "Throughput capacity [A.h]")
    progressed_ah = throughput_ah - throughput_ah[0]
    total_ah = float(progressed_ah[-1])
    if total_ah <= 0:
        raise ValueError("Throughput capacity must increase over the step")

    fraction = np.clip(progressed_ah / total_ah, 0.0, 1.0)
    soc_pct = 100.0 * fraction if direction == "charge" else 100.0 * (1.0 - fraction)
    curve_soc, curve_dudt = entropy_curves[direction]
    dudt_v_per_k = np.interp(
        soc_pct,
        np.asarray(curve_soc, dtype=float),
        np.asarray(curve_dudt, dtype=float),
    )
    reversible_w = current_a * temperature_k * dudt_v_per_k
    return _time_weighted_mean(time_s, reversible_w)


def _optional_step_mean(step, variable_name: str) -> float:
    try:
        time_s = _entries(step, "Time [s]")
        values = _entries(step, variable_name)
    except KeyError:
        return 0.0
    return _time_weighted_mean(time_s, values)


def compute_cycle_calibrated_heat(
    cycle,
    entropy_curves: Mapping[str, tuple[np.ndarray, np.ndarray]],
    *,
    contact_resistance_ohm: float = 0.0,
) -> dict[str, float]:
    """Compute calibrated charge/discharge heat components for one cycle.

    Rest steps are excluded. If a direction contains multiple active steps,
    component powers are averaged by active-step duration.
    """
    steps = list(getattr(cycle, "steps", []))
    if not steps:
        raise ValueError("cycle must expose at least one step")
    contact_resistance = float(contact_resistance_ohm)
    if contact_resistance < 0:
        raise ValueError("contact_resistance_ohm must be non-negative")

    component_variables = {
        "ohmic": "Ohmic heating [W]",
        "reaction": "Irreversible electrochemical heating [W]",
        "mixing": "Heat of mixing [W]",
        "hysteresis": "Hysteresis electrochemical heating [W]",
        "contact": None,
    }
    energy_sums = {
        direction: {component: 0.0 for component in component_variables}
        for direction in DIRECTIONS
    }
    reversible_energy = {direction: 0.0 for direction in DIRECTIONS}
    active_duration = {direction: 0.0 for direction in DIRECTIONS}

    for step in steps:
        time_s = _entries(step, "Time [s]")
        current_a = _entries(step, "Current [A]")
        mean_current = _time_weighted_mean(time_s, current_a)
        if abs(mean_current) <= 1.0e-8:
            continue
        direction = "charge" if mean_current < 0 else "discharge"
        duration_s = float(time_s[-1] - time_s[0])
        active_duration[direction] += duration_s
        for component, variable_name in component_variables.items():
            if component == "contact":
                component_mean = _time_weighted_mean(
                    time_s,
                    current_a**2 * contact_resistance,
                )
            else:
                component_mean = _optional_step_mean(step, variable_name)
            energy_sums[direction][component] += component_mean * duration_s
        reversible_energy[direction] += (
            compute_reference_reversible_heat(step, direction, entropy_curves) * duration_s
        )

    result: dict[str, float] = {}
    for direction in DIRECTIONS:
        duration_s = active_duration[direction]
        if duration_s <= 0:
            for component in component_variables:
                result[f"{component}_{direction}_w"] = np.nan
            result[f"reversible_reference_{direction}_w"] = np.nan
            result[f"internal_irreversible_{direction}_w"] = np.nan
            result[f"calibrated_total_{direction}_w"] = np.nan
            result[f"active_duration_{direction}_s"] = 0.0
            continue

        for component in component_variables:
            result[f"{component}_{direction}_w"] = energy_sums[direction][component] / duration_s
        if all(
            abs(result[f"{component}_{direction}_w"]) <= 1.0e-12
            for component in ("ohmic", "reaction", "mixing", "hysteresis")
        ):
            raise ValueError(
                "All internal heat components are zero for an active step. "
                "Enable PyBaMM option 'calculate heat source for isothermal models'."
            )
        result[f"reversible_reference_{direction}_w"] = reversible_energy[direction] / duration_s
        internal_irreversible = sum(
            result[f"{component}_{direction}_w"]
            for component in component_variables
        )
        result[f"internal_irreversible_{direction}_w"] = internal_irreversible
        result[f"calibrated_total_{direction}_w"] = (
            internal_irreversible + result[f"reversible_reference_{direction}_w"]
        )
        result[f"active_duration_{direction}_s"] = duration_s
    return result


def fit_hysteresis_allocation(
    base_heat_w: Mapping[str, float],
    full_band_heat_w: Mapping[str, float],
    target_heat_w: Mapping[str, float],
) -> dict[str, object]:
    """Fit the equilibrium charge weight against charge and discharge heat.

    Charge receives ``(1-w)`` of its full hysteresis band and discharge receives
    ``w``. The objective is unweighted least squares in relative heat error.
    """
    for direction in DIRECTIONS:
        if direction not in base_heat_w or direction not in full_band_heat_w or direction not in target_heat_w:
            raise KeyError(f"Missing {direction} calibration input")
        if float(full_band_heat_w[direction]) < 0:
            raise ValueError("Full hysteresis-band heat must be non-negative")
        if float(target_heat_w[direction]) <= 0:
            raise ValueError("Target heat must be positive")

    target_charge = float(target_heat_w["charge"])
    target_discharge = float(target_heat_w["discharge"])
    full_charge = float(full_band_heat_w["charge"])
    full_discharge = float(full_band_heat_w["discharge"])

    charge_intercept = (float(base_heat_w["charge"]) + full_charge - target_charge) / target_charge
    charge_slope = full_charge / target_charge
    discharge_intercept = (float(base_heat_w["discharge"]) - target_discharge) / target_discharge
    discharge_slope = full_discharge / target_discharge
    denominator = charge_slope**2 + discharge_slope**2
    if denominator == 0:
        weight = 0.5
    else:
        weight = (charge_slope * charge_intercept - discharge_slope * discharge_intercept) / denominator
    weight = float(np.clip(weight, 0.0, 1.0))

    predicted = {
        "charge": float(base_heat_w["charge"]) + (1.0 - weight) * full_charge,
        "discharge": float(base_heat_w["discharge"]) + weight * full_discharge,
    }
    error_pct = {
        direction: (predicted[direction] / float(target_heat_w[direction]) - 1.0) * 100.0
        for direction in DIRECTIONS
    }
    return {
        "charge_weight": weight,
        "charge_hysteresis_fraction": 1.0 - weight,
        "discharge_hysteresis_fraction": weight,
        "predicted_heat_w": predicted,
        "error_pct": error_pct,
        "within_10pct": all(abs(error_pct[direction]) <= 10.0 for direction in DIRECTIONS),
    }
