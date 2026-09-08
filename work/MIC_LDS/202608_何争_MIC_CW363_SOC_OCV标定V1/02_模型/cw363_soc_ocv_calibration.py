"""Calibrate CW363 discharge-static SOC-OCV against sparse measured points."""

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
CONFIG_PATH = TASK_ROOT / "03_输入数据" / "config.yaml"
RUNS_ROOT = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw363_soc_ocv"
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}

if str(PARAMS_ROOT) not in sys.path:
    sys.path.insert(0, str(PARAMS_ROOT))

from common import build_ocp_function  # noqa: E402
from params1300CW363 import get_hithium_params  # noqa: E402


BASE_LFP_DISCHARGE_OCP = build_ocp_function("LFP.csv", name="Pos_OCP_base", offset=-0.02)


def evaluate_parameter_function(parameter_values, key, sto):
    """Evaluate a scalar OCP or entropic-change parameter function."""
    value = parameter_values[key]
    symbol = value(pybamm.Scalar(float(sto))) if callable(value) else pybamm.Scalar(value)
    return float(np.asarray(parameter_values.process_symbol(symbol).evaluate()).reshape(-1)[0])


def fresh_parameters(temperature_k, endpoint_ocv, correction=None):
    """Return an uncontaminated CW363 parameter set for one temperature."""
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(temperature=temperature_k),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Initial temperature [K]": temperature_k,
            "Open-circuit voltage at 0% SOC [V]": endpoint_ocv[0],
            "Open-circuit voltage at 100% SOC [V]": endpoint_ocv[1],
            "Positive electrode OCP [V]": BASE_LFP_DISCHARGE_OCP,
            "Positive electrode lithiation OCP [V]": BASE_LFP_DISCHARGE_OCP,
        },
        check_already_exists=False,
    )
    if correction is not None:
        sto_knots, correction_v = correction
        base_discharge_ocp = parameters["Positive electrode OCP [V]"]

        def calibrated_lfp_discharge_ocp(sto):
            delta = pybamm.Interpolant(
                sto_knots,
                correction_v,
                sto,
                name="CW363 discharge OCP correction",
                interpolator="linear",
            )
            return base_discharge_ocp(sto) + delta

        parameters.update(
            {
                "Positive electrode OCP [V]": calibrated_lfp_discharge_ocp,
                "Positive electrode lithiation OCP [V]": calibrated_lfp_discharge_ocp,
            }
        )
    return parameters


def endpoint_stoichiometries(parameters):
    """Return negative/positive stoichiometries at calibrated 0% and 100% SOC."""
    xn0, xp0 = pybamm.lithium_ion.get_initial_stoichiometries(0, parameters)
    xn100, xp100 = pybamm.lithium_ion.get_initial_stoichiometries(1, parameters)
    return float(xn0), float(xp0), float(xn100), float(xp100)


def ocv_at_soc(parameters, endpoints, soc_fraction, temperature_k):
    """Evaluate discharge equilibrium full-cell OCV at one normalized SOC."""
    xn0, xp0, xn100, xp100 = endpoints
    xn = xn0 + soc_fraction * (xn100 - xn0)
    xp = xp0 + soc_fraction * (xp100 - xp0)
    reference_k = float(parameters["Reference temperature [K]"])
    up = evaluate_parameter_function(parameters, "Positive electrode OCP [V]", xp)
    un = evaluate_parameter_function(parameters, "Negative electrode OCP [V]", xn)
    dup_dt = evaluate_parameter_function(parameters, "Positive electrode OCP entropic change [V.K-1]", xp)
    dun_dt = evaluate_parameter_function(parameters, "Negative electrode OCP entropic change [V.K-1]", xn)
    return up - un + (temperature_k - reference_k) * (dup_dt - dun_dt)


