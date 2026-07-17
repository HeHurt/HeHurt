"""PyBaMM Branch-RPT 诊断子流程。

提供：
- ``build_rpt_steps`` / ``run_branch_rpt``：一段标定循环（放电→充CV→放电），
  从中提取容量、能量、效率与可选膨胀力。
- ``snapshot_degradation_variables``：从解中抽取 SEI / plating / LLI / LAM 的
  标量诊断数据。
- ``should_run_rpt`` / ``extract_last_rpt_active_blocks``：调度与切片工具。
"""
import logging

import numpy as np
import pybamm

from .simulation_common import _make_parameter_values

logger = logging.getLogger(__name__)


def safe_last_scalar(sol, variable_name):
    """Return the last scalar entry of a variable, or NaN if unavailable."""
    try:
        variable = sol[variable_name]
        last_t = float(np.asarray(sol.t).reshape(-1)[-1])
        values = np.asarray(variable(last_t))
        if values.size > 0:
            return float(values.reshape(-1)[-1])
    except Exception:
        pass

    try:
        values = np.asarray(sol[variable_name].entries)
        if values.size == 0:
            return np.nan
        return float(values.reshape(-1)[-1])
    except Exception:
        return np.nan


def snapshot_degradation_variables(sol, faraday_const=96485.33212):
    """Extract scalar degradation diagnostics from a solution snapshot."""
    snapshot = {
        "throughput_ah": safe_last_scalar(sol, "Throughput capacity [A.h]"),
        "q_sei_ah": safe_last_scalar(sol, "Loss of capacity to negative SEI [A.h]"),
        "q_sei_on_cracks_ah": safe_last_scalar(sol, "Loss of capacity to negative SEI on cracks [A.h]"),
        "q_plating_ah": safe_last_scalar(sol, "Loss of capacity to negative lithium plating [A.h]"),
        "q_side_ah": safe_last_scalar(sol, "Total capacity lost to side reactions [A.h]"),
        "sei_total_thickness_m": safe_last_scalar(sol, "X-averaged negative total SEI thickness [m]"),
        "negative_porosity_avg": safe_last_scalar(sol, "X-averaged negative electrode porosity"),
    }

    lli_mol = safe_last_scalar(sol, "Total lithium lost [mol]")
    lam_neg_mol = safe_last_scalar(sol, "Loss of lithium due to loss of active material in negative electrode [mol]")

    snapshot["lli_ah"] = np.nan if np.isnan(lli_mol) else lli_mol * faraday_const / 3600.0
    snapshot["lam_neg_ah"] = np.nan if np.isnan(lam_neg_mol) else lam_neg_mol * faraday_const / 3600.0
    return snapshot


def step_mean_current(step):
    """Return the mean current for a single step solution."""
    current = np.asarray(step["Current [A]"].entries, dtype=float)
    return float(np.mean(current)) if current.size else 0.0


def integrate_step_capacity_ah(step):
    """Integrate absolute step capacity in Ah."""
    current = np.asarray(step["Current [A]"].entries, dtype=float)
    time_h = np.asarray(step["Time [h]"].entries, dtype=float)
    if current.size == 0 or time_h.size == 0:
        return 0.0
    return abs(float(np.trapz(current, time_h)))


def integrate_step_energy_wh(step):
    """Integrate absolute step energy in Wh."""
    current = np.asarray(step["Current [A]"].entries, dtype=float)
    voltage = np.asarray(step["Voltage [V]"].entries, dtype=float)
    time_h = np.asarray(step["Time [h]"].entries, dtype=float)
    if current.size == 0 or voltage.size == 0 or time_h.size == 0:
        return 0.0
    return abs(float(np.trapz(current * voltage, time_h)))


def extract_last_rpt_active_blocks(sol, current_threshold=0.05):
    """Split the last RPT cycle into charge and discharge active blocks."""
    if sol is None or not getattr(sol, "cycles", None):
        return [], []
    last_cycle = sol.cycles[-1]
    active_steps = []
    for step in last_cycle.steps:
        mean_current = step_mean_current(step)
        if abs(mean_current) >= current_threshold:
            active_steps.append((step, mean_current))

    if not active_steps:
        return [], []

    last_discharge_idx = None
    for idx in range(len(active_steps) - 1, -1, -1):
        if active_steps[idx][1] > current_threshold:
            last_discharge_idx = idx
            break

    if last_discharge_idx is None:
        return [], []

    discharge_steps = []
    idx = last_discharge_idx
    while idx < len(active_steps) and active_steps[idx][1] > current_threshold:
        discharge_steps.append(active_steps[idx][0])
        idx += 1

    charge_steps = []
    idx = last_discharge_idx - 1
    while idx >= 0 and active_steps[idx][1] < -current_threshold:
        charge_steps.insert(0, active_steps[idx][0])
        idx -= 1

    return charge_steps, discharge_steps


