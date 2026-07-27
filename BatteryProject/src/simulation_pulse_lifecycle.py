"""Inserted pulse lifecycle simulation helpers.

This module keeps the pulse-cycle experiment construction, block aging loop,
and voltage-curve extraction reusable outside notebooks.
"""
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pandas as pd
import pybamm

from .analysis import get_discharge_capacity
from .simulation_common import _make_parameter_values, _prepare_solution_for_storage
from .simulation_rpt import (
    snapshot_degradation_variables,
    summarize_rpt_solution,
    validate_rpt_summary,
)


LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS = {
    "SEI": "ec reaction limited",
    "SEI porosity change": "true",
    "lithium plating": "irreversible",
    "lithium plating porosity change": "true",
    "calculate discharge energy": "true",
    "contact resistance": "true",
    "open-circuit potential": ("current sigmoid", "current sigmoid"),
}

FULL_PULSE_LIFECYCLE_MODEL_OPTIONS = {
    **LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    "particle mechanics": ("swelling and cracking", "swelling only"),
    "SEI on cracks": "true",
    "loss of active material": "stress-driven",
}

DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)


def p_rate_to_power_w(p_rate, nominal_capacity_ah, nominal_voltage_v=3.2):
    """Convert P-rate to constant power in watt."""
    p_rate = float(p_rate)
    nominal_capacity_ah = float(nominal_capacity_ah)
    nominal_voltage_v = float(nominal_voltage_v)
    if p_rate <= 0:
        raise ValueError("p_rate must be positive")
    if nominal_capacity_ah <= 0:
        raise ValueError("nominal_capacity_ah must be positive")
    if nominal_voltage_v <= 0:
        raise ValueError("nominal_voltage_v must be positive")
    return p_rate * nominal_capacity_ah * nominal_voltage_v


def _format_power_step(direction, power_w, duration_text, period_minutes):
    return f"{direction} at {power_w:.2f}W {duration_text} ({period_minutes:.3g} minute period)"


def _format_rest_step(rest_minutes, period_minutes):
    return f"Rest for {float(rest_minutes):.3g} minutes ({float(period_minutes):.3g} minute period)"


def _build_inserted_pulse_leg_steps(
    direction,
    base_power_w,
    pulse_power_w,
    cutoff_voltage_v,
    soc_window,
    pulse_seconds,
    interval_minutes,
    period_minutes,
    nominal_capacity_ah,
    nominal_voltage_v,
    tail_to_cutoff=True,
    window_capacity_ah=None,
):
    """Build one charge or discharge leg with pulse steps inserted inside a SOC window."""
    window_start, window_end = [float(value) for value in soc_window]
    if not 0 <= window_start < window_end <= 1:
        raise ValueError("soc_window must satisfy 0 <= start < end <= 1")
    if pulse_seconds <= 0:
        raise ValueError("pulse_seconds must be positive")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")

    steps = []
    direction = str(direction).strip().capitalize()
    if direction not in {"Charge", "Discharge"}:
        raise ValueError("direction must be 'Charge' or 'Discharge'")

    capacity_for_window_ah = nominal_capacity_ah if window_capacity_ah is None else float(window_capacity_ah)
    if capacity_for_window_ah <= 0:
        raise ValueError("window_capacity_ah must be positive")
    full_base_hours = capacity_for_window_ah * nominal_voltage_v / base_power_w
    if direction == "Discharge":
        pre_window_fraction = 1.0 - window_end
        post_window_fraction = window_start
    else:
        pre_window_fraction = window_start
        post_window_fraction = 1.0 - window_end

    pre_window_hours = pre_window_fraction * full_base_hours
    window_hours = (window_end - window_start) * full_base_hours
    interval_hours = interval_minutes / 60.0

    if pre_window_hours > 0:
        steps.append(
            _format_power_step(direction, base_power_w, f"for {pre_window_hours:.6g} hours", period_minutes)
        )

    pulse_hours = pulse_seconds / 3600.0
    elapsed_window_hours = 0.0
    while elapsed_window_hours + pulse_hours <= window_hours + 1e-12:
        steps.append(
            _format_power_step(direction, pulse_power_w, f"for {pulse_seconds:.6g} seconds", period_minutes)
        )
        elapsed_window_hours += pulse_hours
        remaining_window_hours = window_hours - elapsed_window_hours
        if remaining_window_hours <= 1e-12:
            break
        base_hours = min(interval_hours, remaining_window_hours)
        duration_text = f"for {base_hours:.6g} hours"
        if direction == "Discharge":
            duration_text = f"{duration_text} or until {cutoff_voltage_v:.2f} V"
        steps.append(_format_power_step(direction, base_power_w, duration_text, period_minutes))
        elapsed_window_hours += base_hours

    remaining_after_window_hours = max(0.0, post_window_fraction * full_base_hours)
    if tail_to_cutoff:
        steps.append(_format_power_step(direction, base_power_w, f"until {cutoff_voltage_v:.2f} V", period_minutes))
    elif remaining_after_window_hours > 0:
        steps.append(
            _format_power_step(direction, base_power_w, f"for {remaining_after_window_hours:.6g} hours", period_minutes)
        )
    return steps