def main():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    measured = pd.DataFrame(config["measured_discharge_static_ocv"])
    measured_25 = measured[measured["temperature_c"] == 25.0].sort_values("soc_pct")
    endpoint_ocv = {
        0: float(measured_25.loc[measured_25["soc_pct"] == 0, "ocv_v"].iloc[0]),
        1: float(measured_25.loc[measured_25["soc_pct"] == 100, "ocv_v"].iloc[0]),
    }

    baseline_25 = fresh_parameters(298.15, endpoint_ocv)
    baseline_endpoints = endpoint_stoichiometries(baseline_25)
    measured_soc = measured_25["soc_pct"].to_numpy(dtype=float) / 100
    measured_ocv = measured_25["ocv_v"].to_numpy(dtype=float)
    target_ocv = PchipInterpolator(measured_soc, measured_ocv)
    dense_soc = np.linspace(0, 1, 1001)
    baseline_dense_ocv = np.asarray(
        [ocv_at_soc(baseline_25, baseline_endpoints, soc, 298.15) for soc in dense_soc]
    )
    correction_dense = target_ocv(dense_soc) - baseline_dense_ocv
    positive_sto_dense = baseline_endpoints[1] + dense_soc * (
        baseline_endpoints[3] - baseline_endpoints[1]
    )
    order = np.argsort(positive_sto_dense)
    correction = (
        np.concatenate(([0.0], positive_sto_dense[order], [1.0])),
        np.concatenate(([0.0], correction_dense[order], [0.0])),
    )
    calibrated_25 = fresh_parameters(298.15, endpoint_ocv, correction)
    calibrated_endpoints = endpoint_stoichiometries(calibrated_25)

    rows = []
    for temperature_c in (25.0, 45.0):
        temperature_k = temperature_c + 273.15
        baseline = fresh_parameters(temperature_k, endpoint_ocv)
        calibrated = fresh_parameters(temperature_k, endpoint_ocv, correction)
        for soc_pct in range(101):
            soc_fraction = soc_pct / 100
            rows.append(
                {
                    "temperature_c": temperature_c,
                    "soc_pct": soc_pct,
                    "baseline_ocv_v": ocv_at_soc(baseline, baseline_endpoints, soc_fraction, temperature_k),
                    "calibrated_ocv_v": ocv_at_soc(calibrated, calibrated_endpoints, soc_fraction, temperature_k),
                }
            )
    curves = pd.DataFrame(rows)
    comparison = measured.merge(curves, on=["temperature_c", "soc_pct"], how="left")
    comparison["baseline_error_mv"] = (comparison["baseline_ocv_v"] - comparison["ocv_v"]) * 1000
    comparison["calibrated_error_mv"] = (comparison["calibrated_ocv_v"] - comparison["ocv_v"]) * 1000

    calibrated_curve_25 = curves[curves["temperature_c"] == 25.0].sort_values("soc_pct")
    voltage_steps = np.diff(calibrated_curve_25["calibrated_ocv_v"].to_numpy())
    errors_25 = comparison[comparison["temperature_c"] == 25.0]["calibrated_error_mv"].to_numpy()
    metrics = {
        "endpoint_stoichiometries": {
            "xn_0": calibrated_endpoints[0],
            "xp_0": calibrated_endpoints[1],
            "xn_100": calibrated_endpoints[2],
            "xp_100": calibrated_endpoints[3],
        },
        "measured_soc_pct": measured_25["soc_pct"].tolist(),
        "measured_ocv_25c_v": measured_25["ocv_v"].tolist(),
        "rmse_25c_mv": float(np.sqrt(np.mean(errors_25**2))),
        "max_abs_error_25c_mv": float(np.max(np.abs(errors_25))),
        "minimum_1pct_voltage_step_mv": float(np.min(voltage_steps) * 1000),
        "monotonic_non_decreasing": bool(np.all(voltage_steps >= -1e-9)),
        "temperature_calibration_note": "45C 100% excluded from formal entropy calibration; protocol-state effect unresolved.",
    }

    run_dir = RUNS_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S_calibrated_v1")
    run_dir.mkdir(parents=True, exist_ok=False)
    curves.to_csv(run_dir / "soc_ocv_curves.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(run_dir / "measured_comparison.csv", index=False, encoding="utf-8-sig")
    calibrated_ocp = []
    for sto, delta in zip(correction[0], correction[1]):
        calibrated_ocp.append(
            {
                "positive_stoichiometry": sto,
                "calibrated_discharge_ocp_v": evaluate_parameter_function(
                    baseline_25, "Positive electrode OCP [V]", sto
                )
                + delta,
            }
        )
    pd.DataFrame(calibrated_ocp).to_csv(
        run_dir / "LFP_CW363_discharge_calibrated.csv",
        index=False,
        header=False,
        encoding="utf-8",
    )
    (run_dir / "calibration_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    for temperature_c, color in ((25.0, "#005BAC"), (45.0, "#D1495B")):
        subset = curves[curves["temperature_c"] == temperature_c]
        points = measured[measured["temperature_c"] == temperature_c]
        ax.plot(subset["soc_pct"], subset["calibrated_ocv_v"], color=color, label=f"{temperature_c:.0f}°C Sim")
        ax.scatter(points["soc_pct"], points["ocv_v"], color=color, marker="o", facecolors="none", label=f"{temperature_c:.0f}°C Exp")
    ax.set(xlabel="SOC (%)", ylabel="OCV (V)", title="CW363 Discharge Static SOC-OCV Calibration")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(run_dir / "soc_ocv_calibration.png", dpi=220)
    plt.close(fig)

    print(run_dir)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
