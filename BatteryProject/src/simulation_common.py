"""PyBaMM 仿真公共辅助函数。

供 simulation_dcr / simulation_rpt / simulation_frequency 等子模块复用，
不直接对外暴露——通过 simulation.py 的回出口转发。
"""
import pybamm


def ensure_hysteresis_state_params(params):
    """Ensure hysteresis state parameters exist for hysteresis-enabled OCP models."""
    params.update(
        {
            "Initial hysteresis state in negative electrode": 0.0,
            "Initial hysteresis state in positive electrode": 0.0,
        },
        check_already_exists=False,
    )
    return params


def _make_parameter_values(get_hithium_params, t_factor, temperature, *, check_already_exists=False):
    params = pybamm.ParameterValues("OKane2022")
    params.update(
        get_hithium_params(t_factor=t_factor, temperature=temperature),
        check_already_exists=check_already_exists,
    )
    return ensure_hysteresis_state_params(params)


def _compress_solution_to_last_cycle(solution):
    """Return a lightweight copy that only keeps the last cycle for analysis output."""
    if solution is None:
        return None

    cycles = getattr(solution, "cycles", None)
    if not cycles:
        return solution.last_state if hasattr(solution, "last_state") else solution

    last_cycle = cycles[-1]
    compact_solution = last_cycle.copy()
    compact_solution.cycles = [last_cycle]
    compact_solution.all_summary_variables = [getattr(last_cycle, "cycle_summary_variables", None)]
    compact_solution.all_first_states = [last_cycle.first_state]
    compact_solution.initial_start_time = solution.initial_start_time
    return compact_solution


def _prepare_solution_for_storage(solution, keep_only_last_cycle_solution):
    if keep_only_last_cycle_solution:
        return _compress_solution_to_last_cycle(solution)
    return solution
