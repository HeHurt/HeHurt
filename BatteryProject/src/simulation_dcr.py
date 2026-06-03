"""PyBaMM DCR 与功率（恒功率充放电）测试。

提供 ``perform_dcr_test``（单点 DCR + 功率脉冲）和 ``run_dcr_and_power_test``
（多倍率、分块循环 + 每块 DCR/功率），以及一键运行+绘图的 ``run_and_plot_all``。
"""
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pybamm

from .experiment_utils import build_power_step
from .simulation_common import _make_parameter_values, _prepare_solution_for_storage


def perform_dcr_test(
    sol,
    params,
    model,
    solver,
    var_pts,
    current=1175,
    C1=0.25,
    C2=0.5,
    t=10,
    charge_time=None,
    target_soc=0.5,
):
    """Run a DCR / power pulse sequence at a configurable pre-charge SOC.

    Parameters
    ----------
    charge_time : float | None
        Full-charge-equivalent duration in hours at current ``current * C1``.
        The actual pre-charge duration is ``charge_time * target_soc``.
    target_soc : float, optional
        Target SOC for the DCR pulse, expressed on ``[0, 1]``.
        Defaults to ``0.5`` for backward compatibility.
    """
    if charge_time is None:
        charge_time = 60
    if not 0 <= float(target_soc) <= 1:
        raise ValueError("target_soc must be between 0 and 1")

    precharge_hours = float(charge_time) * float(target_soc)
    dcr_exp = pybamm.Experiment([(
        "Charge at {} A for {} hour (10 second period)".format(current * C1, precharge_hours),
        "Rest for 10 minutes (10 second period)",
        "Discharge at {}A for {} second (0.5 second period)".format(current * C2, t),
        "Rest for 10 minutes (10 second period)",
        "Charge at {}A for {} second (0.5 second period)".format(current * C2, t),
        "Rest for 10 minutes (10 second period)")
    ])
    sim = pybamm.Simulation(model, parameter_values=params, experiment=dcr_exp, solver=solver, var_pts=var_pts)
    test_sol = sim.solve(starting_solution=sol, calc_esoh=False)
    rest_before_discharge = test_sol.cycles[-1].steps[1]
    discharge_step = test_sol.cycles[-1].steps[2]
    rest_before_charge = test_sol.cycles[-1].steps[3]
    charge_step = test_sol.cycles[-1].steps[4]
    dcr_discharge = (rest_before_discharge["Voltage [V]"].entries[-1] - discharge_step["Voltage [V]"].entries[-1]) / (current * C2)
    dcr_charge = (charge_step["Voltage [V]"].entries[-1] - rest_before_charge["Voltage [V]"].entries[-1]) / (current * C2)
    # 取放电/充电步末尾 3 个点的电压均值作为稳态电压，避免硬编码索引
    dchg_v = discharge_step["Voltage [V]"].entries
    chg_v = charge_step["Voltage [V]"].entries
    power_discharge = np.mean(dchg_v[-3:]) * (current * C2)
    power_charge = np.mean(chg_v[-3:]) * (current * C2)
    return {
        "dcr_mean": (dcr_discharge + dcr_charge) / 2,
        "dcr_discharge": dcr_discharge,
        "dcr_charge": dcr_charge,
        "power_discharge": power_discharge,
        "power_charge": power_charge,
        "solution": test_sol,
        "charge_time": charge_time,
    }


def _build_constant_power_step(
    direction,
    power_w,
    cutoff_voltage_v,
    nominal_current,
    nominal_voltage,
    period_minutes,
    use_explicit_power_steps,
):
    if use_explicit_power_steps:
        return build_power_step(
            direction=direction,
            power_w=power_w,
            cutoff_voltage_v=cutoff_voltage_v,
            nominal_capacity_ah=nominal_current,
            period_minutes=period_minutes,
            reference_voltage_v=nominal_voltage,
        )
    return f"{direction} at {power_w:.0f}W until {cutoff_voltage_v} V ({period_minutes} minute period)"


def _build_dcr_power_experiment_steps(
    rate,
    nominal_current,
    nominal_voltage,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.5,
    rest_minutes=10,
    period_minutes=0.5,
    use_explicit_power_steps=True,
):
    power_w = rate * nominal_current * nominal_voltage
    rest_step = f"Rest for {rest_minutes} minute ({period_minutes} minute period)"
    exp_steps = [(
        _build_constant_power_step(
            direction="Charge",
            power_w=power_w,
            cutoff_voltage_v=charge_cutoff_v,
            nominal_current=nominal_current,
            nominal_voltage=nominal_voltage,
            period_minutes=period_minutes,
            use_explicit_power_steps=use_explicit_power_steps,
        ),
        rest_step,
        _build_constant_power_step(
            direction="Discharge",
            power_w=power_w,
            cutoff_voltage_v=discharge_cutoff_v,
            nominal_current=nominal_current,
            nominal_voltage=nominal_voltage,
            period_minutes=period_minutes,
            use_explicit_power_steps=use_explicit_power_steps,
        ),
        rest_step,
    )]
    return power_w, exp_steps


