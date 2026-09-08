"""CW368-1300Ah 25°C EU-project-style 1C 30 s DCR at three SOCs."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


PROJECT_ROOT = Path(r"C:\HithiumSSD\hithium")
TASK_ROOT = PROJECT_ROOT / "work" / "MIC_LDS" / "202609_何争_CW368-1300Ah多倍率容量电压与能效V2"
MODEL_DIR = TASK_ROOT / "02_模型"
RUN_ID = "20260904_CW368_1300Ah_EU_DCR_25C"
RUN_DIR = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw368_1300_eu_dcr" / RUN_ID

if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from paramsLDSCW368 import (  # noqa: E402
    EFFECTIVE_AREA_FACTOR,
    RATED_CAPACITY_AH,
    SINGLE_ELECTRODE_HEIGHT_M,
    get_hithium_params,
)


TEMPERATURE_C = 25.0
SOC_POINTS = (0.20, 0.50, 0.80)
PULSE_C_RATE = 1.0
PULSE_CURRENT_A = RATED_CAPACITY_AH * PULSE_C_RATE
PULSE_DURATION_S = 30
REST_MINUTES = 10
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def build_model() -> pybamm.BaseModel:
    return pybamm.lithium_ion.DFN(
        {
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def fresh_parameters() -> pybamm.ParameterValues:
    temperature_k = TEMPERATURE_C + 273.15
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(1, temperature_k, effective_area_factor=EFFECTIVE_AREA_FACTOR),
        check_already_exists=False,
    )
    parameters.update(
        {"Ambient temperature [K]": temperature_k, "Initial temperature [K]": temperature_k},
        check_already_exists=False,
    )
    return parameters


def run_soc(soc: float) -> tuple[dict, pd.DataFrame]:
    experiment = pybamm.Experiment(
        [(
            f"Rest for {REST_MINUTES} minutes (1 second period)",
            f"Discharge at {PULSE_CURRENT_A:g} A for {PULSE_DURATION_S} seconds (0.5 second period)",
            f"Rest for {REST_MINUTES} minutes (1 second period)",
            f"Charge at {PULSE_CURRENT_A:g} A for {PULSE_DURATION_S} seconds (0.5 second period)",
            f"Rest for {REST_MINUTES} minutes (1 second period)",
        )]
    )
    simulation = pybamm.Simulation(
        build_model(),
        parameter_values=fresh_parameters(),
        experiment=experiment,
        solver=pybamm.IDAKLUSolver(rtol=1e-7, atol=1e-9),
        var_pts=VAR_PTS,
    )
    solution = simulation.solve(initial_soc=soc, calc_esoh=False)
    cycle = solution.cycles[0]
    rest_before_discharge = cycle.steps[0]
    discharge = cycle.steps[1]
    rest_before_charge = cycle.steps[2]
    charge = cycle.steps[3]

    v0_discharge = float(rest_before_discharge["Terminal voltage [V]"].entries[-1])
    v30_discharge = float(discharge["Terminal voltage [V]"].entries[-1])
    v0_charge = float(rest_before_charge["Terminal voltage [V]"].entries[-1])
    v30_charge = float(charge["Terminal voltage [V]"].entries[-1])
    dcr_discharge_ohm = (v0_discharge - v30_discharge) / PULSE_CURRENT_A
    dcr_charge_ohm = (v30_charge - v0_charge) / PULSE_CURRENT_A
    result = {
        "soc_pct": soc * 100,
        "temperature_c": TEMPERATURE_C,
        "pulse_current_a": PULSE_CURRENT_A,
        "pulse_duration_s": PULSE_DURATION_S,
        "rest_minutes": REST_MINUTES,
        "v0_discharge_v": v0_discharge,
        "v30_discharge_v": v30_discharge,
        "dcr_discharge_mohm": dcr_discharge_ohm * 1000,
        "v0_charge_v": v0_charge,
        "v30_charge_v": v30_charge,
        "dcr_charge_mohm": dcr_charge_ohm * 1000,
        "dcr_mean_mohm": (dcr_discharge_ohm + dcr_charge_ohm) * 500,
    }

    frames = []
    for direction, step, v0 in (
        ("discharge", discharge, v0_discharge),
        ("charge", charge, v0_charge),
    ):
        time_s = np.asarray(step["Time [s]"].entries, dtype=float)
        time_s -= time_s[0]
        voltage_v = np.asarray(step["Terminal voltage [V]"].entries, dtype=float)
        frames.append(
            pd.DataFrame(
                {
                    "soc_pct": soc * 100,
                    "direction": direction,
                    "pulse_time_s": time_s,
                    "voltage_v": voltage_v,
                    "delta_voltage_v": voltage_v - v0,
                }
            )
        )
    return result, pd.concat(frames, ignore_index=True)


def plot_results(summary: pd.DataFrame, curves: pd.DataFrame, plot_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5), constrained_layout=True)
    ax.plot(summary["soc_pct"], summary["dcr_discharge_mohm"], "o-", label="Discharge DCR")
    ax.plot(summary["soc_pct"], summary["dcr_charge_mohm"], "s-", label="Charge DCR")
    ax.plot(summary["soc_pct"], summary["dcr_mean_mohm"], "^-", label="Mean DCR")
    ax.set(title="CW368-1300Ah 25°C 1C-30s DCR", xlabel="SOC [%]", ylabel="DCR [mΩ]")
    ax.set_xticks([20, 50, 80])
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(plot_dir / "CW368-1300Ah_25C_1C30s_DCR.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True, sharey=True)
    for ax, direction, title in zip(axes, ("discharge", "charge"), ("Discharge pulse", "Charge pulse")):
        for soc in (20.0, 50.0, 80.0):
            data = curves[(curves["direction"] == direction) & (curves["soc_pct"] == soc)]
            ax.plot(data["pulse_time_s"], data["voltage_v"], lw=2, label=f"{soc:g}% SOC")
        ax.set(title=title, xlabel="Pulse time [s]")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Terminal voltage [V]")
    axes[1].legend()
    fig.suptitle("CW368-1300Ah 25°C 1C Pulse Voltage")
    fig.savefig(plot_dir / "CW368-1300Ah_25C_1C30s_pulse_voltage.png", dpi=220)
    plt.close(fig)


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    plot_dir = RUN_DIR / "plots"
    plot_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = []
    curve_frames = []
    for soc in SOC_POINTS:
        logging.info("Running %.0f%% SOC, 1C 30s charge/discharge pulse", soc * 100)
        result, curve = run_soc(soc)
        results.append(result)
        curve_frames.append(curve)
    summary = pd.DataFrame(results)
    curves = pd.concat(curve_frames, ignore_index=True)
    summary.to_csv(RUN_DIR / "dcr_summary.csv", index=False, encoding="utf-8-sig")
    curves.to_csv(RUN_DIR / "pulse_curves.csv", index=False, encoding="utf-8-sig")
    config = {
        "cell": "CW368-1300Ah",
        "rated_capacity_ah": RATED_CAPACITY_AH,
        "single_electrode_height_m": SINGLE_ELECTRODE_HEIGHT_M,
        "temperature_c": TEMPERATURE_C,
        "soc_pct": [20, 50, 80],
        "pulse_c_rate": PULSE_C_RATE,
        "pulse_current_a": PULSE_CURRENT_A,
        "pulse_duration_s": PULSE_DURATION_S,
        "rest_minutes": REST_MINUTES,
        "dcr_definition": "mean of charge and discharge 30 s pulse DCR",
        "project_protocol_note": "EU-battery-regulation project simulation convention",
        "pybamm_version": pybamm.__version__,
    }
    (RUN_DIR / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    plot_results(summary, curves, plot_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