def build_pulse_lifecycle_cycle_steps(
    scenario,
    *,
    nominal_capacity_ah,
    base_p_rate=0.25,
    nominal_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.50,
    rest_minutes=30.0,
    period_minutes=0.5,
    window_capacity_ah=None,
):
    """Build one charge/rest/discharge/rest cycle for a pulse lifecycle scenario."""
    base_power_w = p_rate_to_power_w(base_p_rate, nominal_capacity_ah, nominal_voltage_v)
    pulse_p_rate = scenario.get("pulse_p_rate")
    steps = []

    if pulse_p_rate is None:
        steps.extend(
            [
                _format_power_step("Charge", base_power_w, f"until {charge_cutoff_v:.2f} V", period_minutes),
                _format_rest_step(rest_minutes, period_minutes),
                _format_power_step("Discharge", base_power_w, f"until {discharge_cutoff_v:.2f} V", period_minutes),
                _format_rest_step(rest_minutes, period_minutes),
            ]
        )
        return steps

    pulse_power_w = p_rate_to_power_w(pulse_p_rate, nominal_capacity_ah, nominal_voltage_v)
    pulse_seconds = float(scenario["pulse_seconds"])
    steps.extend(
        _build_inserted_pulse_leg_steps(
            "Charge",
            base_power_w,
            pulse_power_w,
            charge_cutoff_v,
            scenario.get("charge_soc_window", (0.10, 0.90)),
            pulse_seconds,
            scenario["charge_interval_minutes"],
            period_minutes,
            nominal_capacity_ah,
            nominal_voltage_v,
            tail_to_cutoff=True,
            window_capacity_ah=window_capacity_ah,
        )
    )
    steps.append(_format_rest_step(rest_minutes, period_minutes))
    steps.extend(
        _build_inserted_pulse_leg_steps(
            "Discharge",
            base_power_w,
            pulse_power_w,
            discharge_cutoff_v,
            scenario.get("discharge_soc_window", (0.10, 0.90)),
            pulse_seconds,
            scenario["discharge_interval_minutes"],
            period_minutes,
            nominal_capacity_ah,
            nominal_voltage_v,
            tail_to_cutoff=True,
            window_capacity_ah=window_capacity_ah,
        )
    )
    steps.append(_format_rest_step(rest_minutes, period_minutes))
    return steps


def build_pulse_lifecycle_capacity_check_steps(
    *,
    nominal_capacity_ah,
    check_p_rate=0.25,
    nominal_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.50,
    rest_minutes=30.0,
    period_minutes=0.5,
):
    """Build a normal full charge/discharge cycle used only for capacity checks."""
    check_power_w = p_rate_to_power_w(check_p_rate, nominal_capacity_ah, nominal_voltage_v)
    return [
        _format_rest_step(rest_minutes, period_minutes),
        _format_power_step("Charge", check_power_w, f"until {charge_cutoff_v:.2f} V", period_minutes),
        _format_rest_step(rest_minutes, period_minutes),
        _format_power_step("Discharge", check_power_w, f"until {discharge_cutoff_v:.2f} V", period_minutes),
        _format_rest_step(rest_minutes, period_minutes),
    ]


def prepare_pulse_lifecycle_scenarios(
    scenarios,
    *,
    nominal_capacity_ah,
    base_p_rate=0.25,
    nominal_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.50,
    rest_minutes=30.0,
    period_minutes=0.5,
):
    """Normalize pulse lifecycle scenarios and return a reporting table."""
    normalized = []
    rows = []
    for scenario in scenarios:
        item = dict(scenario)
        item["enabled"] = bool(item.get("enabled", True))
        item["base_p_rate"] = float(item.get("base_p_rate", base_p_rate))
        item["base_power_w"] = p_rate_to_power_w(item["base_p_rate"], nominal_capacity_ah, nominal_voltage_v)
        if item.get("pulse_p_rate") is not None:
            item["pulse_p_rate"] = float(item["pulse_p_rate"])
            item["pulse_power_w"] = p_rate_to_power_w(item["pulse_p_rate"], nominal_capacity_ah, nominal_voltage_v)
            item["pulse_seconds"] = float(item["pulse_seconds"])
        else:
            item["pulse_power_w"] = np.nan
            item["pulse_seconds"] = np.nan

        steps = build_pulse_lifecycle_cycle_steps(
            item,
            nominal_capacity_ah=nominal_capacity_ah,
            base_p_rate=item["base_p_rate"],
            nominal_voltage_v=nominal_voltage_v,
            charge_cutoff_v=charge_cutoff_v,
            discharge_cutoff_v=discharge_cutoff_v,
            rest_minutes=rest_minutes,
            period_minutes=period_minutes,
        )
        item["cycle_steps"] = steps
        item["step_count_per_cycle"] = len(steps)
        normalized.append(item)
        rows.append(
            {
                "enabled": item["enabled"],
                "scenario": item.get("display_name", item.get("name", "")),
                "base_p_rate": item["base_p_rate"],
                "pulse_p_rate": item.get("pulse_p_rate", np.nan),
                "pulse_seconds": item.get("pulse_seconds", np.nan),
                "charge_interval_minutes": item.get("charge_interval_minutes", np.nan),
                "discharge_interval_minutes": item.get("discharge_interval_minutes", np.nan),
                "charge_soc_window": item.get("charge_soc_window", ""),
                "discharge_soc_window": item.get("discharge_soc_window", ""),
                "step_count_per_cycle": item["step_count_per_cycle"],
            }
        )
    return {"scenarios": normalized, "scenario_table": pd.DataFrame(rows)}


