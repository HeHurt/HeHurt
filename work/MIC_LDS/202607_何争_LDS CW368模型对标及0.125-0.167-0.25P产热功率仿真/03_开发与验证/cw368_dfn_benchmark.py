"""CW368 constant-power DFN benchmark and heat-generation workflow."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm


PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
TASK_ROOT = (
    PROJECT_ROOT
    / "work"
    / "MIC_LDS"
    / "202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真"
)
PARAMS_ROOT = PROJECT_ROOT / "params"
MODEL_DIR = TASK_ROOT / "02_模型"
DEFAULT_OUTPUT_DIR = TASK_ROOT / "04_输出结果" / "CW368_DFN对标及产热"
EXPERIMENT_FILES = (
    TASK_ROOT / "CW368_00029_CH2_充放电曲线.csv",
    TASK_ROOT / "CW368_00030_CH1_充放电曲线.csv",
)

for path in [MODEL_DIR, PARAMS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from paramsLDSCW368 import (  # noqa: E402
    DESIGN_ELECTRODE_WIDTH_M,
    EFFECTIVE_AREA_FACTOR,
    NEGATIVE_OCP_STO_WARP_DELTA,
    NEGATIVE_OCP_STO_WARP_END,
    NEGATIVE_OCP_STO_WARP_SMOOTHING,
    NEGATIVE_OCP_STO_WARP_START,
    NEGATIVE_OCP_VOLTAGE_OFFSET_V,
    get_hithium_params,
)


TEMPERATURE_C = 25
RATES = (0.125, 0.167, 0.25)
MEASURED_RATES = (0.125, 0.25)
INITIAL_SOC = {"充电": 0.008, "放电": 0.995}
VOLTAGE_LIMITS = {"充电": 3.65, "放电": 2.5}
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
OUTPUT_PERIOD_S = 30
BENCHMARK_AREA_FACTOR = EFFECTIVE_AREA_FACTOR
HEAT_AREA_FACTOR = 1.0


def load_experiment_curves(
    files: tuple[Path, ...] = EXPERIMENT_FILES,
) -> dict[tuple[float, str], list[pd.DataFrame]]:
    """Load full measured charge/discharge curves grouped by rate and direction."""
    grouped: dict[tuple[float, str], list[pd.DataFrame]] = {}
    for file_path in files:
        sample = file_path.stem.replace("CW368_", "").replace("_充放电曲线", "")
        frame = pd.read_csv(file_path, encoding="utf-8-sig")
        frame["p_rate"] = (
            frame["倍率"].astype(str).str.replace("P", "", regex=False).astype(float)
        )
        for (p_rate, direction, cycle), raw in frame.groupby(
            ["p_rate", "方向", "循环序号"],
            sort=True,
        ):
            voltage_column = f"{direction}_电压(V)"
            current_column = f"{direction}_电流(A)"
            capacity_column = f"{direction}_容量(Ah)"
            energy_column = f"{direction}_能量(Wh)"
            power_column = f"{direction}_功率(W)"
            curve = raw.dropna(subset=[voltage_column, capacity_column]).copy()
            if curve.empty:
                continue
            curve = curve.rename(
                columns={
                    "相对时间(s)": "raw_time_s",
                    voltage_column: "voltage_v",
                    current_column: "current_a",
                    capacity_column: "capacity_ah",
                    energy_column: "energy_wh",
                    power_column: "power_w",
                }
            )
            curve["time_s"] = curve["raw_time_s"] - curve["raw_time_s"].iloc[0]
            curve["capacity_ah"] = np.abs(
                curve["capacity_ah"] - curve["capacity_ah"].iloc[0]
            )
            curve["energy_wh"] = np.abs(
                curve["energy_wh"] - curve["energy_wh"].iloc[0]
            )
            curve["power_w"] = np.abs(curve["power_w"])
            curve["sample"] = sample
            curve["cycle"] = int(cycle)
            curve["series"] = f"exp_{sample}_cycle{int(cycle)}"
            # Cycle 3 also contains a short 0.125P finishing segment. Only
            # full-window curves are valid for benchmarking.
            if curve["capacity_ah"].iloc[-1] < 0.5 * 1362.4:
                continue
            keep = [
                "time_s",
                "capacity_ah",
                "energy_wh",
                "voltage_v",
                "current_a",
                "power_w",
                "sample",
                "cycle",
                "series",
            ]
            grouped.setdefault((float(p_rate), direction), []).append(
                curve[keep].reset_index(drop=True)
            )
    return grouped


def measured_power_targets(
    grouped: dict[tuple[float, str], list[pd.DataFrame]],
) -> dict[float, float]:
    """Return measured power targets and interpolate the unmeasured 0.167P case."""
    targets = {}
    for p_rate in MEASURED_RATES:
        powers = []
        for direction in ("充电", "放电"):
            for curve in grouped[(p_rate, direction)]:
                powers.append(float(curve["power_w"].median()))
        targets[p_rate] = float(np.mean(powers))
    targets[0.167] = targets[0.125] * 0.167 / 0.125
    return targets


def build_model() -> pybamm.BaseModel:
    """Build an isothermal DFN with heat-source and contact-resistance options."""
    return pybamm.lithium_ion.DFN(
        {
            "thermal": "isothermal",
            "calculate heat source for isothermal models": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def fresh_parameter_values(
    temperature_c: float = TEMPERATURE_C,
    effective_area_factor: float = BENCHMARK_AREA_FACTOR,
):
    """Create fresh temperature-specific ParameterValues without contamination."""
    temperature_k = float(temperature_c) + 273.15
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(
            t_factor=1,
            temperature=temperature_k,
            effective_area_factor=effective_area_factor,
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


def run_case(
    p_rate: float,
    direction: str,
    power_w: float,
    period_s: int = OUTPUT_PERIOD_S,
    effective_area_factor: float = BENCHMARK_AREA_FACTOR,
    series: str = "dfn_sim",
    calculation_basis: str = "benchmark_calibrated_area",
) -> pd.DataFrame:
    """Run one full constant-power curve and return electrical/heat variables."""
    parameters = fresh_parameter_values(
        effective_area_factor=effective_area_factor,
    )
    action = "Charge" if direction == "充电" else "Discharge"
    experiment = pybamm.Experiment(
        [
            (
                f"{action} at {power_w:.9g} W "
                f"until {VOLTAGE_LIMITS[direction]} V"
            )
        ],
        period=f"{period_s} seconds",
    )
    simulation = pybamm.Simulation(
        build_model(),
        parameter_values=parameters,
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
    ohmic_heat_w = np.asarray(solution["Ohmic heating [W]"].entries, dtype=float)
    irreversible_heat_w = np.asarray(
        solution["Irreversible electrochemical heating [W]"].entries,
        dtype=float,
    )
    reversible_heat_w = np.asarray(
        solution["Reversible heating [W]"].entries,
        dtype=float,
    )
    hysteresis_heat_w = np.asarray(
        solution["Hysteresis electrochemical heating [W]"].entries,
        dtype=float,
    )
    electrochemical_total_heat_w = np.asarray(
        solution["Total heating [W]"].entries,
        dtype=float,
    )
    contact_heat_w = current_a**2 * float(
        parameters["Contact resistance [Ohm]"]
    )
    net_total_heat_w = electrochemical_total_heat_w + contact_heat_w
    gross_total_heat_w = (
        ohmic_heat_w
        + irreversible_heat_w
        + hysteresis_heat_w
        + np.maximum(reversible_heat_w, 0)
        + contact_heat_w
    )
    return pd.DataFrame(
        {
            "temperature_c": TEMPERATURE_C,
            "p_rate": p_rate,
            "direction": direction,
            "series": series,
            "calculation_basis": calculation_basis,
            "effective_area_factor": effective_area_factor,
            "time_s": time_s,
            "capacity_ah": capacity_ah,
            "voltage_v": voltage_v,
            "current_a": current_a,
            "power_w": np.abs(voltage_v * current_a),
            "ohmic_heat_w": ohmic_heat_w,
            "irreversible_heat_w": irreversible_heat_w,
            "reversible_heat_w": reversible_heat_w,
            "hysteresis_heat_w": hysteresis_heat_w,
            "contact_heat_w": contact_heat_w,
            "electrochemical_total_heat_w": electrochemical_total_heat_w,
            "net_total_heat_w": net_total_heat_w,
            "gross_total_heat_w": gross_total_heat_w,
        }
    )


def comparison_metrics(
    exp_curve: pd.DataFrame,
    sim_curve: pd.DataFrame,
) -> dict[str, float]:
    """Align voltage by capacity and calculate curve/capacity errors."""
    exp_capacity = exp_curve["capacity_ah"].to_numpy(dtype=float)
    exp_voltage = exp_curve["voltage_v"].to_numpy(dtype=float)
    sim_capacity = sim_curve["capacity_ah"].to_numpy(dtype=float)
    sim_voltage = sim_curve["voltage_v"].to_numpy(dtype=float)
    unique_capacity, unique_index = np.unique(sim_capacity, return_index=True)
    unique_voltage = sim_voltage[unique_index]
    overlap = (exp_capacity >= unique_capacity.min()) & (
        exp_capacity <= unique_capacity.max()
    )
    aligned_exp = exp_voltage[overlap]
    aligned_sim = np.interp(
        exp_capacity[overlap],
        unique_capacity,
        unique_voltage,
    )
    error = aligned_sim - aligned_exp
    rmse_v = float(np.sqrt(np.mean(error**2)))
    exp_end_capacity = float(exp_curve["capacity_ah"].iloc[-1])
    sim_end_capacity = float(sim_curve["capacity_ah"].iloc[-1])
    return {
        "n_overlap": int(overlap.sum()),
        "rmse_v": rmse_v,
        "rrmse_pct": float(
            rmse_v / np.mean(np.abs(aligned_exp)) * 100
        ),
        "mae_v": float(np.mean(np.abs(error))),
        "max_abs_error_v": float(np.max(np.abs(error))),
        "exp_end_capacity_ah": exp_end_capacity,
        "sim_end_capacity_ah": sim_end_capacity,
        "end_capacity_error_pct": float(
            (sim_end_capacity - exp_end_capacity) / exp_end_capacity * 100
        ),
    }


def _integral_wh(time_s: np.ndarray, power_w: np.ndarray) -> float:
    return float(np.trapz(power_w, time_s) / 3600)


def heat_summary(sim_curve: pd.DataFrame) -> dict[str, float | str]:
    """Summarize heat power components and integrated heat for one case."""
    time_s = sim_curve["time_s"].to_numpy(dtype=float)
    row: dict[str, float | str] = {
        "temperature_c": TEMPERATURE_C,
        "p_rate": float(sim_curve["p_rate"].iloc[0]),
        "direction": str(sim_curve["direction"].iloc[0]),
        "calculation_basis": str(sim_curve["calculation_basis"].iloc[0]),
        "effective_area_factor": float(
            sim_curve["effective_area_factor"].iloc[0]
        ),
        "end_capacity_ah": float(sim_curve["capacity_ah"].iloc[-1]),
        "duration_h": float(time_s[-1] / 3600),
    }
    heat_columns = [
        "ohmic_heat_w",
        "irreversible_heat_w",
        "reversible_heat_w",
        "hysteresis_heat_w",
        "contact_heat_w",
        "net_total_heat_w",
        "gross_total_heat_w",
    ]
    for column in heat_columns:
        values = sim_curve[column].to_numpy(dtype=float)
        row[f"{column}_mean"] = float(np.mean(values))
        row[f"{column}_max"] = float(np.max(values))
        row[f"{column}_integral_wh"] = _integral_wh(time_s, values)
    return row


def efficiency_summary(
    grouped: dict[tuple[float, str], list[pd.DataFrame]],
    simulations: dict[tuple[float, str], pd.DataFrame],
) -> pd.DataFrame:
    """Return measured and simulated round-trip energy efficiency by rate."""
    rows = []
    for p_rate in RATES:
        charge = simulations[(p_rate, "充电")]
        discharge = simulations[(p_rate, "放电")]
        sim_charge_wh = _integral_wh(
            charge["time_s"].to_numpy(),
            charge["power_w"].to_numpy(),
        )
        sim_discharge_wh = _integral_wh(
            discharge["time_s"].to_numpy(),
            discharge["power_w"].to_numpy(),
        )
        exp_efficiency = np.nan
        if p_rate in MEASURED_RATES:
            charge_wh = [
                float(curve["energy_wh"].iloc[-1])
                for curve in grouped[(p_rate, "充电")]
            ]
            discharge_wh = [
                float(curve["energy_wh"].iloc[-1])
                for curve in grouped[(p_rate, "放电")]
            ]
            exp_efficiency = (
                float(np.mean(discharge_wh)) / float(np.mean(charge_wh)) * 100
            )
        sim_efficiency = sim_discharge_wh / sim_charge_wh * 100
        rows.append(
            {
                "p_rate": p_rate,
                "case_type": (
                    "measured_benchmark"
                    if p_rate in MEASURED_RATES
                    else "simulation_prediction_only"
                ),
                "exp_energy_efficiency_pct": exp_efficiency,
                "sim_energy_efficiency_pct": sim_efficiency,
                "efficiency_error_pct_point": (
                    sim_efficiency - exp_efficiency
                    if np.isfinite(exp_efficiency)
                    else np.nan
                ),
                "sim_charge_energy_wh": sim_charge_wh,
                "sim_discharge_energy_wh": sim_discharge_wh,
            }
        )
    return pd.DataFrame(rows)


def run_benchmark(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    period_s: int = OUTPUT_PERIOD_S,
) -> dict[str, pd.DataFrame]:
    """Run all measured benchmarks and the 0.167P prediction."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("cw368_benchmark")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in [
        logging.FileHandler(output_dir / "run.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    grouped = load_experiment_curves()
    powers = measured_power_targets(grouped)
    simulations: dict[tuple[float, str], pd.DataFrame] = {}
    metric_rows = []
    curve_frames = []
    heat_rows = []

    for index, (p_rate, direction) in enumerate(
        [(rate, direction) for rate in RATES for direction in ("充电", "放电")],
        start=1,
    ):
        logger.info(
            "[%d/6] %.3fP %s, %.3f W",
            index,
            p_rate,
            direction,
            powers[p_rate],
        )
        sim_curve = run_case(
            p_rate,
            direction,
            powers[p_rate],
            period_s,
            effective_area_factor=BENCHMARK_AREA_FACTOR,
            series="dfn_sim",
            calculation_basis="benchmark_calibrated_area",
        )
        simulations[(p_rate, direction)] = sim_curve
        curve_frames.append(sim_curve)
        heat_curve = run_case(
            p_rate,
            direction,
            powers[p_rate],
            period_s,
            effective_area_factor=HEAT_AREA_FACTOR,
            series="dfn_heat_design",
            calculation_basis="heat_design_area",
        )
        curve_frames.append(heat_curve)
        heat_rows.append(heat_summary(heat_curve))

        if p_rate not in MEASURED_RATES:
            metric_rows.append(
                {
                    "temperature_c": TEMPERATURE_C,
                    "p_rate": p_rate,
                    "direction": direction,
                    "series": "prediction_only",
                    "status": "prediction_only_no_experiment",
                }
            )
            continue
        for exp_curve in grouped[(p_rate, direction)]:
            metrics = comparison_metrics(exp_curve, sim_curve)
            metric_rows.append(
                {
                    "temperature_c": TEMPERATURE_C,
                    "p_rate": p_rate,
                    "direction": direction,
                    "series": exp_curve["series"].iloc[0],
                    "status": "ok",
                    **metrics,
                }
            )
            exp_output = exp_curve.copy()
            exp_output.insert(0, "temperature_c", TEMPERATURE_C)
            exp_output.insert(1, "p_rate", p_rate)
            exp_output.insert(2, "direction", direction)
            curve_frames.append(exp_output)

    metrics = pd.DataFrame(metric_rows)
    benchmark_metrics = metrics[metrics["status"] == "ok"]
    means = (
        benchmark_metrics.groupby(
            ["temperature_c", "p_rate", "direction"],
            as_index=False,
        )[
            [
                "n_overlap",
                "rmse_v",
                "rrmse_pct",
                "mae_v",
                "max_abs_error_v",
                "exp_end_capacity_ah",
                "sim_end_capacity_ah",
                "end_capacity_error_pct",
            ]
        ]
        .mean()
        .assign(series="mean", status="ok")
    )
    metrics = pd.concat([metrics, means], ignore_index=True, sort=False)
    curves = pd.concat(curve_frames, ignore_index=True, sort=False)
    heat = pd.DataFrame(heat_rows)
    efficiency = efficiency_summary(grouped, simulations)

    config = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "pybamm_version": pybamm.__version__,
        "temperature_c": TEMPERATURE_C,
        "rates": list(RATES),
        "measured_rates": list(MEASURED_RATES),
        "power_targets_w": powers,
        "initial_soc": INITIAL_SOC,
        "voltage_limits_v": VOLTAGE_LIMITS,
        "period_s": period_s,
        "contact_resistance_enabled": True,
        "contact_resistance_ohm": float(
            fresh_parameter_values(
                effective_area_factor=HEAT_AREA_FACTOR,
            )["Contact resistance [Ohm]"]
        ),
        "thermal_method": (
            "isothermal DFN heat sources plus explicit I^2R contact heat"
        ),
        "design_electrode_width_m": DESIGN_ELECTRODE_WIDTH_M,
        "benchmark_effective_area_factor": BENCHMARK_AREA_FACTOR,
        "heat_effective_area_factor": HEAT_AREA_FACTOR,
        "negative_ocp_calibration": {
            "method": "smooth localized stoichiometry warp",
            "warp_delta": NEGATIVE_OCP_STO_WARP_DELTA,
            "warp_start": NEGATIVE_OCP_STO_WARP_START,
            "warp_end": NEGATIVE_OCP_STO_WARP_END,
            "warp_smoothing": NEGATIVE_OCP_STO_WARP_SMOOTHING,
            "voltage_offset_v": NEGATIVE_OCP_VOLTAGE_OFFSET_V,
        },
        "var_pts": VAR_PTS,
    }
    (output_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    curves.to_csv(output_dir / "curves.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output_dir / "metrics.csv", index=False, encoding="utf-8-sig")
    heat.to_csv(output_dir / "heat_summary.csv", index=False, encoding="utf-8-sig")
    efficiency.to_csv(
        output_dir / "efficiency_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    logger.info("Completed all cases. Output: %s", output_dir)
    return {
        "curves": curves,
        "metrics": metrics,
        "heat_summary": heat,
        "efficiency_summary": efficiency,
    }


def load_results(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, pd.DataFrame]:
    """Load previously exported benchmark tables."""
    output_dir = Path(output_dir)
    return {
        "curves": pd.read_csv(output_dir / "curves.csv", encoding="utf-8-sig"),
        "metrics": pd.read_csv(output_dir / "metrics.csv", encoding="utf-8-sig"),
        "heat_summary": pd.read_csv(
            output_dir / "heat_summary.csv",
            encoding="utf-8-sig",
        ),
        "efficiency_summary": pd.read_csv(
            output_dir / "efficiency_summary.csv",
            encoding="utf-8-sig",
        ),
    }
