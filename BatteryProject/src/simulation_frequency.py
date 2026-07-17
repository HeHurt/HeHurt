"""PyBaMM 频率调节工况老化仿真。

围绕 ``run_frequency_scenario``：把 N 天的等效快充快放脉冲打包成一组
PyBaMM Experiment，按 day_acceleration_factor 加速求解，并在指定的真实天数
节点插入 Branch-RPT 诊断（容量、能量、力学）。

本模块同时提供多场景批量运行入口，供 Notebook / example 直接复用，避免把
并行调度、场景衍生量计算和结果汇总逻辑重复写在 Notebook 中。
"""
import logging
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pandas as pd
import pybamm

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover - optional dependency in notebook workflows
    tqdm = None

from .simulation_common import _make_parameter_values, _prepare_solution_for_storage
from .simulation_rpt import (
    run_branch_rpt,
    should_run_rpt,
    snapshot_degradation_variables,
)


logger = logging.getLogger(__name__)

EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE = 100
EQUIVALENT_FREQUENCY_TARGET_POINTS_PER_SEGMENT = 50
RECOVERABLE_FREQUENCY_SOLVE_ERROR_MARKERS = (
    "The `all_ts` time vector must be strictly increasing",
    "non-positive at initial conditions",
    "Experiment is infeasible",
    "Minimum voltage [V]",
    "Maximum voltage [V]",
)
RECOVERABLE_RPT_ERROR_MARKERS = (
    "Invalid RPT summary:",
)


def _maybe_wrap_progress(iterable, *, enabled, total=None, desc=None, unit=None):
    """Wrap an iterable with tqdm when progress display is available."""
    if not enabled or tqdm is None:
        return iterable
    if total is not None and total <= 1:
        return iterable
    return tqdm(iterable, total=total, desc=desc, unit=unit)


def _is_recoverable_frequency_solve_error(exc):
    """Return whether a solve error should trigger fallback instead of aborting."""
    if not isinstance(exc, (pybamm.SolverError, ValueError)):
        return False
    message = str(exc)
    return any(marker in message for marker in RECOVERABLE_FREQUENCY_SOLVE_ERROR_MARKERS)


def _should_relax_frequency_voltage_limits(exc):
    """Return whether the main waveform should widen global voltage events."""
    if not _is_recoverable_frequency_solve_error(exc):
        return False
    message = str(exc)
    return "non-positive at initial conditions" in message and (
        "Minimum voltage [V]" in message or "Maximum voltage [V]" in message
    )


def _is_recoverable_rpt_error(exc):
    """Return whether an RPT failure should be converted into a NaN summary."""
    if _is_recoverable_frequency_solve_error(exc):
        return True
    if isinstance(exc, ValueError):
        message = str(exc)
        return any(marker in message for marker in RECOVERABLE_RPT_ERROR_MARKERS)
    return False


def _with_relaxed_voltage_limits(parameter_values):
    """Return parameter values with widened global voltage limits for the main waveform."""
    relaxed_parameter_values = parameter_values.copy() if hasattr(parameter_values, "copy") else dict(parameter_values)
    relaxed_limits = {
        "Lower voltage cut-off [V]": 0.0,
        "Upper voltage cut-off [V]": 5.0,
    }
    try:
        relaxed_parameter_values.update(relaxed_limits, check_already_exists=False)
    except TypeError:
        relaxed_parameter_values.update(relaxed_limits)
    return relaxed_parameter_values


