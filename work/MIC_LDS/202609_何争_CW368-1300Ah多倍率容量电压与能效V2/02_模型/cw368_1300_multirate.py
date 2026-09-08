"""CW368-1300Ah fixed-average-temperature voltage and efficiency sweep."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
TASK_ROOT = (
    PROJECT_ROOT
    / "work"
    / "MIC_LDS"
    / "202609_何争_CW368-1300Ah多倍率容量电压与能效V2"
)
MODEL_DIR = TASK_ROOT / "02_模型"
RUN_ID = "20260904_151641_CW368_1300Ah_temperature_map"
RUN_DIR = (
    PROJECT_ROOT
    / "BatteryProject"
    / "output"
    / "runs"
    / "cw368_1300_temperature_map"
    / RUN_ID
)

if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from paramsLDSCW368 import (  # noqa: E402
    DESIGN_ELECTRODE_WIDTH_M,
    EFFECTIVE_AREA_FACTOR,
    NEGATIVE_OCP_STO_WARP_DELTA,
    NEGATIVE_OCP_VOLTAGE_OFFSET_V,
    RATED_CAPACITY_AH,
    SINGLE_ELECTRODE_HEIGHT_M,
    get_hithium_params,
)


NOMINAL_VOLTAGE_V = 3.2
P_RATES = (0.125, 0.167, 0.25, 0.33, 0.5)
AVERAGE_TEMPERATURE_C = {
    0.125: 25.0,
    0.167: 26.0,
    0.25: 32.0,
    0.33: 34.0,
    0.5: 38.0,
}
INITIAL_SOC = {"充电": 0.008, "放电": 0.995}
VOLTAGE_LIMITS = {"充电": 3.65, "放电": 2.5}
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
OUTPUT_PERIOD_S = 30


def build_model() -> pybamm.BaseModel:
    """Build the isothermal DFN used by every rate and direction."""
    return pybamm.lithium_ion.DFN(
        {
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def fresh_parameter_values(temperature_c: float) -> pybamm.ParameterValues:
    """Create a fresh parameter object at the rate-specific mean temperature."""
    temperature_k = float(temperature_c) + 273.15
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(
            t_factor=1,
            temperature=temperature_k,
            effective_area_factor=EFFECTIVE_AREA_FACTOR,
        ),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Ambient temperature [K]": temperature_k,
            "Initial temperature [K]": temperature_k,
        },
        check_already_exists=False,
    )
    return parameters


def run_case(p_rate: float, direction: str) -> tuple[pd.DataFrame, dict]:
    """Run one constant-power case and return its curve and summary."""
    power_w = RATED_CAPACITY_AH * NOMINAL_VOLTAGE_V * p_rate
    temperature_c = AVERAGE_TEMPERATURE_C[p_rate]
    action = "Charge" if direction == "充电" else "Discharge"
    experiment = pybamm.Experiment(
        [f"{action} at {power_w:.9g} W until {VOLTAGE_LIMITS[direction]} V"],
        period=f"{OUTPUT_PERIOD_S} seconds",
    )
    simulation = pybamm.Simulation(
        build_model(),
        parameter_values=fresh_parameter_values(temperature_c),
        experiment=experiment,
        solver=pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-8),
        var_pts=VAR_PTS,
    )
    solution = simulation.solve(initial_soc=INITIAL_SOC[direction])
    time_s = np.asarray(solution["Time [s]"].entries, dtype=float)
    voltage_v = np.asarray(solution["Terminal voltage [V]"].entries, dtype=float)
    current_a = np.asarray(solution["Current [A]"].entries, dtype=float)
    capacity_ah = np.asarray(
        solution["Discharge capacity [A.h]"].entries,
        dtype=float,
    )
    capacity_ah = np.abs(capacity_ah - capacity_ah[0])
    actual_power_w = np.abs(voltage_v * current_a)
    energy_wh = np.concatenate(
        ([0.0], np.cumsum((actual_power_w[1:] + actual_power_w[:-1]) / 2 * np.diff(time_s) / 3600))
    )
    curve = pd.DataFrame(
        {
            "temperature_c": temperature_c,
            "p_rate": p_rate,
            "direction": direction,
            "time_s": time_s,
            "capacity_ah": capacity_ah,
            "voltage_v": voltage_v,
            "current_a": current_a,
            "power_w": actual_power_w,
            "energy_wh": energy_wh,
        }
    )
    end_capacity_ah = float(capacity_ah[-1])
    end_energy_wh = float(energy_wh[-1])
    summary = {
        "temperature_c": temperature_c,
        "p_rate": p_rate,
        "direction": direction,
        "target_power_w": power_w,
        "duration_h": float(time_s[-1] / 3600),
        "end_capacity_ah": end_capacity_ah,
        "end_energy_wh": end_energy_wh,
        "mean_voltage_v": end_energy_wh / end_capacity_ah,
        "initial_voltage_v": float(voltage_v[0]),
        "end_voltage_v": float(voltage_v[-1]),
        "max_current_a": float(np.max(np.abs(current_a))),
    }
    return curve, summary


def build_efficiency_summary(case_summary: pd.DataFrame) -> pd.DataFrame:
    """Calculate round-trip energy and capacity efficiency by P-rate."""
    rows = []
    for p_rate in P_RATES:
        charge = case_summary[
            (case_summary["p_rate"] == p_rate) & (case_summary["direction"] == "充电")
        ].iloc[0]
        discharge = case_summary[
            (case_summary["p_rate"] == p_rate) & (case_summary["direction"] == "放电")
        ].iloc[0]
        rows.append(
            {
                "temperature_c": AVERAGE_TEMPERATURE_C[p_rate],
                "p_rate": p_rate,
                "power_w": float(charge["target_power_w"]),
                "charge_capacity_ah": float(charge["end_capacity_ah"]),
                "discharge_capacity_ah": float(discharge["end_capacity_ah"]),
                "capacity_efficiency_pct": float(
                    discharge["end_capacity_ah"] / charge["end_capacity_ah"] * 100
                ),
                "charge_energy_wh": float(charge["end_energy_wh"]),
                "discharge_energy_wh": float(discharge["end_energy_wh"]),
                "energy_efficiency_pct": float(
                    discharge["end_energy_wh"] / charge["end_energy_wh"] * 100
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_voltage_curves(curves: pd.DataFrame, direction: str, path: Path) -> None:
    """Save one capacity-voltage figure for one direction."""
    colors = ["#1f77b4", "#2a9d8f", "#f4a261", "#e76f51", "#7b2cbf"]
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for color, p_rate in zip(colors, P_RATES):
        curve = curves[(curves["p_rate"] == p_rate) & (curves["direction"] == direction)]
        ax.plot(
            curve["capacity_ah"],
            curve["voltage_v"],
            lw=2,
            color=color,
            label=(
                f"{p_rate:g}P, {AVERAGE_TEMPERATURE_C[p_rate]:g}°C "
                f"({RATED_CAPACITY_AH * NOMINAL_VOLTAGE_V * p_rate:.2f} W)"
            ),
        )
    english = "Charge" if direction == "充电" else "Discharge"
    ax.set_title(f"CW368-1300Ah Temperature-Corrected Constant-Power {english}")
    ax.set_xlabel("Capacity [Ah]")
    ax.set_ylabel("Voltage [V]")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_efficiency(efficiency: pd.DataFrame, path: Path) -> None:
    """Save round-trip energy efficiency versus P-rate."""
    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    ax.plot(
        efficiency["p_rate"],
        efficiency["energy_efficiency_pct"],
        marker="o",
        lw=2,
        color="#1f4e78",
    )
    for row in efficiency.itertuples(index=False):
        ax.annotate(
            f"{row.energy_efficiency_pct:.2f}%",
            (row.p_rate, row.energy_efficiency_pct),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
        )
    ax.set_title("CW368-1300Ah Temperature-Corrected Energy Efficiency")
    ax.set_xlabel("P-rate")
    ax.set_ylabel("Energy efficiency [%]")
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def run_sweep() -> dict[str, pd.DataFrame]:
    """Run all ten cases and save machine-readable results and figures."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    plot_dir = RUN_DIR / "plots"
    plot_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(RUN_DIR / "run.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    curve_frames = []
    summary_rows = []
    cases = [(rate, direction) for rate in P_RATES for direction in ("充电", "放电")]
    for index, (p_rate, direction) in enumerate(cases, start=1):
        logging.info(
            "[%d/%d] %.3gP %s %.1f°C %.3f W",
            index,
            len(cases),
            p_rate,
            direction,
            AVERAGE_TEMPERATURE_C[p_rate],
            RATED_CAPACITY_AH * NOMINAL_VOLTAGE_V * p_rate,
        )
        curve, summary = run_case(p_rate, direction)
        curve_frames.append(curve)
        summary_rows.append(summary)
    curves = pd.concat(curve_frames, ignore_index=True)
    case_summary = pd.DataFrame(summary_rows)
    efficiency = build_efficiency_summary(case_summary)
    curves.to_csv(RUN_DIR / "curves.csv", index=False, encoding="utf-8-sig")
    case_summary.to_csv(RUN_DIR / "case_summary.csv", index=False, encoding="utf-8-sig")
    efficiency.to_csv(RUN_DIR / "efficiency_summary.csv", index=False, encoding="utf-8-sig")
    config = {
        "cell": "CW368-1300Ah",
        "temperature_mode": "fixed average temperature by P-rate",
        "average_temperature_c": {str(k): v for k, v in AVERAGE_TEMPERATURE_C.items()},
        "rated_capacity_ah": RATED_CAPACITY_AH,
        "nominal_voltage_v": NOMINAL_VOLTAGE_V,
        "single_electrode_height_m": SINGLE_ELECTRODE_HEIGHT_M,
        "design_electrode_width_m": DESIGN_ELECTRODE_WIDTH_M,
        "effective_area_factor": EFFECTIVE_AREA_FACTOR,
        "negative_ocp_warp_delta": NEGATIVE_OCP_STO_WARP_DELTA,
        "negative_ocp_voltage_offset_v": NEGATIVE_OCP_VOLTAGE_OFFSET_V,
        "p_rates": list(P_RATES),
        "power_targets_w": {
            str(rate): RATED_CAPACITY_AH * NOMINAL_VOLTAGE_V * rate for rate in P_RATES
        },
        "initial_soc": INITIAL_SOC,
        "voltage_limits_v": VOLTAGE_LIMITS,
        "period_s": OUTPUT_PERIOD_S,
        "var_pts": VAR_PTS,
        "pybamm_version": pybamm.__version__,
    }
    (RUN_DIR / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_voltage_curves(curves, "充电", plot_dir / "CW368-1300Ah_temperature_corrected_charge.png")
    plot_voltage_curves(curves, "放电", plot_dir / "CW368-1300Ah_temperature_corrected_discharge.png")
    plot_efficiency(efficiency, plot_dir / "CW368-1300Ah_temperature_corrected_efficiency.png")
    logging.info("Completed. Run directory: %s", RUN_DIR)
    return {"curves": curves, "case_summary": case_summary, "efficiency": efficiency}


if __name__ == "__main__":
    results = run_sweep()
    print(results["efficiency"].to_string(index=False))