def _build_cycle_dataframe(sol, get_discharge_capacity_func):
    capacities = np.asarray(get_discharge_capacity_func(sol).get("discharge_capacity", []), dtype=float)
    capacities = capacities[np.isfinite(capacities)]
    cycle_numbers = np.arange(1, len(capacities) + 1)
    if capacities.size == 0:
        return pd.DataFrame(columns=["sim_cycle", "discharge_capacity_ah", "capacity_retention"])
    return pd.DataFrame(
        {
            "sim_cycle": cycle_numbers,
            "discharge_capacity_ah": capacities,
            "capacity_retention": capacities / capacities[0],
        }
    )


def _capacity_check_summary_to_row(summary):
    return {
        "capacity_check_charge_capacity_ah": summary.get("rpt_charge_capacity_ah", np.nan),
        "capacity_check_discharge_capacity_ah": summary.get("rpt_discharge_capacity_ah", np.nan),
        "capacity_check_charge_energy_wh": summary.get("rpt_charge_energy_wh", np.nan),
        "capacity_check_discharge_energy_wh": summary.get("rpt_discharge_energy_wh", np.nan),
        "capacity_check_efficiency": summary.get("rpt_efficiency", np.nan),
    }


def _add_capacity_check_retention(capacity_check_df):
    if capacity_check_df.empty:
        capacity_check_df["capacity_retention"] = pd.Series(dtype=float)
        capacity_check_df["capacity_check_efficiency_pct"] = pd.Series(dtype=float)
        return capacity_check_df

    capacities = pd.to_numeric(
        capacity_check_df["capacity_check_discharge_capacity_ah"],
        errors="coerce",
    )
    finite_capacities = capacities[np.isfinite(capacities)]
    base_capacity = finite_capacities.iloc[0] if not finite_capacities.empty else np.nan
    capacity_check_df["capacity_retention"] = capacities / base_capacity
    capacity_check_df["capacity_check_efficiency_pct"] = capacity_check_df["capacity_check_efficiency"] * 100.0
    return capacity_check_df


def _next_capacity_check_cycle(completed_real_cycles, total_cycles, interval_cycles):
    if interval_cycles is None:
        return None
    interval_cycles = float(interval_cycles)
    if interval_cycles <= 0:
        raise ValueError("capacity_check_interval_cycles must be positive")
    next_cycle = np.floor(completed_real_cycles / interval_cycles + 1e-12) + 1
    next_cycle *= interval_cycles
    if next_cycle > total_cycles:
        return float(total_cycles) if completed_real_cycles < total_cycles else None
    return float(next_cycle)


def _run_capacity_check(
    model,
    solver,
    *,
    starting_solution,
    initial_soc,
    temperature_k,
    var_pts,
    get_hithium_params,
    nominal_capacity_ah,
    check_p_rate,
    nominal_voltage_v,
    charge_cutoff_v,
    discharge_cutoff_v,
    rest_minutes,
    period_minutes,
    showprogress,
):
    steps = build_pulse_lifecycle_capacity_check_steps(
        nominal_capacity_ah=nominal_capacity_ah,
        check_p_rate=check_p_rate,
        nominal_voltage_v=nominal_voltage_v,
        charge_cutoff_v=charge_cutoff_v,
        discharge_cutoff_v=discharge_cutoff_v,
        rest_minutes=rest_minutes,
        period_minutes=period_minutes,
    )
    check_params = _make_parameter_values(get_hithium_params, 1, temperature_k)
    check_sim = pybamm.Simulation(
        model,
        parameter_values=check_params,
        experiment=pybamm.Experiment([tuple(steps)], temperature=temperature_k),
        var_pts=var_pts,
        solver=solver,
    )
    solve_kwargs = {"showprogress": showprogress}
    if starting_solution is None:
        if initial_soc is not None:
            solve_kwargs["initial_soc"] = initial_soc
    else:
        solve_kwargs["starting_solution"] = starting_solution
        solve_kwargs["calc_esoh"] = False
    check_solution = check_sim.solve(**solve_kwargs)
    summary = summarize_rpt_solution(check_solution, check_params)
    validate_rpt_summary(
        summary,
        required_finite_fields=(
            "rpt_discharge_capacity_ah",
            "rpt_discharge_energy_wh",
        ),
    )
    return check_solution, summary


