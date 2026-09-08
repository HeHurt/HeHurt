"""Build separate 25/45 degC CW363 discharge-static OCV parameter variants."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm
import yaml
from scipy.interpolate import PchipInterpolator


TASK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PARAMS_ROOT = PROJECT_ROOT / "params"
RUNS_ROOT = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw363_soc_ocv"
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
POWER_W = 0.25 * 1175 * 3.2
REST_HOURS = 2
ENDPOINT_VOLTAGES = {0: 2.687, 1: 3.388}

if str(PARAMS_ROOT) not in sys.path:
    sys.path.insert(0, str(PARAMS_ROOT))

from params1300CW363 import get_hithium_params  # noqa: E402


def scalar_parameter(parameters, key, sto):
    value = parameters[key]
    symbol = value(pybamm.Scalar(float(sto))) if callable(value) else pybamm.Scalar(value)
    return float(np.asarray(parameters.process_symbol(symbol).evaluate()).reshape(-1)[0])


def fresh_parameters(temperature_k, discharge_ocp=None):
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(t_factor=1, temperature=temperature_k),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Ambient temperature [K]": temperature_k,
            "Initial temperature [K]": temperature_k,
            "Open-circuit voltage at 0% SOC [V]": ENDPOINT_VOLTAGES[0],
            "Open-circuit voltage at 100% SOC [V]": ENDPOINT_VOLTAGES[1],
        },
        check_already_exists=False,
    )
    if discharge_ocp is not None:
        parameters.update(
            {
                "Positive electrode OCP [V]": discharge_ocp,
                "Positive electrode lithiation OCP [V]": discharge_ocp,
            }
        )
    return parameters


def last_value(solution, name):
    return float(np.asarray(solution[name].entries).reshape(-1)[-1])


def stoichiometry_state(solution, parameters):
    cn = last_value(solution, "X-averaged negative particle concentration [mol.m-3]")
    cp = last_value(solution, "X-averaged positive particle concentration [mol.m-3]")
    return {
        "xn": cn / float(parameters["Maximum concentration in negative electrode [mol.m-3]"]),
        "xp": cp / float(parameters["Maximum concentration in positive electrode [mol.m-3]"]),
        "terminal_voltage_v": last_value(solution, "Terminal voltage [V]"),
        "model_ocv_v": last_value(solution, "Battery open-circuit voltage [V]"),
    }


def run_endpoint_protocol(temperature_c, discharge_ocp=None):
    temperature_k = temperature_c + 273.15
    parameters = fresh_parameters(temperature_k, discharge_ocp)
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
            f"Discharge at {POWER_W:g} W until 2.50 V",
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
    if len(steps) != 4:
        raise RuntimeError(f"Expected four protocol steps, got {len(steps)}")
    charge_step, rest_100, discharge_step, rest_0 = steps
    charge_t = np.asarray(charge_step["Time [s]"].entries).reshape(-1)
    charge_i = np.asarray(charge_step["Current [A]"].entries).reshape(-1)
    discharge_t = np.asarray(discharge_step["Time [s]"].entries).reshape(-1)
    discharge_i = np.asarray(discharge_step["Current [A]"].entries).reshape(-1)
    state_100 = stoichiometry_state(rest_100, parameters)
    state_0 = stoichiometry_state(rest_0, parameters)
    endpoint_row = {
        "temperature_c": temperature_c,
        "xn_0": state_0["xn"],
        "xp_0": state_0["xp"],
        "ocv_0_v": state_0["model_ocv_v"],
        "rested_terminal_0_v": state_0["terminal_voltage_v"],
        "xn_100": state_100["xn"],
        "xp_100": state_100["xp"],
        "ocv_100_v": state_100["model_ocv_v"],
        "rested_terminal_100_v": state_100["terminal_voltage_v"],
        "charge_capacity_ah": float(np.trapz(-charge_i, charge_t) / 3600),
        "discharge_capacity_ah": float(np.trapz(discharge_i, discharge_t) / 3600),
        "charge_duration_h": float((charge_t[-1] - charge_t[0]) / 3600),
        "discharge_duration_h": float((discharge_t[-1] - discharge_t[0]) / 3600),
    }
    timeseries = pd.DataFrame(
        {
            "temperature_c": temperature_c,
            "time_h": np.asarray(solution["Time [s]"].entries).reshape(-1) / 3600,
            "terminal_voltage_v": np.asarray(solution["Terminal voltage [V]"].entries).reshape(-1),
        }
    )
    return parameters, endpoint_row, timeseries


def discharge_ocv(parameters, endpoints, soc, temperature_k):
    xn = endpoints["xn_0"] + soc * (endpoints["xn_100"] - endpoints["xn_0"])
    xp = endpoints["xp_0"] + soc * (endpoints["xp_100"] - endpoints["xp_0"])
    reference_k = float(parameters["Reference temperature [K]"])
    up = scalar_parameter(parameters, "Positive electrode lithiation OCP [V]", xp)
    un = scalar_parameter(parameters, "Negative electrode delithiation OCP [V]", xn)
    dup_dt = scalar_parameter(parameters, "Positive electrode OCP entropic change [V.K-1]", xp)
    dun_dt = scalar_parameter(parameters, "Negative electrode OCP entropic change [V.K-1]", xn)
    return up - un + (temperature_k - reference_k) * (dup_dt - dun_dt), xn, xp


def build_discharge_ocp(temperature_c, endpoints, target_ocv):
    """Assign the full-cell OCV residual to the positive discharge OCP."""
    temperature_k = temperature_c + 273.15
    base_parameters = fresh_parameters(temperature_k)
    base_positive_ocp = base_parameters["Positive electrode lithiation OCP [V]"]
    dense_soc = np.linspace(0, 1, 1001)
    positive_sto = []
    corrections = []
    for soc in dense_soc:
        base_ocv, _, xp = discharge_ocv(base_parameters, endpoints, soc, temperature_k)
        positive_sto.append(xp)
        corrections.append(float(target_ocv(soc)) - base_ocv)
    order = np.argsort(positive_sto)
    sto_knots = np.asarray(positive_sto)[order]
    correction_v = np.asarray(corrections)[order]
    sto_knots = np.concatenate(([0.0], sto_knots, [1.0]))
    correction_v = np.concatenate(([correction_v[0]], correction_v, [correction_v[-1]]))

    def calibrated_discharge_ocp(sto):
        correction = pybamm.Interpolant(
            sto_knots,
            correction_v,
            sto,
            name=f"CW363 {temperature_c:.0f}C discharge OCP correction",
            interpolator="linear",
        )
        return base_positive_ocp(sto) + correction

    return calibrated_discharge_ocp


def endpoint_delta(old, new):
    keys = ("xn_0", "xp_0", "xn_100", "xp_100")
    return max(abs(float(old[key]) - float(new[key])) for key in keys)


def calibrate_protocol_endpoints(temperature_c, target_builder, max_iterations=12, tolerance=1e-4):
    """Iterate cutoff-defined endpoints and discharge OCP until self-consistent."""
    _, endpoints, _ = run_endpoint_protocol(temperature_c)
    history = []
    calibrated_ocp = None
    parameters = None
    timeseries = None
    target_ocv = None
    for iteration in range(1, max_iterations + 1):
        target_ocv = target_builder(endpoints)
        calibrated_ocp = build_discharge_ocp(temperature_c, endpoints, target_ocv)
        parameters, new_endpoints, timeseries = run_endpoint_protocol(temperature_c, calibrated_ocp)
        delta = endpoint_delta(endpoints, new_endpoints)
        history.append({"iteration": iteration, "endpoint_max_abs_delta": delta})
        endpoints = new_endpoints
        if delta < tolerance:
            break
    return parameters, endpoints, timeseries, calibrated_ocp, target_ocv, history


def make_curves(parameters_by_temp, endpoints_by_temp, targets_by_temp, measured):
    dense_soc = np.linspace(0, 1, 1001)
    one_pct_soc = np.linspace(0, 1, 101)
    rows = []
    ocp_rows = []
    measured_keys = set(zip(measured["temperature_c"], measured["soc_pct"]))
    for temperature_c in (25.0, 45.0):
        temperature_k = temperature_c + 273.15
        parameters = parameters_by_temp[temperature_c]
        endpoints = endpoints_by_temp[temperature_c]
        base_parameters = fresh_parameters(temperature_k)
        target_ocv = targets_by_temp[temperature_c]
        for soc in one_pct_soc:
            calibrated, xn, xp = discharge_ocv(parameters, endpoints, soc, temperature_k)
            baseline, _, _ = discharge_ocv(base_parameters, endpoints, soc, temperature_k)
            soc_pct = int(round(soc * 100))
            if (temperature_c, soc_pct) in measured_keys:
                status = "measured_anchor"
            elif temperature_c == 45.0 and soc_pct < 90:
                status = "25C_shape_plus_entropy_extrapolation"
            else:
                status = f"{int(temperature_c)}C_interpolation"
            rows.append(
                {
                    "temperature_c": temperature_c,
                    "soc_pct": soc_pct,
                    "xn": xn,
                    "xp": xp,
                    "baseline_discharge_ocv_v": baseline,
                    "temperature_specific_ocv_v": calibrated,
                    "target_ocv_v": float(target_ocv(soc)),
                    "ocv_correction_mv": (calibrated - baseline) * 1000,
                    "calibration_status": status,
                }
            )
        for soc in dense_soc:
            _, _, xp = discharge_ocv(parameters, endpoints, soc, temperature_k)
            ocp_rows.append(
                {
                    "temperature_c": temperature_c,
                    "soc_pct": soc * 100,
                    "positive_stoichiometry": xp,
                    "calibrated_discharge_ocp_v": scalar_parameter(
                        parameters, "Positive electrode lithiation OCP [V]", xp
                    ),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(ocp_rows)


def plot_results(curves, measured, endpoints, output_path):
    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig = plt.figure(figsize=(13.2, 5.4))
    grid = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.15])
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    colors = {25.0: "#005BAC", 45.0: "#D1495B"}
    for ax, limits, title in zip(axes, ((0, 15), (85, 100)), ("Low SOC", "High SOC")):
        for temperature_c in (25.0, 45.0):
            subset = curves[
                (curves["temperature_c"] == temperature_c)
                & curves["soc_pct"].between(*limits)
            ]
            points = measured[
                (measured["temperature_c"] == temperature_c)
                & measured["soc_pct"].between(*limits)
            ]
            suffix = " (extrap. below 90%)" if temperature_c == 45.0 and limits[0] == 0 else ""
            ax.plot(
                subset["soc_pct"],
                subset["temperature_specific_ocv_v"],
                color=colors[temperature_c],
                label=f"{temperature_c:.0f}°C Sim{suffix}",
            )
            ax.scatter(
                points["soc_pct"],
                points["ocv_v"],
                edgecolor=colors[temperature_c],
                facecolor="white",
                marker="o",
                zorder=3,
                label=f"{temperature_c:.0f}°C Exp",
            )
        ax.set(xlim=limits, xlabel="SOC (%)", ylabel="OCV (V)", title=title)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

    table_ax = fig.add_subplot(grid[0, 2])
    table_ax.axis("off")
    table_data = []
    for temperature_c in (25.0, 45.0):
        row = endpoints[endpoints["temperature_c"] == temperature_c].iloc[0]
        table_data.append(
            [
                f"{temperature_c:.0f}°C",
                f"{row['xn_0']:.5f}",
                f"{row['xp_0']:.5f}",
                f"{row['xn_100']:.5f}",
                f"{row['xp_100']:.5f}",
            ]
        )
    table = table_ax.table(
        cellText=table_data,
        colLabels=["T", "xn@0%", "xp@0%", "xn@100%", "xp@100%"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.05, 1.7)
    table_ax.set_title("Protocol-defined stoichiometry\n940 W cutoff + 2 h rest", pad=16)
    fig.suptitle("CW363 Temperature-specific Discharge-static SOC-OCV", y=1.01)
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main():
    config_path = next(TASK_ROOT.rglob("config.yaml"))
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    measured = pd.DataFrame(config["measured_discharge_static_ocv"])
    run_dir = RUNS_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S_temperature_specific")
    run_dir.mkdir(parents=True, exist_ok=False)

    measured_25 = measured[measured["temperature_c"] == 25].sort_values("soc_pct")
    target_25 = PchipInterpolator(
        measured_25["soc_pct"].to_numpy(dtype=float) / 100,
        measured_25["ocv_v"].to_numpy(dtype=float),
    )

    def target_builder_25(_endpoints):
        return target_25

    params_25, endpoint_25, timeseries_25, _, final_target_25, history_25 = (
        calibrate_protocol_endpoints(25.0, target_builder_25)
    )
    base_25 = fresh_parameters(298.15)
    measured_45 = measured[measured["temperature_c"] == 45].sort_values("soc_pct")
    measured_45_soc = measured_45["soc_pct"].to_numpy(dtype=float) / 100
    measured_45_ocv = measured_45["ocv_v"].to_numpy(dtype=float)

    def target_builder_45(endpoint_45):
        base_45 = fresh_parameters(318.15)
        inherited_soc = np.linspace(0, 0.85, 851)
        inherited_values = []
        for soc in inherited_soc:
            ocv_25, _, _ = discharge_ocv(base_25, endpoint_25, soc, 298.15)
            ocv_45, _, _ = discharge_ocv(base_45, endpoint_45, soc, 318.15)
            inherited_values.append(float(target_25(soc)) + ocv_45 - ocv_25)
        inherited = PchipInterpolator(inherited_soc, inherited_values)
        high_target = PchipInterpolator(
            np.array([0.85, *measured_45_soc]),
            np.array([float(inherited(0.85)), *measured_45_ocv]),
        )

        def target(soc):
            return float(inherited(soc) if soc <= 0.85 else high_target(soc))

        return target

    params_45, endpoint_45, timeseries_45, _, final_target_45, history_45 = (
        calibrate_protocol_endpoints(45.0, target_builder_45)
    )
    parameters_by_temp = {25.0: params_25, 45.0: params_45}
    endpoints_by_temp = {25.0: endpoint_25, 45.0: endpoint_45}
    targets_by_temp = {25.0: final_target_25, 45.0: final_target_45}
    endpoints = pd.DataFrame([endpoint_25, endpoint_45])
    curves, ocp_tables = make_curves(
        parameters_by_temp, endpoints_by_temp, targets_by_temp, measured
    )
    comparison = measured.merge(curves, on=["temperature_c", "soc_pct"], how="left")
    comparison["error_mv"] = (
        comparison["temperature_specific_ocv_v"] - comparison["ocv_v"]
    ) * 1000

    curves.to_csv(run_dir / "temperature_specific_soc_ocv.csv", index=False, encoding="utf-8-sig")
    endpoints.to_csv(run_dir / "protocol_endpoint_stoichiometry.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(run_dir / "measured_comparison.csv", index=False, encoding="utf-8-sig")
    pd.concat([timeseries_25, timeseries_45], ignore_index=True).to_csv(
        run_dir / "endpoint_protocol_timeseries.csv", index=False, encoding="utf-8-sig"
    )
    for temperature_c in (25.0, 45.0):
        table = ocp_tables[ocp_tables["temperature_c"] == temperature_c]
        table[["positive_stoichiometry", "calibrated_discharge_ocp_v"]].to_csv(
            run_dir / f"LFP_CW363_discharge_calibrated_{int(temperature_c)}C.csv",
            index=False,
            header=False,
            encoding="utf-8",
        )
    plot_results(curves, measured, endpoints, run_dir / "temperature_specific_ocv_comparison.png")

    metrics = {
        "protocol": "940 W charge to 3.65 V, rest 2 h, discharge to 2.50 V, rest 2 h",
        "temperature_parameter_isolation": True,
        "endpoint_convergence_tolerance": 1e-4,
        "45C_low_soc_status": "extrapolated from 25C calibrated shape plus entropy; no 45C low-SOC data",
        "max_abs_anchor_error_mv": float(comparison["error_mv"].abs().max()),
        "minimum_1pct_step_mv": {
            str(int(t)): float(
                curves[curves["temperature_c"] == t]["temperature_specific_ocv_v"].diff().dropna().min()
                * 1000
            )
            for t in (25.0, 45.0)
        },
        "endpoint_iteration_history": {"25C": history_25, "45C": history_45},
        "pybamm_version": pybamm.__version__,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(run_dir)
    print(endpoints.to_string(index=False))
    print(comparison[["temperature_c", "soc_pct", "ocv_v", "temperature_specific_ocv_v", "error_mv"]].to_string(index=False))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