def _iter_equivalent_pair_group_sizes(pair_count_per_day, initial_group_size):
    """Yield progressively finer equivalent pair group sizes down to pulse-resolved mode."""
    current_group_size = max(1, min(int(pair_count_per_day), int(initial_group_size)))
    yielded_group_sizes = set()
    while current_group_size not in yielded_group_sizes:
        yielded_group_sizes.add(current_group_size)
        yield current_group_size
        if current_group_size <= 1:
            break
        next_group_size = max(1, current_group_size // 2)
        if next_group_size == current_group_size:
            next_group_size = 1
        current_group_size = next_group_size


def _normalize_frequency_scenario(scenario, current_a, nominal_capacity_ah):
    """Return a scenario copy with derived throughput metrics filled in."""
    normalized = dict(scenario)
    required_keys = {
        "name",
        "display_name",
        "pulse_seconds",
        "total_pulses_per_day",
        "sample_period_seconds",
    }
    missing_keys = sorted(required_keys.difference(normalized))
    if missing_keys:
        raise KeyError(f"scenario is missing required keys: {missing_keys}")

    pulse_seconds = float(normalized["pulse_seconds"])
    total_pulses_per_day = int(normalized["total_pulses_per_day"])
    sample_period_seconds = float(normalized["sample_period_seconds"])
    if pulse_seconds <= 0:
        raise ValueError("pulse_seconds must be positive")
    if total_pulses_per_day <= 0:
        raise ValueError("total_pulses_per_day must be positive")
    if sample_period_seconds <= 0:
        raise ValueError("sample_period_seconds must be positive")
    if current_a <= 0:
        raise ValueError("current_a must be positive")
    if nominal_capacity_ah <= 0:
        raise ValueError("nominal_capacity_ah must be positive")
    if total_pulses_per_day % 2 != 0:
        raise ValueError("total_pulses_per_day 必须为偶数，才能保证充/放对称。")

    pair_count = total_pulses_per_day // 2
    charge_ah_per_day = current_a * pair_count * pulse_seconds / 3600.0
    efc_per_day = charge_ah_per_day / nominal_capacity_ah
    soc_swing = current_a * pulse_seconds / 3600.0 / nominal_capacity_ah
    waveform_hours = total_pulses_per_day * pulse_seconds / 3600.0

    normalized["enabled"] = bool(normalized.get("enabled", True))
    normalized["pair_count_per_day"] = pair_count
    normalized["charge_ah_per_day"] = charge_ah_per_day
    normalized["discharge_ah_per_day"] = charge_ah_per_day
    normalized["efc_per_day"] = efc_per_day
    normalized["soc_swing_per_half_cycle"] = soc_swing
    normalized["waveform_hours_per_day"] = waveform_hours
    return normalized


def prepare_frequency_scenarios(scenarios, current_a, nominal_capacity_ah):
    """Normalize scenario dictionaries and build a reporting table.

    Parameters
    ----------
    scenarios : iterable[dict]
        Raw scenario configuration dictionaries.
    current_a : float
        Applied pulse current in ampere.
    nominal_capacity_ah : float
        Cell nominal capacity in ampere-hour.

    Returns
    -------
    dict
        {
            "scenarios": list[dict],
            "scenario_table": pandas.DataFrame,
        }
    """
    normalized_scenarios = [
        _normalize_frequency_scenario(scenario, current_a, nominal_capacity_ah)
        for scenario in scenarios
    ]
    rows = [
        {
            "enabled": scenario["enabled"],
            "scenario": scenario["display_name"],
            "pulse_seconds": scenario["pulse_seconds"],
            "total_pulses_per_day": scenario["total_pulses_per_day"],
            "pair_count_per_day": scenario["pair_count_per_day"],
            "charge_Ah_per_day": round(scenario["charge_ah_per_day"], 3),
            "equivalent_full_cycles_per_day": round(scenario["efc_per_day"], 3),
            "single_half_cycle_soc_swing_pct": round(scenario["soc_swing_per_half_cycle"] * 100, 3),
            "waveform_hours_per_day": round(scenario["waveform_hours_per_day"], 3),
        }
        for scenario in normalized_scenarios
    ]
    return {
        "scenarios": normalized_scenarios,
        "scenario_table": pd.DataFrame(rows),
    }


def _build_frequency_run_kwargs(
    scenario,
    runtime_config,
    *,
    model_options,
    var_pts,
    current_a,
    nominal_capacity_ah,
    initial_soc,
    temperature_k,
    get_hithium_params,
    calculate_cycle_swelling_func,
    faraday_const,
    solver_rtol,
    solver_atol,
    keep_only_last_cycle_solution,
    keep_only_last_rpt_solution,
    return_solutions,
    use_equivalent_frequency,
    parallel,
):
    scenario_runtime = dict(runtime_config)
    if parallel and scenario_runtime.get("showprogress", False):
        scenario_runtime["showprogress"] = False

    return {
        "scenario": _normalize_frequency_scenario(scenario, current_a, nominal_capacity_ah),
        "runtime_config": scenario_runtime,
        "model_options": dict(model_options),
        "var_pts": dict(var_pts),
        "current_a": current_a,
        "nominal_capacity_ah": nominal_capacity_ah,
        "initial_soc": initial_soc,
        "temperature_k": temperature_k,
        "get_hithium_params": get_hithium_params,
        "calculate_cycle_swelling_func": calculate_cycle_swelling_func,
        "faraday_const": faraday_const,
        "solver_rtol": solver_rtol,
        "solver_atol": solver_atol,
        "keep_only_last_cycle_solution": keep_only_last_cycle_solution,
        "keep_only_last_rpt_solution": keep_only_last_rpt_solution,
        "return_solutions": return_solutions,
        "use_equivalent_frequency": use_equivalent_frequency,
    }


def build_frequency_day_steps(current_a, pulse_seconds, total_pulses_per_day, sample_period_seconds):
    """Build symmetric charge/discharge pulse steps for one frequency-control day."""
    if total_pulses_per_day % 2 != 0:
        raise ValueError("total_pulses_per_day 必须为偶数，才能保证充/放对称。")

    pair_count = total_pulses_per_day // 2
    steps = []
    for _ in range(pair_count):
        steps.append(
            f"Charge at {current_a:.3f} A for {pulse_seconds} second ({sample_period_seconds:.1f} second period)"
        )
        steps.append(
            f"Discharge at {current_a:.3f} A for {pulse_seconds} second ({sample_period_seconds:.1f} second period)"
        )
    return steps


def build_frequency_current_profile(segment_seconds, pair_count, current_a):
    """Build time/current arrays for a symmetric square-wave frequency profile."""
    segment_seconds = float(segment_seconds)
    pair_count = int(pair_count)
    current_a = float(current_a)
    if segment_seconds <= 0:
        raise ValueError("segment_seconds must be positive")
    if pair_count <= 0:
        raise ValueError("pair_count must be positive")
    if current_a <= 0:
        raise ValueError("current_a must be positive")

    time_points = [0.0]
    current_points = []
    elapsed_seconds = 0.0
    for _ in range(pair_count):
        for signed_current in (current_a, -current_a):
            current_points.extend([signed_current, signed_current])
            time_points.extend([elapsed_seconds, elapsed_seconds + segment_seconds])
            elapsed_seconds += segment_seconds
    return np.asarray(time_points[1:], dtype=float), np.asarray(current_points, dtype=float)


def trim_current_profile(time_points, current_points, max_seconds):
    """Trim a time/current profile to a maximum display time."""
    time_points = np.asarray(time_points, dtype=float)
    current_points = np.asarray(current_points, dtype=float)
    max_seconds = float(max_seconds)
    if time_points.shape != current_points.shape:
        raise ValueError("time_points and current_points must have the same shape")
    if time_points.size == 0:
        return time_points, current_points
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    point_count = int(np.sum(time_points <= max_seconds))
    point_count = max(2, min(point_count, time_points.size))
    return time_points[:point_count], current_points[:point_count]


def _build_equivalent_frequency_day_steps(
    scenario,
    current_a,
    pair_group_size=EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE,
):
    """Compress one pulse-rich day into fewer longer charge/discharge segments.

    The approximation preserves the day's total charge/discharge throughput and
    current amplitude, while reducing the number of current reversals that make
    the detailed pulse-resolved solve expensive.
    """
    pair_group_size = max(1, min(int(pair_group_size), int(scenario["pair_count_per_day"])))
    equivalent_pair_count = max(
        1,
        -(-int(scenario["pair_count_per_day"]) // pair_group_size),
    )
    total_charge_seconds = float(scenario["charge_ah_per_day"]) / current_a * 3600.0
    segment_seconds = total_charge_seconds / equivalent_pair_count
    sample_period_seconds = max(
        float(scenario["sample_period_seconds"]),
        segment_seconds / EQUIVALENT_FREQUENCY_TARGET_POINTS_PER_SEGMENT,
    )

    steps = []
    for _ in range(equivalent_pair_count):
        steps.append(
            f"Charge at {current_a:.3f} A for {segment_seconds:.3f} second ({sample_period_seconds:.1f} second period)"
        )
        steps.append(
            f"Discharge at {current_a:.3f} A for {segment_seconds:.3f} second ({sample_period_seconds:.1f} second period)"
        )

    return {
        "steps": steps,
        "equivalent_pair_count": equivalent_pair_count,
        "segment_seconds": segment_seconds,
        "sample_period_seconds": sample_period_seconds,
        "pair_group_size": pair_group_size,
    }


def _build_frequency_day_plan(
    scenario,
    current_a,
    *,
    use_equivalent_frequency,
    equivalent_pair_group_size=None,
):
    """Build one day's experiment steps and reporting metadata."""
    if use_equivalent_frequency:
        equivalent_day = _build_equivalent_frequency_day_steps(
            scenario,
            current_a,
            pair_group_size=equivalent_pair_group_size or EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE,
        )
        day_steps = equivalent_day["steps"]
        simulated_pair_count = equivalent_day["equivalent_pair_count"]
        simulated_segment_seconds = equivalent_day["segment_seconds"]
        pair_group_size = equivalent_day["pair_group_size"]
        used_equivalent_frequency = simulated_pair_count < scenario["pair_count_per_day"]
    else:
        day_steps = build_frequency_day_steps(
            current_a=current_a,
            pulse_seconds=scenario["pulse_seconds"],
            total_pulses_per_day=scenario["total_pulses_per_day"],
            sample_period_seconds=scenario["sample_period_seconds"],
        )
        simulated_pair_count = scenario["pair_count_per_day"]
        simulated_segment_seconds = float(scenario["pulse_seconds"])
        pair_group_size = 1
        used_equivalent_frequency = False

    simulated_segments_per_day = len(day_steps)
    pulse_compression_ratio = (
        float(scenario["total_pulses_per_day"]) / simulated_segments_per_day
        if simulated_segments_per_day > 0 else np.nan
    )
    return {
        "steps": day_steps,
        "simulated_pair_count": simulated_pair_count,
        "simulated_segments_per_day": simulated_segments_per_day,
        "simulated_segment_seconds": simulated_segment_seconds,
        "pulse_compression_ratio": pulse_compression_ratio,
        "equivalent_pair_group_size": pair_group_size,
        "used_equivalent_frequency": used_equivalent_frequency,
    }


def _build_failed_rpt_summary(exc):
    """Return a NaN-filled RPT summary for recoverable diagnostic failures."""
    return {
        "rpt_charge_capacity_ah": np.nan,
        "rpt_discharge_capacity_ah": np.nan,
        "rpt_charge_energy_wh": np.nan,
        "rpt_discharge_energy_wh": np.nan,
        "rpt_efficiency": np.nan,
        "rpt_max_force_n": np.nan,
        "rpt_min_force_n": np.nan,
        "rpt_failure_type": type(exc).__name__,
        "rpt_failure_message": str(exc),
    }


def run_frequency_scenario(
    scenario,
    runtime_config,
    *,
    model_options,
    var_pts,
    current_a,
    nominal_capacity_ah=None,
    initial_soc,
    temperature_k,
    get_hithium_params,
    calculate_cycle_swelling_func=None,
    faraday_const=96485.33212,
    solver_rtol=1e-6,
    solver_atol=1e-6,
    keep_only_last_cycle_solution=False,
    keep_only_last_rpt_solution=False,
    return_solutions=True,
    use_equivalent_frequency=False,
):
    """Run one frequency-control aging scenario with optional lightweight outputs.

    When ``runtime_config["showprogress"]`` is true, the per-block aging loop is
    wrapped in a notebook-friendly progress bar.

    When ``use_equivalent_frequency`` is true, the pulse-rich day waveform is
    approximated by a much smaller set of longer charge/discharge segments.
    """
    if "efc_per_day" not in scenario:
        if nominal_capacity_ah is None:
            raise ValueError("nominal_capacity_ah is required when scenario lacks derived throughput metrics")
        scenario = _normalize_frequency_scenario(scenario, current_a, nominal_capacity_ah)
    else:
        scenario = dict(scenario)

    model = pybamm.lithium_ion.DFN(model_options)
    solver = pybamm.IDAKLUSolver(rtol=solver_rtol, atol=solver_atol)

    total_real_days = int(runtime_config["real_days_total"])
    day_acceleration = int(runtime_config["day_acceleration_factor"])
    rpt_every_real_days = int(runtime_config["rpt_every_real_days"])
    showprogress = bool(runtime_config["showprogress"])

    real_days_elapsed = 0
    total_blocks = (total_real_days + day_acceleration - 1) // day_acceleration if total_real_days > 0 else 0
    restart_solution = None
    final_main_solution = None
    main_records = []
    rpt_records = []
    rpt_solutions = []
    equivalent_pair_group_size = max(
        1,
        min(int(scenario["pair_count_per_day"]), EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE),
    ) if use_equivalent_frequency else None
    terminated_early = False
    termination_reason = ""
    termination_error_type = ""
    relaxed_voltage_limits_active = False

    block_iterator = _maybe_wrap_progress(
        range(total_blocks),
        enabled=showprogress,
        total=total_blocks,
        desc=f"{scenario['display_name']} blocks",
        unit="block",
    )

    for _ in block_iterator:
        requested_real_days = min(day_acceleration, total_real_days - real_days_elapsed)
        pending_sub_block_days = [requested_real_days]

        while pending_sub_block_days:
            real_days_this_block = pending_sub_block_days.pop(0)
            main_params = _make_parameter_values(
                get_hithium_params,
                scenario["efc_per_day"] * real_days_this_block,
                temperature_k,
                check_already_exists=False,
            )
            if relaxed_voltage_limits_active:
                main_params = _with_relaxed_voltage_limits(main_params)
            candidate_pair_group_sizes = [None]
            if use_equivalent_frequency:
                candidate_pair_group_sizes = list(
                    _iter_equivalent_pair_group_sizes(
                        scenario["pair_count_per_day"],
                        equivalent_pair_group_size,
                    )
                )

            main_sol = None
            day_plan = None
            recoverable_exc = None
            for candidate_pair_group_size in candidate_pair_group_sizes:
                day_plan = _build_frequency_day_plan(
                    scenario,
                    current_a,
                    use_equivalent_frequency=use_equivalent_frequency,
                    equivalent_pair_group_size=candidate_pair_group_size,
                )
                day_experiment = pybamm.Experiment([tuple(day_plan["steps"])], temperature=temperature_k)
                main_sim = pybamm.Simulation(
                    model,
                    parameter_values=main_params,
                    experiment=day_experiment,
                    var_pts=var_pts,
                    solver=solver,
                )

                solve_kwargs = {"showprogress": showprogress}
                if restart_solution is None:
                    solve_kwargs["initial_soc"] = initial_soc
                else:
                    solve_kwargs["starting_solution"] = restart_solution
                    solve_kwargs["calc_esoh"] = False

                try:
                    main_sol = main_sim.solve(**solve_kwargs)
                    equivalent_pair_group_size = day_plan["equivalent_pair_group_size"]
                    recoverable_exc = None
                    break
                except Exception as exc:
                    if not _is_recoverable_frequency_solve_error(exc):
                        raise
                    recoverable_exc = exc
                    if use_equivalent_frequency and candidate_pair_group_size != 1:
                        logger.warning(
                            "Frequency block solve failed for %s at %.1f real days with %.1f s equivalent segments; retrying finer grouping.",
                            scenario["display_name"],
                            real_days_elapsed,
                            day_plan["simulated_segment_seconds"],
                        )
                        continue
                    main_sol = None
                    break

            if main_sol is None:
                if recoverable_exc is not None and real_days_this_block > 1:
                    first_half_days = real_days_this_block // 2
                    second_half_days = real_days_this_block - first_half_days
                    pending_sub_block_days = [first_half_days, second_half_days, *pending_sub_block_days]
                    logger.warning(
                        "Frequency block solve failed for %s at %.1f real days even after fallback; splitting %d real days into %d + %d.",
                        scenario["display_name"],
                        real_days_elapsed,
                        real_days_this_block,
                        first_half_days,
                        second_half_days,
                    )
                    continue

                if (
                    recoverable_exc is not None
                    and _should_relax_frequency_voltage_limits(recoverable_exc)
                    and not relaxed_voltage_limits_active
                ):
                    relaxed_voltage_limits_active = True
                    pending_sub_block_days = [real_days_this_block, *pending_sub_block_days]
                    logger.warning(
                        "Relaxing main frequency voltage limits for %s at %.1f real days after initial-condition voltage failure.",
                        scenario["display_name"],
                        real_days_elapsed,
                    )
                    continue

                terminated_early = True
                termination_error_type = type(recoverable_exc).__name__ if recoverable_exc is not None else ""
                termination_reason = str(recoverable_exc) if recoverable_exc is not None else ""
                logger.warning(
                    "Frequency run stopped early for %s at %.1f real days due to %s: %s",
                    scenario["display_name"],
                    real_days_elapsed,
                    termination_error_type,
                    termination_reason,
                )
                break

            real_days_elapsed += real_days_this_block

            main_snapshot = snapshot_degradation_variables(main_sol, faraday_const=faraday_const)
            main_snapshot.update(
                {
                    "scenario": scenario["display_name"],
                    "real_day": real_days_elapsed,
                    "effective_t_factor_this_block": scenario["efc_per_day"] * real_days_this_block,
                    "main_block_pulses": scenario["total_pulses_per_day"],
                    "use_equivalent_frequency": day_plan["used_equivalent_frequency"],
                    "original_pulses_per_day": scenario["total_pulses_per_day"],
                    "simulated_pair_count": day_plan["simulated_pair_count"],
                    "simulated_segments_per_day": day_plan["simulated_segments_per_day"],
                    "simulated_segment_seconds": day_plan["simulated_segment_seconds"],
                    "pulse_compression_ratio": day_plan["pulse_compression_ratio"],
                    "equivalent_pair_group_size": day_plan["equivalent_pair_group_size"],
                    "relaxed_voltage_limits": relaxed_voltage_limits_active,
                }
            )
            main_records.append(main_snapshot)
            if return_solutions:
                final_main_solution = _prepare_solution_for_storage(main_sol, keep_only_last_cycle_solution)
            restart_solution = main_sol.last_state if hasattr(main_sol, "last_state") else main_sol

            if should_run_rpt(real_days_elapsed, total_real_days, rpt_every_real_days):
                try:
                    rpt_sol, rpt_summary = run_branch_rpt(
                        model,
                        solver,
                        main_sol.last_state,
                        temperature_k,
                        current_a,
                        var_pts,
                        get_hithium_params,
                        calculate_cycle_swelling_func=calculate_cycle_swelling_func,
                    )
                except Exception as exc:
                    if not _is_recoverable_rpt_error(exc):
                        raise
                    logger.warning(
                        "Skipping RPT for %s at %.1f real days due to %s: %s",
                        scenario["display_name"],
                        real_days_elapsed,
                        type(exc).__name__,
                        exc,
                    )
                    rpt_sol = None
                    rpt_summary = _build_failed_rpt_summary(exc)
                rpt_summary.update(
                    {
                        "scenario": scenario["display_name"],
                        "real_day": real_days_elapsed,
                    }
                )
                rpt_records.append(rpt_summary)
                if return_solutions and rpt_sol is not None:
                    rpt_solutions.append(
                        (
                            real_days_elapsed,
                            _prepare_solution_for_storage(rpt_sol, keep_only_last_rpt_solution),
                        )
                    )

        if terminated_early:
            break

    main_df = pd.DataFrame(main_records)
    rpt_df = pd.DataFrame(rpt_records)

    if not rpt_df.empty:
        base_capacity = rpt_df["rpt_discharge_capacity_ah"].iloc[0]
        rpt_df["capacity_retention"] = rpt_df["rpt_discharge_capacity_ah"] / base_capacity
        rpt_df["rpt_efficiency_pct"] = rpt_df["rpt_efficiency"] * 100.0
    else:
        rpt_df["capacity_retention"] = pd.Series(dtype=float)
        rpt_df["rpt_efficiency_pct"] = pd.Series(dtype=float)

    return {
        "scenario": scenario,
        "main_df": main_df,
        "rpt_df": rpt_df,
        "final_main_solution": final_main_solution,
        "rpt_solutions": rpt_solutions,
        "real_days_covered": real_days_elapsed,
        "terminated_early": terminated_early,
        "termination_error_type": termination_error_type,
        "termination_reason": termination_reason,
    }


def summarize_frequency_results(results, real_days_covered=None):
    """Build a summary dataframe from batched frequency-control results."""
    summary_rows = []
    for bundle in results.values():
        scenario = bundle["scenario"]
        main_df = bundle["main_df"]
        rpt_df = bundle["rpt_df"]

        final_main = main_df.iloc[-1] if not main_df.empty else pd.Series(dtype=float)
        final_rpt = rpt_df.iloc[-1] if not rpt_df.empty else pd.Series(dtype=float)
        current_real_days = bundle.get("real_days_covered", np.nan)
        if pd.isna(current_real_days):
            if real_days_covered is None:
                if not rpt_df.empty and "real_day" in rpt_df.columns:
                    current_real_days = float(rpt_df["real_day"].iloc[-1])
                elif not main_df.empty and "real_day" in main_df.columns:
                    current_real_days = float(main_df["real_day"].iloc[-1])
                else:
                    current_real_days = np.nan
            else:
                current_real_days = real_days_covered
        elif pd.isna(current_real_days) and real_days_covered is not None:
            current_real_days = real_days_covered

        summary_rows.append(
            {
                "scenario": scenario["display_name"],
                "real_days_covered": current_real_days,
                "terminated_early": bool(bundle.get("terminated_early", False)),
                "termination_error_type": bundle.get("termination_error_type", ""),
                "termination_reason": bundle.get("termination_reason", ""),
                "efc_per_day": scenario.get("efc_per_day", np.nan),
                "use_equivalent_frequency": final_main.get("use_equivalent_frequency", np.nan),
                "original_pulses_per_day": final_main.get(
                    "original_pulses_per_day", scenario.get("total_pulses_per_day", np.nan)
                ),
                "simulated_segments_per_day": final_main.get("simulated_segments_per_day", np.nan),
                "pulse_compression_ratio": final_main.get("pulse_compression_ratio", np.nan),
                "simulated_segment_seconds": final_main.get("simulated_segment_seconds", np.nan),
                "equivalent_pair_group_size": final_main.get("equivalent_pair_group_size", np.nan),
                "relaxed_voltage_limits": final_main.get("relaxed_voltage_limits", np.nan),
                "final_capacity_retention_pct": final_rpt.get("capacity_retention", np.nan) * 100.0,
                "final_rpt_efficiency_pct": final_rpt.get("rpt_efficiency_pct", np.nan),
                "final_q_sei_ah": final_main.get("q_sei_ah", np.nan),
                "final_q_plating_ah": final_main.get("q_plating_ah", np.nan),
                "final_lli_ah": final_main.get("lli_ah", np.nan),
                "final_lam_neg_ah": final_main.get("lam_neg_ah", np.nan),
                "final_sei_total_thickness_m": final_main.get("sei_total_thickness_m", np.nan),
                "final_rpt_failure_type": final_rpt.get("rpt_failure_type", ""),
                "final_rpt_failure_message": final_rpt.get("rpt_failure_message", ""),
            }
        )

    return pd.DataFrame(summary_rows)


def run_frequency_scenarios(
    scenarios,
    runtime_config,
    *,
    model_options,
    var_pts,
    current_a,
    nominal_capacity_ah,
    initial_soc,
    temperature_k,
    get_hithium_params,
    calculate_cycle_swelling_func=None,
    faraday_const=96485.33212,
    solver_rtol=1e-6,
    solver_atol=1e-6,
    parallel=False,
    max_workers=None,
    keep_only_last_cycle_solution=False,
    keep_only_last_rpt_solution=False,
    return_solutions=None,
    use_equivalent_frequency=False,
    enabled_only=True,
):
    """Run multiple frequency-control scenarios and return batched outputs.

    Parameters
    ----------
    parallel : bool, optional
        Whether to parallelize independent scenarios. When ``return_solutions`` is
        false, process-based parallelism is used; otherwise thread-based
        parallelism is used to avoid shipping large Solution objects between
        processes.
    return_solutions : bool | None, optional
        Whether to keep ``final_main_solution`` / ``rpt_solutions`` in each bundle.
        Defaults to ``not parallel``.
    enabled_only : bool, optional
        Whether to skip scenarios whose ``enabled`` flag is false.
    use_equivalent_frequency : bool, optional
        Whether to compress each day of rapid pulses into a smaller equivalent
        charge/discharge sequence for faster notebook studies.

    Notes
    -----
    When ``runtime_config["showprogress"]`` is true, parallel batch runs show an
    outer scenario-level progress bar. Sequential runs rely on the per-scenario
    block progress bar in ``run_frequency_scenario``.

    Returns
    -------
    dict
        {
            "scenarios": normalized_scenarios,
            "scenario_table": DataFrame,
            "results": dict[str, bundle],
            "summary_df": DataFrame,
        }
    """
    prepared = prepare_frequency_scenarios(scenarios, current_a, nominal_capacity_ah)
    normalized_scenarios = prepared["scenarios"]
    if enabled_only:
        selected_scenarios = [scenario for scenario in normalized_scenarios if scenario.get("enabled", True)]
    else:
        selected_scenarios = list(normalized_scenarios)

    if return_solutions is None:
        return_solutions = not parallel

    scenario_tasks = [
        _build_frequency_run_kwargs(
            scenario,
            runtime_config,
            model_options=model_options,
            var_pts=var_pts,
            current_a=current_a,
            nominal_capacity_ah=nominal_capacity_ah,
            initial_soc=initial_soc,
            temperature_k=temperature_k,
            get_hithium_params=get_hithium_params,
            calculate_cycle_swelling_func=calculate_cycle_swelling_func,
            faraday_const=faraday_const,
            solver_rtol=solver_rtol,
            solver_atol=solver_atol,
            keep_only_last_cycle_solution=keep_only_last_cycle_solution,
            keep_only_last_rpt_solution=keep_only_last_rpt_solution,
            return_solutions=return_solutions,
            use_equivalent_frequency=use_equivalent_frequency,
            parallel=parallel,
        )
        for scenario in selected_scenarios
    ]
    show_scenario_progress = bool(runtime_config.get("showprogress", False)) and parallel

    if parallel and len(scenario_tasks) > 1:
        worker_count = max_workers or min(len(scenario_tasks), os.cpu_count() or 1)
        executor_type = ProcessPoolExecutor if not return_solutions else ThreadPoolExecutor
        with executor_type(max_workers=worker_count) as executor:
            ordered_results = list(
                _maybe_wrap_progress(
                    executor.map(run_frequency_scenario_from_kwargs, scenario_tasks),
                    enabled=show_scenario_progress,
                    total=len(scenario_tasks),
                    desc="Frequency scenarios",
                    unit="scenario",
                )
            )
    else:
        ordered_results = [run_frequency_scenario_from_kwargs(task) for task in scenario_tasks]

    results = {
        bundle["scenario"]["name"]: bundle
        for bundle in ordered_results
    }
    summary_df = summarize_frequency_results(
        results,
        real_days_covered=runtime_config.get("real_days_total"),
    )
    return {
        "scenarios": normalized_scenarios,
        "scenario_table": prepared["scenario_table"],
        "results": results,
        "summary_df": summary_df,
    }


def run_frequency_scenario_from_kwargs(kwargs):
    """ProcessPoolExecutor helper that accepts a single kwargs dictionary."""
    return run_frequency_scenario(**kwargs)