def _run_single_pulse_lifecycle_scenario(
    scenario,
    runtime_config,
    *,
    model_options,
    var_pts,
    nominal_capacity_ah,
    temperature_k,
    get_hithium_params,
    get_discharge_capacity_func,
    base_p_rate=0.25,
    nominal_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.50,
    rest_minutes=30.0,
    period_minutes=0.5,
    initial_soc=None,
    solver_rtol=1e-6,
    solver_atol=1e-6,
    keep_only_last_cycle_solution=False,
    keep_only_last_capacity_check_solution=False,
    return_solutions=True,
):
    model = pybamm.lithium_ion.DFN(model_options)
    solver_root_method = str(runtime_config.get("solver_root_method", "casadi"))
    solver_root_tol = float(runtime_config.get("solver_root_tol", 1e-6))
    solver = pybamm.IDAKLUSolver(
        rtol=solver_rtol,
        atol=solver_atol,
        root_method=solver_root_method,
        root_tol=solver_root_tol,
    )
    total_cycles = int(runtime_config["total_cycles"])
    use_block_acceleration = bool(runtime_config.get("use_block_acceleration", True))
    cycles_per_block = (
        int(runtime_config["cycles_per_block"])
        if use_block_acceleration
        else None
    )
    aging_t_factor = float(runtime_config.get("aging_t_factor", 1))
    conditioning_t_factor = float(runtime_config.get("conditioning_t_factor", 1))
    capacity_check_interval_cycles = runtime_config.get("capacity_check_interval_cycles")
    capacity_check_p_rate = float(runtime_config.get("capacity_check_p_rate", base_p_rate))
    capacity_check_at_start = bool(
        runtime_config.get("capacity_check_at_start", capacity_check_interval_cycles is not None)
    )
    diagnostic_soh_targets_pct = sorted(
        {float(value) for value in runtime_config.get("diagnostic_soh_targets_pct", [])},
        reverse=True,
    )
    diagnostic_p_rates = tuple(float(value) for value in runtime_config.get("diagnostic_p_rates", []))
    return_partial_on_error = bool(runtime_config.get("return_partial_on_error", False))
    stop_at_lowest_diagnostic_soh = bool(runtime_config.get("stop_at_lowest_diagnostic_soh", False))
    adapt_pulse_windows_to_capacity = bool(runtime_config.get("adapt_pulse_windows_to_capacity", False))
    showprogress = bool(runtime_config.get("showprogress", False))
    if use_block_acceleration and cycles_per_block <= 0:
        raise ValueError("cycles_per_block must be positive")
    if total_cycles < 0:
        raise ValueError("total_cycles must be non-negative")
    if aging_t_factor <= 0:
        raise ValueError("aging_t_factor must be positive")
    if solver_root_tol <= 0:
        raise ValueError("solver_root_tol must be positive")
    if any(not 0 < target <= 100 for target in diagnostic_soh_targets_pct):
        raise ValueError("diagnostic_soh_targets_pct values must be within (0, 100]")
    if diagnostic_soh_targets_pct and not diagnostic_p_rates:
        raise ValueError("diagnostic_p_rates is required when SOH diagnostics are enabled")
    if any(rate <= 0 for rate in diagnostic_p_rates):
        raise ValueError("diagnostic_p_rates values must be positive")
    if diagnostic_soh_targets_pct and not use_block_acceleration:
        raise ValueError("SOH-triggered diagnostics require use_block_acceleration=True")
    if (not use_block_acceleration) and capacity_check_interval_cycles is not None:
        raise ValueError(
            "capacity_check_interval_cycles requires use_block_acceleration=True; "
            "direct mode solves the requested aging cycles in one experiment."
        )

    current_window_capacity_ah = float(nominal_capacity_ah)

    def update_window_capacity(capacity_ah):
        nonlocal current_window_capacity_ah
        if not adapt_pulse_windows_to_capacity:
            return
        try:
            capacity_ah = float(capacity_ah)
        except (TypeError, ValueError):
            return
        if np.isfinite(capacity_ah) and capacity_ah > 0:
            current_window_capacity_ah = capacity_ah

    def build_current_cycle_steps():
        return build_pulse_lifecycle_cycle_steps(
            scenario,
            nominal_capacity_ah=nominal_capacity_ah,
            base_p_rate=base_p_rate,
            nominal_voltage_v=nominal_voltage_v,
            charge_cutoff_v=charge_cutoff_v,
            discharge_cutoff_v=discharge_cutoff_v,
            rest_minutes=rest_minutes,
            period_minutes=period_minutes,
            window_capacity_ah=(
                current_window_capacity_ah if adapt_pulse_windows_to_capacity else None
            ),
        )

    steps = build_current_cycle_steps()

    if total_cycles == 0:
        empty_df = pd.DataFrame(columns=["sim_cycle", "real_cycle", "discharge_capacity_ah", "capacity_retention"])
        return {
            "scenario": dict(scenario),
            "cycle_steps": steps,
            "main_df": empty_df,
            "capacity_check_df": pd.DataFrame(),
            "solutions": [],
            "solution_real_cycles": [],
            "capacity_check_solutions": [],
            "capacity_check_real_cycles": [],
            "diagnostic_df": pd.DataFrame(),
            "diagnostic_solutions": [],
            "final_solution": None,
            "real_cycles_covered": 0.0,
            "run_status": "completed",
            "failure_message": "",
        }

    params = _make_parameter_values(get_hithium_params, conditioning_t_factor, temperature_k)
    first_sim = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=pybamm.Experiment([tuple(steps)], temperature=temperature_k),
        var_pts=var_pts,
        solver=solver,
    )
    first_solve_kwargs = {"showprogress": showprogress}
    if initial_soc is not None:
        first_solve_kwargs["initial_soc"] = initial_soc
    current_solution = first_sim.solve(**first_solve_kwargs)

    stored_solutions = []
    solution_real_cycles = []
    capacity_check_records = []
    capacity_check_solutions = []
    capacity_check_real_cycles = []
    diagnostic_records = []
    diagnostic_solutions = []
    pending_diagnostic_targets = list(diagnostic_soh_targets_pct)
    diagnostic_base_capacity_ah = None
    last_valid_soh_pct = np.nan
    run_status = "completed"
    failure_message = ""

    def record_capacity_check(real_cycle, starting_solution, source_solution=None):
        check_solution, check_summary = _run_capacity_check(
            model,
            solver,
            starting_solution=starting_solution,
            initial_soc=initial_soc,
            temperature_k=temperature_k,
            var_pts=var_pts,
            get_hithium_params=get_hithium_params,
            nominal_capacity_ah=nominal_capacity_ah,
            check_p_rate=capacity_check_p_rate,
            nominal_voltage_v=nominal_voltage_v,
            charge_cutoff_v=charge_cutoff_v,
            discharge_cutoff_v=discharge_cutoff_v,
            rest_minutes=rest_minutes,
            period_minutes=period_minutes,
            showprogress=showprogress,
        )
        snapshot_source = source_solution if source_solution is not None else check_solution
        row = _capacity_check_summary_to_row(check_summary)
        update_window_capacity(row.get("capacity_check_discharge_capacity_ah"))
        row.update(snapshot_degradation_variables(snapshot_source))
        row["scenario"] = scenario.get("display_name", scenario["name"])
        row["scenario_name"] = scenario["name"]
        row["real_cycle"] = float(real_cycle)
        capacity_check_records.append(row)
        if return_solutions:
            capacity_check_solutions.append(
                _prepare_solution_for_storage(check_solution, keep_only_last_capacity_check_solution)
            )
            capacity_check_real_cycles.append(float(real_cycle))
        return check_solution

    def record_soh_diagnostics(real_cycle, starting_solution, source_solution, capacity_ah):
        """Run independent diagnostic branches for every newly crossed SOH target."""
        nonlocal diagnostic_base_capacity_ah, last_valid_soh_pct
        capacity_ah = float(capacity_ah)
        if diagnostic_base_capacity_ah is None:
            diagnostic_base_capacity_ah = capacity_ah
        if not np.isfinite(capacity_ah) or capacity_ah <= 0:
            return
        last_valid_soh_pct = capacity_ah / diagnostic_base_capacity_ah * 100.0
        crossed_targets = [
            target for target in pending_diagnostic_targets
            if last_valid_soh_pct <= target + 1.0e-9
        ]
        if not crossed_targets:
            return

        degradation_snapshot = snapshot_degradation_variables(source_solution)
        for target_soh_pct in crossed_targets:
            for diagnostic_p_rate in diagnostic_p_rates:
                metadata = {
                    "target_soh_pct": float(target_soh_pct),
                    "actual_soh_pct": float(last_valid_soh_pct),
                    "real_cycle": float(real_cycle),
                    "diagnostic_p_rate": float(diagnostic_p_rate),
                }
                try:
                    check_solution, check_summary = _run_capacity_check(
                        model,
                        solver,
                        starting_solution=starting_solution,
                        initial_soc=initial_soc,
                        temperature_k=temperature_k,
                        var_pts=var_pts,
                        get_hithium_params=get_hithium_params,
                        nominal_capacity_ah=nominal_capacity_ah,
                        check_p_rate=diagnostic_p_rate,
                        nominal_voltage_v=nominal_voltage_v,
                        charge_cutoff_v=charge_cutoff_v,
                        discharge_cutoff_v=discharge_cutoff_v,
                        rest_minutes=rest_minutes,
                        period_minutes=period_minutes,
                        showprogress=showprogress,
                    )
                except Exception as exc:
                    if not return_partial_on_error:
                        raise
                    row = dict(metadata)
                    row.update(degradation_snapshot)
                    row["diagnostic_status"] = "failed"
                    row["diagnostic_error"] = f"{type(exc).__name__}: {exc}"
                    diagnostic_records.append(row)
                    continue

                row = _capacity_check_summary_to_row(check_summary)
                row.update(degradation_snapshot)
                row.update(metadata)
                row["diagnostic_status"] = "simulated"
                row["diagnostic_error"] = ""
                diagnostic_records.append(row)
                if return_solutions:
                    diagnostic_solutions.append(
                        {
                            **metadata,
                            "solution": _prepare_solution_for_storage(
                                check_solution,
                                keep_only_last_capacity_check_solution,
                            ),
                        }
                    )
            pending_diagnostic_targets.remove(target_soh_pct)

    if capacity_check_at_start:
        record_capacity_check(0.0, starting_solution=None, source_solution=None)
    if return_solutions:
        stored_solutions.append(_prepare_solution_for_storage(current_solution, keep_only_last_cycle_solution))
        solution_real_cycles.append(1.0)
    restart_solution = current_solution.last_state if hasattr(current_solution, "last_state") else current_solution
    cycle_records = []
    snapshot = snapshot_degradation_variables(current_solution)
    cycle_df = _build_cycle_dataframe(current_solution, get_discharge_capacity_func)
    if not cycle_df.empty:
        update_window_capacity(cycle_df["discharge_capacity_ah"].iloc[-1])
        row = cycle_df.iloc[-1].to_dict()
        row.update(snapshot)
        row["real_cycle"] = 1
        row["sim_cycle"] = 1
        cycle_records.append(row)
        record_soh_diagnostics(
            1.0,
            restart_solution,
            current_solution,
            row["discharge_capacity_ah"],
        )

    completed_real_cycles = 1.0
    remaining_real_cycles = max(0, total_cycles - completed_real_cycles)
    if not use_block_acceleration:
        if remaining_real_cycles > 0:
            sim_cycles_this_block = int(max(1, np.ceil(remaining_real_cycles / aging_t_factor)))
            effective_t_factor = remaining_real_cycles / sim_cycles_this_block
            block_steps = build_current_cycle_steps()
            params = _make_parameter_values(get_hithium_params, effective_t_factor, temperature_k)
            direct_sim = pybamm.Simulation(
                model,
                parameter_values=params,
                experiment=pybamm.Experiment([tuple(block_steps)] * sim_cycles_this_block, temperature=temperature_k),
                var_pts=var_pts,
                solver=solver,
            )
            current_solution = direct_sim.solve(
                starting_solution=restart_solution,
                showprogress=showprogress,
                calc_esoh=False,
            )
            if return_solutions:
                stored_solutions.append(_prepare_solution_for_storage(current_solution, keep_only_last_cycle_solution))
                solution_real_cycles.append(float(total_cycles))
            cycle_df = _build_cycle_dataframe(current_solution, get_discharge_capacity_func)
            if cycle_df.empty or not np.isfinite(cycle_df["discharge_capacity_ah"].iloc[-1]) or cycle_df["discharge_capacity_ah"].iloc[-1] <= 0:
                raise RuntimeError(
                    "Direct pulse lifecycle solve produced no positive discharge capacity "
                    f"for scenario {scenario.get('name', '<unnamed>')!r}."
                )
            update_window_capacity(cycle_df["discharge_capacity_ah"].iloc[-1])
            snapshot = snapshot_degradation_variables(current_solution)
            for _, row in cycle_df.iterrows():
                row = row.to_dict()
                local_sim_cycle = int(row["sim_cycle"])
                row["sim_cycle"] = completed_real_cycles + local_sim_cycle
                row["real_cycle"] = completed_real_cycles + local_sim_cycle * effective_t_factor
                row.update(snapshot)
                cycle_records.append(row)
            completed_real_cycles += remaining_real_cycles
        main_df = pd.DataFrame(cycle_records)
        if not main_df.empty:
            base_capacity = main_df["discharge_capacity_ah"].iloc[0]
            main_df["capacity_retention"] = main_df["discharge_capacity_ah"] / base_capacity
        capacity_check_df = _add_capacity_check_retention(pd.DataFrame(capacity_check_records))
        return {
            "scenario": dict(scenario),
            "cycle_steps": steps,
            "main_df": main_df,
            "capacity_check_df": capacity_check_df,
            "solutions": stored_solutions,
            "solution_real_cycles": solution_real_cycles,
            "capacity_check_solutions": capacity_check_solutions,
            "capacity_check_real_cycles": capacity_check_real_cycles,
            "final_solution": stored_solutions[-1] if stored_solutions else None,
            "real_cycles_covered": float(completed_real_cycles),
        }

    while remaining_real_cycles > 0:
        next_check_cycle = _next_capacity_check_cycle(
            completed_real_cycles,
            total_cycles,
            capacity_check_interval_cycles,
        )
        real_cycles_this_block = min(cycles_per_block * aging_t_factor, remaining_real_cycles)
        if next_check_cycle is not None:
            real_cycles_this_block = min(real_cycles_this_block, max(0.0, next_check_cycle - completed_real_cycles))
        if real_cycles_this_block <= 0:
            real_cycles_this_block = min(cycles_per_block * aging_t_factor, remaining_real_cycles)
        sim_cycles_this_block = int(
            max(1, min(cycles_per_block, np.ceil(real_cycles_this_block / aging_t_factor)))
        )
        effective_t_factor = real_cycles_this_block / sim_cycles_this_block
        block_steps = build_current_cycle_steps()
        params = _make_parameter_values(get_hithium_params, effective_t_factor, temperature_k)
        try:
            block_sim = pybamm.Simulation(
                model,
                parameter_values=params,
                experiment=pybamm.Experiment([tuple(block_steps)] * sim_cycles_this_block, temperature=temperature_k),
                var_pts=var_pts,
                solver=solver,
            )
            block_solution = block_sim.solve(
                starting_solution=restart_solution,
                showprogress=showprogress,
                calc_esoh=False,
            )
        except Exception as exc:
            if not return_partial_on_error:
                raise
            run_status = "partial"
            failure_message = f"{type(exc).__name__}: {exc}"
            break
        cycle_df = _build_cycle_dataframe(block_solution, get_discharge_capacity_func)
        if (
            cycle_df.empty
            or not np.isfinite(cycle_df["discharge_capacity_ah"].iloc[-1])
            or cycle_df["discharge_capacity_ah"].iloc[-1] <= 0
        ):
            failure_message = (
                "RuntimeError: Pulse lifecycle block produced no positive discharge capacity "
                f"for scenario {scenario.get('name', '<unnamed>')!r} near real cycle "
                f"{completed_real_cycles + real_cycles_this_block:g}."
            )
            if scenario.get("pulse_p_rate") is not None:
                failure_message += (
                    " Enable runtime_config['adapt_pulse_windows_to_capacity'] "
                    "or narrow the pulse SOC window."
                )
            if not return_partial_on_error:
                raise RuntimeError(failure_message.removeprefix("RuntimeError: "))
            run_status = "partial"
            break
        current_solution = block_solution
        if return_solutions:
            stored_solutions.append(_prepare_solution_for_storage(current_solution, keep_only_last_cycle_solution))
            solution_real_cycles.append(completed_real_cycles + real_cycles_this_block)
        restart_solution = current_solution.last_state if hasattr(current_solution, "last_state") else current_solution
        update_window_capacity(cycle_df["discharge_capacity_ah"].iloc[-1])
        snapshot = snapshot_degradation_variables(current_solution)
        if not cycle_df.empty:
            for _, row in cycle_df.iterrows():
                row = row.to_dict()
                local_sim_cycle = int(row["sim_cycle"])
                row["sim_cycle"] = completed_real_cycles + local_sim_cycle
                row["real_cycle"] = completed_real_cycles + local_sim_cycle * effective_t_factor
                row.update(snapshot)
                cycle_records.append(row)
        checkpoint_real_cycle = completed_real_cycles + real_cycles_this_block
        record_soh_diagnostics(
            checkpoint_real_cycle,
            restart_solution,
            current_solution,
            cycle_df["discharge_capacity_ah"].iloc[-1],
        )
        completed_real_cycles += real_cycles_this_block
        if next_check_cycle is not None and completed_real_cycles >= next_check_cycle - 1e-9:
            record_capacity_check(next_check_cycle, restart_solution, source_solution=current_solution)
        remaining_real_cycles = max(0, total_cycles - completed_real_cycles)
        if (
            stop_at_lowest_diagnostic_soh
            and diagnostic_soh_targets_pct
            and np.isfinite(last_valid_soh_pct)
            and last_valid_soh_pct <= min(diagnostic_soh_targets_pct) + 1.0e-9
        ):
            remaining_real_cycles = 0

    if run_status == "completed" and pending_diagnostic_targets:
        run_status = "target_not_reached"

    main_df = pd.DataFrame(cycle_records)
    if not main_df.empty:
        base_capacity = main_df["discharge_capacity_ah"].iloc[0]
        main_df["capacity_retention"] = main_df["discharge_capacity_ah"] / base_capacity
    capacity_check_df = _add_capacity_check_retention(pd.DataFrame(capacity_check_records))

    return {
        "scenario": dict(scenario),
        "cycle_steps": steps,
        "main_df": main_df,
        "capacity_check_df": capacity_check_df,
        "solutions": stored_solutions,
        "solution_real_cycles": solution_real_cycles,
        "capacity_check_solutions": capacity_check_solutions,
        "capacity_check_real_cycles": capacity_check_real_cycles,
        "diagnostic_df": pd.DataFrame(diagnostic_records),
        "diagnostic_solutions": diagnostic_solutions,
        "final_solution": stored_solutions[-1] if stored_solutions else None,
        "real_cycles_covered": completed_real_cycles,
        "last_valid_soh_pct": last_valid_soh_pct,
        "pending_diagnostic_soh_targets_pct": pending_diagnostic_targets,
        "run_status": run_status,
        "failure_message": failure_message,
    }


