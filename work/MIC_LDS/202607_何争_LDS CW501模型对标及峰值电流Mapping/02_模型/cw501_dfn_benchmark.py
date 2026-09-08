"""CW501 constant-power charge/discharge DFN benchmark.

Reads the supplied two-cell experimental workbook, runs the matching power and
temperature cases with contact resistance enabled, and writes reproducible
curve/metric tables plus one comparison figure per temperature.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pybamm

if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"


PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
PARAMS_ROOT = PROJECT_ROOT / "params"
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "work"
    / "MIC_LDS"
    / "202607_何争_LDS CW501模型对标及峰值电流Mapping"
    / "1300-25℃&45℃&5℃不同倍率下充放电数据-to何争.xlsx"
)
DEFAULT_RUN_ROOT = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw501_benchmark"

if str(PARAMS_ROOT) not in sys.path:
    sys.path.insert(0, str(PARAMS_ROOT))

from paramsLDSCW501 import get_hithium_params  # noqa: E402


TITLE_PATTERN = re.compile(
    r"(?P<temperature>\d+)℃-(?P<p_rate>\d+\.\d+)P-(?P<direction>充电|放电)cell(?P<cell>\d+)"
)
RATE_ORDER = [0.125, 0.167, 0.334, 0.668]
COLORS = {
    0.125: "#1f77b4",
    0.167: "#2ca02c",
    0.334: "#ff7f0e",
    0.668: "#d62728",
}


def parse_experiment_workbook(path: Path) -> dict[tuple[int, str, float], list[pd.DataFrame]]:
    """Return experimental curves grouped by temperature, direction, and P-rate."""
    sheets = pd.read_excel(path, sheet_name=None, header=None, engine="openpyxl")
    grouped: dict[tuple[int, str, float], list[pd.DataFrame]] = {}
    for sheet in sheets.values():
        if sheet.shape[1] < 5:
            continue
        for start in range(0, sheet.shape[1], 6):
            title = sheet.iat[0, start] if start < sheet.shape[1] else None
            match = TITLE_PATTERN.fullmatch(str(title).strip()) if pd.notna(title) else None
            if not match:
                continue
            block = sheet.iloc[2:, start : start + 5].copy()  # noqa: E203
            block.columns = ["absolute_time", "capacity_ah", "energy_wh", "voltage_v", "current_a"]
            for column in ["capacity_ah", "energy_wh", "voltage_v", "current_a"]:
                block[column] = pd.to_numeric(block[column], errors="coerce")
            block = block.dropna(subset=["capacity_ah", "voltage_v", "current_a"]).reset_index(drop=True)
            block["capacity_ah"] = (block["capacity_ah"] - block["capacity_ah"].iloc[0]).abs()
            block["cell"] = int(match.group("cell"))
            temperature = int(match.group("temperature"))
            direction = match.group("direction")
            p_rate = float(match.group("p_rate"))
            grouped.setdefault((temperature, direction, p_rate), []).append(block)
    return grouped


def build_model() -> pybamm.BaseModel:
    """Build a DFN with explicit contact resistance and hysteretic OCP selection."""
    return pybamm.lithium_ion.DFN(
        {
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def run_case(
    temperature_c: int,
    direction: str,
    power_w: float,
    period_s: int,
) -> pd.DataFrame:
    """Run one constant-power case from the appropriate SOC endpoint."""
    temperature_k = temperature_c + 273.15
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(t_factor=1, temperature=temperature_k),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Ambient temperature [K]": temperature_k,
            "Initial temperature [K]": temperature_k,
        },
        check_already_exists=False,
    )

    if direction == "充电":
        step = f"Charge at {power_w:.6g} W until 3.65 V"
        initial_soc = 0.0
    else:
        step = f"Discharge at {power_w:.6g} W until 2.5 V"
        initial_soc = 1.0

    experiment = pybamm.Experiment([step], period=f"{period_s} seconds")
    solver = pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-8)
    simulation = pybamm.Simulation(
        build_model(),
        parameter_values=parameters,
        experiment=experiment,
        solver=solver,
        var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
    )
    solution = simulation.solve(initial_soc=initial_soc)

    capacity = np.asarray(solution["Discharge capacity [A.h]"].entries, dtype=float)
    capacity = np.abs(capacity - capacity[0])
    return pd.DataFrame(
        {
            "time_s": np.asarray(solution["Time [s]"].entries, dtype=float),
            "capacity_ah": capacity,
            "voltage_v": np.asarray(solution["Terminal voltage [V]"].entries, dtype=float),
            "current_a": np.asarray(solution["Current [A]"].entries, dtype=float),
            "power_w": np.abs(
                np.asarray(solution["Terminal voltage [V]"].entries, dtype=float)
                * np.asarray(solution["Current [A]"].entries, dtype=float)
            ),
        }
    )


def comparison_metrics(exp_curve: pd.DataFrame, sim_curve: pd.DataFrame) -> dict[str, float]:
    """Interpolate simulation voltage onto experimental capacity and calculate errors."""
    exp_capacity = exp_curve["capacity_ah"].to_numpy(dtype=float)
    exp_voltage = exp_curve["voltage_v"].to_numpy(dtype=float)
    sim_capacity = sim_curve["capacity_ah"].to_numpy(dtype=float)
    sim_voltage = sim_curve["voltage_v"].to_numpy(dtype=float)
    unique_capacity, unique_index = np.unique(sim_capacity, return_index=True)
    unique_voltage = sim_voltage[unique_index]
    overlap = (exp_capacity >= unique_capacity.min()) & (exp_capacity <= unique_capacity.max())
    aligned_exp = exp_voltage[overlap]
    aligned_sim = np.interp(exp_capacity[overlap], unique_capacity, unique_voltage)
    error = aligned_sim - aligned_exp
    rmse = float(np.sqrt(np.mean(error**2)))
    return {
        "n_overlap": int(overlap.sum()),
        "rmse_v": rmse,
        "rrmse_pct": float(rmse / np.mean(np.abs(aligned_exp)) * 100),
        "mae_v": float(np.mean(np.abs(error))),
        "max_abs_error_v": float(np.max(np.abs(error))),
    }


def save_temperature_figure(
    temperature_c: int,
    case_data: dict[tuple[int, str, float], tuple[list[pd.DataFrame], pd.DataFrame]],
    output_path: Path,
) -> None:
    rates = [rate for rate in RATE_ORDER if (temperature_c, "充电", rate) in case_data]
    fig, axes = plt.subplots(2, len(rates), figsize=(4.4 * len(rates), 7.2), squeeze=False)
    for row, direction in enumerate(["充电", "放电"]):
        for col, rate in enumerate(rates):
            ax = axes[row, col]
            if (temperature_c, direction, rate) not in case_data:
                ax.axis("off")
                continue
            exp_curves, sim_curve = case_data[(temperature_c, direction, rate)]
            color = COLORS[rate]
            for idx, exp_curve in enumerate(exp_curves, start=1):
                ax.plot(
                    exp_curve["capacity_ah"],
                    exp_curve["voltage_v"],
                    ls="--",
                    lw=1.1,
                    alpha=0.65,
                    color=color,
                    label=f"Exp cell{idx}",
                )
            ax.plot(
                sim_curve["capacity_ah"],
                sim_curve["voltage_v"],
                ls="-",
                lw=1.8,
                color="#111111",
                label="DFN Sim",
            )
            ax.set_title(f"{temperature_c}°C {rate:.3f}P {'Charge' if direction == '充电' else 'Discharge'}")
            ax.set_xlabel("Capacity [Ah]")
            ax.set_ylabel("Voltage [V]")
            ax.grid(alpha=0.2)
            ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--period-seconds", type=int, default=30)
    parser.add_argument("--temperatures", type=int, nargs="*")
    parser.add_argument("--rates", type=float, nargs="*")
    parser.add_argument("--max-cases", type=int)
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output or DEFAULT_RUN_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(output_dir / "run.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    grouped = parse_experiment_workbook(args.experiment)
    selected_keys = sorted(
        (
            key
            for key in grouped
            if (not args.temperatures or key[0] in args.temperatures)
            and (not args.rates or any(np.isclose(key[2], rate) for rate in args.rates))
        ),
        key=lambda key: (key[0], ["充电", "放电"].index(key[1]), RATE_ORDER.index(key[2])),
    )
    if args.max_cases:
        selected_keys = selected_keys[: args.max_cases]

    config = {
        "run_id": run_id,
        "pybamm_version": pybamm.__version__,
        "experiment_path": str(args.experiment),
        "contact_resistance_enabled": True,
        "contact_resistance_ohm": get_hithium_params(1, 298.15)["Contact resistance [Ohm]"],
        "period_seconds": args.period_seconds,
        "cases": [
            {"temperature_c": temp, "direction": direction, "p_rate": rate}
            for temp, direction, rate in selected_keys
        ],
    }
    (output_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metrics_rows = []
    curve_rows = []
    case_data = {}
    for case_index, key in enumerate(selected_keys, start=1):
        temperature_c, direction, p_rate = key
        exp_curves = grouped[key]
        power_w = float(
            np.mean(
                [
                    np.median(np.abs(curve["voltage_v"] * curve["current_a"]))
                    for curve in exp_curves
                ]
            )
        )
        logging.info(
            "[%d/%d] %d°C %.3fP %s, target %.3f W",
            case_index,
            len(selected_keys),
            temperature_c,
            p_rate,
            direction,
            power_w,
        )
        try:
            sim_curve = run_case(temperature_c, direction, power_w, args.period_seconds)
        except Exception as exc:
            logging.exception("Case failed: %s", key)
            metrics_rows.append(
                {
                    "temperature_c": temperature_c,
                    "direction": direction,
                    "p_rate": p_rate,
                    "power_w": power_w,
                    "cell": None,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            continue

        case_data[key] = (exp_curves, sim_curve)
        for idx, exp_curve in enumerate(exp_curves, start=1):
            metrics = comparison_metrics(exp_curve, sim_curve)
            metrics_rows.append(
                {
                    "temperature_c": temperature_c,
                    "direction": direction,
                    "p_rate": p_rate,
                    "power_w": power_w,
                    "cell": idx,
                    "status": "ok",
                    "exp_end_capacity_ah": float(exp_curve["capacity_ah"].iloc[-1]),
                    "sim_end_capacity_ah": float(sim_curve["capacity_ah"].iloc[-1]),
                    "end_capacity_error_pct": float(
                        (
                            sim_curve["capacity_ah"].iloc[-1]
                            - exp_curve["capacity_ah"].iloc[-1]
                        )
                        / exp_curve["capacity_ah"].iloc[-1]
                        * 100
                    ),
                    **metrics,
                }
            )
            for row in exp_curve.itertuples(index=False):
                curve_rows.append(
                    {
                        "temperature_c": temperature_c,
                        "direction": direction,
                        "p_rate": p_rate,
                        "series": f"exp_cell{idx}",
                        "capacity_ah": row.capacity_ah,
                        "voltage_v": row.voltage_v,
                        "current_a": row.current_a,
                        "power_w": abs(row.voltage_v * row.current_a),
                    }
                )
        for row in sim_curve.itertuples(index=False):
            curve_rows.append(
                {
                    "temperature_c": temperature_c,
                    "direction": direction,
                    "p_rate": p_rate,
                    "series": "dfn_sim",
                    "capacity_ah": row.capacity_ah,
                    "voltage_v": row.voltage_v,
                    "current_a": row.current_a,
                    "power_w": row.power_w,
                }
            )

    metrics_frame = pd.DataFrame(metrics_rows)
    successful = metrics_frame[metrics_frame["status"] == "ok"]
    if not successful.empty:
        numeric_columns = [
            "power_w",
            "exp_end_capacity_ah",
            "sim_end_capacity_ah",
            "end_capacity_error_pct",
            "n_overlap",
            "rmse_v",
            "rrmse_pct",
            "mae_v",
            "max_abs_error_v",
        ]
        mean_rows = (
            successful.groupby(["temperature_c", "direction", "p_rate"], as_index=False)[numeric_columns]
            .mean()
            .assign(cell="mean", status="ok", error="")
        )
        metrics_frame = pd.concat([metrics_frame, mean_rows], ignore_index=True, sort=False)
        metrics_frame = metrics_frame.sort_values(
            ["temperature_c", "direction", "p_rate", "cell"],
            key=lambda column: column.astype(str),
        )
    metrics_frame.to_csv(output_dir / "metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(curve_rows).to_csv(output_dir / "curves.csv", index=False, encoding="utf-8-sig")
    for temperature_c in sorted({key[0] for key in case_data}):
        save_temperature_figure(
            temperature_c,
            case_data,
            output_dir / f"cw501_{temperature_c}C_comparison.png",
        )

    failures = sum(row.get("status") == "failed" for row in metrics_rows)
    logging.info("Completed %d cases with %d failures. Output: %s", len(selected_keys), failures, output_dir)
    print(output_dir)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