def build_rpt_steps(current_a):
    """Build the branch-RPT diagnostic sequence."""
    cv_cutoff_a = current_a * 0.1
    return [
        "Rest for 30 minutes (5 second period)",
        f"Discharge at {current_a:.3f} A for 3 hours or until 2.50 V (5 second period)",
        "Rest for 30 minutes (5 second period)",
        f"Charge at {current_a:.3f} A for 3 hours or until 3.65 V (5 second period)",
        f"Hold at 3.65 V until {cv_cutoff_a:.3f} A (5 second period)",
        "Rest for 30 minutes (5 second period)",
        f"Discharge at {current_a:.3f} A for 3 hours or until 2.50 V (5 second period)",
        "Rest for 30 minutes (5 second period)",
    ]


def summarize_rpt_solution(sol, rpt_params, calculate_cycle_swelling_func=None):
    """Summarise branch-RPT energy, capacity and optional swelling metrics."""
    charge_steps, discharge_steps = extract_last_rpt_active_blocks(sol)

    charge_capacity = sum(integrate_step_capacity_ah(step) for step in charge_steps)
    discharge_capacity = sum(integrate_step_capacity_ah(step) for step in discharge_steps)
    charge_energy = sum(integrate_step_energy_wh(step) for step in charge_steps)
    discharge_energy = sum(integrate_step_energy_wh(step) for step in discharge_steps)
    efficiency = discharge_energy / charge_energy if charge_energy > 0 else np.nan

    summary = {
        "rpt_charge_capacity_ah": charge_capacity if charge_steps else np.nan,
        "rpt_discharge_capacity_ah": discharge_capacity if discharge_steps else np.nan,
        "rpt_charge_energy_wh": charge_energy if charge_steps else np.nan,
        "rpt_discharge_energy_wh": discharge_energy if discharge_steps else np.nan,
        "rpt_efficiency": efficiency,
    }

    if calculate_cycle_swelling_func is None:
        summary["rpt_max_force_n"] = np.nan
        summary["rpt_min_force_n"] = np.nan
        return summary

    try:
        max_forces, min_forces = calculate_cycle_swelling_func(sol, rpt_params)
        max_forces = np.asarray(max_forces, dtype=float)
        min_forces = np.asarray(min_forces, dtype=float)
        summary["rpt_max_force_n"] = float(max_forces[-1]) if max_forces.size else np.nan
        summary["rpt_min_force_n"] = float(min_forces[-1]) if min_forces.size else np.nan
    except Exception as exc:
        logger.warning("Swelling calc failed for RPT summary (%s); using NaN.", exc)
        summary["rpt_max_force_n"] = np.nan
        summary["rpt_min_force_n"] = np.nan

    return summary


def validate_rpt_summary(summary, required_finite_fields=None):
    """Raise when selected RPT summary fields are incomplete or numerically unusable."""
    if required_finite_fields is None:
        required_finite_fields = (
            "rpt_charge_capacity_ah",
            "rpt_discharge_capacity_ah",
            "rpt_charge_energy_wh",
            "rpt_discharge_energy_wh",
        )
    invalid_fields = []
    for field_name in required_finite_fields:
        value = summary.get(field_name, np.nan)
        if not np.isfinite(value):
            invalid_fields.append(field_name)

    if invalid_fields:
        invalid_fields_text = ", ".join(invalid_fields)
        raise ValueError(
            f"Invalid RPT summary: missing finite charge/discharge metrics ({invalid_fields_text})"
        )

    return summary


def run_branch_rpt(
    model,
    solver,
    starting_solution,
    temperature_k,
    current_a,
    var_pts,
    get_hithium_params,
    calculate_cycle_swelling_func=None,
):
    """Run a one-cycle branch RPT from a provided starting state."""
    rpt_params = _make_parameter_values(get_hithium_params, 1, temperature_k, check_already_exists=False)
    rpt_experiment = pybamm.Experiment([tuple(build_rpt_steps(current_a))], temperature=temperature_k)
    rpt_sim = pybamm.Simulation(
        model,
        parameter_values=rpt_params,
        experiment=rpt_experiment,
        var_pts=var_pts,
        solver=solver,
    )
    rpt_sol = rpt_sim.solve(
        starting_solution=starting_solution,
        showprogress=False,
        calc_esoh=False,
    )
    rpt_summary = summarize_rpt_solution(
        rpt_sol,
        rpt_params,
        calculate_cycle_swelling_func=calculate_cycle_swelling_func,
    )
    validate_rpt_summary(rpt_summary)
    return rpt_sol, rpt_summary


def should_run_rpt(real_days_elapsed, real_days_total, rpt_every_real_days):
    """Return whether the branch RPT should be executed at the current milestone."""
    if real_days_elapsed >= real_days_total:
        return True
    return real_days_elapsed % rpt_every_real_days == 0