def _run_single_pulse_lifecycle_scenario_from_kwargs(kwargs):
    return _run_single_pulse_lifecycle_scenario(**kwargs)


def run_pulse_lifecycle_scenarios(
    scenarios,
    runtime_config,
    *,
    model_options=None,
    var_pts=None,
    nominal_capacity_ah,
    temperature_k,
    get_hithium_params,
    get_discharge_capacity_func=None,
    base_p_rate=0.25,
    nominal_voltage_v=3.2,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.50,
    rest_minutes=30.0,
    period_minutes=0.5,
    initial_soc=None,
    solver_rtol=1e-6,
    solver_atol=1e-6,
    parallel=False,
    max_workers=None,
    keep_only_last_cycle_solution=False,
    keep_only_last_capacity_check_solution=False,
    return_solutions=None,
    enabled_only=True,
):
    """Run multiple inserted-pulse lifecycle scenarios and return batch outputs."""
    if model_options is None:
        model_options = DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS
    if var_pts is None:
        var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
    if get_discharge_capacity_func is None:
        get_discharge_capacity_func = get_discharge_capacity
    if return_solutions is None:
        return_solutions = not parallel

    prepared = prepare_pulse_lifecycle_scenarios(
        scenarios,
        nominal_capacity_ah=nominal_capacity_ah,
        base_p_rate=base_p_rate,
        nominal_voltage_v=nominal_voltage_v,
        charge_cutoff_v=charge_cutoff_v,
        discharge_cutoff_v=discharge_cutoff_v,
        rest_minutes=rest_minutes,
        period_minutes=period_minutes,
    )
    selected_scenarios = [
        scenario for scenario in prepared["scenarios"]
        if scenario.get("enabled", True) or not enabled_only
    ]
    tasks = [
        {
            "scenario": scenario,
            "runtime_config": runtime_config,
            "model_options": model_options,
            "var_pts": var_pts,
            "nominal_capacity_ah": nominal_capacity_ah,
            "temperature_k": temperature_k,
            "get_hithium_params": get_hithium_params,
            "get_discharge_capacity_func": get_discharge_capacity_func,
            "base_p_rate": base_p_rate,
            "nominal_voltage_v": nominal_voltage_v,
            "charge_cutoff_v": charge_cutoff_v,
            "discharge_cutoff_v": discharge_cutoff_v,
            "rest_minutes": rest_minutes,
            "period_minutes": period_minutes,
            "initial_soc": initial_soc,
            "solver_rtol": solver_rtol,
            "solver_atol": solver_atol,
            "keep_only_last_cycle_solution": keep_only_last_cycle_solution,
            "keep_only_last_capacity_check_solution": keep_only_last_capacity_check_solution,
            "return_solutions": return_solutions,
        }
        for scenario in selected_scenarios
    ]
    if parallel and len(tasks) > 1:
        worker_count = max_workers or min(len(tasks), os.cpu_count() or 1)
        executor_type = ProcessPoolExecutor if not return_solutions else ThreadPoolExecutor
        with executor_type(max_workers=worker_count) as executor:
            ordered = list(executor.map(_run_single_pulse_lifecycle_scenario_from_kwargs, tasks))
    else:
        ordered = [_run_single_pulse_lifecycle_scenario_from_kwargs(task) for task in tasks]

    results = {bundle["scenario"]["name"]: bundle for bundle in ordered}
    summary_df = summarize_pulse_lifecycle_results(results)
    capacity_check_frames = [
        bundle["capacity_check_df"].assign(scenario_name=name)
        for name, bundle in results.items()
        if not bundle["capacity_check_df"].empty
    ]
    capacity_check_df = (
        pd.concat(capacity_check_frames, ignore_index=True)
        if capacity_check_frames
        else pd.DataFrame()
    )
    return {
        "scenarios": prepared["scenarios"],
        "scenario_table": prepared["scenario_table"],
        "results": results,
        "summary_df": summary_df,
        "capacity_check_df": capacity_check_df,
    }


