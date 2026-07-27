"""Run the 314 Ah BOL ARC heat benchmark for two voltage windows and P-rates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
for path in (PROJECT_ROOT, PARAMS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from params314 import get_hithium_params
from src.heat_calibration import (
    build_calibrated_parameter_loader,
    load_branch_entropy_curves,
)


CELL_NAME = "314Ah"
TEMPERATURE_K = 298.15
NOMINAL_VOLTAGE_V = 3.2
UPPER_CUTOFF_V = 3.65
LOWER_CUTOFFS_V = (2.50, 2.70)
P_RATES = (0.25, 0.50)
PERIOD_SECONDS = 10
SOLVER_RTOL = 1e-6
SOLVER_ATOL = 1e-6
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}

# Keep the same calibrated heat convention as the latest 314 Ah lifecycle notebook.
HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT = 0.350444
CONTACT_RESISTANCE_OHM = 0.1002e-3
ENTROPY_SAMPLE_LABEL = "SOH95%"
ENTROPY_CURVE_FILE = (
    WORKSPACE_ROOT
    / "data_raw"
    / "AI_virtual_cell"
    / "Exp"
    / "熵热系数测试数据"
    / "analysis_output"
    / "entropy_coefficient_fits_by_branch.csv"
)
CALIBRATED_GET_PARAMS = build_calibrated_parameter_loader(
    get_hithium_params,
    HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT,
)

MODEL_OPTIONS = {
    "calculate discharge energy": "true",
    "contact resistance": "true",
    "open-circuit potential": ("current sigmoid", "current sigmoid"),
    "calculate heat source for isothermal models": "true",
}

# The supplied reports and raw cabinet data both terminate at about 2.50 V.
ARC_MEASUREMENTS = {
    (0.25, "charge"): {
        "duration_min": 261.25,
        "capacity_ah": 327.352783,
        "heat_w": 4.679755988516748,
    },
    (0.25, "discharge"): {
        "duration_min": 256.65,
        "capacity_ah": 331.575958,
        "heat_w": 4.199868359244107,
    },
    (0.50, "charge"): {
        "duration_min": 133.10,
        "capacity_ah": 330.894104,
        "heat_w": 12.579147880791387,
    },
    (0.50, "discharge"): {
        "duration_min": 126.68333333333334,
        "capacity_ah": 331.129486,
        "heat_w": 12.166404426785952,
    },
}


def _entries(step, variable_name):
    values = np.asarray(step[variable_name].entries, dtype=float).squeeze()
    if values.ndim > 1:
        values = np.mean(values, axis=tuple(range(values.ndim - 1)))
    return values.reshape(-1)


def _time_weighted_mean(step, variable_name):
    time_s = _entries(step, "Time [s]")
    values = _entries(step, variable_name)
    return float(np.trapz(values, time_s) / (time_s[-1] - time_s[0]))


def _reference_reversible_heat(step, direction, entropy_curves, x_0, x_100):
    time_s = _entries(step, "Time [s]")
    current_a = _entries(step, "Current [A]")
    temperature_k = _entries(step, "Volume-averaged cell temperature [K]")
    negative_stoichiometry = _entries(step, "Average negative particle stoichiometry")
    soc_pct = 100.0 * (negative_stoichiometry - x_0) / (x_100 - x_0)
    soc_pct = np.clip(soc_pct, 0.0, 100.0)
    curve_soc, curve_dudt = entropy_curves[direction]
    dudt_v_per_k = np.interp(soc_pct, curve_soc, curve_dudt)
    reversible_w = current_a * temperature_k * dudt_v_per_k
    return float(np.trapz(reversible_w, time_s) / (time_s[-1] - time_s[0]))


def _build_parameters(lower_cutoff_v):
    parameters = pybamm.ParameterValues("OKane2022")
    cell_parameters = CALIBRATED_GET_PARAMS(1, temperature=TEMPERATURE_K)
    cell_parameters["Contact resistance [Ohm]"] = CONTACT_RESISTANCE_OHM
    cell_parameters["Lower voltage cut-off [V]"] = lower_cutoff_v - 0.01
    cell_parameters["Upper voltage cut-off [V]"] = UPPER_CUTOFF_V + 0.01
    parameters.update(cell_parameters, check_already_exists=False)
    return parameters


def _extract_step_row(step, parameters, lower_cutoff_v, p_rate, direction, entropy_curves):
    nominal_capacity_ah = float(parameters["Nominal cell capacity [A.h]"])
    power_w = p_rate * nominal_capacity_ah * NOMINAL_VOLTAGE_V
    time_s = _entries(step, "Time [s]")
    current_a = _entries(step, "Current [A]")
    voltage_v = _entries(step, "Voltage [V]")
    throughput_ah = _entries(step, "Throughput capacity [A.h]")
    x_0, x_100, _, _ = pybamm.lithium_ion.get_min_max_stoichiometries(
        parameters,
        options=MODEL_OPTIONS,
    )

    ohmic_w = _time_weighted_mean(step, "Ohmic heating [W]")
    reaction_w = _time_weighted_mean(step, "Irreversible electrochemical heating [W]")
    mixing_w = _time_weighted_mean(step, "Heat of mixing [W]")
    hysteresis_w = _time_weighted_mean(step, "Hysteresis electrochemical heating [W]")
    contact_w = float(np.trapz(current_a**2 * CONTACT_RESISTANCE_OHM, time_s) / (time_s[-1] - time_s[0]))
    pybamm_reversible_w = _time_weighted_mean(step, "Reversible heating [W]")
    reference_reversible_w = _reference_reversible_heat(
        step,
        direction,
        entropy_curves,
        float(x_0),
        float(x_100),
    )
    pybamm_total_w = _time_weighted_mean(step, "Total heating [W]") + contact_w
    internal_irreversible_w = ohmic_w + reaction_w + mixing_w + hysteresis_w + contact_w
    calibrated_total_w = internal_irreversible_w + reference_reversible_w

    row = {
        "cell": CELL_NAME,
        "temperature_c": TEMPERATURE_K - 273.15,
        "lower_cutoff_v": lower_cutoff_v,
        "upper_cutoff_v": UPPER_CUTOFF_V,
        "p_rate": p_rate,
        "direction": direction,
        "power_w": power_w,
        "nominal_capacity_ah": nominal_capacity_ah,
        "duration_min": float((time_s[-1] - time_s[0]) / 60.0),
        "capacity_ah": float(throughput_ah[-1] - throughput_ah[0]),
        "start_voltage_v": float(voltage_v[0]),
        "end_voltage_v": float(voltage_v[-1]),
        "mean_voltage_v": float(np.trapz(voltage_v, time_s) / (time_s[-1] - time_s[0])),
        "mean_abs_current_a": float(np.trapz(np.abs(current_a), time_s) / (time_s[-1] - time_s[0])),
        "ohmic_w": ohmic_w,
        "reaction_w": reaction_w,
        "mixing_w": mixing_w,
        "hysteresis_w": hysteresis_w,
        "contact_w": contact_w,
        "internal_irreversible_w": internal_irreversible_w,
        "pybamm_reversible_w": pybamm_reversible_w,
        "reference_reversible_w": reference_reversible_w,
        "pybamm_total_incl_contact_w": pybamm_total_w,
        "calibrated_total_w": calibrated_total_w,
        "entropy_soc_min_pct": float(np.min(100.0 * (_entries(step, "Average negative particle stoichiometry") - x_0) / (x_100 - x_0))),
        "entropy_soc_max_pct": float(np.max(100.0 * (_entries(step, "Average negative particle stoichiometry") - x_0) / (x_100 - x_0))),
    }
    measured = ARC_MEASUREMENTS.get((p_rate, direction)) if lower_cutoff_v == 2.50 else None
    row["arc_measured_heat_w"] = measured["heat_w"] if measured else np.nan
    row["arc_measured_capacity_ah"] = measured["capacity_ah"] if measured else np.nan
    row["arc_measured_duration_min"] = measured["duration_min"] if measured else np.nan
    row["calibrated_error_pct"] = (
        (calibrated_total_w / measured["heat_w"] - 1.0) * 100.0 if measured else np.nan
    )
    row["pybamm_error_pct"] = (
        (pybamm_total_w / measured["heat_w"] - 1.0) * 100.0 if measured else np.nan
    )
    row["capacity_error_pct"] = (
        (row["capacity_ah"] / measured["capacity_ah"] - 1.0) * 100.0 if measured else np.nan
    )
    row["duration_error_pct"] = (
        (row["duration_min"] / measured["duration_min"] - 1.0) * 100.0 if measured else np.nan
    )
    return row


def _solve_case(lower_cutoff_v, p_rate, entropy_curves):
    parameters = _build_parameters(lower_cutoff_v)
    nominal_capacity_ah = float(parameters["Nominal cell capacity [A.h]"])
    power_w = p_rate * nominal_capacity_ah * NOMINAL_VOLTAGE_V
    discharge_step = f"Discharge at {power_w:.3f} W until {lower_cutoff_v:.2f} V ({PERIOD_SECONDS} second period)"
    charge_step = f"Charge at {power_w:.3f} W until {UPPER_CUTOFF_V:.2f} V ({PERIOD_SECONDS} second period)"
    rest_step = "Rest for 10 minutes"
    experiment = pybamm.Experiment(
        [(discharge_step, rest_step, charge_step, rest_step, discharge_step)],
        temperature=TEMPERATURE_K,
    )
    simulation = pybamm.Simulation(
        pybamm.lithium_ion.DFN(MODEL_OPTIONS),
        parameter_values=parameters,
        experiment=experiment,
        var_pts=VAR_PTS,
        solver=pybamm.IDAKLUSolver(rtol=SOLVER_RTOL, atol=SOLVER_ATOL),
    )
    solution = simulation.solve(initial_soc=1.0, showprogress=False)
    cycle_steps = solution.cycles[0].steps
    if len(cycle_steps) != 5:
        raise RuntimeError(f"Expected five conditioning/measurement steps, got {len(cycle_steps)}")
    return [
        _extract_step_row(cycle_steps[2], parameters, lower_cutoff_v, p_rate, "charge", entropy_curves),
        _extract_step_row(cycle_steps[4], parameters, lower_cutoff_v, p_rate, "discharge", entropy_curves),
    ]


def _save_plots(results, plots_dir):
    plt.style.use("science")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Calibri", "SimHei", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    measured = results[results["lower_cutoff_v"].eq(2.50)].copy()
    labels = [f"{rate:g}P\n{'充电' if direction == 'charge' else '放电'}" for rate, direction in zip(measured["p_rate"], measured["direction"])]
    x = np.arange(len(measured))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    ax.bar(x - width, measured["arc_measured_heat_w"], width, label="ARC实测", color="#555555")
    ax.bar(x, measured["pybamm_total_incl_contact_w"], width, label="PyBaMM原始", color="#4C78A8")
    ax.bar(x + width, measured["calibrated_total_w"], width, label="校准后处理", color="#E45756")
    ax.set_xticks(x, labels)
    ax.set_ylabel("平均产热功率 (W)")
    ax.set_title("314Ah 2.5-3.65V BOL产热：实测与仿真")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "01_2.5V实测仿真对标.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    for (p_rate, direction), group in results.groupby(["p_rate", "direction"], sort=True):
        group = group.sort_values("lower_cutoff_v")
        label = f"{p_rate:g}P {'充电' if direction == 'charge' else '放电'}"
        ax.plot(group["lower_cutoff_v"], group["calibrated_total_w"], marker="o", label=label)
    ax.set_xticks(LOWER_CUTOFFS_V)
    ax.set_xlabel("放电截止电压 (V)")
    ax.set_ylabel("校准平均产热功率 (W)")
    ax.set_title("314Ah BOL产热对电压窗口的敏感性")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(plots_dir / "02_2.5V与2.7V窗口敏感性.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    component_columns = ["ohmic_w", "reaction_w", "mixing_w", "hysteresis_w", "contact_w", "reference_reversible_w"]
    component_labels = ["欧姆热", "反应热", "混合热", "滞后热", "接触热", "可逆热(实测熵热)"]
    component_colors = ["#4C78A8", "#72B7B2", "#B279A2", "#F2CF5B", "#9D755D", "#E45756"]
    ordered = results.sort_values(["lower_cutoff_v", "p_rate", "direction"]).reset_index(drop=True)
    labels = [f"{row.lower_cutoff_v:.1f}V {row.p_rate:g}P\n{'充电' if row.direction == 'charge' else '放电'}" for row in ordered.itertuples()]
    x = np.arange(len(ordered))
    positive_bottom = np.zeros(len(ordered))
    negative_bottom = np.zeros(len(ordered))
    fig, ax = plt.subplots(figsize=(12.0, 5.8))
    for column, label, color in zip(component_columns, component_labels, component_colors):
        values = ordered[column].to_numpy(dtype=float)
        bottom = np.where(values >= 0, positive_bottom, negative_bottom)
        ax.bar(x, values, bottom=bottom, label=label, color=color)
        positive_bottom += np.where(values >= 0, values, 0.0)
        negative_bottom += np.where(values < 0, values, 0.0)
    ax.set_xticks(x, labels)
    ax.set_ylabel("平均产热功率 (W)")
    ax.set_title("314Ah BOL校准产热分项")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(ncol=3)
    fig.tight_layout()
    fig.savefig(plots_dir / "03_产热分项.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_benchmark(run_id=None):
    run_id = run_id or f"{datetime.now():%Y%m%d_%H%M%S}_314Ah_BOL_ARC"
    run_dir = PROJECT_ROOT / "output" / "runs" / "bol_heat_benchmark" / run_id
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=False)
    entropy_curves = load_branch_entropy_curves(
        ENTROPY_CURVE_FILE,
        sample_label=ENTROPY_SAMPLE_LABEL,
    )

    rows = []
    for lower_cutoff_v in LOWER_CUTOFFS_V:
        for p_rate in P_RATES:
            print(f"运行：{lower_cutoff_v:.1f}-3.65V, {p_rate:g}P，含预处理放电")
            rows.extend(_solve_case(lower_cutoff_v, p_rate, entropy_curves))
    results = pd.DataFrame(rows).sort_values(["lower_cutoff_v", "p_rate", "direction"]).reset_index(drop=True)
    results.to_csv(run_dir / "metrics.csv", index=False, encoding="utf-8-sig")

    experiment_rows = []
    for (p_rate, direction), values in ARC_MEASUREMENTS.items():
        experiment_rows.append(
            {
                "lower_cutoff_v": 2.50,
                "upper_cutoff_v": 3.65,
                "p_rate": p_rate,
                "direction": direction,
                **values,
            }
        )
    pd.DataFrame(experiment_rows).to_csv(run_dir / "arc_measurements.csv", index=False, encoding="utf-8-sig")

    config = {
        "cell": CELL_NAME,
        "scope": "BOL only; aging submodels disabled; isothermal electrochemical solve with heat-source postprocessing",
        "temperature_c": TEMPERATURE_K - 273.15,
        "lower_cutoffs_v": LOWER_CUTOFFS_V,
        "upper_cutoff_v": UPPER_CUTOFF_V,
        "p_rates": P_RATES,
        "nominal_voltage_v": NOMINAL_VOLTAGE_V,
        "contact_resistance_ohm": CONTACT_RESISTANCE_OHM,
        "hysteresis_equilibrium_charge_weight": HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT,
        "entropy_sample_label": ENTROPY_SAMPLE_LABEL,
        "entropy_curve_file": str(ENTROPY_CURVE_FILE),
        "reversible_heat_soc_basis": "Average negative particle stoichiometry mapped by eSOH x_0/x_100",
        "arc_protocol_verified_from_raw_data": "actual lower cutoff is 2.50 V, not 2.70 V",
        "var_pts": VAR_PTS,
        "pybamm_version": pybamm.__version__,
    }
    (run_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    _save_plots(results, plots_dir)

    benchmark = results[results["lower_cutoff_v"].eq(2.50)]
    mean_abs_error = float(benchmark["calibrated_error_pct"].abs().mean())
    max_abs_error = float(benchmark["calibrated_error_pct"].abs().max())
    log_lines = [
        f"run_id={run_id}",
        f"completed_cases={len(results)}",
        f"mean_absolute_calibrated_error_pct={mean_abs_error:.3f}",
        f"max_absolute_calibrated_error_pct={max_abs_error:.3f}",
        "verified_arc_lower_cutoff_v=2.50",
    ]
    (run_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"完成：{len(results)} 个方向工况，结果目录：{run_dir}")
    return results, run_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    results, run_dir = run_benchmark(args.run_id)
    columns = [
        "lower_cutoff_v",
        "p_rate",
        "direction",
        "calibrated_total_w",
        "pybamm_total_incl_contact_w",
        "arc_measured_heat_w",
        "calibrated_error_pct",
    ]
    print(results[columns].to_string(index=False))
    print(run_dir)


if __name__ == "__main__":
    main()
