"""PyBaMM 峰值电流 / 峰值功率搜索。

提供 ``peak_current_condition`` 与 ``run_peak_current``：在不同 SOC
下搜索受电压上下限约束的最大可施加电流（或恒功率）。
"""
import logging

import numpy as np
import pybamm
from scipy.optimize import root_scalar

logger = logging.getLogger(__name__)


HYSTERESIS_OCP_OPTIONS = {
    "current sigmoid",
    "one-state hysteresis",
    "one-state differential capacity hysteresis",
    "Axen",
    "Wycisk",
}
PEAK_POWER_REFERENCE_VOLTAGE = 3.2


def _normalize_peak_mode(mode):
    normalized_mode = str(mode).upper()
    if normalized_mode not in {"A", "W"}:
        raise ValueError(f"Unsupported peak mode: {mode}. Expected 'A' or 'W'.")
    return normalized_mode


def peak_current_condition(nominal, temperature, ratio, time=10, mode="A"):
    """Build the pulse experiment for peak search in current or power mode.

    Parameters
    ----------
    nominal : float
        Base current in A. In ``mode='W'``, the applied power is
        ``ratio * nominal * 3.2`` W.
    temperature : float
        Experiment temperature in K.
    ratio : float
        Dimensionless search ratio.
    time : float, optional
        Pulse duration in seconds.
    mode : {"A", "W"}, optional
        ``"A"`` for constant-current pulses, ``"W"`` for constant-power pulses.
    """
    normalized_mode = _normalize_peak_mode(mode)
    applied_value = nominal * ratio
    if normalized_mode == "W":
        applied_value *= PEAK_POWER_REFERENCE_VOLTAGE
    if np.isnan(applied_value):
        raise ValueError("Applied peak value is NaN")
    value_unit = "A" if normalized_mode == "A" else "W"
    charge_peak = pybamm.Experiment(
        [f"Charge at {applied_value:.2f}{value_unit} for {time} second until 3.65 V (5 second period)"],
        temperature=temperature,
    )
    discharge_peak = pybamm.Experiment(
        [f"Discharge at {applied_value:.2f}{value_unit} for {time} second until 2.5 V (5 second period)"],
        temperature=temperature,
    )
    return {"charge_peak": charge_peak, "discharge_peak": discharge_peak}


def _option_uses_hysteresis(option_value):
    if isinstance(option_value, str):
        return option_value in HYSTERESIS_OCP_OPTIONS
    if isinstance(option_value, tuple):
        return any(_option_uses_hysteresis(item) for item in option_value)
    return False


def _get_hysteresis_state_parameter_names(model_options):
    parameter_names = []
    for electrode in ["negative", "positive"]:
        domain_options = getattr(model_options, electrode)
        open_circuit_potential = domain_options["open-circuit potential"]
        if domain_options["particle phases"] == "2" and isinstance(
            open_circuit_potential, tuple
        ):
            phase_names = ["Primary", "Secondary"]
            for phase_name, phase_option in zip(phase_names, open_circuit_potential):
                if _option_uses_hysteresis(phase_option):
                    parameter_names.append(
                        f"{phase_name}: Initial hysteresis state in {electrode} electrode"
                    )
        elif _option_uses_hysteresis(open_circuit_potential):
            parameter_names.append(
                f"Initial hysteresis state in {electrode} electrode"
            )
    return parameter_names


def _prepare_peak_current_parameter_values(parameter_values, model):
    prepared_values = parameter_values.copy()
    for parameter_name in _get_hysteresis_state_parameter_names(model.options):
        try:
            prepared_values[parameter_name]
        except KeyError:
            prepared_values.update({parameter_name: 0})
    return prepared_values


def _default_peak_search_ratios(current_guess, min_ratio=0.01, max_ratio=50):
    ratios = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]
    if current_guess is not None and np.isfinite(current_guess) and current_guess > 0:
        ratios.extend([current_guess / 2, current_guess, current_guess * 2])
    unique_ratios = sorted(
        {
            float(ratio)
            for ratio in ratios
            if np.isfinite(ratio) and min_ratio <= float(ratio) <= max_ratio
        }
    )
    return unique_ratios