def summarize_pulse_lifecycle_results(results):
    """Build a summary dataframe, preferring normal capacity-check results."""
    summary_rows = []
    for bundle in results.values():
        scenario = bundle["scenario"]
        main_df = bundle["main_df"]
        capacity_check_df = bundle.get("capacity_check_df", pd.DataFrame())
        final_main = main_df.iloc[-1] if not main_df.empty else pd.Series(dtype=float)
        final_check = (
            capacity_check_df.iloc[-1]
            if not capacity_check_df.empty
            else pd.Series(dtype=float)
        )
        summary_rows.append(
            {
                "scenario": scenario.get("display_name", scenario["name"]),
                "real_cycles_covered": bundle.get("real_cycles_covered", np.nan),
                "final_capacity_ah": final_check.get(
                    "capacity_check_discharge_capacity_ah",
                    final_main.get("discharge_capacity_ah", np.nan),
                ),
                "final_capacity_retention_pct": final_check.get(
                    "capacity_retention",
                    final_main.get("capacity_retention", np.nan),
                ) * 100.0,
                "final_capacity_source": "capacity_check" if not capacity_check_df.empty else "pulse_cycle",
                "final_q_sei_ah": final_main.get("q_sei_ah", final_check.get("q_sei_ah", np.nan)),
                "final_q_plating_ah": final_main.get("q_plating_ah", final_check.get("q_plating_ah", np.nan)),
            }
        )
    return pd.DataFrame(summary_rows)


def extract_cycle_voltage_curve(cycle, direction="charge", x_axis="capacity"):
    """Extract voltage-curve arrays from one cycle for charge or discharge plotting."""
    direction = str(direction).lower()
    if direction not in {"charge", "discharge"}:
        raise ValueError("direction must be 'charge' or 'discharge'")
    if x_axis not in {"capacity", "time"}:
        raise ValueError("x_axis must be 'capacity' or 'time'")
    current = np.asarray(cycle["Current [A]"].entries, dtype=float)
    voltage = np.asarray(cycle["Voltage [V]"].entries, dtype=float)
    capacity = np.asarray(cycle["Throughput capacity [A.h]"].entries, dtype=float)
    time_s = np.asarray(cycle["Time [s]"].entries, dtype=float)
    mask = current < 0 if direction == "charge" else current > 0
    if not np.any(mask):
        return {"x": np.array([]), "voltage": np.array([]), "current": np.array([])}
    x_raw = capacity if x_axis == "capacity" else time_s
    x = x_raw[mask] - x_raw[mask][0]
    return {"x": x, "voltage": voltage[mask], "current": current[mask]}
