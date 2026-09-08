"""Rebuild the CW363 100% SOC state by the actual 0.25P charge protocol."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


TASK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PARAMS_ROOT = PROJECT_ROOT / "params"
RUNS_ROOT = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw363_soc_ocv"
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
POWER_W = 0.25 * 1175 * 3.2
REST_HOURS = 2
ENDPOINT_OCV = {0: 2.687, 1: 3.388}

if str(PARAMS_ROOT) not in sys.path:
    sys.path.insert(0, str(PARAMS_ROOT))

from params1300CW363 import get_hithium_params  # noqa: E402


def scalar_parameter(parameters, key, sto):
    value = parameters[key]
    symbol = value(pybamm.Scalar(float(sto))) if callable(value) else pybamm.Scalar(value)
    return float(np.asarray(parameters.process_symbol(symbol).evaluate()).reshape(-1)[0])


def fresh_parameters(temperature_k):
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(t_factor=1, temperature=temperature_k),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Ambient temperature [K]": temperature_k,
            "Initial temperature [K]": temperature_k,
            "Open-circuit voltage at 0% SOC [V]": ENDPOINT_OCV[0],
            "Open-circuit voltage at 100% SOC [V]": ENDPOINT_OCV[1],
        },
        check_already_exists=False,
    )
    return parameters


def last_value(solution, candidates):
    for name in candidates:
        try:
            return float(np.asarray(solution[name].entries).reshape(-1)[-1]), name
        except KeyError:
            continue
    raise KeyError(f"None of the candidate variables exist: {candidates}")


def branch_ocv(parameters, xn, xp, temperature_k, branch):
    if branch == "charge":
        up_key = "Positive electrode delithiation OCP [V]"
        un_key = "Negative electrode lithiation OCP [V]"
    elif branch == "discharge":
        up_key = "Positive electrode lithiation OCP [V]"
        un_key = "Negative electrode delithiation OCP [V]"
    else:
        raise ValueError(branch)
    reference_k = float(parameters["Reference temperature [K]"])
    up = scalar_parameter(parameters, up_key, xp)
    un = scalar_parameter(parameters, un_key, xn)
    dup_dt = scalar_parameter(parameters, "Positive electrode OCP entropic change [V.K-1]", xp)
    dun_dt = scalar_parameter(parameters, "Negative electrode OCP entropic change [V.K-1]", xn)
    return up - un + (temperature_k - reference_k) * (dup_dt - dun_dt)


def run_case(temperature_c):
    temperature_k = temperature_c + 273.15
    parameters = fresh_parameters(temperature_k)
    model = pybamm.lithium_ion.DFN(
        {
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )
    experiment = pybamm.Experiment(
        [
            f"Charge at {POWER_W:g} W until 3.65 V",
            f"Rest for {REST_HOURS} hours",
        ],
        period="60 seconds",
    )
    simulation = pybamm.Simulation(
        model,
        parameter_values=parameters,
        experiment=experiment,
        var_pts=VAR_PTS,
        solver=pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6),
    )
    solution = simulation.solve(initial_soc=0)
    steps = [step for cycle in solution.cycles for step in cycle.steps]
    if len(steps) != 2:
        raise RuntimeError(f"Expected charge and rest steps, got {len(steps)}")
    charge_step, rest_step = steps

    charge_t = np.asarray(charge_step["Time [s]"].entries).reshape(-1)
    charge_i = np.asarray(charge_step["Current [A]"].entries).reshape(-1)
    charge_capacity_ah = float(np.trapz(-charge_i, charge_t) / 3600)
    cutoff_voltage = float(np.asarray(charge_step["Terminal voltage [V]"].entries).reshape(-1)[-1])
    rested_voltage = float(np.asarray(rest_step["Terminal voltage [V]"].entries).reshape(-1)[-1])
    rested_ocv, ocv_variable = last_value(
        rest_step,
        ["Battery open-circuit voltage [V]", "Surface open-circuit voltage [V]"],
    )
    c_n, c_n_variable = last_value(
        rest_step,
        [
            "X-averaged negative particle concentration [mol.m-3]",
            "X-averaged negative particle surface concentration [mol.m-3]",
        ],
    )
    c_p, c_p_variable = last_value(
        rest_step,
        [
            "X-averaged positive particle concentration [mol.m-3]",
            "X-averaged positive particle surface concentration [mol.m-3]",
        ],
    )
    xn = c_n / float(parameters["Maximum concentration in negative electrode [mol.m-3]"])
    xp = c_p / float(parameters["Maximum concentration in positive electrode [mol.m-3]"])
    charge_branch = branch_ocv(parameters, xn, xp, temperature_k, "charge")
    discharge_branch = branch_ocv(parameters, xn, xp, temperature_k, "discharge")

    all_t = np.asarray(solution["Time [s]"].entries).reshape(-1)
    all_v = np.asarray(solution["Terminal voltage [V]"].entries).reshape(-1)
    timeseries = pd.DataFrame(
        {
            "temperature_c": temperature_c,
            "time_h": all_t / 3600,
            "terminal_voltage_v": all_v,
        }
    )
    metrics = {
        "temperature_c": temperature_c,
        "power_w": POWER_W,
        "charge_capacity_ah": charge_capacity_ah,
        "charge_duration_h": float(charge_t[-1] / 3600),
        "cutoff_voltage_v": cutoff_voltage,
        "rest_duration_h": REST_HOURS,
        "rested_terminal_voltage_v": rested_voltage,
        "rested_model_ocv_v": rested_ocv,
        "final_xn": xn,
        "final_xp": xp,
        "charge_branch_ocv_v": charge_branch,
        "discharge_branch_ocv_v": discharge_branch,
        "current_sigmoid_midpoint_v": 0.5 * (charge_branch + discharge_branch),
        "ocv_variable": ocv_variable,
        "negative_concentration_variable": c_n_variable,
        "positive_concentration_variable": c_p_variable,
        "termination": solution.termination,
    }
    return metrics, timeseries


def main():
    run_dir = RUNS_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S_protocol_100soc")
    run_dir.mkdir(parents=True, exist_ok=False)
    results = []
    series = []
    for temperature_c in (25.0, 45.0):
        metrics, timeseries = run_case(temperature_c)
        results.append(metrics)
        series.append(timeseries)

    metrics_df = pd.DataFrame(results)
    measured = {25.0: 3.388, 45.0: 3.493}
    metrics_df["measured_static_ocv_v"] = metrics_df["temperature_c"].map(measured)
    metrics_df["rested_error_mv"] = (
        metrics_df["rested_terminal_voltage_v"] - metrics_df["measured_static_ocv_v"]
    ) * 1000
    metrics_df["charge_branch_error_mv"] = (
        metrics_df["charge_branch_ocv_v"] - metrics_df["measured_static_ocv_v"]
    ) * 1000
    metrics_df.to_csv(run_dir / "protocol_metrics.csv", index=False, encoding="utf-8-sig")
    pd.concat(series, ignore_index=True).to_csv(
        run_dir / "protocol_timeseries.csv", index=False, encoding="utf-8-sig"
    )
    manifest = {
        "protocol": "Start from calibrated 0% SOC; charge at 940 W to 3.65 V; rest 2 h",
        "capacity_basis_ah": 1175,
        "power_definition": "0.25 x 1175 Ah x 3.2 V",
        "model": "PyBaMM DFN, CW363, current sigmoid OCP",
        "pybamm_version": pybamm.__version__,
        "results": results,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    combined = pd.concat(series, ignore_index=True)
    for temperature_c, color in ((25.0, "#005BAC"), (45.0, "#D1495B")):
        subset = combined[combined["temperature_c"] == temperature_c]
        ax.plot(
            subset["time_h"],
            subset["terminal_voltage_v"],
            color=color,
            label=f"{temperature_c:.0f}°C",
        )
    ax.axhline(3.65, color="#444444", linestyle="--", linewidth=1, label="3.65 V cutoff")
    ax.set(xlabel="Time (h)", ylabel="Terminal voltage (V)", title="CW363 940 W Charge and 2 h Rest")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(run_dir / "charge_rest_voltage.png", dpi=220)
    plt.close(fig)

    print(run_dir)
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