def _find_peak_current_bracket(
    objective_function, search_ratios, max_extensions=8, extension_factor=2.0
):
    """在采样比例中寻找目标函数符号变化区间。

    若给定网格内无符号变化（根落在网格外，例如低温下峰值倍率刚好
    超过最大采样值），则从网格两端按几何步长（×/÷ extension_factor）
    向外自适应扩展，每个方向最多 ``max_extensions`` 次。

    返回 (left_ratio, right_ratio, sampled_values)；left==right 表示采样点
    恰好命中根；两者为 None 表示扩展后仍未找到符号变化。
    """
    sampled_values = []
    for ratio in search_ratios:
        value = float(objective_function(ratio))
        sampled_values.append((ratio, value))
        if abs(value) < 1e-8:
            return ratio, ratio, sampled_values
        if len(sampled_values) >= 2:
            left_ratio, left_value = sampled_values[-2]
            if np.sign(left_value) != np.sign(value):
                return left_ratio, ratio, sampled_values

    if not sampled_values:
        return None, None, sampled_values

    # 网格内无符号变化：先向上扩展（峰值倍率超过最大采样值，最常见），
    # 超大电流的脉冲不可行时目标函数会变号/置负，扩展会很快终止。
    prev_ratio, prev_value = sampled_values[-1]
    ratio = prev_ratio
    for _ in range(max_extensions):
        ratio *= extension_factor
        value = float(objective_function(ratio))
        sampled_values.append((ratio, value))
        if abs(value) < 1e-8:
            return ratio, ratio, sampled_values
        if np.sign(value) != np.sign(prev_value):
            return prev_ratio, ratio, sampled_values
        prev_ratio, prev_value = ratio, value

    # 再向下扩展（根小于最小采样比例的少见情形）
    prev_ratio, prev_value = sampled_values[0]
    ratio = prev_ratio
    for _ in range(max_extensions):
        ratio /= extension_factor
        value = float(objective_function(ratio))
        sampled_values.append((ratio, value))
        if abs(value) < 1e-8:
            return ratio, ratio, sampled_values
        if np.sign(value) != np.sign(prev_value):
            return ratio, prev_ratio, sampled_values
        prev_ratio, prev_value = ratio, value

    return None, None, sampled_values