def _calculate_charge_time_hours(get_discharge_capacity_func, solution, nominal_current, dcr_charge_c_rate):
    full_charge_current = nominal_current * dcr_charge_c_rate
    if full_charge_current <= 0:
        return 0.0

    discharge_data = np.asarray(
        get_discharge_capacity_func(solution).get("discharge_capacity", []),
        dtype=float,
    )
    valid_capacity = discharge_data[np.isfinite(discharge_data)]
    if valid_capacity.size == 0:
        return 0.0
    return float(valid_capacity[-1]) / full_charge_current


def _run_single_dcr_rate_case(
    rate,
    model,
    solver,
    var_pts,
    get_hithium_params,
    get_discharge_capacity_func,
    total_cycles,
    cycles_per_block,
    temperature,
    nominal_current,
    nominal_voltage,
    target_soc,
    keep_only_last_cycle_solution,
    return_solutions,
    showprogress,
    conditioning_t_factor,
    aging_t_factor,
    record_conditioning_cycle,
    conditioning_cycle_number,
    cycle_number_factor,
    dcr_charge_c_rate,
    dcr_pulse_c_rate,
    dcr_pulse_duration_s,
    charge_cutoff_v,
    discharge_cutoff_v,
    conditioning_charge_cutoff_v,
    rest_minutes,
    period_minutes,
    use_explicit_power_steps,
):
    num_blocks = total_cycles // cycles_per_block
    conditioning_cutoff_v = charge_cutoff_v if conditioning_charge_cutoff_v is None else conditioning_charge_cutoff_v
    params = _make_parameter_values(get_hithium_params, conditioning_t_factor, temperature)
    power_w, conditioning_exp_steps = _build_dcr_power_experiment_steps(
        rate,
        nominal_current,
        nominal_voltage,
        charge_cutoff_v=conditioning_cutoff_v,
        discharge_cutoff_v=discharge_cutoff_v,
        rest_minutes=rest_minutes,
        period_minutes=period_minutes,
        use_explicit_power_steps=use_explicit_power_steps,
    )
    aging_exp_steps = None
    if num_blocks > 0:
        _, aging_exp_steps = _build_dcr_power_experiment_steps(
            rate,
            nominal_current,
            nominal_voltage,
            charge_cutoff_v=charge_cutoff_v,
            discharge_cutoff_v=discharge_cutoff_v,
            rest_minutes=rest_minutes,
            period_minutes=period_minutes,
            use_explicit_power_steps=use_explicit_power_steps,
        )

    initial_sim = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=pybamm.Experiment(conditioning_exp_steps, temperature=temperature),
        solver=solver,
        var_pts=var_pts,
    )
    current_solution = initial_sim.solve(showprogress=showprogress)
    stored_solutions = []
    if return_solutions:
        stored_solutions.append(_prepare_solution_for_storage(current_solution, keep_only_last_cycle_solution))
    restart_solution = current_solution.last_state if keep_only_last_cycle_solution else current_solution

    dcr_results = {}
    dcr_discharge_results = {}
    dcr_charge_results = {}
    power_results = {}
    charge_time_results = {}
    log_lines = []

    if record_conditioning_cycle:
        conditioning_charge_time = _calculate_charge_time_hours(
            get_discharge_capacity_func,
            current_solution,
            nominal_current,
            dcr_charge_c_rate,
        )
        conditioning_dcr_result = perform_dcr_test(
            current_solution.last_state if keep_only_last_cycle_solution else current_solution,
            params,
            model,
            solver,
            var_pts,
            current=nominal_current,
            C1=dcr_charge_c_rate,
            C2=dcr_pulse_c_rate,
            t=dcr_pulse_duration_s,
            charge_time=conditioning_charge_time,
            target_soc=target_soc,
        )
        conditioning_cycle = cycle_number_factor if conditioning_cycle_number is None else conditioning_cycle_number
        dcr_results[conditioning_cycle] = conditioning_dcr_result["dcr_mean"]
        dcr_discharge_results[conditioning_cycle] = conditioning_dcr_result["dcr_discharge"]
        dcr_charge_results[conditioning_cycle] = conditioning_dcr_result["dcr_charge"]
        power_results[conditioning_cycle] = {
            "power_discharge": conditioning_dcr_result["power_discharge"],
            "power_charge": conditioning_dcr_result["power_charge"],
        }
        charge_time_results[conditioning_cycle] = conditioning_dcr_result["charge_time"]
        log_lines.append(
            f"rate {rate} , Conditioning Cycle {conditioning_cycle}, DCR: "
            f"{conditioning_dcr_result['dcr_mean'] * 1000:.3f} mΩ, "
            f"Power: Discharge {conditioning_dcr_result['power_discharge']:.2f} W, "
            f"Charge {conditioning_dcr_result['power_charge']:.2f} W, "
            f"Charge Time: {conditioning_dcr_result['charge_time']:.2f} hour"
        )

    for block in range(num_blocks):
        params = _make_parameter_values(get_hithium_params, aging_t_factor, temperature)
        block_sim = pybamm.Simulation(
            model,
            parameter_values=params,
            experiment=pybamm.Experiment(aging_exp_steps * cycles_per_block, temperature=temperature),
            solver=solver,
            var_pts=var_pts,
        )
        current_solution = block_sim.solve(
            starting_solution=restart_solution,
            showprogress=showprogress,
            calc_esoh=False,
        )
        if return_solutions:
            stored_solutions.append(_prepare_solution_for_storage(current_solution, keep_only_last_cycle_solution))
        restart_solution = current_solution.last_state if keep_only_last_cycle_solution else current_solution

        current_discharge_time = _calculate_charge_time_hours(
            get_discharge_capacity_func,
            current_solution,
            nominal_current,
            dcr_charge_c_rate,
        )

        dcr_result = perform_dcr_test(
            current_solution.last_state if keep_only_last_cycle_solution else current_solution,
            params,
            model,
            solver,
            var_pts,
            current=nominal_current,
            C1=dcr_charge_c_rate,
            C2=dcr_pulse_c_rate,
            t=dcr_pulse_duration_s,
            charge_time=current_discharge_time,
            target_soc=target_soc,
        )
        current_cycle = (block + 1) * cycles_per_block * cycle_number_factor
        dcr_results[current_cycle] = dcr_result["dcr_mean"]
        dcr_discharge_results[current_cycle] = dcr_result["dcr_discharge"]
        dcr_charge_results[current_cycle] = dcr_result["dcr_charge"]
        power_results[current_cycle] = {
            "power_discharge": dcr_result["power_discharge"],
            "power_charge": dcr_result["power_charge"],
        }
        charge_time_results[current_cycle] = dcr_result["charge_time"]
        log_lines.append(
            f"rate {rate} , Cycle {current_cycle}, DCR: {dcr_result['dcr_mean'] * 1000:.3f} mΩ, "
            f"Power: Discharge {dcr_result['power_discharge']:.2f} W, Charge {dcr_result['power_charge']:.2f} W, "
            f"Charge Time: {dcr_result['charge_time']:.2f} hour"
        )

    return {
        "rate": rate,
        "power_w": power_w,
        "dcr": dcr_results,
        "dcr_discharge": dcr_discharge_results,
        "dcr_charge": dcr_charge_results,
        "power": power_results,
        "charge_time": charge_time_results,
        "sol_list": stored_solutions,
        "logs": log_lines,
    }