def run_peak_current(
    model,
    param,
    var_pts,
    temperature=298.15,
    nominal=164,
    t_period=60,
    x0=1,
    charge_soc_list=None,
    discharge_soc_list=None,
    search_ratios=None,
    mode="A",
):
    """Search peak charge/discharge capability across SOC.

    Parameters
    ----------
    nominal : float
        Base current in A. In ``mode='A'`` the pulse is ``ratio * nominal`` A.
        In ``mode='W'`` the pulse is ``ratio * nominal * 3.2`` W.
    mode : {"A", "W"}, optional
        Search in constant-current or constant-power mode.

    Returns
    -------
    dict
        Includes SOC grids, equivalent peak currents at 3.2 V, peak powers,
        and the first voltage point of each successful pulse.
    """
    normalized_mode = _normalize_peak_mode(mode)
    solver = pybamm.IDAKLUSolver(
        output_variables=[
            "Time [s]",
            "Current [A]",
            "Voltage [V]",
            "Throughput capacity [A.h]",
            "Negative electrode potential [V]",
        ],
        rtol=1e-6,
        atol=1e-6,
    )
    charge_soc_list = np.asarray(
        charge_soc_list if charge_soc_list is not None else np.arange(0.95, 0 - 1e-8, -0.05),
        dtype=float,
    )
    discharge_soc_list = np.asarray(
        discharge_soc_list if discharge_soc_list is not None else np.arange(1, 0.05 - 1e-8, -0.05),
        dtype=float,
    )
    charge_peak_current = []
    discharge_peak_current = []
    charge_peak_power = []
    discharge_peak_power = []
    charge_first_voltage = []
    discharge_first_voltage = []
    prepared_param = _prepare_peak_current_parameter_values(param, model)

    def sim_objective(ratio, soc, temperature, process_name="charge_peak", t_period=10, return_first_voltage=False):
        V_end = 3.65 if process_name == "charge_peak" else 2.5
        direction = "charge" if process_name == "charge_peak" else "discharge"
        if ratio <= 0:
            return 1000
        exp = peak_current_condition(nominal, temperature, ratio, t_period, mode=normalized_mode)[process_name]
        sim = pybamm.Simulation(
            model,
            parameter_values=prepared_param,
            experiment=exp,
            solver=solver,
            var_pts=var_pts,
        )
        sol = sim.solve(
            initial_soc=np.clip(soc, 0.01, 0.99),
            direction=direction,
        )
        if isinstance(sol, pybamm.EmptySolution):
            if return_first_voltage:
                return np.nan
            return -float(t_period)
        t = sol["Time [s]"].entries[-1]
        V = sol["Voltage [V]"].entries[-1]
        V0 = sol["Voltage [V]"].entries[0]
        if return_first_voltage:
            return V0
        if abs(t - t_period) < 0.02:
            if process_name == "charge_peak":
                return V_end - V
            return V - V_end
        return t - t_period

    def get_peak_current(
        soc,
        temperature,
        process_name,
        current_guess,
        record_first_voltage_list=None,
    ):
        def objective_function(ratio):
            return sim_objective(ratio, soc, temperature, process_name, t_period)

        logger.info("[Start] %s SOC=%.2f ...", process_name, soc)
        try:
            ratio_grid = (
                list(search_ratios)
                if search_ratios is not None
                else _default_peak_search_ratios(current_guess)
            )
            left_ratio, right_ratio, sampled_values = _find_peak_current_bracket(
                objective_function, ratio_grid
            )
            if left_ratio is None:
                logger.warning(
                    "Optimization skipped: no sign change found in sampled ratios %s",
                    sampled_values,
                )
                result = np.nan
            elif left_ratio == right_ratio:
                result = left_ratio
            else:
                sol_result = root_scalar(
                    objective_function,
                    bracket=[left_ratio, right_ratio],
                    method="brentq",
                    xtol=1e-2,
                )
                result = sol_result.root
        except Exception as e:
            logger.warning("Optimization failed: %s", e)
            result = np.nan
        logger.info("[Done] %s SOC=%.2f -> ratio=%.4f", process_name, soc, result)

        if record_first_voltage_list is not None:
            if not np.isnan(result):
                try:
                    v0_val = sim_objective(result, soc, temperature, process_name, t_period, return_first_voltage=True)
                    record_first_voltage_list.append(v0_val)
                except Exception:
                    record_first_voltage_list.append(np.nan)
            else:
                record_first_voltage_list.append(np.nan)
        return result

    current_guess = x0
    for one_soc in charge_soc_list:
        result = get_peak_current(
            one_soc,
            temperature,
            "charge_peak",
            current_guess,
            record_first_voltage_list=charge_first_voltage,
        )
        if result is not None and not np.isnan(result):
            charge_peak_current.append(result * nominal)
            charge_peak_power.append(result * nominal * PEAK_POWER_REFERENCE_VOLTAGE)
            current_guess = result
        else:
            charge_peak_current.append(np.nan)
            charge_peak_power.append(np.nan)
            current_guess = x0

    current_guess = x0
    for one_soc in discharge_soc_list:
        result = get_peak_current(
            one_soc,
            temperature,
            "discharge_peak",
            current_guess,
            record_first_voltage_list=discharge_first_voltage,
        )
        if result is not None and not np.isnan(result):
            discharge_peak_current.append(result * nominal)
            discharge_peak_power.append(result * nominal * PEAK_POWER_REFERENCE_VOLTAGE)
            current_guess = result
        else:
            discharge_peak_current.append(np.nan)
            discharge_peak_power.append(np.nan)
            current_guess = x0

    return {
        "mode": normalized_mode,
        "charge_soc": charge_soc_list.tolist(),
        "charge_peak_current": charge_peak_current,
        "charge_peak_power": charge_peak_power,
        "charge_first_voltage": charge_first_voltage,
        "discharge_soc": discharge_soc_list.tolist(),
        "discharge_peak_current": discharge_peak_current,
        "discharge_peak_power": discharge_peak_power,
        "discharge_first_voltage": discharge_first_voltage,
    }