def _run_single_dcr_rate_case_from_tuple(task):
    return _run_single_dcr_rate_case(*task)


def run_dcr_and_power_test(
    rate_range,
    model,
    solver,
    var_pts,
    get_hithium_params,
    get_discharge_capacity_func=None,
    total_cycles=50,
    cycles_per_block=10,
    temperature=298.15,
    nominal_current=1175,
    nominal_voltage=3.2,
    target_soc=0.5,
    conditioning_t_factor=1,
    aging_t_factor=50,
    record_conditioning_cycle=False,
    conditioning_cycle_number=None,
    cycle_number_factor=1,
    dcr_charge_c_rate=0.25,
    dcr_pulse_c_rate=0.5,
    dcr_pulse_duration_s=10,
    charge_cutoff_v=3.65,
    discharge_cutoff_v=2.5,
    conditioning_charge_cutoff_v=None,
    rest_minutes=10,
    period_minutes=0.5,
    use_explicit_power_steps=True,
    parallel=False,
    max_workers=None,
    keep_only_last_cycle_solution=False,
    return_solutions=True,
    showprogress=True,
):
    """在多倍率与多循环下运行 DCR 与功率测试。

    参数
    ----------
    parallel : bool, optional
        Whether to parallelise independent rate cases with ProcessPoolExecutor.
    max_workers : int | None, optional
        Maximum worker count when ``parallel=True``.
    keep_only_last_cycle_solution : bool, optional
        Whether to only keep the last cycle for each stored solution entry.
    return_solutions : bool, optional
        Whether to return ``sol_list``. Set this to ``False`` to allow true
        process-based parallelism even when parameter functions contain
        non-picklable local closures.
    showprogress : bool, optional
        Forwarded to PyBaMM ``solve`` for progress-bar control.

    返回包含 DCR、功率、充电时间与 sol_list 的字典。
    """
    if get_discharge_capacity_func is None:
        from .analysis import get_discharge_capacity as get_discharge_capacity_func
    sol_list = []
    rate_dcr_results = {}
    rate_dcr_discharge_results = {}
    rate_dcr_charge_results = {}
    rate_power_results = {}
    rate_charge_time_results = {}
    per_rate_results = {}

    tasks = [
        (
            rate,
            model,
            solver,
            var_pts,
            get_hithium_params,
            get_discharge_capacity_func,
            total_cycles,
            cycles_per_block,
            temperature,
            nominal_current,
            nominal_voltage,
            target_soc,
            keep_only_last_cycle_solution,
            return_solutions,
            showprogress,
            conditioning_t_factor,
            aging_t_factor,
            record_conditioning_cycle,
            conditioning_cycle_number,
            cycle_number_factor,
            dcr_charge_c_rate,
            dcr_pulse_c_rate,
            dcr_pulse_duration_s,
            charge_cutoff_v,
            discharge_cutoff_v,
            conditioning_charge_cutoff_v,
            rest_minutes,
            period_minutes,
            use_explicit_power_steps,
        )
        for rate in rate_range
    ]

    if parallel and len(tasks) > 1:
        worker_count = max_workers or min(len(tasks), os.cpu_count() or 1)
        executor_type = ProcessPoolExecutor if not return_solutions else ThreadPoolExecutor
        with executor_type(max_workers=worker_count) as executor:
            rate_results = list(executor.map(_run_single_dcr_rate_case_from_tuple, tasks))
    else:
        rate_results = [_run_single_dcr_rate_case_from_tuple(task) for task in tasks]

    for rate_result in rate_results:
        rate = rate_result["rate"]
        per_rate_results[rate] = rate_result
        rate_dcr_results[rate] = rate_result["dcr"]
        rate_dcr_discharge_results[rate] = rate_result["dcr_discharge"]
        rate_dcr_charge_results[rate] = rate_result["dcr_charge"]
        rate_power_results[rate] = rate_result["power"]
        rate_charge_time_results[rate] = rate_result["charge_time"]
        sol_list.extend(rate_result["sol_list"])
        for log_line in rate_result["logs"]:
            print(log_line)

    return {
        "dcr": rate_dcr_results,
        "dcr_discharge": rate_dcr_discharge_results,
        "dcr_charge": rate_dcr_charge_results,
        "power": rate_power_results,
        "charge_time": rate_charge_time_results,
        "sol_list": sol_list,
        "rate_results": per_rate_results,
    }


def run_and_plot_all(
    rate_range,
    model,
    solver,
    var_pts,
    get_hithium_params,
    get_discharge_capacity_func=None,
    total_cycles=50,
    cycles_per_block=10,
    temperature=298.15,
):
    """[DEPRECATED] One-shot DCR/power simulation + efficiency plot.

    .. deprecated::
        This function violates the rule "src modules must not draw plots"
        (see ``src/AGENTS.md``). Call ``run_dcr_and_power_test`` in a notebook
        and invoke ``plot_efficiency_vs_cycle_all`` separately.
    """
    import warnings
    warnings.warn(
        "src.simulation.run_and_plot_all is deprecated: it draws plots inside "
        "src/, which violates AGENTS.md. Use run_dcr_and_power_test(...) and "
        "call plotting.plot_efficiency_vs_cycle_all(...) yourself in a notebook.",
        DeprecationWarning,
        stacklevel=2,
    )
    from .plotting import plot_efficiency_vs_cycle_all

    results = run_dcr_and_power_test(
        rate_range=rate_range,
        model=model,
        solver=solver,
        var_pts=var_pts,
        get_hithium_params=get_hithium_params,
        get_discharge_capacity_func=get_discharge_capacity_func,
        total_cycles=total_cycles,
        cycles_per_block=cycles_per_block,
        temperature=temperature,
    )
    sol_list = results["sol_list"]
    plot_efficiency_vs_cycle_all(sol_list, rate_range, cycles_per_block)
    return results
